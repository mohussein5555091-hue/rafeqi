"""Exercises, this week's workouts with each exercise's exact target, and workout logging.
Shapes match frontend/src/types.ts (Exercise, Workout, WorkoutWeek)."""

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.engine.catalogue import exercises_from_db
from app.engine.rules import load_rules
from app.engine.training import start_weight, weight_step
from app.engine.warmup import ramp_up
from app.models import (
    CardioLog, Exercise, ExerciseSubstitution, ExerciseSwap, Injury, PainLog, Profile, ProgramDay, ProgramExercise, SetLog, WorkoutLog,
)
from app.plans import person_for
from app.progression import Target, session_target
from app.vocab import get_vocab
from app.week import WEEKDAYS, Week
from app.workouts import ExerciseResult, exercise_results


def bi(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


def no_nones(d: dict) -> dict:
    """Optional fields are left out rather than sent as null (they are `field?:` in types.ts)."""
    return {k: v for k, v in d.items() if v is not None}


def equipment_names(ids: list[str] | None) -> dict | None:
    """"cable machine, dumbbells" in each language (data/vocab/movements.yaml), or None."""
    labels = get_vocab().data["equipment"]
    ids = [i for i in ids or [] if i in labels]
    if not ids:
        return None
    return {"en": ", ".join(labels[i]["en"].lower() for i in ids), "ar": "، ".join(labels[i]["ar"] for i in ids)}


def exercise_out(e: Exercise, alternatives: list[ExerciseSubstitution], images: dict[str, str | None] | None = None) -> dict:
    """`images`: the photo of each alternative that is in the catalogue (for its thumbnail)."""
    images = images or {}
    return no_nones({
        "id": e.id, "type": e.type, "name": bi(e.name_en, e.name_ar), "description": bi(e.description_en, e.description_ar),
        "imageUrl": e.image_url, "imageFrames": e.image_frames or [], "videoUrl": e.video_url, "mediaSource": e.media_source,
        "muscles": {"primary": e.primary_muscles or [], "secondary": e.secondary_muscles or []},
        "muscleNames": bi(e.muscle_names_en, e.muscle_names_ar),
        "instructions": e.instructions, "cues": e.cues, "mistakes": e.mistakes,
        "alternatives": [no_nones({"exerciseId": a.substitute_id, "name": bi(a.name_en, a.name_ar), "kind": a.kind,
                                   "imageUrl": images.get(a.substitute_id), "equipment": equipment_names(a.equipment)}) for a in alternatives],
    })


def all_exercises(db: Session) -> list[dict]:
    alts: dict[str, list[ExerciseSubstitution]] = {}
    for a in db.scalars(select(ExerciseSubstitution).order_by(ExerciseSubstitution.priority)):
        alts.setdefault(a.exercise_id, []).append(a)
    rows = list(db.scalars(select(Exercise).order_by(Exercise.name_en)))
    images = {e.id: e.image_url for e in rows}
    return [exercise_out(e, alts.get(e.id, []), images) for e in rows]


def one_exercise(db: Session, exercise_id: str) -> dict | None:
    e = db.get(Exercise, exercise_id)
    if e is None:
        return None
    alts = list(db.scalars(select(ExerciseSubstitution).where(ExerciseSubstitution.exercise_id == e.id)
                           .order_by(ExerciseSubstitution.priority)))
    ids = [a.substitute_id for a in alts if a.substitute_id]
    images = dict(db.execute(select(Exercise.id, Exercise.image_url).where(Exercise.id.in_(ids))).all()) if ids else {}
    return exercise_out(e, alts, images)


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


@dataclass
class SessionExercise:
    """One exercise as it is in a given session: the program's, or the one swapped in for that day only."""

    pe: ProgramExercise
    exercise_id: str
    sets: int
    reps: str
    rest_sec: int
    target_rpe: float
    weight_step_kg: float
    start_weight_kg: float
    load_factor: float
    weight_offset_kg: float
    swap: dict | None  # what the screen shows (injury swap, or the person's own swap with its reason)
    user_swap: bool  # the person chose it: with no history yet, its first target is "find your weight"


def today_swaps(db: Session, user_id: str, d: dt.date) -> dict[str, ExerciseSwap]:
    """The "just today" swaps for the session on `d`: program exercise → swap."""
    rows = db.scalars(select(ExerciseSwap).where(ExerciseSwap.user_id == user_id, ExerciseSwap.scope == "today", ExerciseSwap.date == d,
                                                 ExerciseSwap.ended_at.is_(None)).order_by(ExerciseSwap.created_at))
    return {r.from_exercise_id: r for r in rows}


def swap_why(db: Session, reason: str, from_id: str, missing: list[str]) -> dict:
    """"no cable machine", "machine busy"… (training.yaml `swaps.reasons`)."""
    t = load_rules()["training"]["swaps"]["reasons"][reason]
    ex = db.get(Exercise, from_id)
    eq = [e for e in (ex.equipment if ex else []) if e in missing] or [e for e in (ex.equipment if ex else []) if e not in ("bodyweight", "bench")]
    label = get_vocab().data["equipment"].get(eq[0] if eq else "", {"en": "equipment", "ar": "الأداة"})
    return {"en": t["en"].format(equipment=label["en"].lower()), "ar": t["ar"].format(equipment=label["ar"])}


def session_exercises(db: Session, user_id: str, day: ProgramDay, d: dt.date, injuries: dict[str, Injury]) -> list[SessionExercise]:
    swaps = today_swaps(db, user_id, d)
    profile = db.get(Profile, user_id)
    missing = list(profile.missing_equipment or []) if profile else []
    cat = person = None
    out = []
    always = {s.to_exercise_id: s for s in db.scalars(select(ExerciseSwap).where(ExerciseSwap.user_id == user_id, ExerciseSwap.scope == "always",
                                                                                 ExerciseSwap.ended_at.is_(None)))}
    for pe in day_exercises(db, day):
        swap = None
        if pe.swap_kind == "user" and pe.user_reason:
            a = always.get(pe.exercise_id)
            swap = {"kind": "user", "scope": "always", "reason": pe.user_reason, "why": swap_why(db, pe.user_reason, pe.replaced_exercise_id, missing),
                    "fromExerciseId": pe.replaced_exercise_id, "swapId": a.id if a else None}
        elif pe.injury_id and pe.swap_kind in ("swapped", "added") and pe.injury_id in injuries:
            swap = {"injuryId": pe.injury_id, "kind": pe.swap_kind, "region": injuries[pe.injury_id].region}
        t = swaps.get(pe.exercise_id)
        if t is not None and db.get(Exercise, t.to_exercise_id) is not None:
            if cat is None:
                cat, person = exercises_from_db(db), person_for(db, user_id)
            to = cat[t.to_exercise_id]
            out.append(SessionExercise(pe, to.id, pe.sets, pe.reps, pe.rest_sec, pe.target_rpe, weight_step(to),
                                       start_weight(to, person, pe.load_factor), pe.load_factor, 0.0,
                                       {"kind": "user", "scope": "today", "reason": t.reason, "why": swap_why(db, t.reason, pe.exercise_id, missing),
                                        "fromExerciseId": pe.exercise_id, "swapId": t.id}, True))
            continue
        out.append(SessionExercise(pe, pe.exercise_id, pe.sets, pe.reps, pe.rest_sec, pe.target_rpe, pe.weight_step_kg, pe.start_weight_kg,
                                   pe.load_factor, pe.weight_offset_kg, swap, pe.swap_kind == "user"))
    return out


def target_for(db: Session, user_id: str, week: Week, se: SessionExercise | ProgramExercise, log: WorkoutLog | None) -> tuple[Target, ExerciseResult | None]:
    """This session's exact target (app/progression.py) and last time's result. An exercise the person swapped in,
    with no history yet, starts as "find your weight" (a light suggestion), and progresses from what they log."""
    last, last_log = _last(db, user_id, se.exercise_id, log)
    ratio = 1.0
    in_this_plan = last_log is not None and last_log.plan_id == week.plan.id
    if last_log is not None and not in_this_plan and last_log.program_day_id:
        prev = db.scalars(select(ProgramExercise).where(ProgramExercise.user_id == user_id, ProgramExercise.exercise_id == se.exercise_id,
                                                        ProgramExercise.program_day_id == last_log.program_day_id)).first()
        if prev is not None and prev.load_factor:
            ratio = se.load_factor / prev.load_factor
    t = session_target(se.sets, se.reps, se.weight_step_kg, se.start_weight_kg, last, last_in_this_program=in_this_plan,
                       load_ratio=ratio, weight_offset_kg=se.weight_offset_kg)
    if last is None and getattr(se, "user_swap", False):
        t = Target(t.sets, t.reps, t.weight_kg, "findWeight")
    return t, last


def _names(db: Session, ids: list[str]) -> dict[str, Exercise]:
    return {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ids)))} if ids else {}


