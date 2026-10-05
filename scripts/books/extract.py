# /// script
# requires-python = ">=3.12"
# dependencies = ["pymupdf>=1.24"]
# ///
"""Phase A of docs/PLAN-AI.md: read the books in Books/ into data/private/books/ (git-ignored, never uploaded).

    npm run books:extract                     # every book not extracted yet (OCR takes a while: about 15 minutes)
    npm run books:extract -- --force          # redo every book
    npm run books:extract -- --book diet-cheat-recipes --force
    npm run books:extract -- --report         # only rewrite data/private/books/REPORT.md

Needs Tesseract for the scanned books (Windows: `scoop install tesseract`). The Arabic and English language files
("best" models) are downloaded into tools/tessdata/ (git-ignored) the first time.

For each book, in data/private/books/<NN>-<slug>/:
  pages.jsonl   one line per PDF page: {"page", "label", "method": "text"|"ocr", "text", "headings", "ocr"}
                "page" is the PDF page number (what a PDF viewer shows, starting at 1), used for citations.
  tables.jsonl  one line per table, rows and columns kept: {"page", "index", "method", "bbox", "rows"}
  links.jsonl   every web link: {"page", "uri", "anchor", "bbox"} (exercise and recipe demo videos)
  images/       recipe pages: the cropped text that was OCR'd, to check numbers by eye against the OCR text
  meta.json     counts and per-page problems (used by REPORT.md)

How each page is read:
  - A page with a text layer: PyMuPDF's text (reading order). A page without text but with an image: OCR.
  - The Diet & Cheat FAQ has a text layer, but its Arabic letters are mapped wrongly by the PDF's font
    ("الربوتني" for "البروتين"), so every page is OCR'd; the broken text is kept as "text_layer" for comparison.
  - Arabic pages are OCR'd twice, Arabic-only and Arabic+English, and the run with the higher mean word confidence is
    kept ("alt_text" keeps the other): Arabic-only reads Arabic words better, Arabic+English reads English words
    ("InBody", "Mifflin", "100g") that Arabic-only turns into noise.
  - Recipe pages (one recipe per page, with a video link): the title and the steps box are OCR'd on their own, with the
    video thumbnail painted white, so the photo and icons don't add noise.
  - Tables: PyMuPDF's table finder (it uses the lines drawn in the PDF). For the FAQ, each cell found that way is
    cropped and OCR'd. Tables that are only pictures (in the scanned books) stay as page text.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import fnmatch
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOKS_DIR = ROOT / "Books"
OUT_DIR = ROOT / "data" / "private" / "books"
TESSDATA = ROOT / "tools" / "tessdata"
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{lang}.traineddata"

OCR_DPI = 300
MIN_TEXT_CHARS = 50       # fewer non-space characters than this in the text layer (and an image on the page) → OCR the page
EMPTY_OCR_CHARS = 20      # an OCR'd page with fewer characters than this is a photo or blank page
LOW_CONFIDENCE = 60       # mean word confidence (0-100) below this → listed as hard to read
LONGEST_TABLE_CELL = 400  # a "table" with a longer cell is a framed paragraph, not a table


@dataclasses.dataclass(frozen=True)
class Book:
    number: int      # the number in docs/PLAN-AI.md
    slug: str
    title: str
    pattern: str     # file name in Books/
    language: str    # "en" or "ar"
    mode: str        # "text": text layer, OCR only pages without one; "ocr": OCR every page
    domain: str      # training / nutrition / anatomy / recipes (used by the book search in Phase C)

    @property
    def folder(self) -> Path:
        return OUT_DIR / f"{self.number:02d}-{self.slug}"


BOOKS = [
    Book(1, "upper-lower", "Upper Lower Strength and Size Program (Jeff Nippard)",
         "Upper Lower Strength and Size Program*.pdf", "en", "text", "training"),
    Book(2, "body-recomposition", "The Ultimate Guide to Body Recomposition (Jeff Nippard, Chris Barakat)",
         "The Ultimate Guide To Body Recomposition*.pdf", "en", "text", "nutrition"),
    Book(3, "lpp", "Intermediate Advanced LPP Program (Jeff Nippard)",
         "Intermediate Advanced LPP Program*.pdf", "en", "text", "training"),
    Book(4, "fundamentals", "Fundamentals Hypertrophy Program (Jeff Nippard)",
         "Fundamentals Hypertrophy Program*.pdf", "en", "text", "training"),
    Book(5, "encyclopedia-of-foods", "Encyclopedia of Foods: A Guide to Healthy Nutrition (Dole, Mayo Clinic, UCLA)",
         "Encyclopedia of Foods*.pdf", "en", "text", "nutrition"),
    Book(6, "strength-training-anatomy", "Strength Training Anatomy, 2nd ed. (Frederic Delavier)",
         "Strength Training Anatomy*.pdf", "en", "ocr", "anatomy"),
    Book(7, "diet-cheat-recipes", "Diet & Cheat Book 1 (Arabic recipes)",
         "Diet & Cheat Book 1*.pdf", "ar", "ocr", "recipes"),
    Book(8, "diet-cheat-faq", "Diet & Cheat Nutrition FAQ (Arabic)",
         "Diet & Cheat Nutrition FAQ*.pdf", "ar", "ocr", "nutrition"),
]


# ---------------------------------------------------------------------------------------------------------------------
# Small pure helpers (tested in tests/backend/test_book_extract.py without PyMuPDF or Tesseract)

def parse_tsv(tsv: str) -> dict:
    """Tesseract's TSV output → {"words", "confidence" (mean, 0-100, None without words), "low_words" (< 60),
    "latin_words" (confident words of 3+ Latin letters: real English words, not noise)}."""
    confs = []
    latin = 0
    for line in tsv.splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 12 or cols[0] != "5" or not cols[11].strip():
            continue
        try:
            conf = float(cols[10])
        except ValueError:
            continue
        if conf >= 0:
            confs.append(conf)
            word = cols[11].strip()
            if conf >= 90 and sum(ch.isascii() and ch.isalpha() for ch in word) >= 3:
                latin += 1
    return {
        "words": len(confs),
        "confidence": round(statistics.fmean(confs), 1) if confs else None,
        "low_words": sum(1 for c in confs if c < LOW_CONFIDENCE),
        "latin_words": latin,
    }


def tsv_words(tsv: str, scale: float = 1.0) -> list[dict]:
    """Tesseract's TSV output → its words in reading order, each {"text", "conf", "box": [x0, y0, x1, y1]}.
    Boxes are in pixels divided by `scale` (pass dpi/72 to get PDF points)."""
    out = []
    for line in tsv.splitlines()[1:]:
        cols = line.split("	")
        if len(cols) < 12 or cols[0] != "5" or not cols[11].strip():
            continue
        try:
            left, top, width, height, conf = (float(v) for v in cols[6:11])
        except ValueError:
            continue
        out.append({"text": cols[11].strip(), "conf": conf,
                    "box": [left / scale, top / scale, (left + width) / scale, (top + height) / scale]})
    return out


def words_in_box(words: list[dict], box: list[float]) -> list[dict]:
    """The words whose centre lies inside the box, in reading order."""
    x0, y0, x1, y1 = box
    return [w for w in words
            if x0 <= (w["box"][0] + w["box"][2]) / 2 <= x1 and y0 <= (w["box"][1] + w["box"][3]) / 2 <= y1]


def pick_cell_text(by_lang: dict[str, list[dict]]) -> str:
    """One table cell's text from the Arabic-only and Arabic+English runs: Arabic-only, unless the other run has more
    confident words with Latin letters ("100g", "InBody"), which Arabic-only turns into digits or noise."""
    def latin(ws):
        return sum(1 for w in ws if w["conf"] >= 85 and any(ch.isascii() and ch.isalpha() for ch in w["text"]))
    ara, mixed = by_lang.get("ara"), by_lang.get("ara+eng")
    if ara is None or (mixed is not None and latin(mixed) > latin(ara)):
        ara = mixed or []
    return " ".join(w["text"] for w in ara)


def drop_empty(rows: list[list[str]]) -> list[list[str]]:
    """Without the columns and rows that are empty everywhere (decorative lines the table finder took for cells)."""
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    keep = [j for j in range(width) if any(j < len(r) and r[j] for r in rows)]
    return [[r[j] if j < len(r) else "" for j in keep] for r in rows]


def pick_best(runs: list[dict]) -> tuple[dict, list[dict]]:
    """Of the OCR runs of one image, the one to keep (and the others).

    Arabic pages: the Arabic-only run, unless the Arabic+English run found at least 2 more confident English words
    (then the page really has English on it). Mean confidence alone isn't enough: on a purely Arabic page the
    Arabic+English run can score higher while turning some Arabic words into Latin noise.
    """
    if len(runs) == 1:
        return runs[0], []
    by_lang = {r["lang"]: r for r in runs}
    if "ara" in by_lang and "ara+eng" in by_lang:
        ara, mixed = by_lang["ara"], by_lang["ara+eng"]
        chosen = mixed if mixed["latin_words"] - ara["latin_words"] >= 2 else ara
        return chosen, [r for r in runs if r is not chosen]
    ranked = sorted(runs, key=lambda r: (r["confidence"] or 0, r["words"]), reverse=True)
    return ranked[0], ranked[1:]


def clean_rows(rows: list[list]) -> list[list[str]]:
    """Table rows with None → "" and surrounding spaces removed."""
    return [[(c or "").strip() for c in row] for row in rows]


def is_real_table(rows: list[list[str]]) -> bool:
    """At least two rows and two columns with content, and no paragraph-sized cell."""
    if len(rows) < 2:
        return False
    if any(len(c) > LONGEST_TABLE_CELL for row in rows for c in row):
        return False
    width = max(len(r) for r in rows)
    filled_cols = sum(1 for j in range(width) if sum(1 for r in rows if j < len(r) and r[j]) >= 2)
    filled_rows = sum(1 for r in rows if sum(1 for c in r if c) >= 2)
    return filled_cols >= 2 and filled_rows >= 2


def headings_from_lines(lines: list[tuple[float, str]]) -> list[str]:
    """Lines (font size, text) whose size is at least 1.3 × the page's most common size: the page's headings."""
    sized = [(s, t.strip()) for s, t in lines if t.strip()]
    if not sized:
        return []
    body = statistics.mode(round(s) for s, _ in sized)
    out = []
    for s, t in sized:
        if s >= body * 1.3 and len(t) <= 120 and t not in out:
            out.append(t)
    return out


def nutrient_boxes(lines: list[tuple[float, float, float, float, float, str]]) -> list[dict]:
    """The Encyclopedia of Foods' "Nutrient Content" boxes on one page, from the page's text lines
    (x0, y0, x1, y1, font size, text):
    [{"servings": ["4 spears, raw (64 g)", "6 spears, cooked (1/2 cup) (72 g)"],
      "rows": [["Energy (kilocalories)", "14", "22"], ["Minerals (mg)", "", ""], …]}].

    A box is the lines under a "Nutrient Content" heading, within the heading's width, until a gap of more than 30
    points. Lines at the same height form one row: a label, then one value per column (a label alone is a section,
    like "Minerals (mg)"). The value columns are the ones of the "Energy" row. A one-column box has its serving in a
    bubble above the heading ("SERVING SIZE: 5, dried (42 g)"); a box with several columns has one serving per
    column, written above the "Energy" row.
    """
    lines = [(x0, y0, x1, y1, size, t.strip()) for x0, y0, x1, y1, size, t in lines if t.strip()]
    heads = sorted((l for l in lines if l[5].lower() == "nutrient content"), key=lambda l: l[1])
    boxes = []
    for k, (hx0, _, hx1, hy1, _, _) in enumerate(heads):
        for widen in (12, 260):  # a wide box (the berries, 7 columns) has its labels left of the heading
            box = _nutrient_box(lines, hx0 - widen, hx1 + widen, hy1, heads[k + 1][1] if k + 1 < len(heads) else None)
            if box:
                boxes.append(box)
                break
    return boxes


def _nutrient_box(lines, left, right, hy1, limit) -> dict | None:
    labels_only = ("SERVING", "SIZE:", "SERVING SIZE:")
    limit = float("inf") if limit is None else limit
    inside = sorted((l for l in lines if left <= l[0] <= right and hy1 - 1 <= l[1] < limit
                     and l[5].lower() != "nutrient content"), key=lambda l: (l[1], l[0]))
    rows: list[list[tuple]] = []
    last_y, row_y = hy1, None
    for line in inside:
        if line[1] - last_y > 30:
            break
        centre = (line[1] + line[3]) / 2
        if row_y is not None and abs(centre - row_y) <= 3:
            rows[-1].append(line)
        else:
            rows.append([line])
            row_y = centre
        last_y = line[3]
    rows = [sorted(r, key=lambda l: l[0]) for r in rows]
    first = next((i for i, r in enumerate(rows) if r[0][5].lower().startswith("energy")), None)
    if first is None:
        return None
    header, body = rows[:first], rows[first:]
    centres = [(l[0] + l[2]) / 2 for l in body[0][1:]] or [right - 20]

    def column(line):
        mid = (line[0] + line[2]) / 2
        return min(range(len(centres)), key=lambda j: abs(centres[j] - mid))

    out_rows = []
    for r in body:
        cells = [""] * len(centres)
        for line in r[1:]:
            j = column(line)
            cells[j] = f"{cells[j]} {line[5]}".strip()
        out_rows.append([r[0][5], *cells])

    servings = [""] * len(centres)
    for r in header:
        for line in r:
            j = column(line)
            # "Black-" + "berry" → "Blackberry" (a word broken over two lines)
            joined = f"{servings[j][:-1]}{line[5]}" if servings[j].endswith("-") else f"{servings[j]} {line[5]}"
            servings[j] = joined.strip()
    if len(centres) == 1 and not servings[0]:
        # The bubble: from the "SERVING" label down to the heading, right of the label's left edge.
        marks = [l for l in lines if l[5].upper() in ("SERVING", "SERVING SIZE:")
                 and left - 30 <= l[0] <= right and hy1 - 90 <= l[1] < hy1]
        if marks:
            lab = max(marks, key=lambda l: l[1])
            parts = sorted((l for l in lines if l[1] >= lab[1] - 2 and l[3] <= hy1 - 8 and l[0] >= lab[0] - 25
                            and l[0] <= right and l[5].upper() not in labels_only), key=lambda l: (l[1], l[0]))
            servings[0] = " ".join(l[5] for l in parts)
    return {"servings": [x.removeprefix("SIZE:").strip() for x in servings], "rows": out_rows}


def food_title(spans: list[tuple[float, str]]) -> str | None:
    """The Encyclopedia of Foods' page title from its text spans (font size, text), in reading order: the big ones
    (36 pt and up). The first letter is a separate, bigger span ("B" + "erries" → "Berries")."""
    big = [t.strip() for size, t in spans if size >= 30 and t.strip()]
    if not big:
        return None
    words, i = [], 0
    while i < len(big):
        if len(big[i]) == 1 and i + 1 < len(big):
            words.append(big[i] + big[i + 1].lower() if big[i + 1].isupper() else big[i] + big[i + 1])
            i += 2
        else:
            words.append(big[i])
            i += 1
    return " ".join(words)


def page_problem(method: str, chars: int, confidence: float | None) -> str | None:
    """Why a page counts as hard to read, or None."""
    if method != "ocr":
        return None
    if chars < EMPTY_OCR_CHARS:
        return "no text found (photo or blank page)"
    if confidence is not None and confidence < LOW_CONFIDENCE:
        return f"low OCR confidence ({confidence:.0f}/100)"
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Tesseract

def tesseract_exe() -> str:
    exe = shutil.which("tesseract")
    if not exe:
        sys.exit("Tesseract is not installed. On Windows: scoop install tesseract  (then run this again)")
    return exe


def ensure_tessdata(langs=("ara", "eng", "osd")) -> None:
    TESSDATA.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        f = TESSDATA / f"{lang}.traineddata"
        if not f.exists():
            print(f"Downloading the {lang} OCR model …")
            urllib.request.urlretrieve(TESSDATA_URL.format(lang=lang), f)


def run_ocr(exe: str, image: Path, lang: str, psm: int) -> dict:
    out = image.with_name(f"{image.stem}.{lang.replace('+', '_')}.{psm}")
    env = dict(os.environ, TESSDATA_PREFIX=str(TESSDATA), OMP_THREAD_LIMIT="1")
    subprocess.run([exe, str(image), str(out), "-l", lang, "--psm", str(psm),
                    "-c", "tessedit_create_txt=1", "-c", "tessedit_create_tsv=1"],
                   env=env, check=True, capture_output=True)
    text = out.with_suffix(out.suffix + ".txt").read_text(encoding="utf-8")
    tsv = out.with_suffix(out.suffix + ".tsv").read_text(encoding="utf-8")
    return {"lang": lang, "psm": psm, "text": _tidy(text), **parse_tsv(tsv),
            "_words": tsv_words(tsv, OCR_DPI / 72)}


def _tidy(text: str) -> str:
    # Tesseract marks direction changes with invisible LRM/RLM characters; drop them and empty lines.
    text = text.replace("‎", "").replace("‏", "").replace("\x0c", "")
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip())


def ocr_langs(book: Book) -> list[str]:
    return ["ara", "ara+eng"] if book.language == "ar" else ["eng"]


# ---------------------------------------------------------------------------------------------------------------------
# Extraction

def find_pdf(book: Book) -> Path:
    for f in sorted(BOOKS_DIR.glob("*.pdf")):
        if fnmatch.fnmatch(f.name, book.pattern):
            return f
    raise FileNotFoundError(f"No file matching {book.pattern!r} in {BOOKS_DIR}")


def _headings(page) -> list[str]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if spans:
                lines.append((max(s["size"] for s in spans), "".join(s["text"] for s in spans)))
    return headings_from_lines(lines)


def _links(page) -> list[dict]:
    out = []
    for link in page.get_links():
        uri = link.get("uri")
        if not uri:
            continue
        r = link["from"]
        anchor = " ".join(page.get_textbox(r + (-1, -1, 1, 1)).split())
        out.append({"page": page.number + 1, "uri": uri, "anchor": anchor, "kind": "link",
                    "bbox": [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)]})
    return out


def printed_urls(page_number: int, text: str, known: set[str]) -> list[dict]:
    """Web addresses written in the text but not clickable (the Fundamentals program prints its video links)."""
    out = []
    for m in re.finditer(r"https?://[^\s<>\"')]+", text):
        uri = m.group(0).rstrip(".,;")
        if uri not in known:
            known.add(uri)
            line = text[text.rfind("\n", 0, m.start()) + 1:m.start()].strip()
            if not line:  # "BACK SQUAT:" on the line above the address
                before = [x.strip() for x in text[:m.start()].splitlines() if x.strip()]
                line = before[-1] if before else ""
            out.append({"page": page_number, "uri": uri, "anchor": line, "kind": "printed", "bbox": None})
    return out


def _is_recipe_page(book: Book, page) -> bool:
    return book.slug == "diet-cheat-recipes" and 4 <= page.number + 1 <= 40 and any(
        "youtube" in (l.get("uri") or "") for l in page.get_links())


def _render(page, path: Path, clip=None, whiteout=()) -> Path:
    import pymupdf
    pix = page.get_pixmap(dpi=OCR_DPI, clip=clip, colorspace=pymupdf.csGRAY)
    if whiteout:
        scale = OCR_DPI / 72
        origin = clip.tl if clip is not None else pymupdf.Point(0, 0)
        for r in whiteout:
            ir = pymupdf.IRect(int((r.x0 - origin.x) * scale), int((r.y0 - origin.y) * scale),
                               int((r.x1 - origin.x) * scale) + 1, int((r.y1 - origin.y) * scale) + 1)
            pix.set_rect(ir & pix.irect, (255,))
    pix.save(path)
    return path


def extract_book(book: Book, exe: str | None, workers: int) -> dict:
    import pymupdf

    pdf = find_pdf(book)
    doc = pymupdf.open(pdf)
    folder = book.folder
    if folder.exists():
        shutil.rmtree(folder)
    (folder / "images").mkdir(parents=True)
    print(f"[{book.number}] {book.title}: {len(doc)} pages")

    pages: list[dict] = []
    tables: list[dict] = []
    food = None  # the Encyclopedia's current food (its title can be on an earlier page)
    links: list[dict] = []
    jobs: list[tuple[str, Path, str, int]] = []  # (key, image, lang, psm)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for page in doc:
            n = page.number + 1
            page_links = _links(page)
            layer = page.get_text("text").strip()  # PDF order keeps each column whole; "sort" mixes columns
            links += page_links + printed_urls(n, layer, {l["uri"] for l in page_links})
            rec = {"page": n, "label": page.get_label() or None, "method": "text", "text": layer,
                   "headings": [], "ocr": None}
            if book.mode == "text" and len("".join(layer.split())) >= MIN_TEXT_CHARS:
                rec["headings"] = _headings(page)
            elif book.mode == "text" and not page.get_images():
                pass  # a (nearly) blank page: keep what little text it has
            else:
                rec["method"] = "ocr"
                if layer:
                    rec["text_layer"] = layer  # FAQ: the broken text layer, kept for comparison
                if _is_recipe_page(book, page):
                    w, h = page.rect.width, page.rect.height
                    thumbs = [l["from"] + (-4, -30, 4, 4) for l in page.get_links() if l.get("uri")]  # + "فيديو"
                    title_clip = pymupdf.Rect(w * 0.22, h * 0.045, w * 0.78, h * 0.112)
                    body_clip = pymupdf.Rect(w * 0.05, h * 0.112, w * 0.94, h * 0.63)
                    _render(page, tmp / f"p{n:04d}-title.png", title_clip)
                    body = _render(page, tmp / f"p{n:04d}-body.png", body_clip, thumbs)
                    shutil.copy(body, folder / "images" / f"recipe-p{n:03d}.png")
                    rec["image"] = f"images/recipe-p{n:03d}.png"
                    for lang in ocr_langs(book):
                        jobs.append((f"{n}:title", tmp / f"p{n:04d}-title.png", lang, 7))
                        jobs.append((f"{n}:body", tmp / f"p{n:04d}-body.png", lang, 4))
                else:
                    _render(page, tmp / f"p{n:04d}.png")
                    for lang in ocr_langs(book):
                        jobs.append((f"{n}:page", tmp / f"p{n:04d}.png", lang, 3))
            pages.append(rec)

            # The Encyclopedia of Foods: one "Nutrient Content" box per food, without lines between the columns.
            if book.slug == "encyclopedia-of-foods":
                spans = [sp for b in page.get_text("dict")["blocks"] for ln in b.get("lines", [])
                         for sp in ln["spans"] if sp["text"].strip()]
                title = food_title([(sp["size"], sp["text"]) for sp in spans])
                food = title or food
            if book.slug == "encyclopedia-of-foods" and "nutrient content" in layer.lower():
                lines = [(*ln["bbox"], max(sp["size"] for sp in ln["spans"]), "".join(sp["text"] for sp in ln["spans"]))
                         for b in page.get_text("dict")["blocks"] for ln in b.get("lines", []) if ln["spans"]]
                for box in nutrient_boxes(lines):
                    if len(box["rows"]) >= 3:
                        tables.append({"page": n, "index": len([t for t in tables if t["page"] == n]),
                                       "method": "nutrient-box", "food": food, "servings": box["servings"],
                                       "bbox": None, "rows": box["rows"]})

            # Tables drawn with lines in the PDF.
            if page.get_drawings():
                try:
                    found = page.find_tables().tables
                except Exception:  # the table finder gives up on some odd pages; the text is still there
                    found = []
                for i, t in enumerate(found):
                    rows = drop_empty(clean_rows(t.extract()))
                    entry = {"page": n, "index": i, "method": "text", "bbox": [round(v, 1) for v in t.bbox],
                             "rows": rows}
                    if book.slug == "diet-cheat-faq":
                        entry["method"] = "ocr-words"
                        entry["text_layer_rows"] = rows
                        entry["cell_boxes"] = [[r, c, list(cell)] for r, row in enumerate(t.rows)
                                               for c, cell in enumerate(row.cells) if cell is not None]
                        tables.append(entry)
                    elif is_real_table(rows):
                        tables.append(entry)

        # OCR, in parallel (each Tesseract on one core).
        results: dict[str, list[dict]] = {}
        if jobs:
            if exe is None:
                exe = tesseract_exe()
            print(f"    OCR: {len(jobs)} runs on {workers} cores …", flush=True)
            with concurrent.futures.ThreadPoolExecutor(workers) as pool:
                futures = {pool.submit(run_ocr, exe, img, lang, psm): key for key, img, lang, psm in jobs}
                for k, fut in enumerate(concurrent.futures.as_completed(futures), 1):
                    results.setdefault(futures[fut], []).append(fut.result())
                    if k % 50 == 0:
                        print(f"    {k}/{len(jobs)}", flush=True)

    def best(key: str) -> tuple[dict, list[dict]]:
        return pick_best(results[key])

    for rec in pages:
        if rec["method"] != "ocr":
            continue
        n = rec["page"]
        if f"{n}:body" in results:
            (t, _), (b, b_alt) = best(f"{n}:title"), best(f"{n}:body")
            rec["text"] = f"{t['text']}\n{b['text']}".strip()
            rec["headings"] = [t["text"]] if t["text"] else []
            rec["ocr"] = {"title": _ocr_info(t), "body": _ocr_info(b)}
            rec["alt_text"] = b_alt[0]["text"] if b_alt else None
            conf = b["confidence"]
        else:
            p, alt = best(f"{n}:page")
            rec["text"] = p["text"]
            rec["ocr"] = _ocr_info(p)
            rec["alt_text"] = alt[0]["text"] if alt else None
            conf = p["confidence"]
        if rec["alt_text"] is None:
            rec.pop("alt_text")
        rec["problem"] = page_problem("ocr", len(rec["text"]), conf)

    for entry in tables:
        if entry["method"] != "ocr-words":
            continue
        runs = {r["lang"]: r["_words"] for r in results[f"{entry['page']}:page"]}
        rows = [["" for _ in r] for r in entry["text_layer_rows"]]
        confs = []
        for r, c, box in entry.pop("cell_boxes"):
            rows[r][c] = pick_cell_text({lang: words_in_box(ws, box) for lang, ws in runs.items()})
            confs += [w["conf"] for w in words_in_box(runs.get("ara", []), box)]
        entry["rows"] = drop_empty(rows)
        entry["ocr_confidence"] = round(statistics.fmean(confs), 1) if confs else None
    tables[:] = [t for t in tables if t["method"] != "ocr-words" or len(t["rows"]) >= 2]

    _write_jsonl(folder / "pages.jsonl", pages)
    _write_jsonl(folder / "tables.jsonl", tables)
    _write_jsonl(folder / "links.jsonl", links)
    meta = {
        "number": book.number, "slug": book.slug, "title": book.title, "file": pdf.name,
        "language": book.language, "domain": book.domain, "pages": len(doc),
        "text_pages": sum(1 for p in pages if p["method"] == "text"),
        "ocr_pages": sum(1 for p in pages if p["method"] == "ocr"),
        "ocr_confidence": _mean([p["ocr"]["body"]["confidence"] if "body" in (p["ocr"] or {}) else
                                 (p["ocr"] or {}).get("confidence") for p in pages if p["method"] == "ocr"]),
        "tables": len(tables), "table_pages": sorted({t["page"] for t in tables}),
        "links": len(links), "video_links": sum(1 for l in links if "youtu" in l["uri"]),
        "problems": {p["page"]: p["problem"] for p in pages if p.get("problem")},
        "empty_text_pages": [p["page"] for p in pages if p["method"] == "text" and len(p["text"]) < EMPTY_OCR_CHARS],
        "ocr_runs": len(jobs),
    }
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if not any((folder / "images").iterdir()):
        (folder / "images").rmdir()
    print(f"    done: {meta['text_pages']} text pages, {meta['ocr_pages']} OCR pages, {meta['tables']} tables, "
          f"{meta['links']} links, {len(meta['problems'])} pages hard to read")
    return meta


def _ocr_info(run: dict) -> dict:
    return {k: run[k] for k in ("lang", "psm", "confidence", "words", "low_words", "latin_words")}


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 1) if values else None


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------------------------------------------------
# Report

def _ranges(pages: list[int]) -> str:
    out, start, prev = [], None, None
    for p in sorted(pages):
        if start is None:
            start = prev = p
        elif p == prev + 1:
            prev = p
        else:
            out.append(f"{start}" if start == prev else f"{start}–{prev}")
            start = prev = p
    if start is not None:
        out.append(f"{start}" if start == prev else f"{start}–{prev}")
    return ", ".join(out) or "none"


def write_report() -> Path:
    lines = ["# Books: what was extracted (Phase A)", "",
             "Made by `npm run books:extract`. Private: this folder is git-ignored. Page numbers are PDF pages.", "",
             "| # | Book | Pages | Read as | OCR mean confidence | Tables | Links (videos) | Hard to read |",
             "|---|---|---|---|---|---|---|---|"]
    details = []
    for book in BOOKS:
        meta_file = book.folder / "meta.json"
        if not meta_file.exists():
            lines.append(f"| {book.number} | {book.title} | – | not extracted yet | | | | |")
            continue
        m = json.loads(meta_file.read_text(encoding="utf-8"))
        read_as = ("text layer" if m["ocr_pages"] == 0 else "OCR" if m["text_pages"] == 0
                   else f"text layer; OCR on {m['ocr_pages']} image-only pages")
        conf = f"{m['ocr_confidence']:.0f}/100" if m["ocr_confidence"] is not None else "–"
        lines.append(f"| {m['number']} | {m['title']} | {m['pages']} | {read_as} | {conf} | {m['tables']} "
                     f"| {m['links']} ({m['video_links']}) | {len(m['problems'])} |")
        details += [f"## {m['number']}. {m['title']}", "",
                    f"- File: `{m['file']}`",
                    f"- Tables on pages: {_ranges(m['table_pages'])}"]
        if m["empty_text_pages"]:
            details.append(f"- Text pages with (almost) no text: {_ranges(m['empty_text_pages'])}")
        by_problem: dict[str, list[int]] = {}
        for page, problem in m["problems"].items():
            key = problem.split(" (")[0]
            by_problem.setdefault(key, []).append(int(page))
        for problem, pages in sorted(by_problem.items()):
            details.append(f"- {problem}: pages {_ranges(pages)}")
        details.append("")
    path = OUT_DIR / "REPORT.md"
    path.write_text("\n".join(lines + [""] + details), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--book", action="append", choices=[b.slug for b in BOOKS], help="only this book (repeatable)")
    ap.add_argument("--force", action="store_true", help="extract again even if already done")
    ap.add_argument("--report", action="store_true", help="only rewrite REPORT.md")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = ap.parse_args(argv)

    if not args.report:
        # data/private/ must be git-ignored before anything is written there.
        check = subprocess.run(["git", "check-ignore", "-q", str(OUT_DIR / "pages.jsonl")], cwd=ROOT)
        if check.returncode != 0:
            sys.exit("data/private/ is not git-ignored: add it to .gitignore first.")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for book in BOOKS:
            if args.book and book.slug not in args.book:
                continue
            if (book.folder / "meta.json").exists() and not args.force:
                print(f"[{book.number}] {book.title}: already extracted (use --force to redo)")
                continue
            ensure_tessdata()
            extract_book(book, None, args.workers)
    print(f"Report: {write_report()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
