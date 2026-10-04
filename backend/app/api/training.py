"""Exercises (shared catalogue) and this week's workouts: read, log one exercise at a time, finish; warm-up and cool-down
ticks; cardio marked done; swapping an exercise (just today, or from now on) and undoing it."""

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import clock
from app.api.deps import CurrentAuth, Db
from app.engine.catalogue import exercises_from_db
from app.engine.training import alternatives, start_weight, weight_step
from app.engine.types import ExerciseInfo
from app.models import CardioLog, Exercise, ExerciseSubstitution, ExerciseSwap, Injury, Profile, ProgramDay
from app.plans import active_swaps, person_for, rebuild_plan
from app.schemas.screens import CardioDoneIn, DoneIn, ExerciseResultIn, FinishWorkoutIn, SwapExerciseIn
from app.views import training as v
from app.views.body import log_pain
from app.week import WEEKDAYS, NoPlan, Week, this_week
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
    if exercise_id not in {se.exercise_id for se in v.session_exercises(db, user_id, day, week.date_of(day), v.user_injuries(db, user_id))}:
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
    planned = {se.exercise_id: v.target_for(db, uid, week, se, log)[0].as_result()
               for se in v.session_exercises(db, uid, day, week.date_of(day), v.user_injuries(db, uid))
               if body.done is None or se.exercise_id in body.done}
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


# ── Warm-up and cool-down ticks ──

def _tick_log(db: Session, user_id: str, week: Week, day: ProgramDay):
    """Today's workout log (started or finished); the warm-up can be ticked before the first exercise."""
    if week.date_of(day) != week.today:
        raise HTTPException(409, "not_today")
    try:
        return v.open_log(db, user_id, week, day)
    except v.AlreadyFinished:
        return v.session_log(db, user_id, week.today)


@router.put("/api/workouts/{day_id}/warmup", status_code=status.HTTP_204_NO_CONTENT)
def tick_warmup(day_id: str, body: DoneIn, auth: CurrentAuth, db: Db):
    week = current_week(db, auth.user.id)
    _tick_log(db, auth.user.id, week, _day(db, week, day_id)).warmup_done = body.done
    db.commit()


@router.put("/api/workouts/{day_id}/cooldown", status_code=status.HTTP_204_NO_CONTENT)
def tick_cooldown(day_id: str, body: DoneIn, auth: CurrentAuth, db: Db):
    week = current_week(db, auth.user.id)
    _tick_log(db, auth.user.id, week, _day(db, week, day_id)).cooldown_done = body.done
    db.commit()


# ── Cardio ──

@router.get("/api/cardio/{weekday}")
def get_cardio_day(weekday: str, auth: CurrentAuth, db: Db):
    """A rest day's cardio session (`/api/workouts/cardio-sat` on the screens)."""
    week = current_week(db, auth.user.id)
    session = v.cardio_sessions(week).get(weekday)
    if session is None:
        raise HTTPException(404, "not_found")
    return v.cardio_day_out(db, auth.user.id, week, session)


@router.put("/api/cardio/{weekday}", status_code=status.HTTP_204_NO_CONTENT)
def log_cardio(weekday: str, body: CardioDoneIn, auth: CurrentAuth, db: Db):
    """Marks this week's cardio on that day as done, with the minutes actually done (today or an earlier day)."""
    week = current_week(db, auth.user.id)
    session = v.cardio_sessions(week).get(weekday)
    if session is None or weekday not in WEEKDAYS:
        raise HTTPException(404, "not_found")
    d = week.start + dt.timedelta(days=WEEKDAYS.index(weekday))
    if d > week.today:
        raise HTTPException(409, "not_yet")
    row = db.scalar(select(CardioLog).where(CardioLog.user_id == auth.user.id, CardioLog.date == d))
    if row is None:
        row = CardioLog(user_id=auth.user.id, date=d, exercise_id=session["exerciseId"], minutes=body.minutes, created_at=clock.now())
        db.add(row)
    row.minutes = body.minutes
    db.commit()


