"""The real programs (Phase B2 of docs/PLAN-AI.md): scripts/books/programs.py's table readers, the program files it
wrote to data/programs/, and the plan engine following them week by week. Needs no books: the program files are
committed, and the helpers are tested on made-up table cells."""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from app.engine.rules import deload_weeks, load_templates
from app.engine.training import RPE_CHART, build_program, choose_template, program_week, rpe_from_pct, template_days
from app.engine.types import Person
from app.models import Plan
from engine_fixtures import exercise_catalogue
from test_plans import catalogue, onboarded  # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("book_programs", ROOT / "scripts" / "books" / "programs.py")
bp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bp
spec.loader.exec_module(bp)

PROGRAMS = ROOT / "data" / "programs"
FILES = sorted(PROGRAMS.glob("*.json"))
CAT = exercise_catalogue()
# What a program file may say about one exercise: numbers and tags only, never the books' coaching notes.
EXERCISE_KEYS = {"exercise", "technique", "sets", "reps", "rpe", "pct_1rm", "rest_sec", "superset", "choose"}


def person(**kw) -> Person:
    base = dict(sex="male", age=29, height_cm=180, weight_kg=80, goal="buildMuscle", pace="steady", experience="beginner",
                days_per_week=3, session_minutes=90, location="gym", meals_per_day=4, cooking_minutes=30)
    return Person(**(base | kw))


# ── Reading the tables (made-up cells) ───────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("A1: LEG  EXTENSION", ("LEG EXTENSION", "A")),
    ("BARBELL BENCH PRESS", ("BARBELL BENCH PRESS", None)),
])
def test_clean_name(raw, expected):
    assert bp.clean_name(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("10-12", "10–12"), ("8", "8"), ("20 EACH LEG", "20 each leg"), ("30SEC", "30 s"), (":30", "30 s"),
    ("AMRAP", "max"), ("TEST", "max"),
])
def test_parse_reps(raw, expected):
    assert bp.parse_reps(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("7", {"rpe": 7}), ("RPE7", {"rpe": 7}), ("7-8", {"rpe": 7.5}), ("75%", {"pct_1rm": 75}), ("72.50%", {"pct_1rm": 72.5}),
    ("", {}), ("N/A", {}),
])
def test_parse_load(raw, expected):
    assert bp.parse_load(raw) == expected


@pytest.mark.parametrize("raw,expected", [("3-4MIN", 210), ("0 MIN", 0), ("1-2 MIN", 90), ("", None)])
def test_parse_rest(raw, expected):
    assert bp.parse_rest(raw) == expected


def test_day_headers_pick_the_program():
    assert bp.day_program("fundamentals", "FULL BODY #1") == "fundamentals_full_body"
    assert bp.day_program("fundamentals", "LOWER BODY #2") == "fundamentals_upper_lower"
    assert bp.day_program("fundamentals", "LEGS & ABS") == "fundamentals_body_part"
    assert bp.day_program("lpp", "PUSH #2") == "lpp_legs_push_pull"
    assert bp.day_program("upper-lower", "LOWER #3") == "upper_lower_size_strength"
    assert bp.day_program("fundamentals", "WARM UP") is None
    assert bp.week_header("LPP PROGRAM  WEEK 3 BLOCK 2") == (3, 2)
    assert bp.week_header("nothing here") is None


# ── The program files ────────────────────────────────────────────────────────────────────────────────────────────────

def test_program_files_exist():
    assert {"fundamentals_full_body", "fundamentals_upper_lower", "fundamentals_body_part"} <= {f.stem for f in FILES}


