"""Warm-up, cool-down, cardio, session length, full-body legs, starting weights and exercise alternatives
(engine/warmup.py, engine/cardio.py, engine/training.py; rules in data/rules/training.yaml)."""

import pytest

from app.engine.cardio import WEEK, place
from app.engine.injuries import allowed, ruled_out_by
from app.engine.nutrition import compute_targets
from app.engine.rules import load_rules
from app.engine.training import Adjustments, alternatives, build_program, exercise_range, fits_equipment, lifting_minutes
from app.engine.types import Health, InjuryInfo, Person
from app.engine.warmup import ramp_up
from app.vocab import get_vocab
from engine_fixtures import exercise_catalogue

CAT = exercise_catalogue()
TR = load_rules()["training"]
KNEE = InjuryInfo("k", "kneeR", painful_movements=("squat", "lunges", "running"))
BACK = InjuryInfo("b", "lowerBack", painful_movements=("squat", "deadlift"))
SHOULDER = InjuryInfo("s", "shoulderL", painful_movements=("overheadPress", "benchPress"), restrictions=("noOverhead",))


def person(**kw) -> Person:
    base = dict(sex="male", age=30, height_cm=178, weight_kg=85, goal="loseFat", pace="steady", experience="intermediate",
                days_per_week=3, session_minutes=60, location="gym", meals_per_day=3, cooking_minutes=30)
    return Person(**(base | kw))


ALL_PEOPLE = [person(location=loc, experience=exp, days_per_week=days, session_minutes=mins, injuries=inj)
              for loc in ("gym", "homeDumbbells", "bodyweight") for exp in ("beginner", "intermediate", "advanced")
              for days in (2, 3, 4, 6) for mins in (45, 90) for inj in ((), (KNEE,), (BACK,), (SHOULDER,))]


# ── Every catalogue entry has a type, and the new kinds have their how-to page ──

def test_catalogue_types():
    types = {e.type for e in CAT.values()}
    assert types == {"strength", "cardio", "mobility", "stretch"}
    for ids in (TR["warmup"]["general_by_location"].values(), TR["cardio"]["options_by_location"].values()):
        for lst in ids:
            assert all(i in CAT for i in lst), lst
    for kind in TR["warmup"]["moves_by_kind"].values():
        assert all(m["id"] in CAT and m["amount"]["en"] and m["amount"]["ar"] for m in kind)
    assert all(CAT[i].type == "stretch" for i in TR["cooldown"]["candidates"])


# ── Warm-up ──

@pytest.mark.parametrize("p", ALL_PEOPLE[::7])
def test_every_session_has_a_warm_up_and_a_cool_down(p):
    for d in build_program(p, CAT).days:
        w, c = d.warmup, d.cooldown
        assert w["general"]["minutes"] == TR["warmup"]["general_minutes"] and w["general"]["id"] in CAT
        assert TR["warmup"]["moves"]["min"] <= len(w["moves"]) <= TR["warmup"]["moves"]["max"], d.name
        assert 6 <= w["minutes"] <= 11, w
        assert 4 <= len(c["stretches"]) <= 6 and all(30 <= s["seconds"] <= 45 for s in c["stretches"])
        assert c["breathing"]["id"] == "ex_slow_breathing"
        assert 4 <= c["minutes"] <= 8, c


def test_warm_up_moves_match_the_day():
    days = {d.kind: d for d in build_program(person(days_per_week=4), CAT).days}
    assert "ex_arm_circles" in [m["id"] for m in days["upper"].warmup["moves"]]
    assert "ex_leg_swings" in [m["id"] for m in days["lower"].warmup["moves"]]
    assert days["upper"].warmup["general"]["id"] == "ex_bike"  # gym
    home = build_program(person(location="homeDumbbells"), CAT).days[0]
    assert home.warmup["general"]["id"] == "ex_march_in_place"