@router.delete("/api/cardio/{weekday}", status_code=status.HTTP_204_NO_CONTENT)
def undo_cardio(weekday: str, auth: CurrentAuth, db: Db):
    week = current_week(db, auth.user.id)
    if weekday not in WEEKDAYS:
        raise HTTPException(404, "not_found")
    d = week.start + dt.timedelta(days=WEEKDAYS.index(weekday))
    db.execute(delete(CardioLog).where(CardioLog.user_id == auth.user.id, CardioLog.date == d))
    db.commit()


# ── Swapping an exercise ──

def _session_exercise(db: Session, user_id: str, week: Week, day: ProgramDay, exercise_id: str) -> v.SessionExercise:
    se = next((x for x in v.session_exercises(db, user_id, day, week.date_of(day), v.user_injuries(db, user_id)) if x.exercise_id == exercise_id), None)
    if se is None:
        raise HTTPException(404, "not_found")
    return se


def _alternatives(db: Session, user_id: str, week: Week, day: ProgramDay, se: v.SessionExercise, reason: str) -> list[ExerciseInfo]:
    cat = exercises_from_db(db)
    person = person_for(db, user_id)
    preferred = list(db.scalars(select(ExerciseSubstitution.substitute_id).where(ExerciseSubstitution.exercise_id == se.exercise_id,
                                                                                ExerciseSubstitution.substitute_id.is_not(None))
                                .order_by(ExerciseSubstitution.priority)))
    taken = {x.exercise_id for x in v.session_exercises(db, user_id, day, week.date_of(day), v.user_injuries(db, user_id))}
    missing = main_equipment(cat[se.exercise_id]) if reason == "equipment" else ()
    return alternatives(cat[se.exercise_id], person, cat, preferred=preferred, taken=taken, reason=reason, missing=missing)


def main_equipment(ex: ExerciseInfo) -> tuple[str, ...]:
    """The equipment that's "not available": the exercise's main piece (not bodyweight or a bench)."""
    main = [e for e in ex.equipment if e not in ("bodyweight", "bench")]
    return tuple(main[:1])


@router.get("/api/workouts/{day_id}/exercises/{exercise_id}/alternatives")
def get_alternatives(day_id: str, exercise_id: str, auth: CurrentAuth, db: Db, reason: str = "cantDo"):
    """2–4 exercises with the same movement and muscles that fit the equipment and every active injury, each with
    the target it would start at ("find your weight" when there's no history)."""
    uid = auth.user.id
    week = current_week(db, uid)
    day = _day(db, week, day_id)
    se = _session_exercise(db, uid, week, day, exercise_id)
    rows = _names_for(db, [a.id for a in _alternatives(db, uid, week, day, se, reason)])
    person = person_for(db, uid)
    cat = exercises_from_db(db)
    out = []
    for e in rows:
        trial = v.SessionExercise(se.pe, e.id, se.sets, se.reps, se.rest_sec, se.target_rpe, weight_step(cat[e.id]),
                                  start_weight(cat[e.id], person, se.load_factor), se.load_factor, 0.0, None, True)
        t, last = v.target_for(db, uid, week, trial, v.session_log(db, uid, week.date_of(day)))
        out.append(v.no_nones({"exerciseId": e.id, "name": v.bi(e.name_en, e.name_ar), "imageUrl": e.image_url,
                               "muscleNames": v.bi(e.muscle_names_en, e.muscle_names_ar),
                               "target": {"sets": t.sets, "reps": t.reps, "weightKg": t.weight_kg, "reason": t.reason}}))
    return out


def _names_for(db: Session, ids: list[str]) -> list[Exercise]:
    rows = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ids)))} if ids else {}
    return [rows[i] for i in ids if i in rows]