def cardio_out(db: Session, user_id: str, session: dict, d: dt.date) -> dict:
    names = load_rules()["training"]["cardio"]["intensity_names"]
    log = db.scalar(select(CardioLog).where(CardioLog.user_id == user_id, CardioLog.date == d))
    out = {"exerciseId": session["exerciseId"], "minutes": session["minutes"], "intensity": session["intensity"],
           "intensityName": names[session["intensity"]], "when": session["when"]}
    if log is not None:
        out["done"] = {"minutes": log.minutes}
    return out


def warmup_out(day: ProgramDay, ramp_from: tuple[str, float, float] | None, done: bool) -> dict:
    w = day.warmup or {}
    general = w.get("general") or {}
    ramp = None
    if ramp_from is not None:
        ex_id, kg, step = ramp_from
        sets = ramp_up(kg, step)
        ramp = {"exerciseId": ex_id, "sets": sets} if sets else None
    out = {"minutes": w.get("minutes", day.warmup_minutes), "moves": [{"exerciseId": m["id"], "amount": m["amount"]} for m in w.get("moves", [])],
           "skipped": [{"exerciseId": x["id"], "why": x["why"]} for x in w.get("skipped", [])], "done": done}
    if general.get("id"):
        out["general"] = {"exerciseId": general["id"], "minutes": general["minutes"]}
    if ramp:
        out["rampUp"] = ramp
    return out


