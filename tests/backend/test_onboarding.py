"""The onboarding questionnaire: saved step by step, validated, resumable, then completed."""

import re
from pathlib import Path

import pytest

from app.schemas.onboarding import ALLERGIES, FOODS

ROOT = Path(__file__).resolve().parents[2]

ABOUT = {"sex": "male", "age": 29, "heightCm": 180, "weightKg": 88, "waistCm": 96}
GOAL = {"goal": "loseFat", "pace": "steady"}
TRAINING = {"experience": "intermediate", "daysPerWeek": 4, "sessionMinutes": 60, "location": "gym", "dailyActivity": "onFeet"}
INJURIES = {"injuries": [{"region": "shoulderL", "side": "left", "type": "tendon", "severity": 3,
                          "painfulMovements": ["overheadPress", "benchPress"], "restrictions": ["noOverhead"]}]}
HEALTH = {"heartCondition": False, "diabetes": False, "pregnancy": False, "recentSurgery": False, "exerciseMedication": False}
FOOD = {"mealsPerDay": 4, "dislikes": ["liver", "eggplant"], "allergies": ["none"], "fasting": ["ramadan"], "cookingMinutes": 30}
ALL = {"about": ABOUT, "goal": GOAL, "training": TRAINING, "injuries": INJURIES, "health": HEALTH, "food": FOOD}


def answer_all(client, **overrides):
    for step, body in ALL.items():
        r = client.put(f"/api/onboarding/{step}", json=overrides.get(step, body))
        assert r.status_code == 200, (step, r.text)
    return r.json()


def test_new_account_starts_at_the_first_step(make_user):
    s = make_user().client.get("/api/onboarding").json()
    assert (s["step"], s["completed"], s["about"], s["injuries"]) == ("about", False, None, [])
    assert s["missing"] == ["about", "goal", "training", "injuries", "health", "food"]


def test_answers_are_saved_step_by_step_and_resume_where_you_left_off(make_user):
    c = make_user().client
    c.put("/api/onboarding/about", json=ABOUT)
    s = c.put("/api/onboarding/goal", json=GOAL).json()
    assert s["step"] == "training" and s["about"] == ABOUT and s["goal"] == GOAL
    # Going back and changing an earlier step doesn't move the resume point back.
    s = c.put("/api/onboarding/about", json=ABOUT | {"weightKg": 87.5}).json()
    assert s["step"] == "training" and s["about"]["weightKg"] == 87.5
    assert c.get("/api/onboarding").json()["missing"] == ["training", "injuries", "health", "food"]


def test_full_questionnaire_then_complete(make_user):
    u = make_user()
    s = answer_all(u.client)
    assert s["step"] == "review" and s["missing"] == [] and not s["completed"]
    assert u.client.get("/api/me").json()["onboardingComplete"] is False
    done = u.client.post("/api/onboarding/complete").json()
    assert done["completed"] is True
    assert u.client.get("/api/me").json()["onboardingComplete"] is True
    assert done["food"] == FOOD and done["training"] == TRAINING and done["health"] == HEALTH
    [inj] = done["injuries"]
    assert (inj["region"], inj["status"], inj["painfulMovements"]) == ("shoulderL", "active", ["overheadPress", "benchPress"])


def test_complete_lists_what_is_missing(make_user):
    c = make_user().client
    c.put("/api/onboarding/about", json=ABOUT)
    r = c.post("/api/onboarding/complete")
    assert r.status_code == 422
    assert r.json()["detail"] == {"error": "onboarding_incomplete", "missing": ["goal", "training", "injuries", "health", "food"]}


def test_no_injuries_is_an_answer(make_user):
    c = make_user().client
    s = answer_all(c, injuries={"injuries": []})
    assert s["injuries"] == [] and s["injuriesAnswered"] is True and s["missing"] == []


