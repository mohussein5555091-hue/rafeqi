"""Injuries (engine/injuries.py) and the training program (engine/training.py)."""

import pytest

from app.engine.injuries import PainEntry, allowed, load_cuts, red_flag, ruled_out_by
from app.engine.rules import load_rules
from app.engine.training import Adjustments, build_program, choose_template, fits_equipment
from app.engine.types import Health, InjuryInfo, Person
from engine_fixtures import exercise_catalogue

CAT = exercise_catalogue()
SHOULDER = InjuryInfo(id="i1", region="shoulderL", painful_movements=("overheadPress", "benchPress", "dips"), restrictions=("noOverhead",))


def person(**kw) -> Person:
    base = dict(sex="male", age=29, height_cm=180, weight_kg=88, goal="loseFat", pace="steady", experience="intermediate",
                days_per_week=4, session_minutes=60, location="gym", meals_per_day=4, cooking_minutes=30)
    return Person(**(base | kw))


def all_exercises(plan):
    return [e for d in plan.days for e in d.exercises]


# ── Injuries ──────────────────────────────────────────────────────────────────
def test_painful_movement_rules_out_matching_tags_only():
    ohp_pain = InjuryInfo(id="x", region="shoulderL", painful_movements=("overheadPress",))
    assert ruled_out_by(CAT["ex_ohp"], ohp_pain) == "overheadPress"            # verticalPush, overhead
    assert ruled_out_by(CAT["ex_db_shoulder_press"], ohp_pain) == "overheadPress"
    assert ruled_out_by(CAT["ex_landmine_press"], ohp_pain) is None            # verticalPush, partial range
    bench = InjuryInfo(id="x", region="shoulderL", painful_movements=("benchPress",))
    assert ruled_out_by(CAT["ex_bb_bench_press"], bench) == "benchPress"       # horizontalPush, full
    assert ruled_out_by(CAT["ex_db_floor_press"], bench) is None               # partial range


def test_restrictions_and_joint_of_injury():
    no_overhead = InjuryInfo(id="x", region="kneeL", restrictions=("noOverhead",))
    assert ruled_out_by(CAT["ex_pull_up"], no_overhead) is None                # overhead, but it doesn't load the knee
    shoulder = InjuryInfo(id="x", region="shoulderL", restrictions=("noOverhead",))
    assert ruled_out_by(CAT["ex_pull_up"], shoulder) == "noOverhead"           # overhead and loads the shoulder
    back = InjuryInfo(id="x", region="lowerBack", restrictions=("noOverhead",))
    assert ruled_out_by(CAT["ex_ohp"], back) == "noOverhead"                   # standing press: the spine carries the bar
    assert ruled_out_by(CAT["ex_arm_circles"], back) is None                   # arm circles don't load the spine
    impact = InjuryInfo(id="x", region="lowerBack", restrictions=("noImpact",))
    assert ruled_out_by(CAT["ex_jump_rope"], impact) == "noImpact"             # impact counts whatever the area
    limit = InjuryInfo(id="x", region="kneeL", restrictions=("limitRange",))
    assert ruled_out_by(CAT["ex_goblet_squat"], limit) == "limitRange"         # loads the knee, full range
    assert ruled_out_by(CAT["ex_cs_row"], limit) is None                       # full range, but not the knee


def test_resolved_injuries_rule_out_nothing():
    resolved = InjuryInfo(id="x", region="shoulderL", status="resolved", painful_movements=("overheadPress",))
    assert ruled_out_by(CAT["ex_ohp"], resolved) is None


def test_load_cuts_for_recovering_injuries_and_load_restrictions():
    recovering = InjuryInfo(id="x", region="kneeR", status="recovering")
    assert [c.factor for c in load_cuts(CAT["ex_bb_squat"], (recovering,))] == [load_rules()["training"]["injury_load"]["recovering_load_factor"]]
    assert load_cuts(CAT["ex_cs_row"], (recovering,)) == []                   # doesn't load the knee
    heavy = InjuryInfo(id="y", region="lowerBack", restrictions=("noHeavyLoad",))
    assert [c.factor for c in load_cuts(CAT["ex_bb_deadlift"], (heavy,))] == [0.7]


@pytest.mark.parametrize("logs,expected", [
    ([PainEntry(3), PainEntry(2)], None),
    ([PainEntry(2, sharp_pain=True)], "sharp_pain"),
    ([PainEntry(1, swelling=True)], "swelling"),
    ([PainEntry(1, numbness=True)], "numbness"),
    ([PainEntry(2, worsening=True)], "worsening"),
    ([PainEntry(3), PainEntry(7)], "pain_at_7"),
    ([PainEntry(2), PainEntry(3), PainEntry(4)], "pain_rising"),
    ([PainEntry(2), PainEntry(4), PainEntry(4)], None),
    ([], None),
])
def test_red_flags(logs, expected):
    assert red_flag(logs) == expected


# ── Training ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("experience,days,location,template,used_days", [
    ("beginner", 3, "gym", "sample_full_body", 3),
    ("beginner", 4, "gym", "sample_full_body", 3),          # beginners stay on full body
    ("intermediate", 4, "gym", "sample_upper_lower", 4),
    ("advanced", 5, "gym", "sample_upper_lower", 5),
    ("intermediate", 2, "gym", "sample_full_body", 2),      # 2 days: full body fits better
    ("intermediate", 4, "homeDumbbells", "sample_full_body", 3),
])
def test_template_choice(experience, days, location, template, used_days):
    t, n, reasons = choose_template(person(experience=experience, days_per_week=days, location=location))
    assert (t["id"], n) == (template, used_days)
    assert reasons and (n == days or "days a week; you chose" in reasons[-1].en)


