"""All tables. Importing this module registers every table on Base.metadata (Alembic relies on it)."""

from app.models.account import Injury, LoginAttempt, PainLog, Profile, User, UserSession, WeightLog
from app.models.base import Base, UserOwned
from app.models.checkin import CheckIn, CheckInAnswer, LlmCall, WeeklyReview
from app.models.nutrition import (
    Food, FoodGroceryItem, GroceryItem, GroceryList, GroceryListItem, MealPlan, MealPlanItem, PantryItem, Recipe,
    RecipeIngredient, RecipeStep,
)
from app.models.training import (
    Exercise, ExerciseSubstitution, Plan, ProgramDay, ProgramExercise, SetLog, TrainingProgram, WorkoutLog,
)

__all__ = [
    "Base", "UserOwned",
    "User", "UserSession", "LoginAttempt", "Profile", "Injury", "PainLog", "WeightLog",
    "Plan", "TrainingProgram", "ProgramDay", "ProgramExercise", "Exercise", "ExerciseSubstitution", "WorkoutLog", "SetLog",
    "Food", "GroceryItem", "FoodGroceryItem", "Recipe", "RecipeIngredient", "RecipeStep",
    "MealPlan", "MealPlanItem", "GroceryList", "GroceryListItem", "PantryItem",
    "CheckIn", "CheckInAnswer", "WeeklyReview", "LlmCall",
]