def test_warm_up_skips_moves_that_hurt():
    for d in build_program(person(injuries=(KNEE,)), CAT).days:
        ids = [m["id"] for m in d.warmup["moves"]]
        assert not any(ruled_out_by(CAT[i], KNEE, get_vocab()) for i in ids)
        if d.kind != "upper":
            assert "ex_bw_squat" in [s["id"] for s in d.warmup["skipped"]]
            assert any("ex_bw_squat" in str(s) and "right knee" in s["why"]["en"] for s in d.warmup["skipped"])


def test_health_flag_warm_up_has_no_jumping():
    p = person(location="bodyweight", health=Health(heart_condition=True))
    assert all(CAT[d.warmup["general"]["id"]].pattern != "jump" for d in build_program(p, CAT).days)


def test_ramp_up_sets_are_lighter_and_rounded():
    # The programs' loading pyramid (Upper/Lower p. 30) as a share of the working weight: 40% × 5, 65% × 4, 80% × 3.
    assert ramp_up(40, 2.5) == [{"pct": 40, "reps": 5, "weightKg": 15.0}, {"pct": 65, "reps": 4, "weightKg": 25.0},
                                {"pct": 80, "reps": 3, "weightKg": 30.0}]
    heavy = ramp_up(100, 2.5)
    assert [s["weightKg"] for s in heavy] == [40.0, 65.0, 80.0, 90.0]  # a fourth, heavier one from 60 kg
    assert ramp_up(22, 2) == [{"pct": 40, "reps": 5, "weightKg": 8}, {"pct": 65, "reps": 4, "weightKg": 14},
                              {"pct": 80, "reps": 3, "weightKg": 16}]
    assert ramp_up(0, 0) == []  # bodyweight: the mobility moves are the warm-up
    assert ramp_up(8, 2) == []  # too light to need lighter sets


# ── Cool-down ──

def test_cool_down_stretches_the_muscles_trained():
    for d in build_program(person(days_per_week=4), CAT).days:
        trained = {m for e in d.exercises for m in CAT[e.exercise_id].muscles}
        stretched = [s["id"] for s in d.cooldown["stretches"]]
        hits = sum(bool(set(CAT[i].muscles) & trained) for i in stretched)
        assert hits >= 4, (d.name, stretched)
        if d.kind == "lower":
            assert {"ex_quad_stretch", "ex_hamstring_stretch"} <= set(stretched)
        if d.kind == "upper":
            assert "ex_chest_stretch" in stretched


# ── Session length and the time estimate ──

@pytest.mark.parametrize("p", ALL_PEOPLE[::5])
def test_exercise_count_fits_the_session_length(p):
    rng = exercise_range(p.session_minutes)
    for d in build_program(p, CAT).days:
        assert len(d.exercises) <= rng["max"], d.name
        if p.location == "gym" and not p.injuries:
            assert len(d.exercises) >= rng["min"], (d.name, p.session_minutes)
        expected = round(d.warmup["minutes"] + lifting_minutes(d.exercises) + d.cooldown["minutes"])
        assert d.est_minutes == expected  # worked out from the sets, rests, warm-up and cool-down
        assert d.est_minutes <= p.session_minutes + 15


def test_longer_sessions_get_more_exercises():
    short = build_program(person(session_minutes=45), CAT).days[0]
    long = build_program(person(session_minutes=90), CAT).days[0]
    assert len(long.exercises) > len(short.exercises)
    assert long.est_minutes > short.est_minutes


def test_three_exercises_never_claim_fifty_minutes():
    for p in ALL_PEOPLE[::3]:
        for d in build_program(p, CAT).days:
            sets = sum(e.sets for e in d.exercises)
            assert d.est_minutes <= 20 + sets * 4, (d.name, sets, d.est_minutes)


# ── Full-body days train the legs ──

