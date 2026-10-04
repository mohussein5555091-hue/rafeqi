"""Injury filtering of exercises, warm-up moves and stretches, and the sentences that explain it (bug report:
arm circles were left out for a lower back "because it involves No overhead lifting", and the glute bridge
"because it involves deadlift").

An injury's painful movements and restrictions only rule out what loads the injured area (except "no jumping or
running", which counts whatever the area); every reason is a whole sentence in English and Arabic."""

import re

import pytest

from app.engine.injuries import allowed, ruled_out_by
from app.engine.training import build_program
from app.engine.types import InjuryInfo, Person
from app.vocab import get_vocab
from engine_fixtures import exercise_catalogue

CAT = exercise_catalogue()
VOCAB = get_vocab()
BACK = InjuryInfo("b", "lowerBack", painful_movements=("squat", "deadlift"), restrictions=("noOverhead",))
SHOULDER = InjuryInfo("s", "shoulderL", painful_movements=("overheadPress", "benchPress", "lateralRaise"), restrictions=("noOverhead",))
KNEE = InjuryInfo("k", "kneeR", painful_movements=("squat", "lunges", "running"), restrictions=("limitRange",))


def person(**kw) -> Person:
    base = dict(sex="female", age=35, height_cm=165, weight_kg=72, goal="loseFat", pace="steady", experience="intermediate",
                days_per_week=4, session_minutes=60, location="gym", meals_per_day=3, cooking_minutes=30)
    return Person(**(base | kw))


def everything(p: Person):
    """Every exercise, warm-up move and stretch in the person's program."""
    plan = build_program(p, CAT)
    for d in plan.days:
        yield from (e.exercise_id for e in d.exercises)
        yield from (m["id"] for m in d.warmup["moves"])
        yield from (s["id"] for s in d.cooldown["stretches"])
        if d.warmup["general"]["id"]:
            yield d.warmup["general"]["id"]


def sentences(p: Person) -> list[dict]:
    plan = build_program(p, CAT)
    out = [{"en": r.en, "ar": r.ar} for r in plan.reasons]
    for d in plan.days:
        out += [{"en": r.en, "ar": r.ar} for r in d.reasons]
        out += [{"en": r.en, "ar": r.ar} for e in d.exercises for r in e.reasons]
        out += [s["why"] for s in d.warmup["skipped"]]
    return out


# ── What each injury rules out ──

def test_lower_back_keeps_arm_circles_and_the_glute_bridge():
    assert ruled_out_by(CAT["ex_arm_circles"], BACK, VOCAB) is None      # overhead, but no load on the spine
    assert ruled_out_by(CAT["ex_glute_bridge"], BACK, VOCAB) is None     # a hip bridge doesn't load the spine
    assert ruled_out_by(CAT["ex_bb_deadlift"], BACK, VOCAB) == "deadlift"
    assert ruled_out_by(CAT["ex_db_rdl"], BACK, VOCAB) == "deadlift"
    assert ruled_out_by(CAT["ex_bb_squat"], BACK, VOCAB) == "squat"
    assert ruled_out_by(CAT["ex_goblet_squat"], BACK, VOCAB) == "squat"  # the weight in front loads the back
    assert ruled_out_by(CAT["ex_leg_press"], BACK, VOCAB) is None        # back supported: the back-friendly squat
    assert ruled_out_by(CAT["ex_ohp"], BACK, VOCAB) == "noOverhead"
    upper_moves = {m["id"] for d in build_program(person(injuries=(BACK,)), CAT).days if d.kind == "upper" for m in d.warmup["moves"]}
    assert "ex_arm_circles" in upper_moves


def test_shoulder_rules_out_overhead_and_pressing_but_not_legs():
    assert ruled_out_by(CAT["ex_arm_circles"], SHOULDER, VOCAB) == "noOverhead"
    assert ruled_out_by(CAT["ex_lat_stretch"], SHOULDER, VOCAB) == "noOverhead"
    assert ruled_out_by(CAT["ex_db_bench_press"], SHOULDER, VOCAB) == "benchPress"
    assert ruled_out_by(CAT["ex_bb_squat"], SHOULDER, VOCAB) is None     # no painful movement or restriction matches
    assert ruled_out_by(CAT["ex_leg_swings"], SHOULDER, VOCAB) is None
    assert ruled_out_by(CAT["ex_db_floor_press"], SHOULDER, VOCAB) is None


