"""Foods, generic grocery items and recipes (data/catalogue/foods.yaml, grocery_items.yaml, recipes.yaml).

Checked before loading: every link points at something that exists, names are in both languages, tags come
from the questionnaire's dislike/allergy lists, and nothing has a price or a brand. If anything is wrong,
nothing is written and every problem is listed. Recipe calories and macros are worked out from the ingredients.
"""

from pathlib import Path

import yaml
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.catalogue import CatalogueError, _bilingual
from app.models import Food, FoodGroceryItem, GroceryItem, Recipe, RecipeIngredient, RecipeStep
from app.schemas.onboarding import ALLERGIES, FOODS

FOOD_TAGS = set(FOODS) | (set(ALLERGIES) - {"none"})
CATEGORIES = {"produce", "meat", "dairy", "bakery", "pantry", "spices"}
SHELF_LIVES = {"weekly", "monthly"}
UNITS = {"kg", "g", "L", "pcs", "cups", "jars"}
SLOTS = {"breakfast", "lunch", "snack", "dinner", "suhoor", "iftar"}
NUTRIENTS = ("kcal", "protein", "carbs", "fat", "fiber")
FORBIDDEN_KEYS = {"price", "cost", "brand", "budget"}


def _load(path: Path, key: str) -> tuple[list[dict], str]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get(key) or [], data.get("source", "")


def read_food_catalogue(folder: Path) -> dict:
    foods, food_source = _load(folder / "foods.yaml", "foods")
    items, _ = _load(folder / "grocery_items.yaml", "grocery_items")
    recipes, recipe_source = _load(folder / "recipes.yaml", "recipes")
    problems = validate_food_catalogue(foods, items, recipes)
    if problems:
        raise CatalogueError(problems)
    return {"foods": foods, "grocery_items": items, "recipes": recipes, "food_source": food_source, "recipe_source": recipe_source}