@router.post("/api/workouts/{day_id}/exercises/{exercise_id}/swap")
def swap_exercise(day_id: str, exercise_id: str, body: SwapExerciseIn, auth: CurrentAuth, db: Db):
    """Swaps an exercise for one of its alternatives.
    - today: only this session. - always: the program from now on (the plan is rebuilt; every later version keeps it).
    - "Equipment not available" also saves that equipment as missing, so future plans avoid it.
    Returns the session's id (it changes when the plan is rebuilt)."""
    uid = auth.user.id
    week = current_week(db, uid)
    day = _day(db, week, day_id)
    d = week.date_of(day)
    finished = (log := v.session_log(db, uid, d)) is not None and log.status == "done"
    if d < week.today or finished:  # past (or finished) sessions can't be changed, from there or "from now on"
        raise HTTPException(409, "session_is_over")
    se = _session_exercise(db, uid, week, day, exercise_id)
    if body.to_exercise_id not in {a.id for a in _alternatives(db, uid, week, day, se, body.reason)}:
        raise HTTPException(422, "not_an_alternative")
    now = clock.now()
    if body.reason == "equipment":
        profile = db.get(Profile, uid)
        missing = list(profile.missing_equipment or [])
        for e in main_equipment(exercises_from_db(db)[se.exercise_id]):
            if e not in missing:
                missing.append(e)
        profile.missing_equipment = missing
    program_from = se.pe.exercise_id  # what the program has (a "just today" swap replaces that one)
    if body.scope == "today":
        for old in v.today_swaps(db, uid, d).values():
            if old.from_exercise_id == program_from:
                old.ended_at = now
        swap = ExerciseSwap(user_id=uid, from_exercise_id=program_from, to_exercise_id=body.to_exercise_id, reason=body.reason,
                            scope="today", date=d, created_at=now)
        db.add(swap)
        db.commit()
        return {"workoutId": day.id, "swapId": swap.id}
    # From now on: replace what the template had (an earlier swap of the same exercise is replaced, not stacked).
    original = se.pe.replaced_exercise_id if se.pe.swap_kind == "user" and se.pe.replaced_exercise_id else program_from
    for old in active_swaps(db, uid):
        if old.from_exercise_id == original:
            old.ended_at = now
    swap = ExerciseSwap(user_id=uid, from_exercise_id=original, to_exercise_id=body.to_exercise_id, reason=body.reason,
                        scope="always", created_at=now)
    db.add(swap)
    db.flush()
    rebuild_plan(db, uid, "swap")
    week = current_week(db, uid)
    same_day = next((x for x in week.days if x.weekday == day.weekday), None)
    db.commit()
    return {"workoutId": same_day.id if same_day else None, "swapId": swap.id}


@router.get("/api/swaps")
def list_swaps(auth: CurrentAuth, db: Db):
    """The "from now on" swaps in effect (each can be undone from the exercise's page)."""
    rows = active_swaps(db, auth.user.id)
    names = {e.id: e for e in _names_for(db, list({r.from_exercise_id for r in rows} | {r.to_exercise_id for r in rows}))}
    profile = db.get(Profile, auth.user.id)
    missing = list(profile.missing_equipment or []) if profile else []
    return [{"id": r.id, "fromExerciseId": r.from_exercise_id, "toExerciseId": r.to_exercise_id, "reason": r.reason,
             "why": v.swap_why(db, r.reason, r.from_exercise_id, missing),
             "fromName": v.bi(names[r.from_exercise_id].name_en, names[r.from_exercise_id].name_ar),
             "toName": v.bi(names[r.to_exercise_id].name_en, names[r.to_exercise_id].name_ar), "createdAt": r.created_at.isoformat()}
            for r in rows]


@router.delete("/api/swaps/{swap_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_swap(swap_id: str, auth: CurrentAuth, db: Db):
    """Undoes a swap: "from now on" puts the original exercise back (the plan is rebuilt); "just today" ends it."""
    row = db.scalar(select(ExerciseSwap).where(ExerciseSwap.id == swap_id, ExerciseSwap.user_id == auth.user.id, ExerciseSwap.ended_at.is_(None)))
    if row is None:
        raise HTTPException(404, "not_found")
    row.ended_at = clock.now()
    db.flush()
    if row.scope == "always":
        rebuild_plan(db, auth.user.id, "swap")
    db.commit()
