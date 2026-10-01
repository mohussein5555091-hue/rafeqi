"""Hard requirement 2: every user sees only their own data.

1. Every table is classified: user data (must have user_id) or shared catalogue. A new table fails
   the test until someone decides which it is.
2. Every endpoint is classified. A new endpoint fails the test until it's listed here, and every
   endpoint that takes an id is attacked with another user's id.
"""

from sqlalchemy import func, inspect, select

from app.models import Base, WeightLog
from populate import populate

CATALOGUE = {"exercises", "exercise_substitutions", "foods", "grocery_items", "food_grocery_items", "recipes",
             "recipe_ingredients", "recipe_steps"}
NOT_USER_DATA = {"login_attempts"}  # keyed by email hash and IP; may not belong to any account

# Every endpoint, and how it's kept to the logged-in user.
PUBLIC = {("GET", "/api/health"), ("POST", "/api/auth/signup"), ("POST", "/api/auth/login")}
SELF_ONLY = {  # no id in the URL: they act on the logged-in user by construction
    ("POST", "/api/auth/logout"), ("POST", "/api/auth/change-password"),
    ("GET", "/api/me"), ("PATCH", "/api/me"), ("DELETE", "/api/me"),
    ("GET", "/api/weights"), ("POST", "/api/weights"),
    ("GET", "/api/onboarding"), ("POST", "/api/onboarding/complete"),
    ("GET", "/api/plan"), ("POST", "/api/plan"),
    *(("PUT", f"/api/onboarding/{step}") for step in ("about", "goal", "training", "injuries", "health", "food")),
}
BY_ID = {  # id in the URL: tested below with another user's id
    ("DELETE", "/api/weights/{weight_id}"): "weight_logs",
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
    unclassified = routes - PUBLIC - SELF_ONLY - set(BY_ID)
    assert not unclassified, f"Classify these endpoints in test_isolation.py and test them with another user's data: {sorted(unclassified)}"


def test_user_a_cannot_touch_user_b_rows_by_id(make_user, db):
    a, b = make_user(), make_user()
    b_ids = populate(db, b.id)
    for (method, path), table in BY_ID.items():
        url = path.replace("{" + path.split("{")[1].split("}")[0] + "}", b_ids[table])
        r = a.client.request(method, url)
        assert r.status_code == 404, f"{method} {path} with B's id answered {r.status_code} for A"
    # B's rows are all still there.
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(WeightLog).where(WeightLog.user_id == b.id)) == 1


def test_lists_only_show_your_own_rows(make_user, db):
    a, b = make_user(), make_user()
    populate(db, b.id)
    a.client.post("/api/weights", json={"weightKg": 70.2})
    rows = a.client.get("/api/weights").json()
    assert [r["weightKg"] for r in rows] == [70.2]
    assert a.client.get("/api/me").json()["id"] == a.id


def test_a_cannot_change_b_through_self_endpoints(make_user, db):
    a, b = make_user(), make_user()
    a.client.patch("/api/me", json={"firstName": "Changed", "language": "ar"})
    a.client.post("/api/weights", json={"weightKg": 71})
    me_b = b.client.get("/api/me").json()
    assert (me_b["firstName"], me_b["language"]) == ("Omar", "en")
    assert b.client.get("/api/weights").json() == []
    assert inspect(db.get_bind()).has_table("users")
