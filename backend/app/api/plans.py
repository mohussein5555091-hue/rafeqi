"""The person's plan: build it (after onboarding, or "regenerate my plan") and read the current version."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import plans
from app.api.deps import CurrentAuth, Db
from app.models import GroceryList, GroceryListItem, MealPlan, MealPlanItem, Plan, ProgramDay, ProgramExercise, TrainingProgram

router = APIRouter(prefix="/api/plan", tags=["plan"])


def plan_out(db: Session, plan: Plan) -> dict:
    """Everything in one plan version. The screens are connected to this in Phase 5."""
    tp = db.scalar(select(TrainingProgram).where(TrainingProgram.plan_id == plan.id))
    mp = db.scalar(select(MealPlan).where(MealPlan.plan_id == plan.id))
    gl = db.scalar(select(GroceryList).where(GroceryList.meal_plan_id == mp.id).order_by(GroceryList.created_at.desc())) if mp else None
    days = list(db.scalars(select(ProgramDay).where(ProgramDay.program_id == tp.id).order_by(ProgramDay.day_index))) if tp else []
    return {
        "id": plan.id, "version": plan.version, "trigger": plan.trigger, "createdAt": plan.created_at.isoformat(),
        "calories": plan.calories, "maintenanceCalories": plan.maintenance_calories, "proteinG": plan.protein_g,
        "carbsG": plan.carbs_g, "fatG": plan.fat_g, "conservative": plan.conservative, "rulesVersion": plan.rules_version,
        "reasons": plan.reasons,
        "program": tp and {
            "name": {"en": tp.name_en, "ar": tp.name_ar}, "templateId": tp.template_id, "daysPerWeek": tp.days_per_week,
            "totalWeeks": tp.total_weeks, "deloadWeek": tp.deload_week, "startDate": tp.start_date.isoformat(),
            "days": [{
                "weekday": d.weekday, "name": {"en": d.name_en, "ar": d.name_ar}, "estMinutes": d.est_minutes,
                "exercises": [{
                    "exerciseId": e.exercise_id, "sets": e.sets, "reps": e.reps, "restSec": e.rest_sec, "rpe": e.target_rpe,
                    "startWeightKg": e.start_weight_kg, "weightStepKg": e.weight_step_kg, "loadFactor": e.load_factor,
                    "replacedExerciseId": e.replaced_exercise_id, "injuryId": e.injury_id, "swapKind": e.swap_kind,
                    "reasons": (e.swap_reason or {}).get("reasons", []),
                } for e in db.scalars(select(ProgramExercise).where(ProgramExercise.program_day_id == d.id).order_by(ProgramExercise.position))],
            } for d in days],
        },
        "meals": [{"date": m.date.isoformat(), "slot": m.slot, "time": m.time, "recipeId": m.recipe_id, "portion": m.portion,
                   "kcal": m.kcal, "proteinG": m.protein_g, "carbsG": m.carbs_g, "fatG": m.fat_g}
                  for m in (db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == mp.id).order_by(MealPlanItem.date, MealPlanItem.time)) if mp else [])],
        "grocery": [{"itemId": g.grocery_item_id, "period": g.period, "qty": g.qty, "unit": g.unit, "haveIt": g.have_it}
                    for g in (db.scalars(select(GroceryListItem).where(GroceryListItem.grocery_list_id == gl.id)) if gl else [])],
    }


@router.get("")
def get_plan(auth: CurrentAuth, db: Db):
    plan = plans.current_plan(db, auth.user.id)
    if plan is None:
        raise HTTPException(404, "no_plan_yet")
    return plan_out(db, plan)


@router.post("")
def build_plan(auth: CurrentAuth, db: Db):
    """Builds a new plan version from the saved questionnaire answers (409 until onboarding is complete)."""
    try:
        first = plans.current_plan(db, auth.user.id) is None
        plan = plans.generate_plan(db, auth.user.id, "onboarding" if first else "regenerate")
    except plans.NotReady as e:
        raise HTTPException(409, "onboarding_incomplete") from e
    db.commit()
    return plan_out(db, plan)
