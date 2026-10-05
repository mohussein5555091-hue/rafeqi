"""Plans in the database: build one from the questionnaire, and update it after each weekly check-in.

A plan is never edited in place. Every change makes version n+1 (status "active") and marks the old one "superseded".
Each version holds: the targets and their reasons (plans), the training program (training_programs, program_days,
program_exercises), the week's meals (meal_plans, meal_plan_items) and the grocery list (grocery_lists, grocery_list_items).
All numbers come from app/engine; this module only reads the inputs and saves the results.
"""

import datetime as dt
from dataclasses import asdict, replace

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import clock
from app.engine.catalogue import exercises_from_db, grocery_from_db, recipes_from_db
from app.engine.grocery import build_grocery_list
from app.engine.meals import NoMealPlan, Targets, plan_week
from app.engine.nutrition import add_cardio_reason, compute_targets
from app.engine.review import ReviewInput, as_reasons, review_week
from app.engine.rules import load_rules, rules_version
from app.engine.training import Adjustments, build_program
from app.engine.types import Health, InjuryInfo, Person, Reason
from app.meal_changes import changes_by_item, copy_changes, item_ingredients, leave_out_disliked, recipe_ingredients
from app.models import (
    CheckIn, CheckInAnswer, ExerciseSwap, GroceryList, GroceryListItem, Injury, MealPlan, MealPlanItem, PainLog, PantryItem, Plan, Profile,
    ProgramDay, ProgramExercise, TrainingProgram, WeeklyReview, WeightLog, WorkoutLog,
)


class NotReady(Exception):
    """Onboarding isn't complete yet."""


def week_start(day: dt.date) -> dt.date:
    """The Saturday on or before `day` (the Egyptian week starts on Saturday)."""
    return day - dt.timedelta(days=(day.weekday() - 5) % 7)


def person_for(db: Session, user_id: str, weight_kg: float | None = None) -> Person:
    p = db.get(Profile, user_id)
    if p is None or p.completed_at is None:
        raise NotReady
    injuries = db.scalars(select(Injury).where(Injury.user_id == user_id, Injury.status != "resolved").order_by(Injury.created_at))
    return Person(
        sex=p.sex, age=p.age, height_cm=p.height_cm, weight_kg=weight_kg or p.weight_kg, goal=p.goal, pace=p.pace,
        experience=p.experience, days_per_week=p.days_per_week, session_minutes=p.session_minutes, location=p.location,
        meals_per_day=p.meals_per_day, cooking_minutes=p.cooking_minutes,
        health=Health(p.heart_condition or False, p.diabetes or False, p.pregnancy or False, p.recent_surgery or False,
                      p.exercise_medication or False),
        dislikes=tuple(p.dislikes or ()), allergies=tuple(p.allergies or ()), fasting=tuple(p.fasting or ()),
        injuries=tuple(InjuryInfo(id=i.id, region=i.region, status=i.status, severity=i.severity,
                                  painful_movements=tuple(i.painful_movements), restrictions=tuple(i.restrictions),
                                  paused=i.paused_at is not None) for i in injuries),
        missing_equipment=tuple(p.missing_equipment or ()), disliked_foods=tuple(p.disliked_foods or ()),
    )


def active_swaps(db: Session, user_id: str) -> list[ExerciseSwap]:
    """The person's "from now on" swaps that haven't been undone, oldest first."""
    return list(db.scalars(select(ExerciseSwap).where(ExerciseSwap.user_id == user_id, ExerciseSwap.scope == "always",
                                                      ExerciseSwap.ended_at.is_(None)).order_by(ExerciseSwap.created_at)))


def current_plan(db: Session, user_id: str) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.user_id == user_id, Plan.status == "active").order_by(Plan.version.desc()))


def _r(reasons: list[Reason]) -> list[dict]:
    return [r.as_dict() for r in reasons]


