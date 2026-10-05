"""One workout log per person per day (data/REVIEW.md F1): the database refuses a second one, starting today's log
when another save just did reuses that log, and the migration merges duplicates that already exist."""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.models import WorkoutLog
from app.workouts import exercise_results
from app.views import training as views
from conftest import run_migrations
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import planned, today_session  # noqa: F401 (fixtures)

BEFORE = "46d696142439"  # the revision before uq_workout_logs_user_date


def test_the_database_refuses_a_second_log_for_the_same_day(planned, db):  # noqa: F811
    c = planned.client
    s = today_session(c)
    assert c.put(f"/api/workouts/{s['id']}/exercises/{s['exercises'][0]['exerciseId']}",
                 json={"sets": 3, "reps": 8, "weightKg": 20, "struggled": False}).status_code == 204
    log = db.scalar(sa.select(WorkoutLog).where(WorkoutLog.user_id == planned.id))
    db.add(WorkoutLog(user_id=planned.id, plan_id=log.plan_id, program_day_id=log.program_day_id, week_number=log.week_number,
                      date=log.date, started_at=log.started_at))
    with pytest.raises(IntegrityError):
        db.flush()


def test_a_save_that_finds_no_log_but_loses_the_race_uses_the_one_just_started(planned, db, monkeypatch):  # noqa: F811
    """Two saves at once: both look for today's log and find none; the second one to insert hits the unique rule and
    reads the log the first one made instead of failing."""
    c = planned.client
    s = today_session(c)
    first, second = s["exercises"][0]["exerciseId"], s["exercises"][1]["exerciseId"]
    assert c.put(f"/api/workouts/{s['id']}/exercises/{first}", json={"sets": 3, "reps": 8, "weightKg": 20, "struggled": False}).status_code == 204
    real, calls = views.session_log, []

    def misses_once(db_, user_id, d):  # the first look finds nothing, as if the other save hadn't committed yet
        calls.append(d)
        return None if len(calls) == 1 else real(db_, user_id, d)

    monkeypatch.setattr(views, "session_log", misses_once)
    assert c.put(f"/api/workouts/{s['id']}/exercises/{second}", json={"sets": 2, "reps": 10, "weightKg": 12, "struggled": False}).status_code == 204
    logs = list(db.scalars(sa.select(WorkoutLog).where(WorkoutLog.user_id == planned.id)))
    assert len(logs) == 1 and len(calls) == 2
    assert set(exercise_results(db, logs[0].id)) == {first, second}


def insert(conn, table: str, values: dict) -> None:
    """A row with these values; any other NOT NULL column without a default gets an empty value of its type."""
    for _, name, type_, notnull, default, pk in conn.execute(sa.text(f"PRAGMA table_info({table})")).all():
        if notnull and default is None and not pk and name not in values:
            values[name] = 0 if any(t in type_.upper() for t in ("INT", "FLOAT", "REAL", "NUMERIC", "BOOL")) else "[]" if "JSON" in type_.upper() else ""
    cols = ", ".join(values)
    conn.execute(sa.text(f"INSERT INTO {table} ({cols}) VALUES ({', '.join(':' + c for c in values)})"), values)


def test_the_migration_merges_duplicate_logs(tmp_path):
    """Also proves SQLite migrations keep dependent rows: workout_logs is rebuilt (copy, drop, rename) to add the rule, and
    the set logs and pain logs that point at it survive (foreign keys are off while migrating, migrations/env.py)."""
    url = f"sqlite:///{(tmp_path / 'dup.db').as_posix()}"
    run_migrations(url, BEFORE)
    engine = sa.create_engine(url)
    now, day = "2026-10-05 08:00:00", "2026-10-05"  # as text: the sqlite3 date adapters are deprecated
    ids = {k: str(uuid.uuid4()) for k in ("user", "a", "b", "c", "injury", "pain")}
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO users (id, email, password_hash, first_name, last_name, language, theme, adult_confirmed_at, created_at) "
                             "VALUES (:id, 'x@example.com', 'h', 'X', '', 'en', 'system', :t, :t)"), {"id": ids["user"], "t": now})
        for ex in ("ex_bb_squat", "ex_bb_bench_press", "ex_lat_pulldown"):
            insert(conn, "exercises", {"id": ex})
        for log, status, minutes in (("a", "inProgress", 0), ("b", "done", 5), ("c", "inProgress", 9)):
            conn.execute(sa.text("INSERT INTO workout_logs (id, user_id, week_number, date, status, warmup_done, cooldown_done, started_at) "
                                 "VALUES (:id, :u, 1, :d, :s, 0, 0, :t)"),
                         {"id": ids[log], "u": ids["user"], "d": day, "s": status, "t": f"2026-10-05 08:{minutes:02d}:00"})

        def sets(log, exercise, n):
            for i in range(1, n + 1):
                conn.execute(sa.text("INSERT INTO set_logs (id, user_id, workout_log_id, exercise_id, set_number, reps, weight_kg, logged_at) "
                                     "VALUES (:id, :u, :l, :e, :n, 8, 20, :t)"),
                             {"id": str(uuid.uuid4()), "u": ids["user"], "l": ids[log], "e": exercise, "n": i, "t": now})
        sets("a", "ex_bb_squat", 3)      # only in the first duplicate: moves over
        sets("a", "ex_bb_bench_press", 2)  # also in the kept log: the kept one wins
        sets("b", "ex_bb_bench_press", 4)
        sets("c", "ex_lat_pulldown", 3)  # only in the last duplicate: moves over
        conn.execute(sa.text("INSERT INTO injuries (id, user_id, region, side, type, severity, status, painful_movements, restrictions, since, created_at, updated_at) "
                             "VALUES (:id, :u, 'kneeR', 'right', 'pain', 2, 'active', '[]', '[]', :d, :t, :t)"),
                     {"id": ids["injury"], "u": ids["user"], "d": day, "t": now})
        conn.execute(sa.text("INSERT INTO pain_logs (id, user_id, injury_id, region, pain, source, workout_log_id, worsening, sharp_pain, swelling, numbness, logged_at) "
                             "VALUES (:id, :u, :i, 'kneeR', 3, 'workout', :l, 0, 0, 0, 0, :t)"),
                     {"id": ids["pain"], "u": ids["user"], "i": ids["injury"], "l": ids["c"], "t": now})

    run_migrations(url)

    with engine.connect() as conn:
        logs = conn.execute(sa.text("SELECT id FROM workout_logs")).scalars().all()
        assert logs == [ids["b"]]  # the finished one is kept
        per_exercise = dict(conn.execute(sa.text("SELECT exercise_id, COUNT(*) FROM set_logs GROUP BY exercise_id")).all())
        assert per_exercise == {"ex_bb_squat": 3, "ex_bb_bench_press": 4, "ex_lat_pulldown": 3}
        assert conn.execute(sa.text("SELECT DISTINCT workout_log_id FROM set_logs")).scalars().all() == [ids["b"]]
        assert conn.execute(sa.text("SELECT workout_log_id FROM pain_logs")).scalar() == ids["b"]
    engine.dispose()