def test_knee_rules_out_squats_lunges_and_impact_but_not_the_upper_body():
    assert ruled_out_by(CAT["ex_bw_squat"], KNEE, VOCAB) == "squat"
    assert ruled_out_by(CAT["ex_walking_lunge_bw"], KNEE, VOCAB) == "lunges"
    assert ruled_out_by(CAT["ex_jump_rope"], KNEE, VOCAB) == "running"
    assert ruled_out_by(CAT["ex_quad_stretch"], KNEE, VOCAB) == "limitRange"
    assert ruled_out_by(CAT["ex_arm_circles"], KNEE, VOCAB) is None
    assert ruled_out_by(CAT["ex_pull_up"], KNEE, VOCAB) is None


@pytest.mark.parametrize("injury", [BACK, SHOULDER, KNEE], ids=["back", "shoulder", "knee"])
@pytest.mark.parametrize("location", ["gym", "homeDumbbells", "bodyweight"])
@pytest.mark.parametrize("experience", ["beginner", "intermediate"])
def test_nothing_in_the_plan_conflicts_with_the_injury(injury, location, experience):
    p = person(injuries=(injury,), location=location, experience=experience)
    for ex_id in everything(p):
        assert allowed(CAT[ex_id], (injury,), VOCAB), ex_id


# ── The sentences ──

TAG_LABELS = {v["en"] for cat in ("painful_movements", "restrictions") for v in VOCAB.data[cat].values()}


@pytest.mark.parametrize("injury", [BACK, SHOULDER, KNEE], ids=["back", "shoulder", "knee"])
def test_every_injury_reason_is_a_proper_sentence(injury):
    for s in sentences(person(injuries=(injury,), experience="beginner", days_per_week=3)) + sentences(person(injuries=(injury,))):
        en, ar = s["en"], s["ar"]
        assert en and ar and en.rstrip().endswith((".", ")")), en
        assert "{" not in en and "{" not in ar, en
        # A restriction's name is only ever quoted ("the "No overhead lifting" restriction"), never "involves No …".
        assert not re.search(r"involves [A-Z]", en) and "involves deadlift" not in en, en
        for label in TAG_LABELS:
            if label in en:
                assert f'"{label}"' in en, en


def test_warm_up_skips_read_as_sentences():
    knee_days = build_program(person(injuries=(KNEE,), experience="beginner", days_per_week=3), CAT).days
    squat = next(s for d in knee_days for s in d.warmup["skipped"] if s["id"] == "ex_bw_squat")
    assert squat["why"]["en"] == "Not in your warm-up: Bodyweight squat. It involves squatting, which hurts your right knee."
    assert squat["why"]["ar"].startswith("سكوات") and "اتشال من التسخين" in squat["why"]["ar"]
    shoulder_days = build_program(person(injuries=(SHOULDER,)), CAT).days
    circles = next(s for d in shoulder_days for s in d.warmup["skipped"] if s["id"] == "ex_arm_circles")
    assert circles["why"]["en"] == 'Not in your warm-up: Arm circles. It goes against the "No overhead lifting" restriction for your left shoulder.'
    assert "«ممنوع الرفع فوق الراس»" in circles["why"]["ar"]


def test_injury_swap_reason_names_the_movement():
    plan = build_program(person(injuries=(SHOULDER,)), CAT)
    swapped = [r.en for d in plan.days for e in d.exercises if e.swap_kind == "swapped" for r in e.reasons if r.rule == "training.injuries"]
    assert any("avoids bench pressing, which hurts your left shoulder." in s for s in swapped), swapped


# ── Lower back: back-friendly compound leg exercises; ramp-up only on a compound lift ──

