"""Exercises (shared catalogue) and this week's workouts: read, log one exercise at a time, finish."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentAuth, Db
from app.models import Injury, ProgramDay
from app.plans import rebuild_plan
from app.schemas.screens import ExerciseResultIn, FinishWorkoutIn
from app.views import training as v
from app.views.body import log_pain
from app.week import NoPlan, Week, this_week
from app.workouts import ExerciseResult, finish_workout, save_exercise_result

router = APIRouter(tags=["training"])


def current_week(db: Session, user_id: str) -> Week:
    try:
        return this_week(db, user_id)
    except NoPlan:
        raise HTTPException(404, "no_plan_yet") from None


@router.get("/api/exercises")
def list_exercises(auth: CurrentAuth, db: Db):
    return v.all_exercises(db)


@router.get("/api/exercises/{exercise_id}")
def get_exercise(exercise_id: str, auth: CurrentAuth, db: Db):
    out = v.one_exercise(db, exercise_id)
    if out is None:
        raise HTTPException(404, "not_found")
    return out


@router.get("/api/workouts/week")
def get_week(auth: CurrentAuth, db: Db):
    return v.workout_week(db, auth.user.id, current_week(db, auth.user.id))


def _day(db: Session, week: Week, day_id: str) -> ProgramDay:
    """A session of the current plan. Anyone else's (or an old plan's) id is simply not found."""
    day = next((d for d in week.days if d.id == day_id), None)
    if day is None:
        raise HTTPException(404, "not_found")
    return day


@router.get("/api/workouts/{day_id}")
def get_workout(day_id: str, auth: CurrentAuth, db: Db):
    week = current_week(db, auth.user.id)
    return v.workout_out(db, auth.user.id, week, _day(db, week, day_id), v.user_injuries(db, auth.user.id))


def _log(db: Session, user_id: str, day_id: str, exercise_id: str):
    week = current_week(db, user_id)
    day = _day(db, week, day_id)
    if exercise_id not in {pe.exercise_id for pe in v.day_exercises(db, day)}:
        raise HTTPException(404, "not_found")
    try:
        return v.open_log(db, user_id, week, day)
    except v.NotToday:
        raise HTTPException(409, "not_today") from None
    except v.AlreadyFinished:
        raise HTTPException(409, "already_finished") from None


@router.put("/api/workouts/{day_id}/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def log_exercise(day_id: str, exercise_id: str, body: ExerciseResultIn, auth: CurrentAuth, db: Db):
    """Saves one exercise's result (logging it again replaces it). Only today's session can be logged."""
    log = _log(db, auth.user.id, day_id, exercise_id)
    save_exercise_result(db, log, exercise_id, ExerciseResult(body.sets, body.reps, body.weight_kg, body.struggled and body.sets > 0))
    db.commit()


@router.delete("/api/workouts/{day_id}/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_exercise(day_id: str, exercise_id: str, auth: CurrentAuth, db: Db):
    log = _log(db, auth.user.id, day_id, exercise_id)
    save_exercise_result(db, log, exercise_id, ExerciseResult(0, 0, 0))
    db.commit()


@router.post("/api/workouts/{day_id}/finish")
def finish(day_id: str, body: FinishWorkoutIn, auth: CurrentAuth, db: Db):
    """Logs every exercise not logged yet as done as planned, saves the effort rating and the pain check.
    A red flag (sharp pain, swelling, numbness, pain too high or rising) pauses that body area and rebuilds the plan without it."""
    uid = auth.user.id
    week = current_week(db, uid)
    day = _day(db, week, day_id)
    try:
        log = v.open_log(db, uid, week, day)
    except v.NotToday:
        raise HTTPException(409, "not_today") from None
    except v.AlreadyFinished:
        raise HTTPException(409, "already_finished") from None
    planned = {pe.exercise_id: v.target_for(db, uid, week, pe, log)[0].as_result() for pe in v.day_exercises(db, day)
               if body.done is None or pe.exercise_id in body.done}
    finish_workout(db, log, body.effort, planned)
    paused = []
    flags = set(body.red_flags)
    for p in body.pain:
        inj = db.scalar(select(Injury).where(Injury.id == p.injury_id, Injury.user_id == uid, Injury.status != "resolved"))
        if inj is None:
            raise HTTPException(404, "not_found")
        was_paused = inj.paused_at is not None
        if log_pain(db, inj, p.pain, flags, log.id) and not was_paused:
            paused.append(inj.id)
    if paused:
        rebuild_plan(db, uid, "pain")
    db.commit()
    return {"paused": paused}
