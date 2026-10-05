"""The migrations match the models, run both ways, and enforce the agreed constraints."""

import datetime as dt

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.models import Base, CheckIn, LlmCall, Plan, Profile, User
from conftest import run_migrations


def test_migrations_match_the_models(db):
    with db.get_bind().connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    assert diff == [], f"Models changed without a migration. Run: uv run alembic revision --autogenerate -m '…'\n{diff}"


def test_migrations_go_down_and_up_again(tmp_path, db_url):
    # SQLite: a new file. PostgreSQL (RAFEQI_TEST_POSTGRES_URL): this test's own database, taken down to empty first.
    url = db_url if db_url.startswith("postgresql") else f"sqlite:///{(tmp_path / 'roundtrip.db').as_posix()}"
    if url.startswith("postgresql"):
        run_migrations(url, "base", down=True)
    run_migrations(url)
    run_migrations(url, "base", down=True)
    assert set(inspect(create_engine(url)).get_table_names()) == {"alembic_version"}
    run_migrations(url)
    assert set(Base.metadata.tables) <= set(inspect(create_engine(url)).get_table_names())


def test_no_units_budget_or_price_columns():
    columns = {f"{t.name}.{c.name}" for t in Base.metadata.tables.values() for c in t.c}
    for banned in ("units", "budget", "price", "cost_egp", "brand"):
        hits = [c for c in columns if banned in c.split(".")[1] and c != "foods.units"]  # foods.units = portion sizes
        assert not hits, hits


@pytest.mark.parametrize("model,make", [
    (Plan, lambda uid, v: Plan(user_id=uid, version=v, trigger="onboarding", calories=1, maintenance_calories=1,
                               protein_g=1, carbs_g=1, fat_g=1)),
])
def test_plan_versions_are_unique_per_user(make_user, db, model, make):
    u = make_user()
    db.add(make(u.id, 1))
    db.commit()
    db.add(make(u.id, 1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(make(u.id, 2))
    db.commit()


def test_one_checkin_per_user_per_week(make_user, db):
    a, b = make_user(), make_user()
    week = dt.date(2026, 9, 26)
    db.add_all([CheckIn(user_id=a.id, week_number=3, week_start=week), CheckIn(user_id=b.id, week_number=3, week_start=week)])
    db.commit()  # different users, same week: fine
    db.add(CheckIn(user_id=a.id, week_number=3, week_start=week))
    with pytest.raises(IntegrityError):
        db.commit()


def test_checkin_note_is_at_most_300_characters(make_user, db):
    u = make_user()
    db.add(CheckIn(user_id=u.id, week_number=1, week_start=dt.date(2026, 9, 26), note="x" * 301))
    with pytest.raises(IntegrityError):
        db.commit()


def test_profile_age_must_be_adult(make_user, db):
    u = make_user()
    db.get(Profile, u.id).age = 17
    with pytest.raises(IntegrityError):
        db.commit()


def test_llm_call_keeps_its_row_when_user_is_deleted(make_user, db):
    u = make_user()
    db.add(LlmCall(user_id=u.id, task="weekly_review", model="m"))
    db.commit()
    db.delete(db.get(User, u.id))
    db.commit()
    db.expire_all()
    calls = db.query(LlmCall).all()
    assert len(calls) == 1 and calls[0].user_id is None


def test_text_columns_are_long_enough_for_their_values():
    """SQLite never checks VARCHAR lengths; PostgreSQL does. Values the code writes must fit (found by running the
    suite on PostgreSQL: RAFEQI_TEST_POSTGRES_URL)."""
    from app.engine.rules import rules_version
    from app.models import ProgramExercise

    assert len(rules_version()) <= Plan.__table__.c.rules_version.type.length
    kinds = ("swapped", "added", "equipment", "review", "user")
    assert max(map(len, kinds)) <= ProgramExercise.__table__.c.swap_kind.type.length
    triggers = ("onboarding", "checkin", "regenerate", "injury", "swap", "pain", "equipment")
    assert max(map(len, triggers)) <= Plan.__table__.c.trigger.type.length
