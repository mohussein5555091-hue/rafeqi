"""Injuries, the weekly check-in, weekly reviews and progress.
Shapes match frontend/src/types.ts (Injury, CheckIn, WeeklyReview, Progress)."""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.engine.checkin import check_answers
from app.engine.injuries import PainEntry, red_flag
from app.models import (
    CheckIn, CheckInAnswer, Exercise, Injury, MealPlanItem, PainLog, Plan, ProgramDay, ProgramExercise, Recipe, SetLog,
    TrainingProgram, WeeklyReview, WeightLog, WorkoutLog,
)
from app.plans import week_start
from app.views.training import bi
from app.week import CHECKIN_OPENS_DAYS_BEFORE_END, Week
from app.weights import record_weight

# ── Injuries ─────────────────────────────────────────────────────────


def pain_logs(db: Session, user_id: str, injury_id: str) -> list[PainLog]:
    return list(db.scalars(select(PainLog).where(PainLog.user_id == user_id, PainLog.injury_id == injury_id).order_by(PainLog.logged_at)))


def injury_out(db: Session, inj: Injury, week: Week | None) -> dict:
    logs = pain_logs(db, inj.user_id, inj.id)
    avoided, seen = [], set()
    if week is not None:
        names = {e.id: e for e in db.scalars(select(Exercise))}
        rows = db.scalars(select(ProgramExercise).join(ProgramDay, ProgramExercise.program_day_id == ProgramDay.id)
                          .where(ProgramDay.program_id == week.program.id, ProgramExercise.injury_id == inj.id,
                                 ProgramExercise.replaced_exercise_id.is_not(None)))
        for pe in rows:
            if pe.replaced_exercise_id in seen:
                continue
            seen.add(pe.replaced_exercise_id)
            a, b = names[pe.replaced_exercise_id], names[pe.exercise_id]
            avoided.append({"from": bi(a.name_en, a.name_ar), "to": bi(b.name_en, b.name_ar)})
    last = logs[-1] if logs else None
    return {
        "id": inj.id, "region": inj.region, "side": inj.side, "type": inj.type, "severity": inj.severity,
        "painfulMovements": inj.painful_movements, "restrictions": inj.restrictions, "status": inj.status,
        "since": inj.since.isoformat(), "paused": inj.paused_at is not None,
        "painLog": [{"date": p.logged_at.date().isoformat(), "pain": p.pain} for p in logs],
        "avoided": avoided,
        "redFlags": {k: bool(last and getattr(last, s)) for k, s in
                     (("sharpPain", "sharp_pain"), ("swelling", "swelling"), ("numbness", "numbness"), ("worsening", "worsening"))},
    }


def log_pain(db: Session, inj: Injury, pain: int, flags: set[str], workout_log_id: str | None) -> str | None:
    """Saves one pain entry after a workout. Returns why the area is now paused (a red flag), or None."""
    db.add(PainLog(user_id=inj.user_id, injury_id=inj.id, region=inj.region, pain=pain, source="workout", workout_log_id=workout_log_id,
                   sharp_pain="sharpPain" in flags, swelling="swelling" in flags, numbness="numbness" in flags, logged_at=clock.now()))
    db.flush()
    why = red_flag([PainEntry(p.pain, p.sharp_pain, p.swelling, p.numbness, p.worsening) for p in pain_logs(db, inj.user_id, inj.id)])
    if why and inj.paused_at is None:
        inj.paused_at = clock.now()
    return why


# ── Weekly check-in ──────────────────────────────────────────────────


def submitted_checkin(db: Session, user_id: str, start: dt.date) -> CheckIn | None:
    return db.scalar(select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.week_start == start, CheckIn.status == "submitted"))


def next_checkin(db: Session, user_id: str, today: dt.date) -> dict:
    """Each week's check-in opens on Thursday and stays due until it's sent."""
    start = week_start(today)
    if submitted_checkin(db, user_id, start):
        opens = start + dt.timedelta(days=7 + 6 - CHECKIN_OPENS_DAYS_BEFORE_END)
        return {"date": opens.isoformat(), "due": False}
    opens = start + dt.timedelta(days=6 - CHECKIN_OPENS_DAYS_BEFORE_END)
    return {"date": opens.isoformat(), "due": today >= opens}


