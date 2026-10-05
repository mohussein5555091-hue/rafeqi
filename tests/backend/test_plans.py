"""Plans in the database: built after onboarding, versioned, private, and updated by the weekly review."""

import datetime as dt

import pytest
from sqlalchemy import select

from app import clock
from app.catalogue import read_exercises, seed_exercises
from app.config import get_settings
from app.food_catalogue import read_food_catalogue, seed_food_catalogue
from app.models import CheckIn, CheckInAnswer, GroceryListItem, Injury, PantryItem, Plan, WeeklyReview, WeightLog
from app.plans import current_plan, person_for, regenerate_grocery_list, run_weekly_review, week_start
from app.vocab import get_vocab
from test_onboarding import ALL, answer_all

SHOULDER_EXERCISES = {"ex_bb_bench_press", "ex_ohp", "ex_db_shoulder_press", "ex_pull_up", "ex_db_bench_press"}


@pytest.fixture
def catalogue(db):
    seed_exercises(db, read_exercises(get_settings().catalogue_dir / "exercises.yaml", get_vocab()))
    seed_food_catalogue(db, read_food_catalogue(get_settings().catalogue_dir))
    db.commit()


@pytest.fixture
def onboarded(make_user, catalogue):
    u = make_user()
    answer_all(u.client)
    assert u.client.post("/api/onboarding/complete").status_code == 200
    return u


def test_week_starts_on_saturday():
    assert week_start(dt.date(2026, 10, 1)) == dt.date(2026, 9, 26)   # Thursday → the Saturday before
    assert week_start(dt.date(2026, 10, 3)) == dt.date(2026, 10, 3)   # Saturday → itself


def test_no_plan_before_onboarding(make_user, catalogue):
    c = make_user().client
    assert c.post("/api/plan").status_code == 409
    assert c.get("/api/plan").status_code == 404


def test_plan_after_onboarding(onboarded):
    plan = onboarded.client.post("/api/plan").json()
    assert plan["version"] == 1 and plan["trigger"] == "onboarding"
    assert {"calories", "protein", "fat", "carbs", "training", "meals"} <= set(plan["reasons"])
    assert len(plan["program"]["days"]) == ALL["training"]["daysPerWeek"]
    assert len(plan["meals"]) == 7 * ALL["food"]["mealsPerDay"]
    assert {g["period"] for g in plan["grocery"]} == {"week", "month"}
    used = {e["exerciseId"] for d in plan["program"]["days"] for e in d["exercises"]}
    assert not used & SHOULDER_EXERCISES  # left shoulder: no overhead press, bench press or dips
    assert any(e["swapKind"] == "swapped" and e["injuryId"] for d in plan["program"]["days"] for e in d["exercises"])
    assert onboarded.client.get("/api/plan").json()["id"] == plan["id"]


def test_regenerating_makes_a_new_version(onboarded, db):
    first = onboarded.client.post("/api/plan").json()
    onboarded.client.put("/api/onboarding/training", json=ALL["training"] | {"daysPerWeek": 3})
    second = onboarded.client.post("/api/plan").json()
    assert (second["version"], second["trigger"]) == (2, "regenerate")
    assert len(second["program"]["days"]) == 3
    statuses = {p.version: p.status for p in db.scalars(select(Plan).where(Plan.user_id == onboarded.id))}
    assert statuses == {1: "superseded", 2: "active"}
    assert onboarded.client.get("/api/plan").json()["id"] != first["id"]


def test_plans_are_private(onboarded, make_user):
    onboarded.client.post("/api/plan")
    other = make_user()
    assert other.client.get("/api/plan").status_code == 404


def test_pantry_changes_the_grocery_list(onboarded, db):
    onboarded.client.post("/api/plan")
    plan = current_plan(db, onboarded.id)
    from app.models import MealPlan
    mp = db.scalar(select(MealPlan).where(MealPlan.plan_id == plan.id))
    db.add(PantryItem(user_id=onboarded.id, grocery_item_id="gi_rice", level="plenty", updated_at=clock.now()))
    gl = regenerate_grocery_list(db, onboarded.id, mp)
    db.commit()
    rice = db.scalar(select(GroceryListItem).where(GroceryListItem.grocery_list_id == gl.id, GroceryListItem.grocery_item_id == "gi_rice"))
    assert rice is not None and rice.have_it