def generate_plan(db: Session, user_id: str, trigger: str = "onboarding", *, today: dt.date | None = None,
                  adjust: Adjustments = Adjustments(), calories: int | None = None, banned: frozenset[str] = frozenset(),
                  weight_kg: float | None = None, extra_reasons: list[Reason] | None = None, keep_meals: bool = False) -> Plan:
    """Builds and saves a new plan version from the saved questionnaire answers (plus any weekly-review changes).
    `keep_meals`: when only the training changed (a swap, an injury), the week's meals and grocery list (with its ticks)
    are carried over as they are, as long as the nutrition targets are the same."""
    person = person_for(db, user_id, weight_kg)
    start = week_start(today or clock.today())
    targets = compute_targets(person, calories_override=calories)
    # The person's own "from now on" swaps are kept by every version (and what they took out never comes back).
    swaps = active_swaps(db, user_id)
    adjust = replace(adjust, replace=tuple((s.from_exercise_id, s.to_exercise_id, s.reason) for s in swaps))
    program = build_program(person, exercises_from_db(db), adjust=adjust)
    if program.cardio and program.cardio.sessions:
        add_cardio_reason(targets, person, len(program.cardio.sessions), program.cardio.sessions[0].minutes)
    before = current_plan(db, user_id) if keep_meals else None
    same_targets = before is not None and (before.calories, before.protein_g, before.carbs_g, before.fat_g) == (
        targets.calories, targets.protein_g, targets.carbs_g, targets.fat_g)
    if same_targets:
        return _new_version_keeping_meals(db, user_id, trigger, person, targets, program, adjust, calories, banned, extra_reasons, before)
    recipes = recipes_from_db(db)
    meal_reasons: list[Reason] = []
    try:
        week = plan_week(start, person, Targets(targets.calories, targets.protein_g, targets.carbs_g, targets.fat_g), recipes, banned)
    except NoMealPlan:
        if not banned:
            raise
        week = plan_week(start, person, Targets(targets.calories, targets.protein_g, targets.carbs_g, targets.fat_g), recipes)
        meal_reasons.append(Reason("nutrition.review.meals", "Meals you asked to change came back: nothing else fits your targets yet.",
                                   "الوجبات اللي طلبت تغييرها رجعت: لسه مفيش غيرها مناسب لأهدافك.", ""))
    meal_reasons = week.reasons + meal_reasons

    now = clock.now()
    db.execute(update(Plan).where(Plan.user_id == user_id, Plan.status == "active").values(status="superseded"))
    version = (db.scalar(select(func.max(Plan.version)).where(Plan.user_id == user_id)) or 0) + 1
    plan = Plan(
        user_id=user_id, version=version, status="active", trigger=trigger, calories=targets.calories,
        maintenance_calories=targets.maintenance, protein_g=targets.protein_g, carbs_g=targets.carbs_g, fat_g=targets.fat_g,
        conservative=person.conservative, rules_version=rules_version(), created_at=now,
        reasons={**{k: _r(v) for k, v in targets.reasons.items()}, "training": _r(program.reasons), "meals": _r(meal_reasons),
                 "cardio": _r(program.cardio.reasons if program.cardio else []),
                 "review": _r(extra_reasons or [])},
        inputs={"person": {k: v for k, v in asdict(person).items() if k != "injuries"},
                "injuries": [asdict(i) for i in person.injuries], "week_start": start.isoformat(),
                "adjustments": {"avoid": sorted(adjust.avoid), "injury_factors": dict(adjust.injury_factors), "deload": adjust.deload,
                                "weight_offsets": dict(adjust.weight_offsets), "calories": calories, "banned_recipes": sorted(banned)}},
    )
    db.add(plan)
    db.flush()

    _save_program(db, user_id, plan, program, start)

    mp = MealPlan(user_id=user_id, plan_id=plan.id, week_start=start, created_at=now)
    db.add(mp)
    db.flush()
    items = [MealPlanItem(user_id=user_id, meal_plan_id=mp.id, date=m.date, slot=m.slot, time=m.time, recipe_id=m.recipe_id,
                          portion=m.portion, planned_portion=m.portion, kcal=m.kcal, protein_g=m.protein, carbs_g=m.carbs, fat_g=m.fat)
             for m in week.meals]
    db.add_all(items)
    db.flush()
    leave_out_disliked(db, user_id, items, person.disliked_foods)
    regenerate_grocery_list(db, user_id, mp)
    db.flush()
    return plan