def test_injuries_step_replaces_the_list(make_user):
    c = make_user().client
    first = c.put("/api/onboarding/injuries", json=INJURIES).json()["injuries"][0]
    knee = {"region": "kneeR", "side": "right", "type": "sprain", "severity": 2, "painfulMovements": ["squat"], "restrictions": []}
    changed = INJURIES["injuries"][0] | {"severity": 4}
    s = c.put("/api/onboarding/injuries", json={"injuries": [changed, knee]}).json()
    by_region = {i["region"]: i for i in s["injuries"]}
    assert by_region["shoulderL"]["id"] == first["id"] and by_region["shoulderL"]["severity"] == 4  # same row, updated
    assert set(by_region) == {"shoulderL", "kneeR"}
    s = c.put("/api/onboarding/injuries", json={"injuries": [knee]}).json()
    assert [i["region"] for i in s["injuries"]] == ["kneeR"]


def test_any_health_yes_makes_the_plan_conservative(make_user):
    c = make_user().client
    assert c.put("/api/onboarding/health", json=HEALTH | {"diabetes": True}).json()["conservative"] is True
    assert c.put("/api/onboarding/health", json=HEALTH).json()["conservative"] is False


@pytest.mark.parametrize("step,body,error", [
    ("about", ABOUT | {"age": 17}, "must_be_adult"),
    ("about", ABOUT | {"age": 91}, "age_out_of_range"),
    ("about", ABOUT | {"heightCm": 300}, "less than or equal to 220"),
    ("about", ABOUT | {"weightKg": 20}, "greater than or equal to 35"),
    ("about", ABOUT | {"sex": "other"}, "male"),
    ("goal", GOAL | {"goal": "getHuge"}, "loseFat"),
    ("training", TRAINING | {"daysPerWeek": 7}, "less than or equal to 6"),
    ("training", TRAINING | {"sessionMinutes": 50}, "45"),
    ("injuries", {"injuries": [INJURIES["injuries"][0] | {"painfulMovements": ["overheadPres"]}]}, "overheadPres"),
    ("injuries", {"injuries": INJURIES["injuries"] * 2}, "one_injury_per_region"),
    ("injuries", {"injuries": [INJURIES["injuries"][0] | {"severity": 6}]}, "less than or equal to 5"),
    ("health", {k: v for k, v in HEALTH.items() if k != "diabetes"}, "Field required"),
    ("food", FOOD | {"dislikes": ["pizza"]}, "unknown_food: pizza"),
    ("food", FOOD | {"allergies": ["none", "nuts"]}, "none_with_allergies"),
    ("food", FOOD | {"mealsPerDay": 6}, "less than or equal to 5"),
    ("food", FOOD | {"cookingMinutes": 45}, "15"),
    ("food", FOOD | {"extra": 1}, "Extra inputs are not permitted"),
])
def test_bad_answers_are_refused(make_user, step, body, error):
    c = make_user().client
    r = c.put(f"/api/onboarding/{step}", json=body)
    assert r.status_code == 422 and error in r.text, r.text
    assert c.get("/api/onboarding").json()["step"] == "about"  # nothing saved


def test_onboarding_needs_login(client_factory):
    c = client_factory()
    assert c.get("/api/onboarding").status_code == 401
    assert c.put("/api/onboarding/about", json=ABOUT).status_code == 401


def test_answers_can_be_changed_after_completing(make_user):
    c = make_user().client
    answer_all(c)
    c.post("/api/onboarding/complete")
    s = c.put("/api/onboarding/training", json=TRAINING | {"daysPerWeek": 3}).json()
    assert s["completed"] is True and s["training"]["daysPerWeek"] == 3


def test_daily_activity_is_required_when_the_training_step_is_saved(make_user):
    c = make_user().client
    no_answer = {k: v for k, v in TRAINING.items() if k != "dailyActivity"}
    assert c.put("/api/onboarding/training", json=no_answer).status_code == 422
    assert c.put("/api/onboarding/training", json=TRAINING | {"dailyActivity": "standing"}).status_code == 422
    for answer in ("sitting", "onFeet", "active"):
        s = c.put("/api/onboarding/training", json=TRAINING | {"dailyActivity": answer}).json()
        assert s["training"]["dailyActivity"] == answer


def test_frontend_food_options_match():
    src = (ROOT / "frontend" / "src" / "constants.ts").read_text(encoding="utf-8")

    def ids(const: str) -> tuple[str, ...]:
        return tuple(re.findall(r"'([^']+)'", re.search(rf"export const {const} = \[(.*?)\]", src, re.S).group(1)))

    assert ids("FOODS") == FOODS and ids("ALLERGIES") == ALLERGIES
