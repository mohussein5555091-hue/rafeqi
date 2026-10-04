"""Workouts are logged per exercise, stored as one set_logs row per set, plus one effort rating per session."""

import datetime as dt

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Exercise, SetLog, WorkoutLog
from app.workouts import (
    STRUGGLED_RPE, ExerciseResult, exercise_results, finish_workout, last_result, rep_range,
    save_exercise_result,
)
from populate import ensure_catalogue
from test_plans import catalogue  # noqa: F401 (fixture)

MONDAY = dt.date(2026, 9, 28)


@pytest.fixture
def log(make_user, db) -> WorkoutLog:
    user_id = make_user().id  # signs up through the API, so before this session starts writing
    ensure_catalogue(db)
    row = WorkoutLog(user_id=user_id, week_number=3, date=MONDAY)
    db.add(row)
    db.flush()
    return row


def rows(db, log: WorkoutLog, exercise_id: str = "ex_test") -> list[tuple[int, int, float, float | None]]:
    q = select(SetLog).where(SetLog.workout_log_id == log.id, SetLog.exercise_id == exercise_id).order_by(SetLog.set_number)
    return [(r.set_number, r.reps, r.weight_kg, r.rpe) for r in db.scalars(q)]


@pytest.mark.parametrize("text,expected", [("8-10", (8, 10)), ("8–10", (8, 10)), ("15", (15, 15)), ("10 each side", (10, 10))])
def test_rep_range(text, expected):
    assert rep_range(text) == expected


def test_one_result_becomes_one_row_per_set(db, log):
    save_exercise_result(db, log, "ex_test", ExerciseResult(sets=3, reps=9, weight_kg=22.5))
    assert rows(db, log) == [(1, 9, 22.5, None), (2, 9, 22.5, None), (3, 9, 22.5, None)]


def test_struggled_marks_only_the_last_set(db, log):
    save_exercise_result(db, log, "ex_test", ExerciseResult(sets=2, reps=8, weight_kg=20, struggled=True))
    assert rows(db, log) == [(1, 8, 20, None), (2, 8, 20, STRUGGLED_RPE)]
    assert exercise_results(db, log.id) == {"ex_test": ExerciseResult(sets=2, reps=8, weight_kg=20, struggled=True)}


def test_editing_an_exercise_replaces_its_rows(db, log):
    save_exercise_result(db, log, "ex_test", ExerciseResult(sets=3, reps=10, weight_kg=22.5))
    save_exercise_result(db, log, "ex_test", ExerciseResult(sets=2, reps=8, weight_kg=20))
    assert rows(db, log) == [(1, 8, 20, None), (2, 8, 20, None)]


def test_zero_sets_means_skipped_and_leaves_no_rows(db, log):
    save_exercise_result(db, log, "ex_test", ExerciseResult(sets=0, reps=0, weight_kg=0))
    assert rows(db, log) == [] and exercise_results(db, log.id) == {}


@pytest.mark.parametrize("bad", [dict(sets=21, reps=8, weight_kg=20), dict(sets=3, reps=101, weight_kg=20),
                                 dict(sets=3, reps=8, weight_kg=-1)])
def test_result_ranges(bad):
    with pytest.raises(ValueError):
        ExerciseResult(**bad)


def test_finish_marks_untouched_exercises_as_planned_and_keeps_edits(db, log):
    second = "ex_test_2"
    db.add(Exercise(id=second, name_en="Row", name_ar="تجديف", description_en="d", description_ar="د",
                    movement_pattern="horizontalPull", joints_loaded=["shoulder"], range_of_motion="full",
                    equipment=["dumbbells"], difficulty="beginner"))
    db.flush()
    edited = ExerciseResult(sets=3, reps=8, weight_kg=22.5, struggled=True)
    save_exercise_result(db, log, "ex_test", edited)

    results = finish_workout(db, log, effort=7, planned={"ex_test": ExerciseResult(sets=3, reps=10, weight_kg=22.5), second: ExerciseResult(sets=3, reps=12, weight_kg=20)})

    assert results == {"ex_test": edited, second: ExerciseResult(sets=3, reps=12, weight_kg=20)}
    assert (log.status, log.effort) == ("done", 7) and log.finished_at is not None
    assert db.scalar(select(func.count()).select_from(SetLog).where(SetLog.workout_log_id == log.id)) == 6