@pytest.mark.parametrize("p", ALL_PEOPLE)
def test_every_full_body_day_has_a_leg_exercise(p):
    for d in build_program(p, CAT).days:
        if d.kind != "full":
            continue
        patterns = {CAT[e.exercise_id].pattern for e in d.exercises}
        leg = patterns & {"squat", "hinge"} or patterns & set(TR["full_body_legs"]["patterns"])
        assert leg, (d.name, p.location, p.injuries, [e.exercise_id for e in d.exercises])
        if not p.injuries:
            assert patterns & {"squat", "hinge"}, (d.name, p.location)


def test_back_injury_full_body_day_still_trains_legs():
    p = person(experience="beginner", location="homeDumbbells", injuries=(BACK,))
    for d in build_program(p, CAT).days:
        ids = [e.exercise_id for e in d.exercises]
        assert any(CAT[i].pattern in TR["full_body_legs"]["patterns"] for i in ids), ids
        assert len(ids) >= exercise_range(p.session_minutes)["min"]


# ── Starting weights ──

def test_starting_weights_follow_experience_and_are_capped():
    by = {exp: {e.exercise_id: e.start_weight_kg for d in build_program(person(experience=exp, weight_kg=96), CAT).days for e in d.exercises}
          for exp in ("beginner", "intermediate", "advanced")}
    assert by["beginner"]["ex_db_bench_press"] <= TR["start_load"]["max_kg"]["beginner"]["dumbbells"]
    assert by["beginner"]["ex_db_bench_press"] <= 10
    for ex, kg in by["beginner"].items():
        for other in ("intermediate", "advanced"):
            if ex in by[other]:
                assert kg <= by[other][ex], ex


def test_beginner_dumbbells_stay_light_for_heavy_people():
    p = person(experience="beginner", weight_kg=140)
    caps = TR["start_load"]["max_kg"]["beginner"]
    for d in build_program(p, CAT).days:
        for e in d.exercises:
            for eq in CAT[e.exercise_id].equipment:
                if eq in caps:
                    assert e.start_weight_kg <= caps[eq], (e.exercise_id, e.start_weight_kg)


# ── Cardio ──

@pytest.mark.parametrize("goal,sessions,minutes", [("loseFat", (2, 3), (30, 30)), ("recomp", (1, 2), (30, 30)),
                                                   ("buildMuscle", (1, 1), (15, 15)), ("strength", (1, 1), (15, 15))])
def test_cardio_by_goal(goal, sessions, minutes):
    for exp in ("beginner", "intermediate", "advanced"):
        c = build_program(person(goal=goal, experience=exp), CAT).cardio
        assert sessions[0] <= len(c.sessions) <= sessions[1]
        assert all(minutes[0] <= s.minutes <= minutes[1] for s in c.sessions)
        assert c.steps_per_day == 8000  # the recomposition guide's step goal (p. 177)
    assert len(build_program(person(goal="loseFat", experience="beginner"), CAT).cardio.sessions) == 2
    assert len(build_program(person(goal="loseFat", experience="advanced"), CAT).cardio.sessions) == 3


def test_cardio_type_by_equipment_injury_and_health():
    assert build_program(person(), CAT).cardio.sessions[0].exercise_id == "ex_incline_walk"
    assert build_program(person(location="homeDumbbells"), CAT).cardio.sessions[0].exercise_id == "ex_brisk_walk"
    knee = build_program(person(injuries=(KNEE,)), CAT).cardio
    assert {s.exercise_id for s in knee.sessions} == {"ex_bike"}  # a knee injury means the bike, not running
    assert any("knee" in r.en for r in knee.reasons)
    for loc in ("homeDumbbells", "bodyweight"):
        home_knee = build_program(person(location=loc, injuries=(KNEE,)), CAT).cardio
        assert all(CAT[s.exercise_id].pattern not in ("jump", "locomotion") for s in home_knee.sessions)
    flag = build_program(person(goal="buildMuscle", health=Health(diabetes=True)), CAT).cardio
    assert all(s.intensity == "easy" for s in flag.sessions) and any("health" in r.en for r in flag.reasons)
    assert build_program(person(goal="buildMuscle"), CAT).cardio.sessions[0].intensity == "moderate"


