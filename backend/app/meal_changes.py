"""The person's ingredient changes to the week's meals (meal_ingredient_changes), shared by the plan builder
(app/plans.py: new plans leave out disliked foods, the grocery list uses what's really cooked) and the screens
(app/views/ingredients.py: removing, replacing, undoing, and rebalancing the day).

All numbers come from app/engine/ingredients.py; this module only reads and writes rows.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.ingredients import Change, effective
from app.models import MealIngredientChange, MealPlanItem, RecipeIngredient

PLAN_GROUP = "plan-"  # group_id prefix of the foods a new plan left out for good (not an action of the person's)


def by_person(c: MealIngredientChange) -> bool:
    """A change the person made on this plan (not a disliked food the plan was built without)."""
    return not c.group_id.startswith(PLAN_GROUP)


def recipe_ingredients(db: Session) -> dict[str, list[RecipeIngredient]]:
    out: dict[str, list[RecipeIngredient]] = {}
    for i in db.scalars(select(RecipeIngredient).order_by(RecipeIngredient.id)):
        out.setdefault(i.recipe_id, []).append(i)
    return out


def changes_by_item(db: Session, user_id: str, item_ids: list[str]) -> dict[str, list[MealIngredientChange]]:
    out: dict[str, list[MealIngredientChange]] = {}
    if not item_ids:
        return out
    for c in db.scalars(select(MealIngredientChange).where(MealIngredientChange.user_id == user_id,
                                                           MealIngredientChange.meal_plan_item_id.in_(item_ids))
                        .order_by(MealIngredientChange.created_at)):
        out.setdefault(c.meal_plan_item_id, []).append(c)
    return out


def as_changes(rows: list[MealIngredientChange]) -> list[Change]:
    return [Change(c.food_id, c.replacement_food_id, c.replacement_grams) for c in rows]


def item_ingredients(item: MealPlanItem, recipes: dict[str, list[RecipeIngredient]], rows: list[MealIngredientChange]) -> list[tuple[str, float]]:
    """What this meal is really made of (per serving), after the person's changes."""
    return effective(tuple((i.food_id, i.grams) for i in recipes.get(item.recipe_id, [])), as_changes(rows))


def leave_out_disliked(db: Session, user_id: str, items: list[MealPlanItem], disliked: tuple[str, ...],
                       recipes: dict[str, list[RecipeIngredient]] | None = None) -> None:
    """New meals with a food the person removed for good: it's marked removed (the optimizer already planned the
    recipe without it, app/engine/meals.py eligible_recipes), so the recipe page and the grocery list leave it out."""
    if not disliked:
        return
    recipes = recipes if recipes is not None else recipe_ingredients(db)
    groups = {f: PLAN_GROUP + str(uuid.uuid4())[: 36 - len(PLAN_GROUP)] for f in disliked}  # one per food, so Undo is per food
    for item in items:
        for ing in recipes.get(item.recipe_id, []):
            if ing.food_id in disliked and not ing.essential:
                db.add(MealIngredientChange(user_id=user_id, meal_plan_item_id=item.id, group_id=groups[ing.food_id], food_id=ing.food_id,
                                            reason="dislike", scope="always", added_dislike=False))
    db.flush()


def copy_changes(db: Session, user_id: str, id_map: dict[str, str]) -> None:
    """When a new plan version keeps the week's meals, the ingredient changes come along (same groups)."""
    for old, rows in changes_by_item(db, user_id, list(id_map)).items():
        for c in rows:
            db.add(MealIngredientChange(user_id=user_id, meal_plan_item_id=id_map[old], group_id=c.group_id, food_id=c.food_id,
                                        replacement_food_id=c.replacement_food_id, replacement_grams=c.replacement_grams,
                                        reason=c.reason, scope=c.scope, added_dislike=c.added_dislike, created_at=c.created_at))
    db.flush()