def cooldown_out(day: ProgramDay, done: bool) -> dict:
    c = day.cooldown or {}
    out = {"minutes": c.get("minutes", 0), "done": done,
           "stretches": [{"exerciseId": x["id"], "seconds": x["seconds"], "eachSide": x["eachSide"]} for x in c.get("stretches", [])]}
    if (c.get("breathing") or {}).get("id"):
        out["breathing"] = {"exerciseId": c["breathing"]["id"], "minutes": c["breathing"]["minutes"]}
    return out


def cardio_sessions(week: Week) -> dict[str, dict]:
    return {s["weekday"]: s for s in (week.program.cardio or {}).get("sessions", [])}


def workout_out(db: Session, user_id: str, week: Week, day: ProgramDay, injuries: dict[str, Injury]) -> dict:
    d = week.date_of(day)
    log = session_log(db, user_id, d)
    done = log is not None and log.status == "done"
    status = "done" if done else "today" if d == week.today else "missed" if d < week.today else "planned"
    ses = session_exercises(db, user_id, day, d, injuries)
    joints = dict(db.execute(select(Exercise.id, Exercise.joints_loaded).where(Exercise.id.in_([se.exercise_id for se in ses]))).all()) if ses else {}
    exercises, ramp_from = [], None
    for se in ses:
        t, last = target_for(db, user_id, week, se, log)
        # Ramp-up sets: the first main compound lift (several joints) with a weight, as in engine/training.py.
        if ramp_from is None and se.weight_step_kg > 0 and t.weight_kg > 0 and len(set(joints.get(se.exercise_id) or ())) >= 2:
            ramp_from = (se.exercise_id, t.weight_kg, se.weight_step_kg)
        exercises.append(no_nones({
            "exerciseId": se.exercise_id, "sets": se.sets, "reps": se.reps.replace("-", "–"), "restSec": se.rest_sec,
            "rpe": se.target_rpe, "swap": se.swap and no_nones(se.swap), "lastTime": result_out(last) if last else None,
            "target": {"sets": t.sets, "reps": t.reps, "weightKg": t.weight_kg, "reason": t.reason},
            "weightStepKg": se.weight_step_kg,
        }))
    out = {"id": day.id, "kind": "strength", "name": bi(day.name_en, day.name_ar), "day": day.weekday, "date": d.isoformat(), "status": status,
           "estMinutes": day.est_minutes, "warmupMinutes": day.warmup_minutes, "exercises": exercises,
           "warmup": warmup_out(day, ramp_from, bool(log and log.warmup_done)), "cooldown": cooldown_out(day, bool(log and log.cooldown_done))}
    if (c := cardio_sessions(week).get(day.weekday)) is not None:
        out["cardio"] = cardio_out(db, user_id, c, d)
    if done:
        results = exercise_results(db, log.id)
        minutes = round((log.finished_at - log.started_at).total_seconds() / 60) if log.finished_at else day.est_minutes
        pain = {p.injury_id: p.pain for p in db.scalars(select(PainLog).where(PainLog.user_id == user_id, PainLog.workout_log_id == log.id))
                if p.injury_id}
        out["summary"] = {"minutes": minutes if 0 < minutes <= 300 else day.est_minutes,
                          "setsDone": sum(r.sets for r in results.values()), "setsTotal": sum(se.sets for se in ses), "painByInjury": pain}
        out["log"] = {"effort": log.effort, "results": {k: result_out(v) for k, v in results.items() if v.sets > 0}}
    return out