def _latest_weight(db: Session, user_id: str, before: dt.date | None = None) -> float | None:
    q = select(WeightLog.weight_kg).where(WeightLog.user_id == user_id)
    if before:
        q = q.where(WeightLog.date < before)
    return db.scalar(q.order_by(WeightLog.date.desc()).limit(1))


def _sessions_done(db: Session, user_id: str, week: Week) -> int:
    return len(set(db.scalars(select(WorkoutLog.date).where(WorkoutLog.user_id == user_id, WorkoutLog.status == "done",
                                                             WorkoutLog.date >= week.start, WorkoutLog.date <= week.end))))


def checkin_draft(db: Session, user_id: str, week: Week, profile_weight: float) -> dict:
    last_ci = db.scalars(select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.status == "submitted")
                         .order_by(CheckIn.week_start.desc())).first()
    last_weight = (last_ci.weight_kg if last_ci and last_ci.weight_kg else None) or _latest_weight(db, user_id, week.start) or profile_weight
    measurements = {k: getattr(last_ci, f"{k}_cm") for k in ("waist", "hips", "chest", "arm", "thigh")} if last_ci else {}
    measurements = {k: v for k, v in measurements.items() if v is not None}
    recipes = {r.id: r for r in db.scalars(select(Recipe))}
    in_plan = dict.fromkeys(db.scalars(select(MealPlanItem.recipe_id).where(MealPlanItem.meal_plan_id == week.meal_plan.id)
                                       .order_by(MealPlanItem.date, MealPlanItem.time)))
    draft = {
        "id": "draft", "weekNumber": week.number,
        "body": {"weightKg": _latest_weight(db, user_id) or last_weight, "measurementsCm": dict(measurements), "photos": {}},
        "training": {"sessionsDone": _sessions_done(db, user_id, week), "sessionsPlanned": week.program.days_per_week,
                     "difficulty": 3, "soreness": 3, "exerciseFeedback": []},
        "injuries": [], "newPainRegions": [], "redFlags": {"sharpPain": False, "swelling": False, "numbness": False},
        "nutrition": {"adherencePct": 80, "hunger": 3, "mealsToChange": [], "moreOf": [], "lessOf": []},
        "life": {"sleep": 3, "energy": 3, "stress": 3, "daysAvailable": week.program.days_per_week, "obstacles": []},
    }
    return {"draft": draft, "last": {"weightKg": last_weight, "measurementsCm": measurements},
            "mealOptions": [{"id": rid, "name": bi(recipes[rid].name_en, recipes[rid].name_ar)} for rid in in_plan]}


def answers_from(c) -> dict:
    """The screen's CheckIn → {question id: value} (ids from data/checkin_questions.yaml)."""
    m = c.body.measurements_cm
    a = {
        "weight_kg": c.body.weight_kg, "waist_cm": m.waist, "hips_cm": m.hips, "chest_cm": m.chest, "arm_cm": m.arm, "thigh_cm": m.thigh,
        "sessions_done": c.training.sessions_done, "difficulty": c.training.difficulty, "soreness": c.training.soreness,
        "exercise_feedback": [{"exercise_id": f.exercise_id, "feel": f.feel} for f in c.training.exercise_feedback],
        "injury_pain": [{"injury_id": i.injury_id, "pain": i.pain, "trend": i.trend} for i in c.injuries],
        "new_pain_regions": list(c.new_pain_regions),
        "sharp_pain": c.red_flags.sharp_pain, "swelling": c.red_flags.swelling, "numbness": c.red_flags.numbness,
        "adherence_pct": c.nutrition.adherence_pct, "hunger": c.nutrition.hunger, "meals_to_change": list(c.nutrition.meals_to_change),
        "more_of": list(c.nutrition.more_of), "less_of": list(c.nutrition.less_of),
        "sleep": c.life.sleep, "energy": c.life.energy, "stress": c.life.stress, "days_available": c.life.days_available,
        "obstacles": list(c.life.obstacles), "note": (c.note or "").strip() or None,
    }
    return {k: v for k, v in a.items() if v is not None}


