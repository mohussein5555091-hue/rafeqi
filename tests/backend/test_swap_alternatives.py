"""Swap alternatives keep the movement direction (push stays push, pull stays pull, knee- and hip-dominant leg
exercises stay so) and the main muscles (bug report: a curl was offered a triceps pushdown, a leg extension a deadlift)."""

import pytest

from app.engine.rules import load_rules
from app.engine.training import alternatives, direction
from app.engine.types import InjuryInfo, Person
from engine_fixtures import exercise_catalogue

CAT = exercise_catalogue()
STRENGTH = sorted(i for i, e in CAT.items() if e.type == "strength")
PEOPLE = {
    "gym": dict(location="gym"),
    "home": dict(location="homeDumbbells"),
    "bodyweight": dict(location="bodyweight"),
    "back": dict(location="gym", injuries=(InjuryInfo("b", "lowerBack", painful_movements=("squat", "deadlift")),)),
    "shoulder": dict(location="gym", injuries=(InjuryInfo("s", "shoulderL", painful_movements=("overheadPress", "benchPress"),
                                                          restrictions=("noOverhead",)),)),
    "no-machines": dict(location="gym", missing_equipment=("machine", "cable")),
}


def person(**kw) -> Person:
    base = dict(sex="male", age=30, height_cm=178, weight_kg=85, goal="loseFat", pace="steady", experience="intermediate",
                days_per_week=4, session_minutes=60, location="gym", meals_per_day=3, cooking_minutes=30)
    return Person(**(base | kw))


def test_every_strength_pattern_has_a_direction():
    for i in STRENGTH:
        assert direction(CAT[i].pattern) is not None, (i, CAT[i].pattern)
    named = [p for ps in load_rules()["training"]["swaps"]["directions"].values() for p in ps]
    assert len(named) == len(set(named))  # each pattern in one direction only


@pytest.mark.parametrize("who", PEOPLE)
@pytest.mark.parametrize("reason", ["busy", "cantDo", "pain", "equipment"])
def test_alternatives_keep_direction_and_main_muscles(who, reason):
    p = person(**PEOPLE[who])
    for ex_id in STRENGTH:
        ex = CAT[ex_id]
        for a in alternatives(ex, p, CAT, reason=reason):
            assert direction(a.pattern) == direction(ex.pattern), (ex_id, a.id)
            assert a.pattern == ex.pattern or set(a.muscles) & set(ex.muscles), (ex_id, a.id)


def test_the_reported_cases():
    p = person()
    assert "ex_pushdown" not in {a.id for a in alternatives(CAT["ex_incline_curl"], p, CAT, reason="busy")}
    assert "ex_incline_curl" not in {a.id for a in alternatives(CAT["ex_pushdown"], p, CAT, reason="busy")}
    leg_ext = {a.id for a in alternatives(CAT["ex_leg_extension"], p, CAT, reason="busy")}
    assert not leg_ext & {"ex_bb_deadlift", "ex_db_rdl", "ex_glute_bridge", "ex_seated_leg_curl"}
