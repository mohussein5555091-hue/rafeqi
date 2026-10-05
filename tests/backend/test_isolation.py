"""Hard requirement 2: every user sees only their own data.

1. Every table is classified: user data (must have user_id) or shared catalogue. A new table fails
   the test until someone decides which it is.
2. Every endpoint is classified. A new endpoint fails the test until it's listed here, and every
   endpoint that takes an id is attacked with another user's id.
"""

import re

from sqlalchemy import func, inspect, select

from app.catalogue import read_exercises, seed_exercises
from app.config import get_settings
from app.food_catalogue import read_food_catalogue, seed_food_catalogue
from app.models import Base, ExerciseSwap, Injury, MealIngredientChange, WeightLog
from app.vocab import get_vocab
from populate import populate
from test_onboarding import answer_all

CATALOGUE = {"exercises", "exercise_substitutions", "foods", "grocery_items", "food_grocery_items", "recipes",
             "recipe_ingredients", "recipe_steps"}
NOT_USER_DATA = {"login_attempts"}  # keyed by email hash and IP; may not belong to any account

# Every endpoint, and how it's kept to the logged-in user.
PUBLIC = {("GET", "/api/health"), ("POST", "/api/auth/signup"), ("POST", "/api/auth/login")}
CATALOGUE_READS = {  # login required, but they only read the shared catalogue (the recipe is scaled to your own plan)
    ("GET", "/api/exercises"), ("GET", "/api/exercises/{exercise_id}"), ("GET", "/api/recipes/{recipe_id}"),
    ("GET", "/api/checkins/questions"),  # the fixed questions from data/checkin_questions.yaml
}
SELF_ONLY = {  # no id in the URL: they act on the logged-in user by construction
    ("POST", "/api/auth/logout"), ("POST", "/api/auth/change-password"),
    ("GET", "/api/me"), ("PATCH", "/api/me"), ("DELETE", "/api/me"), ("GET", "/api/me/equipment"), ("PUT", "/api/me/equipment"),
    ("GET", "/api/weights"), ("POST", "/api/weights"),
    ("GET", "/api/onboarding"), ("POST", "/api/onboarding/complete"),
    ("GET", "/api/plan"), ("POST", "/api/plan"), ("GET", "/api/plan/why"),
    ("GET", "/api/workouts/week"), ("GET", "/api/meals/week"), ("GET", "/api/meals/day/{date}"),  # a date, not a row id
    ("GET", "/api/groceries"), ("GET", "/api/pantry"), ("GET", "/api/injuries"), ("POST", "/api/injuries"),
    ("GET", "/api/checkins/next"), ("GET", "/api/checkins/draft"), ("POST", "/api/checkins"),
    ("GET", "/api/reviews"), ("GET", "/api/progress"),
    ("GET", "/api/cardio/{weekday}"), ("PUT", "/api/cardio/{weekday}"), ("DELETE", "/api/cardio/{weekday}"),  # a weekday, not a row id
    ("GET", "/api/swaps"),
    *(("PUT", f"/api/onboarding/{step}") for step in ("about", "goal", "training", "injuries", "health", "food")),
}
RESULT = {"sets": 3, "reps": 10, "weightKg": 20, "struggled": False}
INJURY = {"region": "shoulderL", "side": "left", "type": "tendon", "severity": 2, "painfulMovements": [], "restrictions": [],
          "status": "active"}
BY_ID = {  # id in the URL: tested below with another user's id → (the table the id comes from, a valid request body)
    ("DELETE", "/api/weights/{weight_id}"): ("weight_logs", None),
    ("GET", "/api/workouts/{day_id}"): ("program_days", None),
    ("PUT", "/api/workouts/{day_id}/exercises/{exercise_id}"): ("program_days", RESULT),
    ("DELETE", "/api/workouts/{day_id}/exercises/{exercise_id}"): ("program_days", None),
    ("POST", "/api/workouts/{day_id}/finish"): ("program_days", {"effort": 7}),
    ("GET", "/api/meals/{item_id}/swap-options"): ("meal_plan_items", None),
    ("POST", "/api/meals/{item_id}/swap"): ("meal_plan_items", {"recipeId": "r_test"}),
    ("GET", "/api/meals/{item_id}/ingredients/{food_id}/replacements"): ("meal_plan_items", None),
    ("POST", "/api/meals/{item_id}/ingredients/{food_id}/remove"): ("meal_plan_items", {"reason": "dislike", "scope": "always"}),
    ("DELETE", "/api/meals/{item_id}/ingredients/{food_id}"): ("meal_plan_items", None),
    ("PATCH", "/api/groceries/items/{item_id}"): ("grocery_list_items", {"checked": True}),
    ("GET", "/api/injuries/{injury_id}"): ("injuries", None),
    ("PUT", "/api/injuries/{injury_id}"): ("injuries", INJURY),
    ("DELETE", "/api/injuries/{injury_id}"): ("injuries", None),
    ("GET", "/api/reviews/{review_id}"): ("weekly_reviews", None),
    ("GET", "/api/workouts/{day_id}/exercises/{exercise_id}/alternatives"): ("program_days", None),
    ("POST", "/api/workouts/{day_id}/exercises/{exercise_id}/swap"): ("program_days", {"toExerciseId": "ex_test", "reason": "busy", "scope": "today"}),
    ("PUT", "/api/workouts/{day_id}/warmup"): ("program_days", {"done": True}),
    ("PUT", "/api/workouts/{day_id}/cooldown"): ("program_days", {"done": True}),
    ("GET", "/api/workouts/{day_id}/move-options"): ("program_days", None),
    ("POST", "/api/workouts/{day_id}/move"): ("program_days", {"date": "2026-10-01"}),
    ("DELETE", "/api/swaps/{swap_id}"): ("exercise_swaps", None),
    ("PUT", "/api/checkins/{checkin_id}/photos/{view}"): ("checkins", None),
    ("GET", "/api/photos/{checkin_id}/{view}"): ("checkins", None),
}


