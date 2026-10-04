"""This week's meals, meal swaps, recipes scaled to the person's portion, the grocery list and the pantry.
Shapes match frontend/src/types.ts (MealDay, MealWeekDay, Meal, Recipe, GroceryList, PantryItem). No prices anywhere."""

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.engine.catalogue import recipes_from_db
from app.engine.meals import MealChoice, Targets, swap_options
from app.engine.rules import load_rules
from app.models import Food, GroceryItem, GroceryList, GroceryListItem, MealPlanItem, PantryItem, Recipe, RecipeIngredient, RecipeStep
from app.plans import person_for, regenerate_grocery_list
from app.views.training import bi
from app.week import Week, weekday_of

PORTION_INGREDIENTS = 2  # the meal card names the biggest ingredients, with grams for this person's portion


def _foods(db: Session) -> dict[str, Food]:
    return {f.id: f for f in db.scalars(select(Food))}


def _ingredients(db: Session, recipe_id: str) -> list[RecipeIngredient]:
    return list(db.scalars(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id).order_by(RecipeIngredient.id)))


def portions_text(db: Session, recipe_id: str, portion: float, foods: dict[str, Food]) -> dict:
    """"Fava beans 200 g · Baladi bread 90 g": the main ingredients in everyday amounts for this portion."""
    main = sorted(_ingredients(db, recipe_id), key=lambda i: -i.grams)[:PORTION_INGREDIENTS]
    parts = [(foods[i.food_id], round(i.grams * portion)) for i in main]
    return bi(" · ".join(f"{f.name_en} {g} g" for f, g in parts), " · ".join(f"{f.name_ar} {g} جم" for f, g in parts))


def meal_out(db: Session, item: MealPlanItem, recipes: dict[str, Recipe], foods: dict[str, Food]) -> dict:
    r = recipes[item.recipe_id]
    return {"id": item.id, "slot": item.slot, "time": item.time, "name": bi(r.name_en, r.name_ar),
            "portions": portions_text(db, r.id, item.portion, foods), "kcal": item.kcal, "proteinG": item.protein_g,
            "carbsG": item.carbs_g, "fatG": item.fat_g, "recipeId": r.id, "eaten": item.eaten}


def _items(db: Session, week: Week, d: dt.date) -> list[MealPlanItem]:
    return list(db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == week.meal_plan.id, MealPlanItem.user_id == week.plan.user_id,
                                                      MealPlanItem.date == week.meal_date(d)).order_by(MealPlanItem.time)))


def _recipes(db: Session) -> dict[str, Recipe]:
    return {r.id: r for r in db.scalars(select(Recipe))}


def meal_day(db: Session, week: Week, d: dt.date) -> dict:
    recipes, foods = _recipes(db), _foods(db)
    return {"date": d.isoformat(), "day": weekday_of(d), "isTrainingDay": week.day_on(d) is not None,
            "meals": [meal_out(db, i, recipes, foods) for i in _items(db, week, d)]}


def meal_week(db: Session, week: Week) -> list[dict]:
    recipes = _recipes(db)
    out = []
    for d in week.dates:
        items = _items(db, week, d)
        main = max(items, key=lambda i: i.kcal) if items else None
        name = lambda i: recipes[i.recipe_id]  # noqa: E731
        out.append({"date": d.isoformat(), "day": weekday_of(d), "kcal": sum(i.kcal for i in items),
                    "main": bi(name(main).name_en, name(main).name_ar) if main else bi("", ""),
                    "others": bi(" · ".join(name(i).name_en for i in items if i is not main),
                                 " · ".join(name(i).name_ar for i in items if i is not main))})
    return out


def _choice(i: MealPlanItem) -> MealChoice:
    return MealChoice(date=i.date, slot=i.slot, time=i.time, recipe_id=i.recipe_id, portion=i.portion, kcal=i.kcal,
                      protein=i.protein_g, carbs=i.carbs_g, fat=i.fat_g)