class CheckInProblem(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def save_checkin(db: Session, user_id: str, week: Week, answers: dict) -> CheckIn:
    """Checks the answers against the questions file, then saves the check-in, one row per answer, and the weight."""
    injuries = set(db.scalars(select(Injury.id).where(Injury.user_id == user_id, Injury.status != "resolved")))
    exercises = set(db.scalars(select(ProgramExercise.exercise_id).join(ProgramDay, ProgramExercise.program_day_id == ProgramDay.id)
                               .where(ProgramDay.program_id == week.program.id)))
    recipes = set(db.scalars(select(MealPlanItem.recipe_id).where(MealPlanItem.meal_plan_id == week.meal_plan.id)))
    if problems := check_answers(answers, sessions_planned=week.program.days_per_week, injury_ids=injuries,
                                 exercise_ids=exercises, recipe_ids=recipes):
        raise CheckInProblem(problems)
    now = clock.now()
    ci = db.scalar(select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.week_start == week.start)) or CheckIn(
        user_id=user_id, week_start=week.start, week_number=week.number)
    ci.status, ci.submitted_at, ci.week_number = "submitted", now, week.number
    ci.weight_kg, ci.note = answers["weight_kg"], answers.get("note")
    for k in ("waist", "hips", "chest", "arm", "thigh"):
        setattr(ci, f"{k}_cm", answers.get(f"{k}_cm"))
    db.add(ci)
    db.flush()
    for qid, value in answers.items():
        db.add(CheckInAnswer(user_id=user_id, checkin_id=ci.id, question_id=qid, value={"value": value}, answered_at=now))
    record_weight(db, user_id, week.today, answers["weight_kg"], "checkin")
    db.flush()
    return ci


# ── Weekly reviews ───────────────────────────────────────────────────

SUMMARY = {
    "red_flag": bi("Something you reported needs a professional to look at it first. We paused the affected exercises; "
                   "please see a doctor or physiotherapist before training that area again.",
                   "في حاجة قلتها محتاجة دكتور يشوفها الأول. وقفنا التمارين اللي ليها علاقة؛ من فضلك اكشف عند دكتور أو أخصائي علاج طبيعي "
                   "قبل ما تمرّن المنطقة دي تاني."),
    "none": bi("No changes this week: your plan stays the same. Keep going.", "مفيش تغييرات الأسبوع ده: خطتك زي ما هي. كمّل."),
    "some": bi("Your check-in made {n} change(s) to next week's plan. Each one is listed below with the reason.",
               "الـcheck-in بتاعك عمل {n} تغيير في خطة الأسبوع الجاي. كل تغيير مكتوب تحت بالسبب بتاعه."),
}


