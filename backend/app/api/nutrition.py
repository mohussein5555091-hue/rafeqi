"""This week's meals, swaps, recipes, the grocery list and the pantry."""

import datetime as dt

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentAuth, Db
from app.api.training import current_week
from app.schemas.screens import GroceryPatchIn, RemoveIngredientIn, SwapIn
from app.views import ingredients as ing
from app.views import nutrition as v
from app.week import NoPlan, this_week

router = APIRouter(tags=["nutrition"])


@router.get("/api/meals/week")
def get_meal_week(auth: CurrentAuth, db: Db):
    return v.meal_week(db, current_week(db, auth.user.id))


@router.get("/api/meals/day/{date}")
def get_meal_day(date: str, auth: CurrentAuth, db: Db):
    """One date of this week (the week runs Saturday to Friday), as 2026-10-02, or `today`."""
    week = current_week(db, auth.user.id)
    try:
        day = week.today if date == "today" else dt.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(404, "not_found") from None
    if not week.in_week(day):
        raise HTTPException(404, "not_found")
    return v.meal_day(db, week, day)


def _item(db, user_id: str, item_id: str):
    week = current_week(db, user_id)
    item = v.meal_item(db, week, item_id)
    if item is None:
        raise HTTPException(404, "not_found")
    return week, item


@router.get("/api/meals/{item_id}/swap-options")
def get_swap_options(item_id: str, auth: CurrentAuth, db: Db):
    week, item = _item(db, auth.user.id, item_id)
    return v.swap_options_out(db, week, item)


@router.post("/api/meals/{item_id}/swap")
def swap(item_id: str, body: SwapIn, auth: CurrentAuth, db: Db):
    """Replaces the meal (on every week this plan repeats) and rebuilds the grocery list. Returns the day."""
    week, item = _item(db, auth.user.id, item_id)
    try:
        v.swap_meal(db, week, item, body.recipe_id)
    except v.NotAnOption:
        raise HTTPException(422, "not_a_swap_option") from None
    db.commit()
    return v.meal_day(db, week, _shown(week, item))


def _shown(week, item) -> dt.date:
    """The meal's day as the screens show it (this week's date for that plan day)."""
    return next(d for d in week.dates if week.meal_date(d) == item.date)


@router.get("/api/meals/{item_id}/ingredients/{food_id}/replacements")
def get_replacements(item_id: str, food_id: str, auth: CurrentAuth, db: Db):
    """What the Remove sheet offers for one ingredient: whether it's essential (then: swap the meal), and 1–3
    replacements with the same role, sized for this meal's portion."""
    week, item = _item(db, auth.user.id, item_id)
    try:
        return ing.replacement_options(db, week, item, food_id)
    except ing.NotInMeal:
        raise HTTPException(404, "not_found") from None


@router.post("/api/meals/{item_id}/ingredients/{food_id}/remove")
def remove_ingredient(item_id: str, food_id: str, body: RemoveIngredientIn, auth: CurrentAuth, db: Db):
    """Removes (or replaces) an ingredient: this meal, or "always" (every meal this week, and every later plan).
    Rebalances the day and rebuilds the grocery list. Returns the meal's day. 409 for an essential ingredient."""
    week, item = _item(db, auth.user.id, item_id)
    try:
        ing.remove_ingredient(db, week, item, food_id, body.reason, body.scope, body.replacement_food_id)
    except ing.NotInMeal:
        raise HTTPException(404, "not_found") from None
    except ing.Essential:
        raise HTTPException(409, "essential_ingredient") from None
    except ing.NotAReplacement:
        raise HTTPException(422, "not_a_replacement") from None
    v.rebuild_grocery_list(db, week, ing.change_note(db, food_id, body.replacement_food_id))
    db.commit()
    return v.meal_day(db, week, _shown(week, item))


@router.delete("/api/meals/{item_id}/ingredients/{food_id}")
def undo_ingredient(item_id: str, food_id: str, auth: CurrentAuth, db: Db):
    """Undo: the ingredient is back (in every meal the same action changed), and it's no longer a disliked food."""
    week, item = _item(db, auth.user.id, item_id)
    try:
        ing.undo_change(db, week, item, food_id)
    except ing.NotInMeal:
        raise HTTPException(404, "not_found") from None
    v.rebuild_grocery_list(db, week, ing.change_note(db, food_id, None, undo=True))
    db.commit()
    return v.meal_day(db, week, _shown(week, item))


@router.get("/api/recipes/{recipe_id}")
def get_recipe(recipe_id: str, auth: CurrentAuth, db: Db, meal: str | None = None):
    """`meal`: the meal it was opened from (portions, and that meal's removed or replaced ingredients)."""
    try:
        week = this_week(db, auth.user.id)
    except NoPlan:
        week = None
    out = v.recipe_out(db, recipe_id, week, meal)
    if out is None:
        raise HTTPException(404, "not_found")
    return out


@router.get("/api/groceries")
def get_groceries(auth: CurrentAuth, db: Db):
    return v.grocery_out(db, current_week(db, auth.user.id))


@router.patch("/api/groceries/items/{item_id}")
def update_grocery_item(item_id: str, body: GroceryPatchIn, auth: CurrentAuth, db: Db):
    """Tick an item, or mark "I already have this". Returns the whole list."""
    week = current_week(db, auth.user.id)
    line = v.grocery_line(db, week, item_id)
    if line is None:
        raise HTTPException(404, "not_found")
    if body.checked is not None:
        line.checked = body.checked
    if body.have_it is not None:
        line.have_it = body.have_it
    db.commit()
    return v.grocery_out(db, week)


@router.get("/api/pantry")
def get_pantry(auth: CurrentAuth, db: Db):
    return v.pantry_out(db, auth.user.id)