def _save_program(db: Session, user_id: str, plan: Plan, program, start: dt.date) -> None:
    tp = TrainingProgram(user_id=user_id, plan_id=plan.id, template_id=program.template_id, name_en=program.name["en"],
                         name_ar=program.name["ar"], days_per_week=program.days_per_week, total_weeks=program.total_weeks,
                         deload_week=program.deload_week, start_date=start, cardio=program.cardio.as_dict() if program.cardio else {})
    db.add(tp)
    db.flush()
    for d in program.days:
        pd = ProgramDay(user_id=user_id, program_id=tp.id, day_index=d.day_index, weekday=d.weekday, name_en=d.name["en"],
                        name_ar=d.name["ar"], est_minutes=d.est_minutes, warmup_minutes=d.warmup_minutes, kind=d.kind,
                        warmup=d.warmup, cooldown=d.cooldown, reasons=_r(d.reasons))
        db.add(pd)
        db.flush()
        for e in d.exercises:
            db.add(ProgramExercise(
                user_id=user_id, program_day_id=pd.id, exercise_id=e.exercise_id, position=e.position, sets=e.sets, reps=e.reps,
                rest_sec=e.rest_sec, target_rpe=e.target_rpe, load_factor=e.load_factor, weight_step_kg=e.weight_step_kg,
                start_weight_kg=e.start_weight_kg, weight_offset_kg=e.weight_offset_kg, replaced_exercise_id=e.replaced_exercise_id,
                injury_id=e.injury_id, swap_kind=e.swap_kind, user_reason=e.user_reason, swap_reason={"reasons": _r(e.reasons)}))


def _new_version_keeping_meals(db: Session, user_id: str, trigger: str, person, targets, program, adjust: Adjustments, calories,
                               banned, extra_reasons, before: Plan) -> Plan:
    """A new version with the new program, and the previous version's meals and grocery list copied as they are."""
    now = clock.now()
    old_mp = db.scalar(select(MealPlan).where(MealPlan.plan_id == before.id))
    db.execute(update(Plan).where(Plan.user_id == user_id, Plan.status == "active").values(status="superseded"))
    version = (db.scalar(select(func.max(Plan.version)).where(Plan.user_id == user_id)) or 0) + 1
    reasons = dict(before.reasons or {})
    reasons.update({k: _r(v) for k, v in targets.reasons.items()})
    reasons.update({"training": _r(program.reasons), "cardio": _r(program.cardio.reasons if program.cardio else []), "review": _r(extra_reasons or [])})
    inputs = dict(before.inputs or {})
    inputs["person"] = {k: v for k, v in asdict(person).items() if k != "injuries"}
    inputs["injuries"] = [asdict(i) for i in person.injuries]
    inputs["adjustments"] = {"avoid": sorted(adjust.avoid), "injury_factors": dict(adjust.injury_factors), "deload": adjust.deload,
                             "weight_offsets": dict(adjust.weight_offsets), "calories": calories, "banned_recipes": sorted(banned)}
    plan = Plan(user_id=user_id, version=version, status="active", trigger=trigger, calories=before.calories,
                maintenance_calories=targets.maintenance, protein_g=before.protein_g, carbs_g=before.carbs_g, fat_g=before.fat_g,
                conservative=person.conservative, rules_version=rules_version(), created_at=now, reasons=reasons, inputs=inputs)
    db.add(plan)
    db.flush()
    start = old_mp.week_start if old_mp else week_start(clock.today())
    _save_program(db, user_id, plan, program, start)
    if old_mp is not None:
        mp = MealPlan(user_id=user_id, plan_id=plan.id, week_start=old_mp.week_start, created_at=now)
        db.add(mp)
        db.flush()
        mp.day_notes = dict(old_mp.day_notes or {})
        id_map = {}
        for m in db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == old_mp.id)):
            new = MealPlanItem(user_id=user_id, meal_plan_id=mp.id, date=m.date, slot=m.slot, time=m.time, recipe_id=m.recipe_id,
                               portion=m.portion, planned_portion=m.planned_portion, kcal=m.kcal, protein_g=m.protein_g, carbs_g=m.carbs_g,
                               fat_g=m.fat_g, eaten=m.eaten, replaced_recipe_id=m.replaced_recipe_id, reason=m.reason)
            db.add(new)
            db.flush()
            id_map[m.id] = new.id
        copy_changes(db, user_id, id_map)
        old_gl = db.scalars(select(GroceryList).where(GroceryList.meal_plan_id == old_mp.id).order_by(GroceryList.created_at.desc())).first()
        if old_gl is not None:
            gl = GroceryList(user_id=user_id, meal_plan_id=mp.id, week_start=old_gl.week_start, change_note=old_gl.change_note, created_at=now)
            db.add(gl)
            db.flush()
            for g in db.scalars(select(GroceryListItem).where(GroceryListItem.grocery_list_id == old_gl.id)):
                db.add(GroceryListItem(user_id=user_id, grocery_list_id=gl.id, grocery_item_id=g.grocery_item_id, period=g.period,
                                       grams_needed=g.grams_needed, qty=g.qty, unit=g.unit, checked=g.checked, have_it=g.have_it))
    db.flush()
    return plan


