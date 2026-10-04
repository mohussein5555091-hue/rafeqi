"""Removing an ingredient from a meal (the meal cards and the recipe page), with one-tap reasons, an optional
same-role replacement, "Just this meal" or "Always", and Undo.

- "Always" changes every meal of the week that has the food (where it isn't essential), and "Always" or
  "I don't like it" also puts it in the profile's disliked foods, so every later plan (the weekly review,
  "regenerate my plan") leaves it out (app/engine/meals.py eligible_recipes).
- An essential ingredient (lentils in lentil soup) can't be removed: the meal is swapped instead.
- After every change the meal's and the day's calories and macros are worked out again, and if the day fell below
  its targets the engine moves the other portions a little or suggests a snack (app/engine/ingredients.py). What it
  changed is saved with the day (meal_plans.day_notes) and shown on the day.
- The grocery list is rebuilt from what's really cooked: a removed food leaves it unless another meal needs it, and a
  replacement is added.
"""

import datetime as dt
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.engine.catalogue import foods_from_db, recipes_from_db
from app.engine.ingredients import DayMeal, per_serving, rebalance_day, replacement_grams, replacements
from app.engine.meals import eligible_recipes
from app.engine.rules import load_rules
from app.engine.types import FoodInfo
from app.meal_changes import by_person, changes_by_item, item_ingredients, recipe_ingredients
from app.models import MealIngredientChange, MealPlanItem, Profile, Recipe
from app.plans import person_for
from app.week import Week

REASONS = ("dislike", "unavailable")
SCOPES = ("meal", "always")


class NotInMeal(Exception):
    pass


class Essential(Exception):
    pass


class NotAReplacement(Exception):
    pass