@pytest.mark.parametrize("path", FILES, ids=[f.stem for f in FILES])
def test_every_week_is_complete_and_uses_the_catalogue(path):
    t = json.loads(path.read_text(encoding="utf-8"))
    assert [w["week"] for w in t["weeks"]] == list(range(1, t["total_weeks"] + 1))
    keys = {d["key"] for d in t["days"]}
    for w in t["weeks"]:
        assert set(w["days"]) == keys and re.fullmatch(r"\d+(–\d+)?", w["pages"]), w["week"]
        for day in w["days"].values():
            assert day, (w["week"], "a day without exercises")
            for e in day:
                assert set(e) <= EXERCISE_KEYS, e
                assert e["exercise"] in CAT, e["exercise"]
                assert e["sets"] >= 1 and e["rest_sec"] >= 0 and e["reps"]
                assert ("rpe" in e) != ("pct_1rm" in e), e
                assert 5 <= e.get("rpe", 7) <= 10 and 30 <= e.get("pct_1rm", 70) <= 100, e
                if "technique" in e:
                    assert e["technique"] in t["techniques"], e
    assert set(deload_weeks(t)) <= set(range(1, t["total_weeks"] + 1))
    for rotation in t["rotation"].values():
        assert set(rotation) <= keys


def test_every_book_name_maps_to_a_catalogue_exercise():
    names = yaml.safe_load((PROGRAMS / "exercise_names.yaml").read_text(encoding="utf-8"))["names"]
    techniques = yaml.safe_load((PROGRAMS / "program_meta.yaml").read_text(encoding="utf-8"))["techniques"]
    used = {e["exercise"] for f in FILES for w in json.loads(f.read_text(encoding="utf-8"))["weeks"]
            for day in w["days"].values() for e in day}
    for name, entry in names.items():
        assert entry["id"] in CAT or entry["id"] not in used, name  # (all of them once every program is in)
        assert entry.get("technique") is None or entry["technique"] in techniques, name


def test_program_exercises_have_the_book_video_or_a_search_link():
    """The Fundamentals book prints its demo-video links as plain text (pp. 88–91): they're the catalogue's video_url."""
    doc = yaml.safe_load((ROOT / "data" / "catalogue" / "exercises.yaml").read_text(encoding="utf-8"))["exercises"]
    by_id = {e["id"]: e for e in doc}
    assert by_id["ex_bb_squat"]["video_url"] == "https://www.youtube.com/watch?v=dW5-C1fsMjk"
    assert by_id["ex_db_curl"]["video_url"] == "https://www.youtube.com/watch?v=ykJmrZ5v0Oo"
    used = {e["exercise"] for f in FILES for w in json.loads(f.read_text(encoding="utf-8"))["weeks"]
            for day in w["days"].values() for e in day}
    for ex_id in used:
        assert by_id[ex_id]["video_url"].startswith(("https://www.youtube.com/", "https://youtu.be/")), ex_id
        assert "PLACEHOLDER" not in by_id[ex_id]["source"] or ex_id in SAMPLE_ENTRIES, ex_id


# Catalogue entries written before the books phase; their sources are rewritten with the exercise catalogue commit.
SAMPLE_ENTRIES = {"ex_bb_squat", "ex_bb_deadlift", "ex_leg_extension", "ex_calf_raise", "ex_bb_bench_press", "ex_ohp",
                  "ex_lateral_raise", "ex_face_pull", "ex_lat_pulldown", "ex_leg_press", "ex_seated_leg_curl", "ex_pushdown",
                  "ex_db_rdl", "ex_one_arm_db_row", "ex_db_bench_press", "ex_db_shoulder_press", "ex_pull_up", "ex_push_up",
                  "ex_goblet_squat", "ex_split_squat", "ex_incline_curl", "ex_cs_row", "ex_glute_bridge", "ex_step_up",
                  "ex_db_floor_press", "ex_landmine_press", "ex_inverted_row", "ex_bw_squat", "ex_walking_lunge_bw"}


# ── Following the program week by week ───────────────────────────────────────────────────────────────────────────────

def test_program_week_cycles():
    t = {"total_weeks": 8}
    assert [program_week(t, n) for n in (0, 1, 7, 8, 9)] == [1, 2, 8, 1, 2]


@pytest.mark.parametrize("reps,pct,rpe", [
    ("1", 100, 10), ("5", RPE_CHART[6], 8), ("3", RPE_CHART[2], 10), ("8–10", 40, 5), ("max", 95.5, 9),
])
def test_rpe_from_a_percentage(reps, pct, rpe):
    assert rpe_from_pct(reps, pct) == rpe