def regenerate_grocery_list(db: Session, user_id: str, meal_plan: MealPlan, change_note: dict | None = None) -> GroceryList:
    """Runs whenever a meal plan is created or changes. Each meal counts what it's really made of: its recipe after
    the person's ingredient changes (removed foods out, replacements in), × its portion."""
    items_ = list(db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == meal_plan.id, MealPlanItem.user_id == user_id)))
    recipes, changes = recipe_ingredients(db), changes_by_item(db, user_id, [i.id for i in items_])
    ingredients = {i.id: item_ingredients(i, recipes, changes.get(i.id, [])) for i in items_}
    week_meals = [(i.id, i.portion) for i in items_]
    items, food_map = grocery_from_db(db)
    pantry = {p.grocery_item_id: p.level for p in db.scalars(select(PantryItem).where(PantryItem.user_id == user_id))}
    gl = GroceryList(user_id=user_id, meal_plan_id=meal_plan.id, week_start=meal_plan.week_start, change_note=change_note, created_at=clock.now())
    db.add(gl)
    db.flush()
    for line in build_grocery_list(week_meals, ingredients, food_map, items, pantry):
        db.add(GroceryListItem(user_id=user_id, grocery_list_id=gl.id, grocery_item_id=line.item_id, period=line.period,
                               grams_needed=line.grams_needed, qty=line.qty, unit=line.unit, have_it=line.have_it))
    db.flush()
    return gl


def _answers(db: Session, checkin: CheckIn) -> dict:
    return {a.question_id: a.value.get("value") for a in db.scalars(select(CheckInAnswer).where(CheckInAnswer.checkin_id == checkin.id))}


