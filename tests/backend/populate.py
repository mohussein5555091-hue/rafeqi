"""Gives a user one row in every table that holds personal data, linked the way the app links them.

Used by the isolation and account-deletion tests. `test_populate_covers_every_user_table` fails if a
new user-data table is added without being added here, so no table can escape those tests.
"""

import datetime as dt

from sqlalchemy.orm import Session

from app import clock
from app.models import (
    CardioLog, CheckIn, WorkoutMove, CheckInAnswer, Exercise, ExerciseSwap, Food, GroceryItem, GroceryList, GroceryListItem, Injury, LlmCall,
    MealIngredientChange, MealPlan,
    MealPlanItem, PainLog, PantryItem, Plan, ProgramDay, ProgramExercise, Recipe, SetLog, TrainingProgram, WeeklyReview,
    WeightLog, WorkoutLog,
)


def ensure_catalogue(db: Session) -> None:
    if db.get(Exercise, "ex_test"):
        return
    db.add(Exercise(id="ex_test", name_en="Test press", name_ar="ضغط", description_en="d", description_ar="د",
                    movement_pattern="horizontalPush", joints_loaded=["shoulder"], range_of_motion="full",
                    equipment=["dumbbells"], difficulty="beginner"))
    db.add(Food(id="food_test", name_en="Rice", name_ar="رز", kcal_100g=130, protein_100g=2.7, carbs_100g=28, fat_100g=0.3, fiber_100g=0.4))
    db.add(GroceryItem(id="gi_test", name_en="Rice", name_ar="رز", category="pantry", shelf_life="monthly",
                       buying_unit="kg", pack_size=1, grams_per_unit=1000))
    db.add(Recipe(id="r_test", name_en="Rice bowl", name_ar="طبق رز", prep_min=5, cook_min=20, fridge_days=3))
    db.flush()


def populate(db: Session, user_id: str) -> dict[str, str]:
    """Creates the rows; returns {table name: id of the row} for rows that have their own id."""
    ensure_catalogue(db)
    today = dt.date(2026, 9, 28)
    now = clock.now()
    ids: dict[str, str] = {}

    def add(obj):
        db.add(obj)
        db.flush()
        if hasattr(obj, "id"):
            ids[obj.__tablename__] = obj.id
        return obj

    injury = add(Injury(user_id=user_id, region="shoulderL", side="left", type="tendon", severity=3,
                        painful_movements=["overheadPress"], restrictions=["noOverhead"], since=today))
    plan = add(Plan(user_id=user_id, version=1, trigger="onboarding", calories=2200, maintenance_calories=2700,
                    protein_g=170, carbs_g=220, fat_g=65))
    program = add(TrainingProgram(user_id=user_id, plan_id=plan.id, template_id="sample", name_en="P", name_ar="ب",
                                  days_per_week=4, total_weeks=8, deload_week=5, start_date=today))
    day = add(ProgramDay(user_id=user_id, program_id=program.id, day_index=0, weekday="mon", name_en="Upper A",
                         name_ar="علوي أ", est_minutes=58, warmup_minutes=6))
    add(ProgramExercise(user_id=user_id, program_day_id=day.id, exercise_id="ex_test", position=1, sets=3, reps="8-10",
                        rest_sec=120, target_rpe=7))
    workout = add(WorkoutLog(user_id=user_id, plan_id=plan.id, program_day_id=day.id, week_number=1, date=today))
    add(SetLog(user_id=user_id, workout_log_id=workout.id, exercise_id="ex_test", set_number=1, reps=10, weight_kg=20))
    add(ExerciseSwap(user_id=user_id, from_exercise_id="ex_test", to_exercise_id="ex_test", reason="busy", scope="today", date=today))
    add(CardioLog(user_id=user_id, date=today, exercise_id="ex_test", minutes=25))
    add(WorkoutMove(user_id=user_id, week_start=today, from_weekday="sat", to_date=today))
    checkin = add(CheckIn(user_id=user_id, week_number=1, week_start=today, weight_kg=88.0, note="ok"))
    add(CheckInAnswer(user_id=user_id, checkin_id=checkin.id, question_id="sleep", value={"value": 4}))
    add(PainLog(user_id=user_id, injury_id=injury.id, region="shoulderL", pain=3, source="workout", workout_log_id=workout.id))
    add(WeightLog(user_id=user_id, date=today, weight_kg=88.0, source="checkin"))
    meal_plan = add(MealPlan(user_id=user_id, plan_id=plan.id, week_start=today))
    meal = add(MealPlanItem(user_id=user_id, meal_plan_id=meal_plan.id, date=today, slot="lunch", time="14:00",
                            recipe_id="r_test", kcal=600, protein_g=40, carbs_g=70, fat_g=15))
    add(MealIngredientChange(user_id=user_id, meal_plan_item_id=meal.id, group_id="g-test", food_id="food_test",
                             reason="unavailable", scope="meal"))
    grocery = add(GroceryList(user_id=user_id, meal_plan_id=meal_plan.id, week_start=today))
    add(GroceryListItem(user_id=user_id, grocery_list_id=grocery.id, grocery_item_id="gi_test", period="month",
                        grams_needed=1200, qty=2, unit="kg"))
    add(PantryItem(user_id=user_id, grocery_item_id="gi_test", level="low"))
    review = add(WeeklyReview(user_id=user_id, checkin_id=checkin.id, plan_before_id=plan.id, week_number=1))
    add(LlmCall(user_id=user_id, plan_id=plan.id, weekly_review_id=review.id, task="weekly_review", model="test-model",
                prompt_tokens=100, completion_tokens=50, created_at=now))
    db.commit()
    return ids