def test_every_table_is_classified_and_user_tables_have_user_id():
    for name, table in Base.metadata.tables.items():
        if name in CATALOGUE | NOT_USER_DATA:
            assert "user_id" not in table.c, f"{name} is catalogue but has user_id"
            continue
        if name == "users":
            continue
        assert "user_id" in table.c, f"{name} holds user data but has no user_id column"
        assert any(fk.column.table.name == "users" for fk in table.c.user_id.foreign_keys), f"{name}.user_id isn't linked to users"


def test_populate_covers_every_user_table(make_user, db):
    u = make_user()
    populate(db, u.id)
    user_tables = [t for n, t in Base.metadata.tables.items() if "user_id" in t.c]
    for table in user_tables:
        n = db.scalar(select(func.count()).select_from(table).where(table.c.user_id == u.id))
        assert n >= 1, f"populate() doesn't create a {table.name} row; add one so isolation and deletion tests cover it"


def test_every_endpoint_is_classified(client_factory):
    routes = {(m.upper(), p) for p, ops in client_factory().app.openapi()["paths"].items() for m in ops}
    unclassified = routes - PUBLIC - CATALOGUE_READS - SELF_ONLY - set(BY_ID)
    assert not unclassified, f"Classify these endpoints in test_isolation.py and test them with another user's data: {sorted(unclassified)}"


def _attack(a, b_ids: dict[str, str]) -> None:
    for (method, path), (table, body) in BY_ID.items():
        url = re.sub(r"\{\w+_id\}", b_ids[table], path, count=1).replace("{exercise_id}", "ex_test").replace("{food_id}", "food_test")
        r = a.client.request(method, url, json=body)
        assert r.status_code == 404, f"{method} {path} with B's id answered {r.status_code} for A: {r.text}"


def test_user_a_cannot_touch_user_b_rows_by_id(make_user, db):
    a, b = make_user(), make_user()
    b_ids = populate(db, b.id)
    _attack(a, b_ids)
    # B's rows are all still there.
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(WeightLog).where(WeightLog.user_id == b.id)) == 1
    assert db.scalar(select(func.count()).select_from(Injury).where(Injury.user_id == b.id)) == 1
    assert db.scalar(select(func.count()).select_from(ExerciseSwap).where(ExerciseSwap.user_id == b.id, ExerciseSwap.ended_at.is_(None))) == 1
    assert db.scalar(select(func.count()).select_from(MealIngredientChange).where(MealIngredientChange.user_id == b.id)) == 1


def test_a_with_a_plan_still_cannot_reach_b_rows(make_user, db):
    """The same attack when A has a plan of their own, so "no plan yet" can't be what stops it."""
    seed_exercises(db, read_exercises(get_settings().catalogue_dir / "exercises.yaml", get_vocab()))
    seed_food_catalogue(db, read_food_catalogue(get_settings().catalogue_dir))
    db.commit()
    a, b = make_user(), make_user()
    answer_all(a.client)
    a.client.post("/api/onboarding/complete")
    assert a.client.post("/api/plan").status_code == 200
    _attack(a, populate(db, b.id))
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Injury).where(Injury.user_id == b.id)) == 1


def test_lists_only_show_your_own_rows(make_user, db):
    a, b = make_user(), make_user()
    populate(db, b.id)
    a.client.post("/api/weights", json={"weightKg": 70.2})
    rows = a.client.get("/api/weights").json()
    assert [r["weightKg"] for r in rows] == [70.2]
    assert a.client.get("/api/me").json()["id"] == a.id
    assert a.client.get("/api/plan/why").status_code == 404  # B's plan is never A's "why"


def test_a_cannot_change_b_through_self_endpoints(make_user, db):
    a, b = make_user(), make_user()
    a.client.patch("/api/me", json={"firstName": "Changed", "language": "ar"})
    a.client.post("/api/weights", json={"weightKg": 71})
    me_b = b.client.get("/api/me").json()
    assert (me_b["firstName"], me_b["language"]) == ("Omar", "en")
    assert b.client.get("/api/weights").json() == []
    assert inspect(db.get_bind()).has_table("users")