def _bi(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


def _recipe_names(db: Session) -> dict[str, dict]:
    return {r.id: _bi(r.name_en, r.name_ar) for r in db.scalars(select(Recipe))}


def ingredient_rows(item: MealPlanItem, recipes: dict, rows: list[MealIngredientChange], foods: dict[str, FoodInfo]) -> list[dict]:
    """The meal's ingredients for the screens: kept, removed (struck through) or replaced, at this meal's portion."""
    by_food = {c.food_id: c for c in rows}
    out = []
    for ing in recipes.get(item.recipe_id, []):
        grams = round(ing.grams * item.portion)
        row = {"foodId": ing.food_id, "name": foods[ing.food_id].name, "grams": grams, "essential": ing.essential,
               "amount": _bi(ing.amount_en, ing.amount_ar or ing.amount_en) if item.portion == 1 and ing.amount_en else _bi(f"{grams} g", f"{grams} جم"),
               "status": "kept"}
        c = by_food.get(ing.food_id)
        if c is not None:
            row["status"] = "replaced" if c.replacement_food_id else "removed"
            row["change"] = {"reason": c.reason, "scope": c.scope}
            if c.replacement_food_id:
                g = round((c.replacement_grams or 0) * item.portion)
                row["replacement"] = {"foodId": c.replacement_food_id, "name": foods[c.replacement_food_id].name, "grams": g,
                                      "amount": _bi(f"{g} g", f"{g} جم")}
        out.append(row)
    return out


def _base(recipes: dict, item: MealPlanItem) -> dict:
    return {i.food_id: i for i in recipes.get(item.recipe_id, [])}


def replacement_options(db: Session, week: Week, item: MealPlanItem, food_id: str) -> dict:
    """What the Remove sheet offers: whether it's essential, and 1–3 same-role replacements (grams at this portion)."""
    recipes = recipe_ingredients(db)
    base = _base(recipes, item)
    if food_id not in base:
        raise NotInMeal
    foods = foods_from_db(db)
    p = person_for(db, week.plan.user_id)
    out = {"foodId": food_id, "name": foods[food_id].name, "essential": base[food_id].essential, "role": foods[food_id].role, "options": []}
    if base[food_id].essential:
        return out
    for f, grams in replacements(food_id, base[food_id].grams, set(base), foods, p.avoided_food_tags, set(p.disliked_foods)):
        g = round(grams * item.portion)
        mac = {k: round(getattr(f, k) * grams * item.portion / 100) for k in ("kcal", "protein", "carbs", "fat")}
        out["options"].append({"foodId": f.id, "name": f.name, "grams": g, "kcal": mac["kcal"], "proteinG": mac["protein"],
                               "carbsG": mac["carbs"], "fatG": mac["fat"]})
    return out


def _set_dislike(db: Session, user_id: str, food_id: str, on: bool) -> bool:
    """Adds (or removes) a food in the profile's disliked foods. True if it changed."""
    prof = db.get(Profile, user_id)
    current = list(prof.disliked_foods or [])
    if on and food_id not in current:
        prof.disliked_foods = current + [food_id]
        return True
    if not on and food_id in current:
        prof.disliked_foods = [f for f in current if f != food_id]
        return True
    return False


def remove_ingredient(db: Session, week: Week, item: MealPlanItem, food_id: str, reason: str, scope: str,
                      replacement_id: str | None) -> list[dt.date]:
    """Saves the change (one meal, or every meal of the week that has the food), then rebalances each changed day and
    rebuilds the grocery list. Returns the plan dates that changed."""
    recipes = recipe_ingredients(db)
    base = _base(recipes, item)
    if food_id not in base:
        raise NotInMeal
    if base[food_id].essential:
        raise Essential
    foods = foods_from_db(db)
    user_id = week.plan.user_id
    if replacement_id is not None and replacement_id not in {o["foodId"] for o in replacement_options(db, week, item, food_id)["options"]}:
        raise NotAReplacement

    targets = [item]
    if scope == "always":
        others = db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == week.meal_plan.id, MealPlanItem.user_id == user_id,
                                                       MealPlanItem.id != item.id))
        targets += [o for o in others if food_id in (b := _base(recipes, o)) and not b[food_id].essential]
    added = (reason == "dislike" or scope == "always") and _set_dislike(db, user_id, food_id, True)
    group = str(uuid.uuid4())
    existing = changes_by_item(db, user_id, [t.id for t in targets])
    for t in targets:
        if any(c.food_id == food_id for c in existing.get(t.id, [])):
            if t is not item:
                continue  # already changed there: "Always" doesn't undo an earlier choice
            db.execute(delete(MealIngredientChange).where(MealIngredientChange.meal_plan_item_id == t.id, MealIngredientChange.food_id == food_id))
        repl, grams = replacement_id, None
        if repl is not None:
            if repl in _base(recipes, t):
                repl = None  # that meal already has it: just leave the food out
            else:
                grams = replacement_grams(foods[food_id], _base(recipes, t)[food_id].grams, foods[repl])
        db.add(MealIngredientChange(user_id=user_id, meal_plan_item_id=t.id, group_id=group, food_id=food_id, replacement_food_id=repl,
                                    replacement_grams=grams, reason=reason, scope=scope, added_dislike=added))
    db.flush()
    dates = sorted({t.date for t in targets})
    for d in dates:
        recompute_day(db, week, d)
    return dates


def undo_change(db: Session, week: Week, item: MealPlanItem, food_id: str) -> list[dt.date]:
    """Undo: the whole action (every meal "Always" changed), and the disliked food it added to the profile."""
    user_id = week.plan.user_id
    row = db.scalar(select(MealIngredientChange).where(MealIngredientChange.user_id == user_id, MealIngredientChange.meal_plan_item_id == item.id,
                                                       MealIngredientChange.food_id == food_id))
    if row is None:
        raise NotInMeal
    rows = list(db.scalars(select(MealIngredientChange).where(MealIngredientChange.user_id == user_id, MealIngredientChange.group_id == row.group_id)))
    item_ids = [r.meal_plan_item_id for r in rows]
    if any(r.added_dislike for r in rows) or not by_person(row):  # a food the plan left out for good: it's liked again
        _set_dislike(db, user_id, food_id, False)
    db.execute(delete(MealIngredientChange).where(MealIngredientChange.user_id == user_id, MealIngredientChange.group_id == row.group_id))
    db.flush()
    dates = sorted({i.date for i in db.scalars(select(MealPlanItem).where(MealPlanItem.id.in_(item_ids), MealPlanItem.user_id == user_id))})
    for d in dates:
        recompute_day(db, week, d)
    return dates


