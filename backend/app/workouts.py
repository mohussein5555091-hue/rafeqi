"""Workout logging, one result per exercise.

People log an exercise in one tap ("done as planned") or one row (sets, reps, weight, "struggled on the last set").
It is stored in the existing tables so anything reading set by set keeps working:
- set_logs: one row per set done, all with the same reps and weight. rpe is set only on the last set, to
  STRUGGLED_RPE, when the person struggled on it; otherwise it stays empty.
- workout_logs.effort: one "how hard was today's workout?" rating (1–10) for the whole session.
"""

import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import clock
from app.models import SetLog, WorkoutLog

STRUGGLED_RPE = 10.0


@dataclass(frozen=True)
class ExerciseResult:
    sets: int
    reps: int
    weight_kg: float
    struggled: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.sets <= 20:
            raise ValueError("sets must be between 0 and 20")
        if not 0 <= self.reps <= 100:
            raise ValueError("reps must be between 0 and 100")
        if not 0 <= self.weight_kg <= 500:
            raise ValueError("weight must be between 0 and 500 kg")


def rep_range(reps: str) -> tuple[int, int]:
    """'8-10' or '8–10' → (8, 10); '15' or '10 each side' → (15, 15) / (10, 10)."""
    numbers = [int(n) for n in re.findall(r"\d+", reps)]
    if not numbers:
        raise ValueError(f"no rep count in {reps!r}")
    return (numbers[0], numbers[1]) if len(numbers) > 1 else (numbers[0], numbers[0])


def as_planned(sets: int, reps: str, weight_kg: float) -> ExerciseResult:
    """What "Done as planned" records: every planned set, at the top of the rep range, at the planned weight."""
    return ExerciseResult(sets=sets, reps=rep_range(reps)[1], weight_kg=weight_kg)


def save_exercise_result(db: Session, log: WorkoutLog, exercise_id: str, result: ExerciseResult) -> list[SetLog]:
    """Replaces whatever was logged for this exercise in this workout (logging again = correcting it)."""
    db.execute(delete(SetLog).where(SetLog.workout_log_id == log.id, SetLog.exercise_id == exercise_id))
    now = clock.now()
    rows = [
        SetLog(user_id=log.user_id, workout_log_id=log.id, exercise_id=exercise_id, set_number=n, reps=result.reps,
               weight_kg=result.weight_kg, rpe=STRUGGLED_RPE if result.struggled and n == result.sets else None, logged_at=now)
        for n in range(1, result.sets + 1)
    ]
    db.add_all(rows)
    db.flush()
    return rows


def exercise_results(db: Session, workout_log_id: str) -> dict[str, ExerciseResult]:
    """Reads set_logs back into one result per exercise (for "last time", the session page and the weekly review)."""
    rows = db.scalars(select(SetLog).where(SetLog.workout_log_id == workout_log_id).order_by(SetLog.set_number))
    by_exercise: dict[str, list[SetLog]] = {}
    for r in rows:
        by_exercise.setdefault(r.exercise_id, []).append(r)
    return {
        ex: ExerciseResult(sets=len(sets), reps=min(s.reps for s in sets), weight_kg=max(s.weight_kg for s in sets),
                           struggled=(sets[-1].rpe or 0) >= STRUGGLED_RPE)
        for ex, sets in by_exercise.items()
    }


def last_result(db: Session, user_id: str, exercise_id: str, before_log: WorkoutLog | None = None) -> ExerciseResult | None:
    """The most recent finished workout's result for this exercise ("Last time: 3 × 10 @ 22.5 kg")."""
    q = (select(WorkoutLog.id).join(SetLog, SetLog.workout_log_id == WorkoutLog.id)
         .where(WorkoutLog.user_id == user_id, WorkoutLog.status == "done", SetLog.exercise_id == exercise_id))
    if before_log is not None:
        q = q.where(WorkoutLog.id != before_log.id, WorkoutLog.date <= before_log.date)
    log_id = db.scalar(q.order_by(WorkoutLog.date.desc(), WorkoutLog.finished_at.desc()).limit(1))
    return exercise_results(db, log_id).get(exercise_id) if log_id else None


def finish_workout(db: Session, log: WorkoutLog, effort: int, planned: dict[str, ExerciseResult]) -> dict[str, ExerciseResult]:
    """"Finish workout": every planned exercise not logged yet is saved as done as planned; the session rating is stored.

    `planned` is {exercise_id: as_planned(...)} for the session. Exercises the person already logged keep their result.
    """
    if not 1 <= effort <= 10:
        raise ValueError("effort must be between 1 and 10")
    logged = exercise_results(db, log.id)
    for exercise_id, result in planned.items():
        if exercise_id not in logged:
            save_exercise_result(db, log, exercise_id, result)
    log.effort, log.status, log.finished_at = effort, "done", clock.now()
    db.flush()
    return exercise_results(db, log.id)