def _options(db: Session, week: Week, item: MealPlanItem) -> list[MealChoice]:
    day = list(db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == item.meal_plan_id, MealPlanItem.date == item.date)
                          .order_by(MealPlanItem.time)))
    p = week.plan
    banned = frozenset(((p.inputs or {}).get("adjustments") or {}).get("banned_recipes") or ())
    return swap_options([_choice(i) for i in day], [i.id for i in day].index(item.id), Targets(p.calories, p.protein_g, p.carbs_g, p.fat_g),
                        person_for(db, p.user_id), recipes_from_db(db), banned)


def meal_item(db: Session, week: Week, item_id: str) -> MealPlanItem | None:
    """One meal of the current plan (None for someone else's, or an old plan's)."""
    return db.scalar(select(MealPlanItem).where(MealPlanItem.id == item_id, MealPlanItem.user_id == week.plan.user_id,
                                                MealPlanItem.meal_plan_id == week.meal_plan.id))


def swap_options_out(db: Session, week: Week, item: MealPlanItem) -> list[dict]:
    recipes, foods = _recipes(db), _foods(db)
    out = []
    for c in _options(db, week, item):
        r = recipes[c.recipe_id]
        out.append({"id": c.recipe_id, "slot": c.slot, "time": item.time, "name": bi(r.name_en, r.name_ar),
                    "portions": portions_text(db, r.id, c.portion, foods), "kcal": c.kcal, "proteinG": c.protein,
                    "carbsG": c.carbs, "fatG": c.fat, "recipeId": r.id})
    return out


class NotAnOption(Exception):
    pass


def swap_meal(db: Session, week: Week, item: MealPlanItem, recipe_id: str) -> None:
    """Replaces one meal with one of its swap options (portion from the engine), then rebuilds the grocery list."""
    choice = next((c for c in _options(db, week, item) if c.recipe_id == recipe_id), None)
    if choice is None:
        raise NotAnOption
    recipes = _recipes(db)
    old, new = recipes[item.recipe_id], recipes[recipe_id]
    item.replaced_recipe_id = item.replaced_recipe_id or item.recipe_id
    item.recipe_id, item.portion = choice.recipe_id, choice.portion
    item.kcal, item.protein_g, item.carbs_g, item.fat_g = choice.kcal, choice.protein, choice.carbs, choice.fat
    tol = load_rules()["nutrition"]["meals"]["calorie_tolerance_pct"]
    item.reason = {"rule": "nutrition.meals.swap", "source": load_rules()["nutrition"]["meals"]["source"],
                   "en": f"You swapped {old.name_en} for {new.name_en}; the day stays within {tol}% of your calories with enough protein.",
                   "ar": f"بدّلت {old.name_ar} بـ{new.name_ar}؛ اليوم لسه في حدود {tol}% من سعراتك وفيه بروتين كفاية."}
    db.flush()
    note = bi(f"Updated: you swapped {old.name_en} for {new.name_en}.", f"اتحدّثت: بدّلت {old.name_ar} بـ{new.name_ar}.")
    rebuild_grocery_list(db, week, note)


def latest_grocery_list(db: Session, week: Week) -> GroceryList | None:
    return db.scalars(select(GroceryList).where(GroceryList.meal_plan_id == week.meal_plan.id, GroceryList.user_id == week.plan.user_id)
                      .order_by(GroceryList.created_at.desc())).first()


def rebuild_grocery_list(db: Session, week: Week, note: dict | None) -> GroceryList:
    """A new list after the meals changed; ticks and "I already have this" carry over for items still on it."""
    before = latest_grocery_list(db, week)
    kept = {}
    if before is not None:
        kept = {(i.grocery_item_id, i.period): (i.checked, i.have_it)
                for i in db.scalars(select(GroceryListItem).where(GroceryListItem.grocery_list_id == before.id))}
    if before is not None:
        db.execute(delete(GroceryListItem).where(GroceryListItem.grocery_list_id == before.id))
        db.delete(before)  # only the latest list is ever shown
        db.flush()
    gl = regenerate_grocery_list(db, week.plan.user_id, week.meal_plan, change_note=note)
    for i in db.scalars(select(GroceryListItem).where(GroceryListItem.grocery_list_id == gl.id)):
        if (i.grocery_item_id, i.period) in kept:
            i.checked, have_it = kept[(i.grocery_item_id, i.period)]
            i.have_it = i.have_it or have_it
    db.flush()
    return gl