def _forbidden(where: str, obj: object, problems: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(bad in str(k).lower() for bad in FORBIDDEN_KEYS):
                problems.append(f"{where}: '{k}' is not allowed (no prices or brands anywhere)")
            _forbidden(where, v, problems)
    elif isinstance(obj, list):
        for v in obj:
            _forbidden(where, v, problems)


def validate_food_catalogue(foods: list[dict], items: list[dict], recipes: list[dict]) -> list[str]:
    problems: list[str] = []
    item_ids = [i.get("id") for i in items]
    food_ids = [f.get("id") for f in foods]
    for kind, ids in (("grocery item", item_ids), ("food", food_ids), ("recipe", [r.get("id") for r in recipes])):
        for dup in {x for x in ids if ids.count(x) > 1}:
            problems.append(f"{kind} {dup}: duplicate id")
    for i in items:
        where = f"grocery item {i.get('id')}"
        _forbidden(where, i, problems)
        if not (str(i.get("en", "")).strip() and str(i.get("ar", "")).strip()):
            problems.append(f"{where}: needs en and ar names")
        if i.get("category") not in CATEGORIES:
            problems.append(f"{where}: category must be one of {sorted(CATEGORIES)}")
        if i.get("shelf_life") not in SHELF_LIVES:
            problems.append(f"{where}: shelf_life must be weekly or monthly")
        if i.get("buying_unit") not in UNITS:
            problems.append(f"{where}: buying_unit must be one of {sorted(UNITS)}")
        for k in ("pack_size", "grams_per_unit"):
            if not isinstance(i.get(k), (int, float)) or i[k] <= 0:
                problems.append(f"{where}: {k} must be a positive number")
    for f in foods:
        where = f"food {f.get('id')}"
        _forbidden(where, f, problems)
        if not (str(f.get("en", "")).strip() and str(f.get("ar", "")).strip()):
            problems.append(f"{where}: needs en and ar names")
        for n in NUTRIENTS:
            if not isinstance(f.get(n), (int, float)) or f[n] < 0:
                problems.append(f"{where}: {n} per 100 g must be a number ≥ 0")
        if all(isinstance(f.get(n), (int, float)) for n in ("kcal", "protein", "carbs", "fat")):
            energy = 4 * f["protein"] + 4 * f["carbs"] + 9 * f["fat"]
            if abs(energy - f["kcal"]) > max(25, 0.2 * f["kcal"]):
                problems.append(f"{where}: kcal {f['kcal']} doesn't match its macros (~{energy:.0f})")
        if bad := set(f.get("tags") or []) - FOOD_TAGS:
            problems.append(f"{where}: unknown tags {sorted(bad)}; allowed: {sorted(FOOD_TAGS)}")
        g = f.get("grocery") or {}
        if g.get("item") not in item_ids:
            problems.append(f"{where}: grocery item {g.get('item')} doesn't exist")
        if not isinstance(g.get("ratio"), (int, float)) or g["ratio"] <= 0:
            problems.append(f"{where}: grocery ratio must be a positive number")
    for r in recipes:
        where = f"recipe {r.get('id')}"
        _forbidden(where, r, problems)
        for field in ("name", "storage", "reheating"):
            if not _bilingual(r.get(field)):
                problems.append(f"{where}: {field} needs en and ar")
        if not r.get("slots") or set(r["slots"]) - SLOTS:
            problems.append(f"{where}: slots must be some of {sorted(SLOTS)}")
        for k in ("prep_min", "cook_min", "fridge_days", "batch"):
            if not isinstance(r.get(k), int) or r[k] < 0 or (k == "batch" and r[k] < 1):
                problems.append(f"{where}: {k} must be a whole number{' ≥ 1' if k == 'batch' else ' ≥ 0'}")
        ings = r.get("ingredients") or []
        if not ings:
            problems.append(f"{where}: needs ingredients")
        for ing in ings:
            if ing.get("food") not in food_ids:
                problems.append(f"{where}: ingredient food {ing.get('food')} doesn't exist")
            if not isinstance(ing.get("grams"), (int, float)) or ing["grams"] <= 0:
                problems.append(f"{where}: ingredient {ing.get('food')} needs grams > 0")
            if not (ing.get("en") and ing.get("ar")):
                problems.append(f"{where}: ingredient {ing.get('food')} needs an en and ar amount")
        steps = r.get("steps") or []
        if not steps or not all(_bilingual(s) for s in steps):
            problems.append(f"{where}: steps must be a non-empty list of {{en, ar}}")
    return problems


def seed_food_catalogue(db: Session, data: dict) -> tuple[int, int, int]:
    for i in data["grocery_items"]:
        db.merge(GroceryItem(id=i["id"], name_en=i["en"], name_ar=i["ar"], category=i["category"], shelf_life=i["shelf_life"],
                             buying_unit=i["buying_unit"], pack_size=i["pack_size"], grams_per_unit=i["grams_per_unit"]))
    db.flush()
    for f in data["foods"]:
        db.merge(Food(id=f["id"], name_en=f["en"], name_ar=f["ar"], kcal_100g=f["kcal"], protein_100g=f["protein"],
                      carbs_100g=f["carbs"], fat_100g=f["fat"], fiber_100g=f["fiber"], units=f.get("units") or [],
                      tags=f.get("tags") or [], source=data["food_source"]))
    db.flush()
    db.execute(delete(FoodGroceryItem).where(FoodGroceryItem.food_id.in_([f["id"] for f in data["foods"]])))
    for f in data["foods"]:
        db.add(FoodGroceryItem(food_id=f["id"], grocery_item_id=f["grocery"]["item"], raw_grams_per_gram=f["grocery"]["ratio"]))
    tags = {f["id"]: set(f.get("tags") or []) for f in data["foods"]}
    for r in data["recipes"]:
        db.merge(Recipe(id=r["id"], name_en=r["name"]["en"], name_ar=r["name"]["ar"], slots=r["slots"], prep_min=r["prep_min"],
                        cook_min=r["cook_min"], fridge_days=r["fridge_days"], servings=r["batch"],
                        storage_en=r["storage"]["en"], storage_ar=r["storage"]["ar"],
                        reheating_en=r["reheating"]["en"], reheating_ar=r["reheating"]["ar"],
                        tags=sorted(set().union(*(tags[i["food"]] for i in r["ingredients"]))), source=data["recipe_source"]))
        db.flush()
        db.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id == r["id"]))
        db.execute(delete(RecipeStep).where(RecipeStep.recipe_id == r["id"]))
        for ing in r["ingredients"]:
            db.add(RecipeIngredient(recipe_id=r["id"], food_id=ing["food"], grams=ing["grams"], amount_en=ing["en"], amount_ar=ing["ar"]))
        for n, s in enumerate(r["steps"], 1):
            db.add(RecipeStep(recipe_id=r["id"], position=n, text_en=s["en"], text_ar=s["ar"], timer_sec=s.get("timer_sec")))
    db.flush()
    return len(data["foods"]), len(data["grocery_items"]), len(data["recipes"])