def run_weekly_review(db: Session, user_id: str, checkin_id: str) -> WeeklyReview:
    """Decides this week's changes from a submitted check-in and saves them as a new plan version."""
    ci = db.scalar(select(CheckIn).where(CheckIn.id == checkin_id, CheckIn.user_id == user_id))
    before = current_plan(db, user_id)
    if ci is None or before is None:
        raise NotReady
    answers = _answers(db, ci)
    person = person_for(db, user_id, ci.weight_kg)
    start = ci.week_start  # the week being reviewed (Saturday to Friday); the new plan starts the week after

    def weights(a: dt.date, b: dt.date) -> tuple[float, ...]:
        return tuple(w.weight_kg for w in db.scalars(select(WeightLog).where(WeightLog.user_id == user_id, WeightLog.date >= a,
                                                                             WeightLog.date <= b).order_by(WeightLog.date)))

    efforts = [e for e in db.scalars(select(WorkoutLog.effort).where(WorkoutLog.user_id == user_id, WorkoutLog.status == "done",
                                                                     WorkoutLog.date >= start,
                                                                     WorkoutLog.date < start + dt.timedelta(days=7))) if e]
    previous_pain = {}
    for inj in person.injuries:
        last = db.scalar(select(PainLog.pain).where(PainLog.user_id == user_id, PainLog.injury_id == inj.id,
                                                    PainLog.checkin_id.is_(None) | (PainLog.checkin_id != ci.id))
                         .order_by(PainLog.logged_at.desc()).limit(1))
        if last is not None:
            previous_pain[inj.id] = last
    tp = db.scalar(select(TrainingProgram).where(TrainingProgram.plan_id == before.id))
    pe_ids = tuple(db.scalars(select(ProgramExercise.exercise_id).join(ProgramDay, ProgramExercise.program_day_id == ProgramDay.id)
                              .where(ProgramDay.program_id == tp.id)))
    recipe_ids = frozenset(db.scalars(select(MealPlanItem.recipe_id).join(MealPlan, MealPlanItem.meal_plan_id == MealPlan.id)
                                      .where(MealPlan.plan_id == before.id)))
    exp = round((before.calories - before.maintenance_calories) * 7 / load_rules()["nutrition"]["goal"]["kcal_per_kg"], 2)
    result = review_week(ReviewInput(
        person=person, calories=before.calories, maintenance=before.maintenance_calories, expected_weekly_change_kg=exp,
        weights_this_week=weights(start, start + dt.timedelta(days=6)),
        weights_last_week=weights(start - dt.timedelta(days=7), start - dt.timedelta(days=1)),
        answers=answers, avg_effort=sum(efforts) / len(efforts) if efforts else None, program_exercise_ids=pe_ids,
        previous_pain=previous_pain, plan_recipe_ids=recipe_ids, sessions_planned=tp.days_per_week), exercises_from_db(db))

    now = clock.now()
    for iid in result.pause_injuries:
        db.get(Injury, iid).paused_at = now
    for e in answers.get("injury_pain") or []:
        if any(i.id == e["injury_id"] for i in person.injuries):
            region = next(i.region for i in person.injuries if i.id == e["injury_id"])
            db.add(PainLog(user_id=user_id, injury_id=e["injury_id"], region=region, pain=e["pain"], source="checkin",
                           checkin_id=ci.id, worsening=e["trend"] == "worse", sharp_pain=bool(answers.get("sharp_pain")),
                           swelling=bool(answers.get("swelling")), numbness=bool(answers.get("numbness")), logged_at=now))
    db.flush()

    prev = (before.inputs or {}).get("adjustments") or {}
    factors = dict(prev.get("injury_factors") or {})
    for iid, f in result.injury_factors.items():
        factors[iid] = max(load_rules()["training"]["injury_load"]["min_load_factor"], round(factors.get(iid, 1.0) * f, 3))
    adjust = Adjustments(avoid=frozenset(prev.get("avoid") or ()) | frozenset(result.avoid_exercises),
                         injury_factors=tuple(sorted(factors.items())), deload=result.deload,
                         weight_offsets=tuple(sorted(result.weight_offsets.items())))
    calories = result.calories if result.calories is not None else before.calories
    after = generate_plan(db, user_id, "checkin", today=start + dt.timedelta(days=7), adjust=adjust, calories=calories,
                          banned=frozenset(prev.get("banned_recipes") or ()) | frozenset(result.ban_recipes),
                          weight_kg=ci.weight_kg, extra_reasons=as_reasons(result.changes))
    review = WeeklyReview(user_id=user_id, checkin_id=ci.id, plan_before_id=before.id, plan_after_id=after.id, week_number=ci.week_number,
                          state="ready", status=result.status, red_flag=result.red_flag, changes=[c.as_dict() for c in result.changes],
                          created_at=now)
    db.add(review)
    db.flush()
    return review


def rebuild_plan(db: Session, user_id: str, trigger: str) -> Plan | None:
    """A new version after an injury changed (edited, added, removed or paused) or an exercise swap, keeping what the weekly reviews decided
    (calories, swapped exercises, lighter loads, replaced meals) and the week's meals. One-off changes (deload, ± one step)
    aren't repeated. Does nothing before the first plan."""
    before = current_plan(db, user_id)
    if before is None:
        return None
    prev = (before.inputs or {}).get("adjustments") or {}
    adjust = Adjustments(avoid=frozenset(prev.get("avoid") or ()), injury_factors=tuple(sorted((prev.get("injury_factors") or {}).items())))
    return generate_plan(db, user_id, trigger, adjust=adjust, calories=prev.get("calories"),
                         banned=frozenset(prev.get("banned_recipes") or ()), keep_meals=True)