def _avg(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def review_out(db: Session, r: WeeklyReview) -> dict:
    ci = db.get(CheckIn, r.checkin_id) if r.checkin_id else None
    start = ci.week_start if ci else r.created_at.date()
    answers = {a.question_id: a.value.get("value") for a in db.scalars(select(CheckInAnswer).where(CheckInAnswer.checkin_id == ci.id))} if ci else {}

    def weights(a: dt.date, b: dt.date) -> list[float]:
        return list(db.scalars(select(WeightLog.weight_kg).where(WeightLog.user_id == r.user_id, WeightLog.date >= a, WeightLog.date <= b)))

    now, before = _avg(weights(start, start + dt.timedelta(days=6))), _avg(weights(start - dt.timedelta(days=7), start - dt.timedelta(days=1)))
    planned = db.scalar(select(TrainingProgram.days_per_week).where(TrainingProgram.plan_id == r.plan_before_id)) if r.plan_before_id else None
    pains = [e["pain"] for e in answers.get("injury_pain") or []]
    n = len(r.changes)
    if r.ai_summary_en:
        summary = bi(r.ai_summary_en, r.ai_summary_ar or r.ai_summary_en)
    elif r.red_flag:
        summary = SUMMARY["red_flag"]
    else:
        summary = {k: v.format(n=n) for k, v in SUMMARY["some" if n else "none"].items()}
    out = {
        "id": r.id, "weekNumber": r.week_number, "start": start.isoformat(), "end": (start + dt.timedelta(days=6)).isoformat(),
        "state": r.state, "status": r.status, "summary": summary,
        "shortSummary": r.changes[0]["what"] if n else summary,
        "stats": {"weightChangeKg": round(now - before, 1) if now is not None and before is not None else 0.0,
                  "sessionsDone": answers.get("sessions_done", 0), "sessionsPlanned": planned or 0},
        "changes": [{"kind": c["kind"], "what": c["what"], "why": c["why"], "citation": bi(c.get("source", ""), c.get("source", ""))}
                    for c in r.changes],
        "focus": [],
    }
    if pains:
        out["stats"]["pain"] = max(pains)
    if any(c["kind"] == "meals" for c in r.changes):
        out["groceryUpdate"] = {"note": bi("Your grocery list follows the new meals.", "قائمة المشتريات اتحدّثت على الوجبات الجديدة.")}
    return out


def reviews_out(db: Session, user_id: str) -> list[dict]:
    rows = db.scalars(select(WeeklyReview).where(WeeklyReview.user_id == user_id).order_by(WeeklyReview.created_at.desc()))
    return [review_out(db, r) for r in rows]


# ── Progress ─────────────────────────────────────────────────────────

MAX_LIFTS = 3


def progress_out(db: Session, user_id: str, since: dt.date) -> dict:
    weights = [{"date": w.date.isoformat(), "kg": w.weight_kg}
               for w in db.scalars(select(WeightLog).where(WeightLog.user_id == user_id).order_by(WeightLog.date))]
    measurements = []
    for ci in db.scalars(select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.status == "submitted").order_by(CheckIn.week_start)):
        row = {k: getattr(ci, f"{k}_cm") for k in ("waist", "hips", "chest", "arm", "thigh")}
        if any(v is not None for v in row.values()):
            measurements.append({"date": ci.week_start.isoformat(), **{k: v for k, v in row.items() if v is not None}})

    # Strength: the heaviest set of each finished workout, per exercise.
    rows = db.execute(select(WorkoutLog.date, SetLog.exercise_id, SetLog.weight_kg, SetLog.reps)
                      .join(WorkoutLog, SetLog.workout_log_id == WorkoutLog.id)
                      .where(SetLog.user_id == user_id, WorkoutLog.status == "done", SetLog.weight_kg > 0)
                      .order_by(WorkoutLog.date))
    top: dict[str, dict[dt.date, tuple[float, int]]] = {}
    for d, ex, kg, reps in rows:
        cur = top.setdefault(ex, {}).get(d)
        if cur is None or (kg, reps) > cur:
            top[ex][d] = (kg, reps)
    names = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(list(top))))}
    kg_unit = bi("kg", "كجم")
    busiest = sorted(top, key=lambda ex: (-len(top[ex]), names[ex].name_en))[:MAX_LIFTS]
    lifts = [{"exerciseId": ex, "name": bi(names[ex].name_en, names[ex].name_ar), "unit": kg_unit,
              "points": [{"date": d.isoformat(), "kg": kg} for d, (kg, _) in sorted(top[ex].items())]} for ex in busiest]
    records = []
    for ex in sorted(top, key=lambda e: names[e].name_en):
        d, (kg, reps) = max(top[ex].items(), key=lambda x: (x[1], -x[0].toordinal()))
        records.append({"exerciseId": ex, "name": bi(names[ex].name_en, names[ex].name_ar), "date": d.isoformat(),
                        "value": bi(f"{kg:g} kg × {reps}", f"{kg:g} كجم × {reps}")})
    return {"since": since.isoformat(), "weights": weights, "measurements": measurements, "lifts": lifts, "records": records, "photos": []}


def first_plan_date(db: Session, user_id: str) -> dt.date | None:
    first = db.scalar(select(Plan.created_at).where(Plan.user_id == user_id).order_by(Plan.version).limit(1))
    return first.date() if first else None