def test_effort_must_be_1_to_10(db, log):
    with pytest.raises(ValueError):
        finish_workout(db, log, effort=11, planned={})
    log.effort = 0  # the database refuses it too
    with pytest.raises(IntegrityError):
        db.commit()


def test_last_time_comes_from_the_latest_finished_workout(db, log, clock):
    finish_workout(db, log, effort=6, planned={"ex_test": ExerciseResult(sets=3, reps=10, weight_kg=22.5)})
    clock.advance(days=7)
    nxt = WorkoutLog(user_id=log.user_id, week_number=4, date=MONDAY + dt.timedelta(days=7))
    db.add(nxt)
    db.flush()
    assert last_result(db, log.user_id, "ex_test", before_log=nxt) == ExerciseResult(sets=3, reps=10, weight_kg=22.5)

    save_exercise_result(db, nxt, "ex_test", ExerciseResult(sets=3, reps=10, weight_kg=24))  # in progress: not "last time" yet
    assert last_result(db, log.user_id, "ex_test").weight_kg == 22.5
    finish_workout(db, nxt, effort=8, planned={})
    assert last_result(db, log.user_id, "ex_test").weight_kg == 24


def test_per_set_readers_still_get_what_they_need(db, log):
    """Progression and the weekly review read set_logs set by set: top of the range on every set, volume, struggles."""
    finish_workout(db, log, effort=7, planned={"ex_test": ExerciseResult(sets=3, reps=10, weight_kg=22.5)})
    sets = db.scalars(select(SetLog).where(SetLog.workout_log_id == log.id)).all()
    assert all(s.reps >= rep_range("8–10")[1] for s in sets)  # → ready for the next weight step
    assert sum(s.reps * s.weight_kg for s in sets) == 3 * 10 * 22.5
    assert not any((s.rpe or 0) >= STRUGGLED_RPE for s in sets)


# ── "Log each set": one row per set, and the next target from what was really done ──

def test_log_each_set_keeps_every_set_and_drives_the_next_target(make_user, catalogue, clock):  # noqa: F811
    from test_onboarding import answer_all

    c = make_user().client
    answer_all(c)
    c.post("/api/onboarding/complete")
    c.post("/api/plan")
    week = c.get("/api/workouts/week").json()
    mon = next(s for s in week["sessions"] if s["status"] == "today")
    ex = next(e for e in mon["exercises"] if e["target"]["weightKg"] > 0)
    kg = ex["target"]["weightKg"]
    sets = [{"reps": 10, "weightKg": kg}, {"reps": 9, "weightKg": kg}, {"reps": 10, "weightKg": kg - ex["weightStepKg"]}]
    r = c.put(f"/api/workouts/{mon['id']}/exercises/{ex['exerciseId']}", json={"sets": 3, "reps": 0, "weightKg": 0, "perSet": sets})
    assert r.status_code == 204, r.text
    assert c.post(f"/api/workouts/{mon['id']}/finish", json={"effort": 7}).status_code == 200
    done = next(s for s in c.get("/api/workouts/week").json()["sessions"] if s["id"] == mon["id"])
    assert done["log"]["results"][ex["exerciseId"]] == {"sets": 3, "reps": 9, "weightKg": kg, "struggled": False, "perSet": sets}
    clock.advance(days=7)
    nxt = next(s for s in c.get("/api/workouts/week").json()["sessions"] if s["status"] == "today")
    e = next(x for x in nxt["exercises"] if x["exerciseId"] == ex["exerciseId"])
    assert e["lastTime"]["perSet"] == sets  # "Last time" shows each set
    # Only 2 of 3 sets at the heaviest weight: same weight again, reps kept in the range.
    assert (e["target"]["weightKg"], e["target"]["reason"]) == (kg, "repeat")


def test_log_each_set_validation(make_user, catalogue):  # noqa: F811
    from test_onboarding import answer_all

    c = make_user().client
    answer_all(c)
    c.post("/api/onboarding/complete")
    c.post("/api/plan")
    mon = next(s for s in c.get("/api/workouts/week").json()["sessions"] if s["status"] == "today")
    ex = mon["exercises"][0]["exerciseId"]
    bad = {"sets": 1, "reps": 0, "weightKg": 0, "perSet": [{"reps": 101, "weightKg": 10}]}
    assert c.put(f"/api/workouts/{mon['id']}/exercises/{ex}", json=bad).status_code == 422