def test_program_follows_the_weekly_schedule():
    plan = build_program(person(), CAT)
    assert [d.weekday for d in plan.days] == ["sat", "mon", "wed", "thu"]
    assert [d.key for d in plan.days] == ["UA", "LA", "UB", "LB"]


def test_shoulder_injury_swaps_to_the_closest_safe_exercise():
    plan = build_program(person(injuries=(SHOULDER,)), CAT)
    exs = all_exercises(plan)
    for e in exs:
        assert allowed(CAT[e.exercise_id], (SHOULDER,)), e.exercise_id
    swaps = {e.replaced_exercise_id: e.exercise_id for e in exs if e.swap_kind == "swapped"}
    assert swaps["ex_bb_bench_press"] == "ex_db_floor_press"    # same movement pattern, partial range
    assert swaps["ex_ohp"] == "ex_landmine_press"
    assert swaps["ex_pull_up"] == "ex_lat_pulldown"
    for e in exs:
        if e.swap_kind == "swapped":
            assert e.injury_id == "i1" and CAT[e.exercise_id].pattern == CAT[e.replaced_exercise_id].pattern
            assert any("left shoulder" in r.en for r in e.reasons)


def test_no_safe_substitute_removes_the_exercise_with_a_reason():
    hips = InjuryInfo(id="h", region="hipL", painful_movements=("deadlift",))  # no other hinge avoids it
    plan = build_program(person(injuries=(hips,)), CAT)
    assert not any(CAT[e.exercise_id].pattern == "hinge" for e in all_exercises(plan))
    assert any("removed" in r.en and "Barbell deadlift" in r.en for r in plan.reasons)


def test_equipment_swaps_at_home():
    plan = build_program(person(experience="beginner", days_per_week=3, location="homeDumbbells"), CAT)
    for e in all_exercises(plan):
        assert fits_equipment(CAT[e.exercise_id], "homeDumbbells"), e.exercise_id
    assert any(e.swap_kind == "equipment" and e.replaced_exercise_id == "ex_leg_press" for e in all_exercises(plan))
    # The cable pushdown becomes a dumbbell triceps exercise (data/catalogue has one since the Fundamentals program).
    pushdown = next(e for e in all_exercises(plan) if e.replaced_exercise_id == "ex_pushdown")
    assert pushdown.swap_kind == "equipment" and CAT[pushdown.exercise_id].pattern == "elbowExtension"


def test_paused_area_removes_its_exercises():
    paused = InjuryInfo(id="p", region="kneeR", paused=True)
    plan = build_program(person(injuries=(paused,)), CAT)
    assert not any("knee" in CAT[e.exercise_id].joints for e in all_exercises(plan))
    assert any("doctor or physiotherapist" in r.en for r in plan.reasons)


def test_recovering_injury_lightens_only_its_area():
    knee = InjuryInfo(id="k", region="kneeR", status="recovering")
    healthy, injured = build_program(person(), CAT), build_program(person(injuries=(knee,)), CAT)
    by_id = {e.exercise_id: e for e in all_exercises(injured)}
    assert by_id["ex_bb_squat"].load_factor == 0.8 and by_id["ex_bb_squat"].injury_id == "k"
    assert by_id["ex_bb_squat"].start_weight_kg < {e.exercise_id: e for e in all_exercises(healthy)}["ex_bb_squat"].start_weight_kg
    assert by_id["ex_cs_row"].load_factor == 1.0


def test_health_flag_lowers_effort_and_load_and_adds_rest():
    normal, careful = build_program(person(), CAT), build_program(person(health=Health(heart_condition=True)), CAT)
    for a, b in zip(all_exercises(normal), all_exercises(careful)):
        assert b.target_rpe == a.target_rpe - 1 and b.rest_sec == a.rest_sec + 30 and b.load_factor == 0.85
        assert b.start_weight_kg <= a.start_weight_kg


def test_start_weights_round_down_to_the_weight_step():
    for e in all_exercises(build_program(person(sex="female", weight_kg=61), CAT)):
        if e.weight_step_kg:
            assert e.start_weight_kg >= e.weight_step_kg
            assert abs(e.start_weight_kg / e.weight_step_kg - round(e.start_weight_kg / e.weight_step_kg)) < 1e-9


def test_review_adjustments():
    adjust = Adjustments(avoid=frozenset({"ex_cs_row"}), deload=True, weight_offsets=(("ex_lat_pulldown", 2.5),))
    normal, adjusted = build_program(person(), CAT), build_program(person(), CAT, adjust=adjust)
    ids = [e.exercise_id for e in all_exercises(adjusted)]
    assert "ex_cs_row" not in ids and any(e.replaced_exercise_id == "ex_cs_row" for e in all_exercises(adjusted))
    # Deload: one set less and effort 1 lower on every exercise (fewer sets can leave room for one more exercise).
    for nd, ad in zip(normal.days, adjusted.days):
        before = {e.exercise_id: e for e in nd.exercises}
        for e in ad.exercises:
            a = before.get(e.replaced_exercise_id or e.exercise_id) or before.get(e.exercise_id)
            if a is not None:
                assert e.sets == max(1, a.sets - 1) and e.target_rpe == a.target_rpe - 1, e.exercise_id
    assert {e.exercise_id: e.weight_offset_kg for e in all_exercises(adjusted)}["ex_lat_pulldown"] == 2.5