@pytest.mark.parametrize("experience,days,program,used", [
    ("beginner", 2, "fundamentals_full_body", 2),
    ("beginner", 3, "fundamentals_full_body", 3),
    ("beginner", 4, "fundamentals_upper_lower", 4),
    ("beginner", 5, "fundamentals_body_part", 5),
    ("beginner", 6, "fundamentals_body_part", 5),   # beginners stay on Fundamentals, the closest days it has
    ("intermediate", 3, "fundamentals_full_body", 3),
    ("advanced", 4, "fundamentals_upper_lower", 4),
    ("intermediate", 6, "lpp_legs_push_pull", 6),
    ("advanced", 6, "lpp_legs_push_pull", 6),
])
def test_real_program_choice(real_programs, experience, days, program, used):
    t, n, _ = choose_template(person(experience=experience, days_per_week=days))
    assert (t["id"], n) == (program, used)


def test_each_week_follows_that_weeks_table(real_programs):
    t = next(x for x in load_templates() if x["id"] == "fundamentals_full_body")
    for done in (0, 3, 8):
        plan = build_program(person(), CAT, weeks_done=done)
        week = program_week(t, done)
        assert plan.week == week and plan.template_id == "fundamentals_full_body"
        table = template_days(t, week)
        for d in plan.days:
            first = table[d.key]["exercises"][0]
            planned = d.exercises[0]
            if planned.exercise_id == first["exercise"]:  # (unless the equipment or an injury swapped it)
                assert (planned.sets, planned.reps, planned.rest_sec) == (first["sets"], first["reps"], first["rest_sec"])
    assert build_program(person(), CAT, weeks_done=8).days[0].exercises[0].reps == build_program(person(), CAT).days[0].exercises[0].reps


def test_technique_and_reasons_are_explained(real_programs):
    plan = build_program(person(experience="beginner", days_per_week=4), CAT)
    reasons = [r for d in plan.days for e in d.exercises for r in e.reasons]
    assert all(r.en and r.ar and r.source for r in reasons)
    assert any(r.rule == "training.template_choice" and "Fundamentals" in r.en for r in plan.reasons)


def test_lpp_percentages_techniques_and_lighter_week(real_programs):
    """LPP loads its main lifts as a % of a one-rep max (shown as the effort it means), names techniques, and its
    block 2 starts with a lighter week that's already in its tables."""
    p = person(experience="intermediate", days_per_week=6)
    plan = build_program(p, CAT)
    assert plan.template_id == "lpp_legs_push_pull" and [d.key for d in plan.days] == ["LE1", "PU1", "PL1", "LE2", "PU2", "PL2"]
    reasons = [r for d in plan.days for e in d.exercises for r in e.reasons]
    assert any(r.rule == "training.pct_1rm" and "% of your one-rep max" in r.en for r in reasons)
    assert any(r.rule == "training.volume" and ": " in r.en for r in reasons)  # a technique line
    assert any(r.rule == "training.deload" and "Weeks 9 of 16" in r.en for r in plan.reasons)
    t = next(x for x in load_templates() if x["id"] == "lpp_legs_push_pull")
    sets = lambda w: sum(e["sets"] for d in template_days(t, w).values() for e in d["exercises"])  # noqa: E731
    assert sets(9) < sets(8)  # the lighter week has fewer sets than the week before it


def test_a_new_program_week_makes_a_new_plan_version(real_programs, onboarded, clock, db):  # noqa: F811
    """The first screen that asks for "this week" in a new program week builds that week's sessions, once."""
    c = onboarded.client
    assert c.post("/api/plan").json()["version"] == 1
    first = c.get("/api/workouts/week").json()
    assert c.get("/api/workouts/week").json() == first  # same week: no new version
    clock.advance(days=7)
    c.get("/api/workouts/week")
    plans = db.scalars(select(Plan).where(Plan.user_id == onboarded.id).order_by(Plan.version)).all()
    assert plans[-1].trigger == "newWeek" and plans[-1].inputs["program_week"] == 2
    c.get("/api/workouts/week")
    assert len(db.scalars(select(Plan).where(Plan.user_id == onboarded.id)).all()) == len(plans)  # only once a week
