"""Each exercise gets one exact target from last time (data/rules/progression.yaml); "Done as planned" saves exactly it."""

import datetime as dt
import json

import pytest

from app.config import get_settings
from app.models import WorkoutLog
from app.progression import load_rules, next_target
from app.workouts import ExerciseResult, finish_workout, last_result
from populate import ensure_catalogue

CASES = json.loads((get_settings().rules_dir / "progression_cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_worked_examples(case):
    last = case["last"] and ExerciseResult(sets=case["last"]["sets"], reps=case["last"]["reps"],
                                           weight_kg=case["last"]["weightKg"], struggled=case["last"]["struggled"])
    t = next_target(case["sets"], case["reps"], case["step"], case["start"], last)
    want = case["target"]
    assert (t.sets, t.reps, t.weight_kg, t.reason) == (want["sets"], want["reps"], want["weightKg"], want["reason"])


def test_rules_file_is_valid():
    assert load_rules()["reps_per_step"] >= 1


def test_bad_rules_are_refused(tmp_path, monkeypatch):
    (tmp_path / "progression.yaml").write_text("version: 1\nreps_per_step: 0\n", encoding="utf-8")
    monkeypatch.setattr(get_settings(), "rules_dir", tmp_path)
    load_rules.cache_clear()
    try:
        with pytest.raises(ValueError, match="reps_per_step"):
            load_rules()
    finally:
        load_rules.cache_clear()


def test_done_as_planned_three_sessions_in_a_row(make_user, db, clock):
    """Tapping "Done as planned" every week walks up the range, then adds weight."""
    user_id = make_user().id
    ensure_catalogue(db)
    seen = []
    for week in range(4):
        log = WorkoutLog(user_id=user_id, week_number=week + 1, date=dt.date(2026, 9, 28) + dt.timedelta(weeks=week))
        db.add(log)
        db.flush()
        target = next_target(3, "8–10", 2.5, 20, last_result(db, user_id, "ex_test", before_log=log))
        finish_workout(db, log, effort=7, planned={"ex_test": target.as_result()})
        seen.append((target.reps, target.weight_kg, target.reason))
        clock.advance(weeks=1)
    assert seen == [(8, 20, "start"), (9, 20, "addReps"), (10, 20, "addReps"), (8, 22.5, "addWeight")]
