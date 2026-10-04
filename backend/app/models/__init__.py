"""All tables. Importing this module registers every table on Base.metadata (Alembic relies on it)."""

from app.models.account import Injury, LoginAttempt, PainLog, Profile, User, UserSession, WeightLog
from app.models.base import Base, UserOwned
from app.models.checkin import CheckIn, CheckInAnswer, LlmCall, WeeklyReview
from app.models.nutrition import (
    Food, FoodGroceryItem, GroceryItem, GroceryList, GroceryListItem, MealIngredientChange, MealPlan, MealPlanItem, PantryItem, Recipe,
    RecipeIngredient, RecipeStep,
)
from app.models.training import (
    CardioLog, Exercise, ExerciseSubstitution, ExerciseSwap, Plan, ProgramDay, ProgramExercise, SetLog, TrainingProgram, WorkoutLog,
    WorkoutMove,
)

__all__ = [
    "Base", "UserOwned",
    "User", "UserSession", "LoginAttempt", "Profile", "Injury", "PainLog", "WeightLog",
    "Plan", "TrainingProgram", "ProgramDay", "ProgramExercise", "Exercise", "ExerciseSubstitution", "WorkoutLog", "SetLog", "ExerciseSwap", "CardioLog", "WorkoutMove",
    "Food", "GroceryItem", "FoodGroceryItem", "Recipe", "RecipeIngredient", "RecipeStep",
    "MealPlan", "MealPlanItem", "MealIngredientChange", "GroceryList", "GroceryListItem", "PantryItem",
    "CheckIn", "CheckInAnswer", "WeeklyReview", "LlmCall",
]
