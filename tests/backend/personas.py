"""The 5 test personas from docs/PLAN.md, and a helper that runs the whole plan engine for one of them.

Used by test_personas.py (safety checks) and scripts/personas.py (the readable report in docs/personas.md).
"""

import datetime as dt
from dataclasses import dataclass

from app.engine.catalogue import grocery_from_catalogue
from app.engine.grocery import GroceryLine, build_grocery_list
from app.engine.meals import Targets, WeekMeals, plan_week
from app.engine.nutrition import NutritionTargets, add_cardio_reason, compute_targets
from app.engine.training import ProgramPlan, build_program
from app.engine.types import Health, InjuryInfo, Person
from engine_fixtures import exercise_catalogue, food_catalogue, recipe_infos

NORMAL_WEEK = dt.date(2026, 10, 3)    # a Saturday
RAMADAN_WEEK = dt.date(2027, 2, 13)   # a Saturday in Ramadan 2027

PERSONAS: dict[str, tuple[str, Person, dt.date]] = {
    "beginner_woman": ("Beginner woman losing fat (home, dumbbells)", Person(
        sex="female", age=27, height_cm=163, weight_kg=74, goal="loseFat", pace="steady", experience="beginner",
        days_per_week=3, session_minutes=45, location="homeDumbbells", meals_per_day=3, cooking_minutes=30,
        dislikes=("okra", "liver"), allergies=("none",), daily_activity="sitting"), NORMAL_WEEK),
    "shoulder_man": ("Intermediate man with a left shoulder injury", Person(
        sex="male", age=29, height_cm=180, weight_kg=88, goal="loseFat", pace="steady", experience="intermediate",
        days_per_week=4, session_minutes=60, location="gym", meals_per_day=4, cooking_minutes=30,
        dislikes=("liver", "eggplant"), allergies=("none",), fasting=("ramadan",),
        injuries=(InjuryInfo(id="inj_shoulder_l", region="shoulderL", status="active", severity=3,
                             painful_movements=("overheadPress", "benchPress", "dips"), restrictions=("noOverhead",)),),
        daily_activity="onFeet", waist_cm=96), NORMAL_WEEK),
    "advanced_lifter": ("Advanced lifter (strength, 5 days, recovering right knee)", Person(
        sex="male", age=34, height_cm=178, weight_kg=85, goal="strength", pace="steady", experience="advanced",
        days_per_week=5, session_minutes=90, location="gym", meals_per_day=5, cooking_minutes=60,
        injuries=(InjuryInfo(id="inj_knee_r", region="kneeR", status="recovering", severity=2),), daily_activity="onFeet"), NORMAL_WEEK),
    "health_flag": ("Health flag: diabetes and blood-pressure medication, wants to lose fat fast", Person(
        sex="male", age=52, height_cm=172, weight_kg=101, goal="loseFat", pace="faster", experience="beginner",
        days_per_week=3, session_minutes=45, location="gym", meals_per_day=3, cooking_minutes=30,
        health=Health(diabetes=True, exercise_medication=True), allergies=("lactose",), daily_activity="sitting"), NORMAL_WEEK),
    "ramadan_two_meals": ("Fasting in Ramadan, 2 meals a day (suhoor and iftar)", Person(
        sex="female", age=36, height_cm=160, weight_kg=68, goal="recomp", pace="steady", experience="intermediate",
        days_per_week=4, session_minutes=60, location="gym", meals_per_day=2, cooking_minutes=60, fasting=("ramadan",),
        daily_activity="onFeet"), RAMADAN_WEEK),
}


@dataclass
class PersonaPlan:
    person: Person
    week_start: dt.date
    targets: NutritionTargets
    program: ProgramPlan
    meals: WeekMeals
    grocery: list[GroceryLine]


def run(key: str) -> PersonaPlan:
    _, p, start = PERSONAS[key]
    targets = compute_targets(p)
    program = build_program(p, exercise_catalogue())
    if program.cardio and program.cardio.sessions:
        add_cardio_reason(targets, p, len(program.cardio.sessions), program.cardio.sessions[0].minutes)
    meals = plan_week(start, p, Targets(targets.calories, targets.protein_g, targets.carbs_g, targets.fat_g), list(recipe_infos()))
    items, food_map = grocery_from_catalogue(food_catalogue())
    ingredients = {r.id: list(r.ingredients) for r in recipe_infos()}
    grocery = build_grocery_list([(m.recipe_id, m.portion) for m in meals.meals], ingredients, food_map, items)
    return PersonaPlan(p, start, targets, program, meals, grocery)


def why_counts(r: PersonaPlan) -> dict:
    """The "Why this plan" counter for a persona's plan: the same reasons the app stores with a plan (app/plans.py)
    counted the same way as the page (app/views/why.py)."""
    from app.views.why import counts, decision

    reasons = [(x, b) for b, xs in r.targets.reasons.items() for x in xs]
    reasons += [(x, "training") for x in r.program.reasons] + [(x, "meals") for x in r.meals.reasons]
    reasons += [(x, "cardio") for x in (r.program.cardio.reasons if r.program.cardio else [])]
    reasons += [(x, None) for d in r.program.days for x in d.reasons]
    reasons += [(x, None) for d in r.program.days for e in d.exercises for x in e.reasons]
    return counts([decision(x.as_dict(), b, {}) for x, b in reasons])
