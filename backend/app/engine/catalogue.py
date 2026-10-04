"""Turns catalogue rows (from the database or straight from the YAML files) into the engine's plain inputs."""

from app.engine.types import ExerciseInfo, FoodInfo, GroceryItemInfo, RecipeInfo


def recipe_macros(ingredients: list[tuple[str, float]], foods: dict[str, dict]) -> dict[str, float]:
    """Per serving, from foods per 100 g."""
    total = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for food_id, grams in ingredients:
        f = foods[food_id]
        for k in total:
            total[k] += f[k] * grams / 100
    return total


def recipes_from_catalogue(data: dict) -> list[RecipeInfo]:
    """From read_food_catalogue() (the YAML files)."""
    foods = {f["id"]: f for f in data["foods"]}
    out = []
    for r in data["recipes"]:
        ings = tuple((i["food"], float(i["grams"])) for i in r["ingredients"])
        mac = recipe_macros(list(ings), foods)
        tags = frozenset().union(*(set(foods[f]["tags"]) for f, _ in ings))
        out.append(RecipeInfo(id=r["id"], name=r["name"], slots=tuple(r["slots"]), prep_min=r["prep_min"], cook_min=r["cook_min"],
                              batch=r["batch"], tags=tags, ingredients=ings, **mac,
                              essential=frozenset(i["food"] for i in r["ingredients"] if i.get("essential")),
                              per100=tuple((foods[f]["kcal"], foods[f]["protein"], foods[f]["carbs"], foods[f]["fat"]) for f, _ in ings)))
    return out


def foods_from_catalogue(data: dict) -> dict[str, FoodInfo]:
    return {f["id"]: FoodInfo(id=f["id"], name={"en": f["en"], "ar": f["ar"]}, role=f["role"], tags=frozenset(f.get("tags") or ()),
                              kcal=f["kcal"], protein=f["protein"], carbs=f["carbs"], fat=f["fat"]) for f in data["foods"]}


def foods_from_db(db) -> dict[str, FoodInfo]:
    from sqlalchemy import select

    from app.models import Food

    return {f.id: FoodInfo(id=f.id, name={"en": f.name_en, "ar": f.name_ar}, role=f.role, tags=frozenset(f.tags or ()),
                           kcal=f.kcal_100g, protein=f.protein_100g, carbs=f.carbs_100g, fat=f.fat_100g) for f in db.scalars(select(Food))}


def recipes_from_db(db) -> list[RecipeInfo]:
    from sqlalchemy import select

    from app.models import Food, Recipe, RecipeIngredient

    foods = {f.id: {"kcal": f.kcal_100g, "protein": f.protein_100g, "carbs": f.carbs_100g, "fat": f.fat_100g, "tags": f.tags}
             for f in db.scalars(select(Food))}
    ings: dict[str, list[tuple[str, float]]] = {}
    essential: dict[str, set[str]] = {}
    for i in db.scalars(select(RecipeIngredient).order_by(RecipeIngredient.id)):
        ings.setdefault(i.recipe_id, []).append((i.food_id, i.grams))
        if i.essential:
            essential.setdefault(i.recipe_id, set()).add(i.food_id)
    out = []
    for r in db.scalars(select(Recipe).order_by(Recipe.id)):
        lst = ings.get(r.id, [])
        mac = recipe_macros(lst, foods)
        out.append(RecipeInfo(id=r.id, name={"en": r.name_en, "ar": r.name_ar}, slots=tuple(r.slots), prep_min=r.prep_min,
                              cook_min=r.cook_min, batch=r.servings, tags=frozenset().union(*(set(foods[f]["tags"]) for f, _ in lst)),
                              ingredients=tuple(lst), **mac, essential=frozenset(essential.get(r.id, ())),
                              per100=tuple((foods[f]["kcal"], foods[f]["protein"], foods[f]["carbs"], foods[f]["fat"]) for f, _ in lst)))
    return out


def exercises_from_db(db) -> dict[str, ExerciseInfo]:
    from sqlalchemy import select

    from app.models import Exercise

    return {e.id: ExerciseInfo(id=e.id, name={"en": e.name_en, "ar": e.name_ar}, pattern=e.movement_pattern,
                               joints=tuple(e.joints_loaded), rom=e.range_of_motion, equipment=tuple(e.equipment), difficulty=e.difficulty,
                               type=e.type, muscles=tuple(e.primary_muscles or ()))
            for e in db.scalars(select(Exercise))}


def grocery_from_catalogue(data: dict) -> tuple[dict[str, GroceryItemInfo], dict[str, tuple[str, float]]]:
    items = {i["id"]: GroceryItemInfo(id=i["id"], name={"en": i["en"], "ar": i["ar"]}, category=i["category"], shelf_life=i["shelf_life"],
                                      unit=i["buying_unit"], pack_size=i["pack_size"], grams_per_unit=i["grams_per_unit"])
             for i in data["grocery_items"]}
    food_map = {f["id"]: (f["grocery"]["item"], f["grocery"]["ratio"]) for f in data["foods"]}
    return items, food_map


def grocery_from_db(db) -> tuple[dict[str, GroceryItemInfo], dict[str, tuple[str, float]]]:
    from sqlalchemy import select

    from app.models import FoodGroceryItem, GroceryItem

    items = {i.id: GroceryItemInfo(id=i.id, name={"en": i.name_en, "ar": i.name_ar}, category=i.category, shelf_life=i.shelf_life,
                                   unit=i.buying_unit, pack_size=i.pack_size, grams_per_unit=i.grams_per_unit)
             for i in db.scalars(select(GroceryItem))}
    food_map = {m.food_id: (m.grocery_item_id, m.raw_grams_per_gram) for m in db.scalars(select(FoodGroceryItem))}
    return items, food_map
