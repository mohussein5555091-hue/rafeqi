# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6"]
# ///
"""Phase B2 of docs/PLAN-AI.md: the three Jeff Nippard programs, from the tables extracted in Phase A, into
data/programs/*.json (what the plan engine reads). Runs on your PC (it needs data/private/books/, which is never
committed):

    npm run books:programs            # writes data/programs/<id>.json for every program
    npm run books:programs -- --check # only reports names that aren't mapped to an exercise yet
    npm run books:programs -- --only fundamentals_full_body --only lpp_legs_push_pull

Only numbers are taken from the tables: sets, reps, effort (RPE) or %1RM, and rest. The books' coaching notes are not
copied: each exercise's how-to (in our own words) lives in data/catalogue/exercises.yaml.

data/programs/exercise_names.yaml maps every exercise name the books use to a catalogue id, with an optional technique
("tempo", "21s"…) for names that are a way of doing a catalogue exercise rather than a different exercise.
data/programs/program_meta.yaml gives each program its name, who it's for, its days and rotation, and its deload weeks
(everything that isn't a table).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BOOKS = ROOT / "data" / "private" / "books"
OUT = ROOT / "data" / "programs"
NAMES = OUT / "exercise_names.yaml"
META = OUT / "program_meta.yaml"

SOURCES = {"fundamentals": "04-fundamentals", "lpp": "03-lpp", "upper-lower": "01-upper-lower"}
DAYS = {"fundamentals_full_body": 3, "fundamentals_upper_lower": 4, "fundamentals_body_part": 5,
        "lpp_legs_push_pull": 6, "upper_lower_size_strength": 6}  # sessions in a week of each program


# ── Small pure helpers (tested in tests/backend/test_book_programs.py) ───────────────────────────────────────────────

def clean_name(raw: str) -> tuple[str, str | None]:
    """'A1: LEG EXTENSION' → ('LEG EXTENSION', 'A'): a superset's letter, and the name with spaces tidied."""
    name = " ".join(raw.split())
    m = re.match(r"^([A-Z])\d\s*:\s*(.+)$", name)
    return (m.group(2).strip(), m.group(1)) if m else (name, None)


def parse_sets(raw: str) -> int | None:
    m = re.search(r"\d+", raw or "")
    return int(m.group()) if m else None


def parse_reps(raw: str) -> str:
    """The rep target as the app shows it: '10-12' → '10–12', '20 EACH LEG' → '20 each leg', '30SEC' → '30 s'."""
    r = " ".join((raw or "").split()).replace("-", "–")
    if re.search(r"AMRAP|TEST", r, re.I):  # as many reps as possible (with good form): "max"
        return "max"
    r = re.sub(r"^:(\d+)$", r"\1 s", r)  # ":30" → "30 s"
    r = re.sub(r"(\d)\s*SEC\b", r"\1 s", r, flags=re.I)
    return r.lower() if re.search(r"[A-Za-z]{3,}", r) else r


def parse_load(raw: str) -> dict:
    """'7' or 'RPE7' → {'rpe': 7}; '7-8' → {'rpe': 7.5}; '75%' or '72.50%' → {'pct_1rm': 75 / 72.5}; '' or N/A → {}."""
    r = (raw or "").strip().upper().replace(",", ".")
    if m := re.match(r"^(\d+(?:\.\d+)?)\s*%$", r):
        return {"pct_1rm": float(m.group(1)) if "." in m.group(1) and not m.group(1).endswith(".00") else int(float(m.group(1)))}
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", r)]
    if not nums:
        return {}
    v = sum(nums[:2]) / len(nums[:2])
    return {"rpe": int(v) if v == int(v) else v}


def parse_rest(raw: str) -> int | None:
    """'3-4MIN' → 210 (the middle, in seconds); '0 MIN' → 0; '1-2 MIN' → 90."""
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", raw or "")]
    if not nums:
        return None
    return int(round(sum(nums[:2]) / len(nums[:2]) * 60))


def day_program(book: str, header: str) -> str | None:
    """Which program a day header belongs to (the Fundamentals book has three)."""
    h = header.upper()
    if book == "fundamentals":
        if h.startswith("FULL BODY"):
            return "fundamentals_full_body"
        if h.startswith(("LOWER BODY", "UPPER BODY")):
            return "fundamentals_upper_lower"
        if "&" in h:
            return "fundamentals_body_part"
        return None
    if book == "lpp" and re.match(r"^(LEGS|PUSH|PULL) #\d", h):
        return "lpp_legs_push_pull"
    if book == "upper-lower" and re.match(r"^(LOWER|UPPER) #\d", h):
        return "upper_lower_size_strength"
    return None


def week_header(text: str) -> tuple[int, int] | None:
    """'… PROGRAM WEEK 3 BLOCK 2' → (3, 2): the week (and block) a header page starts."""
    t = " ".join(text.split()).upper()
    m = re.search(r"PROGRAM WEEK (\d+)(?: BLOCK (\d+))?", t)
    return (int(m.group(1)), int(m.group(2) or 1)) if m else None


# ── Reading the tables ───────────────────────────────────────────────────────────────────────────────────────────────