def grocery_out(db: Session, week: Week) -> dict:
    gl = latest_grocery_list(db, week)
    out = {"weekNumber": week.number, "start": week.start.isoformat(), "end": week.end.isoformat(), "items": []}
    if gl is None:
        return out
    if gl.change_note:
        out["changeNote"] = gl.change_note
    items = {g.id: g for g in db.scalars(select(GroceryItem))}
    for i in db.scalars(select(GroceryListItem).where(GroceryListItem.grocery_list_id == gl.id)):
        g = items[i.grocery_item_id]
        out["items"].append({"id": i.id, "name": bi(g.name_en, g.name_ar), "category": g.category, "qty": i.qty, "unit": i.unit,
                             "period": i.period, "checked": i.checked, "haveIt": i.have_it})
    out["items"].sort(key=lambda x: x["name"]["en"])
    return out


def grocery_line(db: Session, week: Week, line_id: str) -> GroceryListItem | None:
    gl = latest_grocery_list(db, week)
    if gl is None:
        return None
    return db.scalar(select(GroceryListItem).where(GroceryListItem.id == line_id, GroceryListItem.user_id == week.plan.user_id,
                                                   GroceryListItem.grocery_list_id == gl.id))


def pantry_out(db: Session, user_id: str) -> list[dict]:
    items = {g.id: g for g in db.scalars(select(GroceryItem))}
    rows = db.scalars(select(PantryItem).where(PantryItem.user_id == user_id))
    return sorted(({"id": p.id, "name": bi(items[p.grocery_item_id].name_en, items[p.grocery_item_id].name_ar), "level": p.level}
                   for p in rows), key=lambda x: x["name"]["en"])


def recipe_out(db: Session, recipe_id: str, week: Week | None) -> dict | None:
    """Ingredient amounts are scaled to the person's portion of this recipe in the current plan (1 when it isn't in it)."""
    r = db.get(Recipe, recipe_id)
    if r is None:
        return None
    portion = 1.0
    if week is not None:
        # The next time it's on the plan (today first), as the plan's week repeats.
        items = db.scalars(select(MealPlanItem).where(MealPlanItem.meal_plan_id == week.meal_plan.id, MealPlanItem.recipe_id == r.id))
        upcoming = sorted(items, key=lambda i: ((i.date - week.meal_date(week.today)).days % 7, i.time))
        portion = upcoming[0].portion if upcoming else 1.0
    foods = _foods(db)
    ings = _ingredients(db, r.id)
    total = {k: sum(getattr(foods[i.food_id], f"{k}_100g") * i.grams / 100 for i in ings) * portion for k in ("kcal", "protein", "carbs", "fat")}

    def amount(i: RecipeIngredient) -> dict:
        grams = round(i.grams * portion)
        if portion == 1 and i.amount_en:
            return bi(i.amount_en, i.amount_ar or i.amount_en)
        return bi(f"{grams} g", f"{grams} جم")

    out = {
        "id": r.id, "name": bi(r.name_en, r.name_ar), "prepMin": r.prep_min, "cookMin": r.cook_min, "fridgeDays": r.fridge_days,
        "kcal": round(total["kcal"]), "proteinG": round(total["protein"]), "carbsG": round(total["carbs"]), "fatG": round(total["fat"]),
        "ingredients": [{"name": bi(foods[i.food_id].name_en, foods[i.food_id].name_ar), "grams": round(i.grams * portion), "amount": amount(i)}
                        for i in ings],
        "steps": [{"text": bi(s.text_en, s.text_ar), **({"timerSec": s.timer_sec} if s.timer_sec else {})}
                  for s in db.scalars(select(RecipeStep).where(RecipeStep.recipe_id == r.id).order_by(RecipeStep.position))],
        "storage": bi(r.storage_en, r.storage_ar), "reheating": bi(r.reheating_en, r.reheating_ar),
    }
    if r.photo_url:
        out["photoUrl"] = r.photo_url
    return out
