"""scripts/books/extract.py (Phase A of docs/PLAN-AI.md): the extracted book text stays private, and the helpers that
turn PDF lines and OCR output into pages and tables work. Needs no books, PyMuPDF or Tesseract."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("book_extract", ROOT / "scripts" / "books" / "extract.py")
ex = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ex  # its dataclass looks itself up there
spec.loader.exec_module(ex)


# --- Privacy ---------------------------------------------------------------------------------------------------------

def _git(*args):
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


@pytest.mark.parametrize("path", [
    "data/private/books/07-diet-cheat-recipes/pages.jsonl",
    "data/private/books/07-diet-cheat-recipes/images/recipe-p010.png",
    "data/private/books/REPORT.md",
    "Books/Some book.pdf",
    "books/Some book.pdf",
    "anything.pdf",
    "tools/tessdata/ara.traineddata",
])
def test_book_text_books_and_ocr_models_are_git_ignored(path):
    assert _git("check-ignore", "-q", path).returncode == 0, f"{path} is not git-ignored"


def test_nothing_private_is_tracked():
    tracked = _git("ls-files").stdout.splitlines()
    assert not [f for f in tracked if f.startswith(("data/private/", "Books/", "books/")) or f.lower().endswith(".pdf")]


def test_the_extractor_writes_only_inside_data_private():
    assert ex.OUT_DIR == ROOT / "data" / "private" / "books"
    for book in ex.BOOKS:
        assert ex.OUT_DIR in book.folder.parents


def test_every_book_in_the_plan_is_listed_once():
    assert [b.number for b in ex.BOOKS] == list(range(1, 9))
    assert len({b.slug for b in ex.BOOKS}) == 8
    assert {b.domain for b in ex.BOOKS} == {"training", "nutrition", "anatomy", "recipes"}


# --- OCR output ------------------------------------------------------------------------------------------------------

TSV = "\n".join([
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
    "1\t1\t0\t0\t0\t0\t0\t0\t600\t300\t-1\t",
    "5\t1\t1\t1\t1\t1\t300\t30\t60\t30\t96.5\tMifflin",
    "5\t1\t1\t1\t1\t2\t200\t30\t60\t30\t40\tالبروتين",
    "5\t1\t1\t1\t1\t3\t100\t30\t60\t30\t91\tok",
    "5\t1\t1\t1\t1\t4\t10\t30\t60\t30\t-1\t ",
])


def test_tsv_gives_confidence_low_words_and_real_english_words():
    stats = ex.parse_tsv(TSV)
    assert stats == {"words": 3, "confidence": 75.8, "low_words": 1, "latin_words": 1}  # "ok" is too short
    assert ex.parse_tsv("level\tconf\n") == {"words": 0, "confidence": None, "low_words": 0, "latin_words": 0}


def test_tsv_words_keep_reading_order_and_boxes_in_pdf_points():
    words = ex.tsv_words(TSV, scale=300 / 72)
    assert [w["text"] for w in words] == ["Mifflin", "البروتين", "ok"]
    assert words[0]["box"] == pytest.approx([72, 7.2, 86.4, 14.4])
    assert [w["text"] for w in ex.words_in_box(words, [40, 0, 90, 20])] == ["Mifflin", "البروتين"]  # centres inside
    assert [w["text"] for w in ex.words_in_box(words, [0, 0, 200, 20])] == ["Mifflin", "البروتين", "ok"]


def run(lang, conf, latin, text="t"):
    return {"lang": lang, "confidence": conf, "words": 10, "latin_words": latin, "text": text}


def test_arabic_pages_keep_the_arabic_only_run_unless_the_other_finds_english():
    ara, mixed = run("ara", 80, 0), run("ara+eng", 90, 1)  # higher confidence, but no real English: Latin noise
    assert ex.pick_best([mixed, ara]) == (ara, [mixed])
    ara, mixed = run("ara", 85, 0), run("ara+eng", 80, 4)  # "Total calories: 203Cal"
    assert ex.pick_best([ara, mixed]) == (mixed, [ara])
    one = run("eng", 70, 9)
    assert ex.pick_best([one]) == (one, [])


def test_a_table_cell_switches_to_arabic_and_english_for_100g():
    w = lambda text, conf=95: {"text": text, "conf": conf, "box": [0, 0, 1, 1]}  # noqa: E731
    assert ex.pick_cell_text({"ara": [w("سمك"), w("1008")], "ara+eng": [w("سمك"), w("100g")]}) == "سمك 100g"
    assert ex.pick_cell_text({"ara": [w("سمك")], "ara+eng": [w("ald", 50)]}) == "سمك"


def test_ocr_text_loses_direction_marks_and_empty_lines():
    assert ex._tidy("‏ضع ٢‎\n\n  \nملعقة\x0c") == "ضع ٢\nملعقة"


def test_hard_to_read_pages():
    assert ex.page_problem("text", 0, None) is None
    assert ex.page_problem("ocr", 5, 90) == "no text found (photo or blank page)"
    assert ex.page_problem("ocr", 500, 41.4) == "low OCR confidence (41/100)"
    assert ex.page_problem("ocr", 500, 85) is None


# --- Tables, headings, links -----------------------------------------------------------------------------------------

def test_tables_drop_empty_columns_and_reject_framed_paragraphs():
    assert ex.drop_empty([["a", "", "b"], ["", "", ""], ["c", "", "d"]]) == [["a", "b"], ["c", "d"]]
    assert ex.drop_empty([["", ""]]) == []
    assert ex.is_real_table([["EXERCISE", "SETS"], ["BACK SQUAT", "3"]])
    assert not ex.is_real_table([["Preface " * 100, ""], ["", ""]])
    assert not ex.is_real_table([["only", "one row"]])
    assert ex.clean_rows([[" a ", None]]) == [["a", ""]]


def test_headings_are_lines_much_bigger_than_the_body_text():
    lines = [(10, "body"), (10, "more body"), (10.2, "body"), (24, "PROGRESSIVE OVERLOAD"), (13, "minor")]
    assert ex.headings_from_lines(lines) == ["PROGRESSIVE OVERLOAD", "minor"]
    assert ex.headings_from_lines([]) == []


def test_printed_web_addresses_take_the_exercise_name_above_them():
    text = "EXERCISE VIDEOS\n\nBACK SQUAT:\nhttps://www.youtube.com/watch?v=abc\n\nSee https://x.org/a.\n"
    found = ex.printed_urls(88, text, {"https://already.clickable"})
    assert [(f["anchor"], f["uri"]) for f in found] == [
        ("BACK SQUAT:", "https://www.youtube.com/watch?v=abc"), ("See", "https://x.org/a")]
    assert all(f["kind"] == "printed" and f["page"] == 88 for f in found)
    assert ex.printed_urls(1, "https://www.youtube.com/watch?v=abc", {"https://www.youtube.com/watch?v=abc"}) == []


# --- The Encyclopedia of Foods' "Nutrient Content" boxes -------------------------------------------------------------

def L(x0, y0, text, w=40, size=8):  # noqa: N802 - a PDF text line
    return (x0, y0, x0 + w, y0 + 8, size, text)


def test_a_one_column_box_with_its_serving_bubble():
    lines = [
        L(48, 300, "Body text in the left column"),
        L(475, 412, "SERVING"), L(482, 420, "SIZE:"), L(501, 429, "5, dried (42 g)", size=9),
        L(426, 444, "Nutrient Content", w=153, size=12),
        L(426, 472, "Energy (kilocalories)"), L(534, 472, "114", w=13),
        L(426, 483, "Water (%)"), L(539, 483, "22", w=8),
        L(426, 494, "Minerals (mg)"),
        L(435, 505, "Calcium"), L(539, 505, "13", w=8),
        L(435, 700, "far below: another part of the page"),
    ]
    assert ex.nutrient_boxes(lines) == [{
        "servings": ["5, dried (42 g)"],
        "rows": [["Energy (kilocalories)", "114"], ["Water (%)", "22"], ["Minerals (mg)", ""], ["Calcium", "13"]],
    }]


def test_a_two_column_box_has_one_serving_per_column():
    lines = [
        L(427, 402, "Nutrient Content", w=152, size=12),
        L(530, 420, "4 spears,", w=30), L(560, 420, "6 spears,", w=30),
        L(530, 428, "raw (64 g)", w=30), L(560, 428, "cooked (72 g)", w=30),
        L(427, 445, "Energy (kilocalories)"), L(538, 445, "14", w=8), L(570, 445, "22", w=8),
        L(427, 456, "Fat (grams)"), L(540, 456, "0", w=4), L(572, 456, "0", w=4),
    ]
    assert ex.nutrient_boxes(lines) == [{
        "servings": ["4 spears, raw (64 g)", "6 spears, cooked (72 g)"],
        "rows": [["Energy (kilocalories)", "14", "22"], ["Fat (grams)", "0", "0"]],
    }]


def test_a_wide_box_with_labels_left_of_the_heading():
    lines = [
        L(300, 160, "Nutrient Content", w=120, size=12),
        L(271, 186, "Black-", w=20), L(330, 186, "Straw-", w=20),
        L(272, 195, "berry", w=20), L(331, 195, "berry", w=20),
        L(120, 217, "Energy (kilocalories)"), L(278, 217, "37", w=9), L(337, 217, "22", w=9),
    ]
    assert ex.nutrient_boxes(lines) == [{
        "servings": ["Blackberry", "Strawberry"], "rows": [["Energy (kilocalories)", "37", "22"]]}]


def test_no_box_without_an_energy_row():
    assert ex.nutrient_boxes([L(400, 100, "Nutrient Content", w=150), L(400, 120, "Some words", w=80)]) == []


def test_the_food_title_glues_the_drop_cap_back_on():
    assert ex.food_title([(48, "B"), (36, "ERRIES"), (18, "C"), (14, "ranberry")]) == "Berries"
    assert ex.food_title([(48, "D"), (36, "ate"), (10, "body")]) == "Date"
    assert ex.food_title([(48, "Passion Fruit")]) == "Passion Fruit"
    assert ex.food_title([(10, "no title here")]) is None