def recompute_day(db: Session, week: Week, d: dt.date) -> None:
    """Every meal's calories and macros from what it's really made of, and the day kept on target
    (app/engine/ingredients.py rebalance_day). The engine's notes are saved with the day."""
    user_id, plan, mp = week.plan.user_id, week.plan, week.meal_plan
    items = list(db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == mp.id, MealPlanItem.user_id == user_id,
                                                       MealPlanItem.date == d).order_by(MealPlanItem.time)))
    recipes, foods, names = recipe_ingredients(db), foods_from_db(db), _recipe_names(db)
    changes = changes_by_item(db, user_id, [i.id for i in items])
    meals, before = [], {"kcal": 0.0, "protein": 0.0}
    for i in items:
        if i.planned_portion is None:
            i.planned_portion = i.portion
        orig = per_serving(item_ingredients(i, recipes, [c for c in changes.get(i.id, []) if not by_person(c)]), foods)
        before = {k: before[k] + orig[k] * i.planned_portion for k in before}
        now = per_serving(item_ingredients(i, recipes, changes.get(i.id, [])), foods)
        meals.append(DayMeal(i.id, names[i.recipe_id], now["kcal"], now["protein"], now["carbs"], now["fat"], i.planned_portion, i.eaten))
    notes = dict(mp.day_notes or {})
    # Only the person's own choices on this day count (foods left out of a new plan for good are already planned for).
    mine = [c for i in items for c in changes.get(i.id, []) if by_person(c)]
    if not mine:
        portions = {m.id: m.planned for m in meals}
        notes.pop(d.isoformat(), None)
    else:
        p = person_for(db, user_id)
        day_recipes = {i.recipe_id for i in items}
        snacks = [r for r in eligible_recipes(recipes_from_db(db), p) if "snack" in r.slots and r.id not in day_recipes]
        rb = rebalance_day(meals, plan.calories, plan.protein_g, before, snacks)
        portions = rb.portions
        lines = [_change_line(c, items, names, foods) for c in mine] + [{"en": r.en, "ar": r.ar} for r in rb.reasons]
        notes[d.isoformat()] = {"lines": lines, "snack": rb.snack, "onTarget": rb.on_target}
    for i, m in zip(items, meals):
        i.portion = portions[m.id]
        i.kcal, i.protein_g, i.carbs_g, i.fat_g = (round(getattr(m, k) * i.portion) for k in ("kcal", "protein", "carbs", "fat"))
    mp.day_notes = notes
    db.flush()


def _change_line(c: MealIngredientChange, items: list[MealPlanItem], names: dict, foods: dict[str, FoodInfo]) -> dict:
    t = load_rules()["nutrition"]["ingredients"]["explain"]
    item = next(i for i in items if i.id == c.meal_plan_item_id)
    meal, name = names[item.recipe_id], foods[c.food_id].name
    if c.replacement_food_id:
        g = round((c.replacement_grams or 0) * item.portion)
        to = foods[c.replacement_food_id].name
        return {lang: t["replaced"][lang].format(name=name[lang], to=to[lang], grams=g, meal=meal[lang]) for lang in ("en", "ar")}
    return {lang: t["removed"][lang].format(name=name[lang], meal=meal[lang]) for lang in ("en", "ar")}


def change_note(db: Session, food_id: str, replacement_id: str | None, undo: bool = False) -> dict:
    """The grocery list's "Updated: …" line."""
    foods = foods_from_db(db)
    name = foods[food_id].name
    if undo:
        return _bi(f"Updated: {name['en']} is back in your meals.", f"اتحدّثت: {name['ar']} رجع لوجباتك.")
    if replacement_id:
        to = foods[replacement_id].name
        return _bi(f"Updated: {name['en']} replaced by {to['en']}.", f"اتحدّثت: {to['ar']} بدل {name['ar']}.")
    return _bi(f"Updated: {name['en']} removed from your meals.", f"اتحدّثت: {name['ar']} اتشال من وجباتك.")