def read_book(book: str) -> dict[str, list[dict]]:
    """{program id: [{week, pages, days: [{header, rows}]}]} in the order the book prints them."""
    folder = BOOKS / SOURCES[book]
    pages = [json.loads(line) for line in (folder / "pages.jsonl").open(encoding="utf-8")]
    tables: dict[int, list[dict]] = {}
    for line in (folder / "tables.jsonl").open(encoding="utf-8"):
        t = json.loads(line)
        tables.setdefault(t["page"], []).append(t)
    out: dict[str, list[dict]] = {}
    block_weeks = 8  # LPP: block 2 week 1 is week 9
    current: dict[str, dict] = {}
    header_week: tuple[int, int] | None = None
    for page in pages:
        if (h := week_header(page["text"][:400])) is not None:
            header_week = h
        for t in sorted(tables.get(page["page"], []), key=lambda x: x["index"]):
            rows = t["rows"]
            if not rows or len(rows[0]) < 2 or rows[0][1].upper() != "SETS":
                continue
            header = " ".join(rows[0][0].split())
            program = day_program(book, header)
            if program is None:
                continue
            weeks = out.setdefault(program, [])
            wanted = (header_week[0] + (header_week[1] - 1) * block_weeks) if header_week else 1
            week = current.get(program)
            full = week is not None and len(week["days"]) >= DAYS[program]  # (body-part split repeats "LEGS & ABS")
            if week is None or wanted > week["week"] or full:
                # A new week: its header page, or (when a header page didn't extract) the last week is complete.
                week = {"week": max(wanted, week["week"] + 1) if week else wanted, "pages": [], "days": []}
                weeks.append(week)
            current[program] = week
            if page["page"] not in week["pages"]:
                week["pages"].append(page["page"])
            week["days"].append({"header": header, "rows": rows[1:], "page": page["page"]})
    return out


def exercise_of(row: list[str], names: dict, missing: set[str]) -> dict | None:
    raw_name = row[0]
    if not raw_name.strip():
        return None
    name, superset = clean_name(raw_name)
    entry = names.get(name.upper())
    if entry is None:
        missing.add(name)
        return None
    ex = {"exercise": entry["id"]}
    if entry.get("technique"):
        ex["technique"] = entry["technique"]
    ex["sets"] = parse_sets(row[1]) or 1
    ex["reps"] = parse_reps(row[2])
    ex |= parse_load(row[3])
    ex["rest_sec"] = parse_rest(row[4]) if len(row) > 4 else None
    if ex["rest_sec"] is None:
        ex["rest_sec"] = 90
    if superset:
        ex["superset"] = superset
    if entry.get("choose"):
        ex["choose"] = entry["choose"]
    return ex


def build(check_only: bool = False, only: list[str] | None = None) -> int:
    names = {k.upper(): v for k, v in yaml.safe_load(NAMES.read_text(encoding="utf-8"))["names"].items()}
    meta_doc = yaml.safe_load(META.read_text(encoding="utf-8"))
    meta, techniques = meta_doc["programs"], meta_doc["techniques"]
    missing: set[str] = set()
    written = []
    for book in SOURCES:
        for program, weeks in read_book(book).items():
            m = meta[program]
            out_weeks = []
            for w in weeks:
                if len(w["days"]) != len(m["days"]):
                    raise SystemExit(f"{program} week {w['week']}: {len(w['days'])} days, expected {len(m['days'])}")
                days = {}
                for key_meta, d in zip(m["days"], w["days"]):
                    days[key_meta["key"]] = [e for r in d["rows"] if (e := exercise_of(r, names, missing))]
                out_weeks.append({"week": w["week"], "pages": "–".join(str(p) for p in (w["pages"][0], w["pages"][-1])) if len(w["pages"]) > 1 else str(w["pages"][0]),
                                  "days": days})
            if [w["week"] for w in out_weeks] != list(range(1, m["total_weeks"] + 1)):
                raise SystemExit(f"{program}: weeks {[w['week'] for w in out_weeks]}, expected 1–{m['total_weeks']}")
            doc = {k: v for k, v in m.items() if k != "days"}
            doc["days"] = [{k: v for k, v in d.items()} for d in m["days"]]
            doc["weeks"] = out_weeks
            used = sorted({e["technique"] for w in out_weeks for es in w["days"].values() for e in es if "technique" in e})
            doc["techniques"] = {k: techniques[k] for k in used}
            chosen = sorted({e["choose"] for w in out_weeks for es in w["days"].values() for e in es if "choose" in e})
            if chosen:
                doc["weak_points"] = {k: meta_doc["weak_points"][k] for k in chosen}
            if not check_only and (not only or program in only):
                path = OUT / f"{program}.json"
                path.write_text(json.dumps({"id": program, **doc}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                written.append(path.name)
    if missing:
        print("Names not mapped yet (add them to data/programs/exercise_names.yaml):")
        for n in sorted(missing):
            print("  ", n)
        return 1
    print("Wrote:", ", ".join(written) if written else "(check only)")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="only list the exercise names that aren't mapped yet")
    ap.add_argument("--only", action="append", help="write only this program (repeatable)")
    args = ap.parse_args(argv)
    return build(args.check, args.only)


if __name__ == "__main__":
    raise SystemExit(main())