@pytest.mark.parametrize("p", ALL_PEOPLE[::4])
def test_cardio_is_never_the_day_before_a_leg_day(p):
    prog = build_program(p, CAT)
    kinds = {d.weekday: d.kind for d in prog.days}
    lifting = set(kinds)
    for s in prog.cardio.sessions:
        nxt = WEEK[(WEEK.index(s.weekday) + 1) % 7]
        assert kinds.get(nxt) not in ("lower", "full"), (s.weekday, kinds)
        assert (s.when == "afterLifting") == (s.weekday in lifting)


def test_cardio_goes_on_rest_days_first():
    slots = place([("sat", "upper"), ("mon", "lower"), ("wed", "upper"), ("thu", "lower")], 3)
    assert [w for _, w in slots].count("restDay") == 2
    assert ("sun", "restDay") not in slots  # Sunday is before Monday's leg day


def test_cardio_calories_are_counted_once():
    """The activity level already includes the weekly cardio, so the targets don't change with it."""
    p = person()
    t = compute_targets(p)
    prog = build_program(p, CAT)
    assert len(prog.cardio.sessions) > 0
    assert compute_targets(p).calories == t.calories  # nothing added for cardio
    assert "cardio_counted" in load_rules()["nutrition"]


# ── Swaps and alternatives ──

INJURIES = [(KNEE,), (BACK,), (SHOULDER,), (KNEE, SHOULDER)]


@pytest.mark.parametrize("injuries", INJURIES)
def test_alternatives_never_conflict_with_an_active_injury(injuries):
    vocab = get_vocab()
    for loc in ("gym", "homeDumbbells"):
        p = person(location=loc, injuries=injuries)
        for ex in (e for e in CAT.values() if e.type == "strength"):
            for a in alternatives(ex, p, CAT):
                assert allowed(a, p.injuries, vocab), (ex.id, a.id, injuries)
                assert fits_equipment(a, loc) and a.id != ex.id and a.type == "strength"


def test_alternatives_keep_the_movement_and_respect_missing_equipment():
    p = person()
    alts = alternatives(CAT["ex_lat_pulldown"], p, CAT, taken={"ex_cs_row"})
    assert 2 <= len(alts) <= TR["swaps"]["max_alternatives"]
    assert CAT[alts[0].id].pattern == "verticalPull"
    no_cable = alternatives(CAT["ex_face_pull"], p, CAT, reason="equipment", missing=("cable",))
    assert no_cable and all("cable" not in a.equipment for a in no_cable)
    assert all(a.id != "ex_cs_row" for a in alternatives(CAT["ex_one_arm_db_row"], p, CAT, taken={"ex_cs_row"}))


def test_a_from_now_on_swap_replaces_the_exercise_and_never_puts_it_back():
    p = person(days_per_week=4)
    swap = Adjustments(replace=(("ex_cs_row", "ex_one_arm_db_row", "busy"),))
    prog = build_program(p, CAT, adjust=swap)
    ids = [e.exercise_id for d in prog.days for e in d.exercises]
    assert "ex_cs_row" not in ids and "ex_one_arm_db_row" in ids
    swapped = next(e for d in prog.days for e in d.exercises if e.replaced_exercise_id == "ex_cs_row")
    assert (swapped.swap_kind, swapped.user_reason) == ("user", "busy")


def test_missing_equipment_is_never_used():
    p = person(days_per_week=4, missing_equipment=("cable", "machine"))
    prog = build_program(p, CAT)
    for d in prog.days:
        for e in d.exercises:
            assert not {"cable", "machine"} & set(CAT[e.exercise_id].equipment), e.exercise_id
        assert CAT[d.warmup["general"]["id"]].equipment != ("machine",)
    assert all("machine" not in CAT[s.exercise_id].equipment for s in prog.cardio.sessions)