LEG_COMPOUNDS = {"ex_leg_press", "ex_split_squat", "ex_step_up", "ex_walking_lunge_bw", "ex_bw_squat"}


@pytest.mark.parametrize("experience,days,location", [("intermediate", 4, "gym"), ("beginner", 3, "gym"), ("beginner", 3, "homeDumbbells")])
def test_lower_back_gets_back_friendly_compound_leg_exercises(experience, days, location):
    plan = build_program(person(injuries=(BACK,), experience=experience, days_per_week=days, location=location), CAT)
    for d in plan.days:
        if d.kind == "upper":
            continue
        ids = [e.exercise_id for e in d.exercises]
        loaded = [i for i in ids if i in LEG_COMPOUNDS and CAT[i].equipment != ("bodyweight",)]
        assert loaded, (d.name, ids)  # never only leg extensions and calf raises
        assert not {"ex_bb_squat", "ex_goblet_squat", "ex_bb_deadlift", "ex_db_rdl"} & set(ids)
    ids = {e.exercise_id for d in plan.days for e in d.exercises}
    assert ids & ({"ex_leg_press"} if location == "gym" else {"ex_step_up", "ex_split_squat"})


def test_a_barbell_squat_becomes_a_loaded_leg_exercise_not_a_bodyweight_squat():
    plan = build_program(person(injuries=(BACK,)), CAT)
    subs = {e.replaced_exercise_id: e.exercise_id for d in plan.days for e in d.exercises if e.swap_kind == "swapped"}
    assert subs["ex_bb_squat"] == "ex_leg_press"
    home = build_program(person(injuries=(BACK,), experience="beginner", days_per_week=3, location="homeDumbbells"), CAT)
    assert all(e.exercise_id != "ex_bw_squat" for d in home.days for e in d.exercises)


@pytest.mark.parametrize("injuries", [(), (BACK,), (SHOULDER,), (KNEE,)], ids=["none", "back", "shoulder", "knee"])
@pytest.mark.parametrize("location", ["gym", "homeDumbbells"])
def test_ramp_up_sets_go_on_the_first_compound_lift_only(injuries, location):
    from app.engine.training import is_compound

    for p in (person(injuries=injuries, location=location), person(injuries=injuries, location=location, experience="beginner", days_per_week=3)):
        for d in build_program(p, CAT).days:
            ramp = d.warmup["ramp"]["id"]
            if ramp is None:
                continue
            assert is_compound(CAT[ramp]), (d.name, ramp)
            first_compound = next(e.exercise_id for e in d.exercises if e.weight_step_kg > 0 and e.start_weight_kg > 0 and is_compound(CAT[e.exercise_id]))
            assert ramp == first_compound


def test_an_isolation_exercise_first_gets_no_ramp_up():
    from app.engine.warmup import build_warmup  # noqa: F401  (the engine decides; this checks the knee case)

    knee = InjuryInfo("k", "kneeR", painful_movements=("squat", "lunges", "deadlift"))
    for d in build_program(person(injuries=(knee,)), CAT).days:
        ramp = d.warmup["ramp"]["id"]
        assert ramp is None or ramp not in {"ex_leg_extension", "ex_seated_leg_curl", "ex_calf_raise", "ex_incline_curl", "ex_lateral_raise"}


def test_injury_badge_only_for_real_injury_swaps():
    """An exercise the weekly review swapped (marked uncomfortable) is not shown as "Swapped for your shoulder"."""
    from app.engine.training import Adjustments

    recovering = InjuryInfo("s", "shoulderL", status="recovering")
    plan = build_program(person(injuries=(recovering,)), CAT, adjust=Adjustments(avoid=frozenset({"ex_cs_row"})))
    row = next(e for d in plan.days for e in d.exercises if e.replaced_exercise_id == "ex_cs_row")
    assert row.swap_kind == "review"
    for d in plan.days:
        for e in d.exercises:
            if e.swap_kind in ("swapped", "added"):
                assert any(r.rule in ("training.injuries", "training.full_body_legs") for r in e.reasons)