def checkin(db, user_id, answers: dict, *, weights_last=(88.0, 88.0), weights_this=(88.0, 88.0), start=None) -> CheckIn:
    start = start or week_start(clock.today())
    for i, kg in enumerate(weights_last):
        db.add(WeightLog(user_id=user_id, date=start - dt.timedelta(days=7 - i), weight_kg=kg, source="daily", created_at=clock.now(), updated_at=clock.now()))
    for i, kg in enumerate(weights_this):
        db.add(WeightLog(user_id=user_id, date=start + dt.timedelta(days=i), weight_kg=kg, source="daily", created_at=clock.now(), updated_at=clock.now()))
    ci = CheckIn(user_id=user_id, week_number=1, week_start=start, status="submitted", submitted_at=clock.now(), weight_kg=weights_this[-1])
    db.add(ci)
    db.flush()
    for qid, value in answers.items():
        db.add(CheckInAnswer(user_id=user_id, checkin_id=ci.id, question_id=qid, value={"value": value}, answered_at=clock.now()))
    db.commit()
    return ci


BASE = {"sessions_done": 4, "difficulty": 3, "soreness": 2, "sharp_pain": False, "swelling": False, "numbness": False,
        "adherence_pct": 90, "hunger": 3, "sleep": 4, "energy": 4, "stress": 2, "days_available": 4}


def test_weekly_review_makes_a_new_version_with_its_changes(onboarded, db):
    onboarded.client.post("/api/plan")
    before = current_plan(db, onboarded.id)
    ci = checkin(db, onboarded.id, BASE | {"exercise_feedback": [{"exercise_id": "ex_cs_row", "feel": "uncomfortable"}]})
    review = run_weekly_review(db, onboarded.id, ci.id)
    db.commit()
    after = current_plan(db, onboarded.id)
    assert (review.plan_before_id, review.plan_after_id) == (before.id, after.id)
    assert after.version == before.version + 1 and after.trigger == "checkin"
    kinds = [c["kind"] for c in review.changes]
    # The plan is days old: calories wait for the 2-week review (the weekly check-in still changed the exercise).
    assert "calories" in kinds and after.calories == before.calories
    assert any("every 2 weeks" in c["why"]["en"] for c in review.changes if c["kind"] == "calories")
    plan = onboarded.client.get("/api/plan").json()
    assert "ex_cs_row" not in {e["exerciseId"] for d in plan["program"]["days"] for e in d["exercises"]}
    assert plan["reasons"]["review"]
    assert db.scalar(select(WeeklyReview).where(WeeklyReview.user_id == onboarded.id)).state == "ready"


def test_calories_change_once_two_weeks_have_passed(onboarded, db, clock):
    onboarded.client.post("/api/plan")
    before = current_plan(db, onboarded.id)
    clock.advance(days=15)
    ci = checkin(db, onboarded.id, BASE)  # the same weight both weeks on a fat-loss plan: too slow
    run_weekly_review(db, onboarded.id, ci.id)
    db.commit()
    after = current_plan(db, onboarded.id)
    expected = (before.calories - before.maintenance_calories) * 7 / 7700  # kg a week
    step = 10 * round(min(max(abs(expected) * 1100, 100), 250) / 10)  # the book's 100-250 kcal down
    assert after.calories == before.calories - step


def test_red_flag_pauses_the_area_and_skips_the_normal_review(onboarded, db):
    onboarded.client.post("/api/plan")
    before = current_plan(db, onboarded.id)
    inj = db.scalar(select(Injury).where(Injury.user_id == onboarded.id))
    ci = checkin(db, onboarded.id, BASE | {"sharp_pain": True, "injury_pain": [{"injury_id": inj.id, "pain": 5, "trend": "same"}]})
    review = run_weekly_review(db, onboarded.id, ci.id)
    db.commit()
    assert review.red_flag and review.status == "warning"
    db.refresh(inj)
    assert inj.paused_at is not None
    after = current_plan(db, onboarded.id)
    assert after.calories == before.calories  # nothing else changes
    plan = onboarded.client.get("/api/plan").json()
    shoulder = [e for d in plan["program"]["days"] for e in d["exercises"] if e["exerciseId"] in
                {"ex_db_floor_press", "ex_landmine_press", "ex_lat_pulldown", "ex_cs_row", "ex_face_pull"}]
    assert shoulder == []  # every exercise loading the shoulder is paused
    assert any("doctor or physiotherapist" in r["en"] for r in plan["reasons"]["training"])


def test_people_who_answered_before_the_question_keep_their_plan_until_their_next_edit(onboarded, db):
    """Finished before daily activity was asked: still complete (no missing step), the answer shows as empty, and the
    plan counts them as on their feet part of the day; saving the training step again then needs the answer."""
    from app.models import Profile

    u = onboarded
    db.get(Profile, u.id).daily_activity = None  # as for someone who answered before the question existed
    db.commit()
    s = u.client.get("/api/onboarding").json()
    assert s["completed"] and s["missing"] == [] and s["training"]["dailyActivity"] is None
    assert person_for(db, u.id).daily_activity is None
    assert u.client.post("/api/plan").status_code == 200
    reasons = [r["en"] for r in u.client.get("/api/plan").json()["reasons"]["calories"]]
    assert any("Until you answer the daily-activity question" in r for r in reasons)
