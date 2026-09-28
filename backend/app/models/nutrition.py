"""Food catalogue, recipes, meal plans, grocery lists and the pantry. No prices or brands anywhere."""

import datetime as dt
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UserOwned, owner, timestamp, uuid_pk


class Food(Base):
    """Catalogue. Nutrition per 100 g."""

    __tablename__ = "foods"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    kcal_100g: Mapped[float]
    protein_100g: Mapped[float]
    carbs_100g: Mapped[float]
    fat_100g: Mapped[float]
    fiber_100g: Mapped[float]
    units: Mapped[list] = mapped_column(default=list)  # [{en: "1 baladi loaf", ar: "رغيف بلدي", grams: 90}]
    tags: Mapped[list] = mapped_column(default=list)  # matched against dislikes and allergies
    source: Mapped[str] = mapped_column(String(200), default="")


class GroceryItem(Base):
    """Catalogue. Generic names only ("Milk", "Chicken breast"), never brands, and no prices."""

    __tablename__ = "grocery_items"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(12))  # produce | meat | dairy | bakery | pantry | spices
    shelf_life: Mapped[str] = mapped_column(String(8))  # weekly | monthly
    buying_unit: Mapped[str] = mapped_column(String(8))  # kg | g | L | pcs | …
    pack_size: Mapped[float]  # 1 (L), 1 (kg), 30 (eggs)
    grams_per_unit: Mapped[float]  # 1 egg = 60 g, 1 L milk = 1030 g


class FoodGroceryItem(Base):
    """Catalogue: which grocery item covers a food, and how much raw item per gram of food."""

    __tablename__ = "food_grocery_items"

    food_id: Mapped[str] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True)
    grocery_item_id: Mapped[str] = mapped_column(ForeignKey("grocery_items.id", ondelete="CASCADE"), primary_key=True)
    raw_grams_per_gram: Mapped[float] = mapped_column(default=1.0)  # cooked rice → dry rice ≈ 0.4


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    slots: Mapped[list] = mapped_column(default=list)  # breakfast, lunch, snack, dinner, suhoor, iftar
    prep_min: Mapped[int]
    cook_min: Mapped[int]
    fridge_days: Mapped[int]
    servings: Mapped[int] = mapped_column(default=1)
    storage_en: Mapped[str] = mapped_column(Text, default="")
    storage_ar: Mapped[str] = mapped_column(Text, default="")
    reheating_en: Mapped[str] = mapped_column(Text, default="")
    reheating_ar: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(default=list)
    photo_url: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(200), default="")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[str] = mapped_column(ForeignKey("foods.id"))
    grams: Mapped[float]  # per serving
    amount_en: Mapped[str] = mapped_column(String(80), default="")  # "1 ladle"
    amount_ar: Mapped[str] = mapped_column(String(80), default="")


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    text_en: Mapped[str] = mapped_column(Text)
    text_ar: Mapped[str] = mapped_column(Text)
    timer_sec: Mapped[int | None]


class MealPlan(Base, UserOwned):
    __tablename__ = "meal_plans"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[dt.date]
    status: Mapped[str] = mapped_column(String(12), default="active")
    created_at: Mapped[datetime] = timestamp()


class MealPlanItem(Base, UserOwned):
    __tablename__ = "meal_plan_items"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    meal_plan_id: Mapped[str] = mapped_column(ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date]
    slot: Mapped[str] = mapped_column(String(10))
    time: Mapped[str] = mapped_column(String(5))  # "08:30"
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id"))
    portion: Mapped[float] = mapped_column(default=1.0)  # scale factor chosen by the optimizer
    kcal: Mapped[int]
    protein_g: Mapped[int]
    carbs_g: Mapped[int]
    fat_g: Mapped[int]
    eaten: Mapped[bool] = mapped_column(default=False)
    replaced_recipe_id: Mapped[str | None] = mapped_column(ForeignKey("recipes.id"))
    reason: Mapped[dict | None]


class GroceryList(Base, UserOwned):
    __tablename__ = "grocery_lists"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    meal_plan_id: Mapped[str] = mapped_column(ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[dt.date]
    change_note: Mapped[dict | None]  # {en, ar}
    created_at: Mapped[datetime] = timestamp()


class GroceryListItem(Base, UserOwned):
    __tablename__ = "grocery_list_items"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    grocery_list_id: Mapped[str] = mapped_column(ForeignKey("grocery_lists.id", ondelete="CASCADE"), index=True)
    grocery_item_id: Mapped[str] = mapped_column(ForeignKey("grocery_items.id"))
    period: Mapped[str] = mapped_column(String(5))  # week | month
    grams_needed: Mapped[float]
    qty: Mapped[float]  # rounded up to pack sizes
    unit: Mapped[str] = mapped_column(String(8))
    checked: Mapped[bool] = mapped_column(default=False)
    have_it: Mapped[bool] = mapped_column(default=False)


class PantryItem(Base, UserOwned):
    __tablename__ = "pantry_items"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    grocery_item_id: Mapped[str] = mapped_column(ForeignKey("grocery_items.id"))
    level: Mapped[str] = mapped_column(String(10), default="plenty")  # plenty | low | untracked
    updated_at: Mapped[datetime] = timestamp()

    __table_args__ = (UniqueConstraint("user_id", "grocery_item_id"),)