CARDIO_PREFIX = "cardio-"


def cardio_day_out(db: Session, user_id: str, week: Week, session: dict) -> dict:
    """A rest day with cardio: it opens like any other day, and is marked done with the minutes."""
    d = week.start + dt.timedelta(days=WEEKDAYS.index(session["weekday"]))
    c = cardio_out(db, user_id, session, d)
    ex = db.get(Exercise, session["exerciseId"])
    status = "done" if "done" in c else "today" if d == week.today else "missed" if d < week.today else "planned"
    return {"id": CARDIO_PREFIX + session["weekday"], "kind": "cardio", "name": bi(f"Cardio: {ex.name_en}", f"كارديو: {ex.name_ar}"),
            "day": session["weekday"], "date": d.isoformat(), "status": status, "estMinutes": session["minutes"], "warmupMinutes": 0,
            "exercises": [], "cardio": c}


def user_injuries(db: Session, user_id: str) -> dict[str, Injury]:
    return {i.id: i for i in db.scalars(select(Injury).where(Injury.user_id == user_id))}


def workout_week(db: Session, user_id: str, week: Week) -> dict:
    injuries = user_injuries(db, user_id)
    sessions = [workout_out(db, user_id, week, d, injuries) for d in week.days]
    lifting = {d.weekday for d in week.days}
    sessions += [cardio_day_out(db, user_id, week, c) for c in cardio_sessions(week).values() if c["weekday"] not in lifting]
    cardio = week.program.cardio or {}
    why = cardio.get("reasons") or []
    return {"programName": bi(week.program.name_en, week.program.name_ar), "weekNumber": week.number, "totalWeeks": week.program.total_weeks, "start": week.start.isoformat(),
            "end": week.end.isoformat(), "deloadWeek": week.program.deload_week, "sessions": sorted(sessions, key=lambda s: s["date"]),
            "cardio": {"sessionsPerWeek": len(cardio.get("sessions", [])), "stepsPerDay": cardio.get("stepsPerDay", 0),
                       "why": bi(" ".join(r["en"] for r in why), " ".join(r["ar"] for r in why))}}


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

