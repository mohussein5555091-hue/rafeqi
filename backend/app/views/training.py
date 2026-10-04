"""Exercises, this week's workouts with each exercise's exact target, and workout logging.
Shapes match frontend/src/types.ts (Exercise, Workout, WorkoutWeek)."""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.models import Exercise, ExerciseSubstitution, Injury, PainLog, ProgramDay, ProgramExercise, SetLog, WorkoutLog
from app.progression import Target, session_target
from app.week import Week
from app.workouts import ExerciseResult, exercise_results


def bi(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


def no_nones(d: dict) -> dict:
    """Optional fields are left out rather than sent as null (they are `field?:` in types.ts)."""
    return {k: v for k, v in d.items() if v is not None}


def exercise_out(e: Exercise, alternatives: list[ExerciseSubstitution]) -> dict:
    return no_nones({
        "id": e.id, "name": bi(e.name_en, e.name_ar), "description": bi(e.description_en, e.description_ar),
        "imageUrl": e.image_url, "imageFrames": e.image_frames or [], "videoUrl": e.video_url, "mediaSource": e.media_source,
        "muscles": {"primary": e.primary_muscles or [], "secondary": e.secondary_muscles or []},
        "muscleNames": bi(e.muscle_names_en, e.muscle_names_ar),
        "instructions": e.instructions, "cues": e.cues, "mistakes": e.mistakes,
        "alternatives": [{"exerciseId": a.substitute_id, "name": bi(a.name_en, a.name_ar), "kind": a.kind} for a in alternatives],
    })


def all_exercises(db: Session) -> list[dict]:
    alts: dict[str, list[ExerciseSubstitution]] = {}
    for a in db.scalars(select(ExerciseSubstitution).order_by(ExerciseSubstitution.priority)):
        alts.setdefault(a.exercise_id, []).append(a)
    return [exercise_out(e, alts.get(e.id, [])) for e in db.scalars(select(Exercise).order_by(Exercise.name_en))]


def one_exercise(db: Session, exercise_id: str) -> dict | None:
    e = db.get(Exercise, exercise_id)
    if e is None:
        return None
    alts = list(db.scalars(select(ExerciseSubstitution).where(ExerciseSubstitution.exercise_id == e.id)
                           .order_by(ExerciseSubstitution.priority)))
    return exercise_out(e, alts)


def result_out(r: ExerciseResult) -> dict:
    return {"sets": r.sets, "reps": r.reps, "weightKg": r.weight_kg, "struggled": r.struggled}


def day_exercises(db: Session, day: ProgramDay) -> list[ProgramExercise]:
    return list(db.scalars(select(ProgramExercise).where(ProgramExercise.program_day_id == day.id).order_by(ProgramExercise.position)))


def session_log(db: Session, user_id: str, d: dt.date) -> WorkoutLog | None:
    """The workout logged on that date (one session a day); a finished one wins over one still in progress."""
    logs = list(db.scalars(select(WorkoutLog).where(WorkoutLog.user_id == user_id, WorkoutLog.date == d)
                           .order_by(WorkoutLog.started_at.desc())))
    return next((x for x in logs if x.status == "done"), logs[0] if logs else None)


def _last(db: Session, user_id: str, exercise_id: str, before: WorkoutLog | None) -> tuple[ExerciseResult | None, WorkoutLog | None]:
    """The most recent finished result for this exercise, and the workout it came from."""
    q = (select(WorkoutLog).join(SetLog, SetLog.workout_log_id == WorkoutLog.id)
         .where(WorkoutLog.user_id == user_id, WorkoutLog.status == "done", SetLog.exercise_id == exercise_id))
    if before is not None:
        q = q.where(WorkoutLog.id != before.id, WorkoutLog.date <= before.date)
    log = db.scalars(q.order_by(WorkoutLog.date.desc(), WorkoutLog.finished_at.desc()).limit(1)).first()
    return (exercise_results(db, log.id).get(exercise_id), log) if log else (None, None)


def target_for(db: Session, user_id: str, week: Week, pe: ProgramExercise, log: WorkoutLog | None) -> tuple[Target, ExerciseResult | None]:
    """This session's exact target (app/progression.py) and last time's result."""
    last, last_log = _last(db, user_id, pe.exercise_id, log)
    ratio = 1.0
    in_this_plan = last_log is not None and last_log.plan_id == week.plan.id
    if last_log is not None and not in_this_plan and last_log.program_day_id:
        prev = db.scalars(select(ProgramExercise).where(ProgramExercise.user_id == user_id, ProgramExercise.exercise_id == pe.exercise_id,
                                                        ProgramExercise.program_day_id == last_log.program_day_id)).first()
        if prev is not None and prev.load_factor:
            ratio = pe.load_factor / prev.load_factor
    t = session_target(pe.sets, pe.reps, pe.weight_step_kg, pe.start_weight_kg, last, last_in_this_program=in_this_plan,
                       load_ratio=ratio, weight_offset_kg=pe.weight_offset_kg)
    return t, last


def workout_out(db: Session, user_id: str, week: Week, day: ProgramDay, injuries: dict[str, Injury]) -> dict:
    d = week.date_of(day)
    log = session_log(db, user_id, d)
    done = log is not None and log.status == "done"
    status = "done" if done else "today" if d == week.today else "missed" if d < week.today else "planned"
    pes = day_exercises(db, day)
    exercises = []
    for pe in pes:
        t, last = target_for(db, user_id, week, pe, log)
        swap = None
        if pe.injury_id and pe.swap_kind in ("swapped", "added") and pe.injury_id in injuries:
            swap = {"injuryId": pe.injury_id, "kind": pe.swap_kind, "region": injuries[pe.injury_id].region}
        exercises.append(no_nones({
            "exerciseId": pe.exercise_id, "sets": pe.sets, "reps": pe.reps.replace("-", "–"), "restSec": pe.rest_sec,
            "rpe": pe.target_rpe, "swap": swap, "lastTime": result_out(last) if last else None,
            "target": {"sets": t.sets, "reps": t.reps, "weightKg": t.weight_kg, "reason": t.reason},
            "weightStepKg": pe.weight_step_kg,
        }))
    out = {"id": day.id, "name": bi(day.name_en, day.name_ar), "day": day.weekday, "date": d.isoformat(), "status": status,
           "estMinutes": day.est_minutes, "warmupMinutes": day.warmup_minutes, "exercises": exercises}
    if done:
        results = exercise_results(db, log.id)
        minutes = round((log.finished_at - log.started_at).total_seconds() / 60) if log.finished_at else day.est_minutes
        pain = {p.injury_id: p.pain for p in db.scalars(select(PainLog).where(PainLog.user_id == user_id, PainLog.workout_log_id == log.id))
                if p.injury_id}
        out["summary"] = {"minutes": minutes if 0 < minutes <= 300 else day.est_minutes,
                          "setsDone": sum(r.sets for r in results.values()), "setsTotal": sum(pe.sets for pe in pes), "painByInjury": pain}
        out["log"] = {"effort": log.effort, "results": {k: result_out(v) for k, v in results.items() if v.sets > 0}}
    return out


def user_injuries(db: Session, user_id: str) -> dict[str, Injury]:
    return {i.id: i for i in db.scalars(select(Injury).where(Injury.user_id == user_id))}


def workout_week(db: Session, user_id: str, week: Week) -> dict:
    injuries = user_injuries(db, user_id)
    sessions = sorted((workout_out(db, user_id, week, d, injuries) for d in week.days), key=lambda s: s["date"])
    return {"weekNumber": week.number, "totalWeeks": week.program.total_weeks, "start": week.start.isoformat(),
            "end": week.end.isoformat(), "deloadWeek": week.program.deload_week, "sessions": sessions}


class NotToday(Exception):
    pass


class AlreadyFinished(Exception):
    pass


def open_log(db: Session, user_id: str, week: Week, day: ProgramDay) -> WorkoutLog:
    """Today's workout log for this session, started on the first exercise logged. Only today's session can be logged."""
    d = week.date_of(day)
    if d != week.today:
        raise NotToday
    log = session_log(db, user_id, d)
    if log is not None and log.status == "done":
        raise AlreadyFinished
    if log is None:
        log = WorkoutLog(user_id=user_id, plan_id=week.plan.id, program_day_id=day.id, week_number=week.number, date=d,
                         started_at=clock.now())
        db.add(log)
        db.flush()
    return log

