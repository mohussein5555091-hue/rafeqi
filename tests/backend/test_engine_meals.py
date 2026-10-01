"""The meal optimizer (engine/meals.py) and the grocery list (engine/grocery.py)."""

import datetime as dt
import math
import re

import pytest

from app.engine.catalogue import grocery_from_catalogue
from app.engine.grocery import CATEGORY_ORDER, as_text, build_grocery_list, item_grams
from app.engine.meals import Targets, day_slots, is_ramadan, plan_week
from app.engine.nutrition import compute_targets
from app.engine.rules import load_rules
from app.engine.types import Person
from engine_fixtures import food_catalogue, recipe_infos

WEEK = dt.date(2026, 10, 3)
RECIPES = list(recipe_infos())
BY_ID = {r.id: r for r in RECIPES}


def person(**kw) -> Person:
    base = dict(sex="male", age=29, height_cm=180, weight_kg=80, goal="loseFat", pace="steady", experience="intermediate",
                days_per_week=4, session_minutes=60, location="gym", meals_per_day=4, cooking_minutes=60)
    return Person(**(base | kw))


def week_for(p: Person, start=WEEK, banned=frozenset()):
    t = compute_targets(p)
    return t, plan_week(start, p, Targets(t.calories, t.protein_g, t.carbs_g, t.fat_g), RECIPES, banned)


def test_recipe_macros_come_from_the_ingredients():
    foods = {f["id"]: f for f in food_catalogue()["foods"]}
    r = BY_ID["r_zabadi_oats"]
    assert r.kcal == pytest.approx(sum(foods[f]["kcal"] * g / 100 for f, g in r.ingredients))
    assert r.tags == {"dairy", "lactose", "gluten"}


def test_every_day_hits_calories_within_5_percent_and_protein():
    t, w = week_for(person())
    tol = load_rules()["nutrition"]["meals"]["calorie_tolerance_pct"] / 100
    assert w.relaxed == []
    for d in {m.date for m in w.meals}:
        tot = w.totals(d)
        assert abs(tot["kcal"] - t.calories) <= t.calories * tol + 4, d  # + rounding of each meal
        assert tot["protein"] >= t.protein_g - 2, d


def test_slots_follow_meals_per_day():
    for n in (2, 3, 4, 5):
        _, w = week_for(person(meals_per_day=n))
        expected = load_rules()["nutrition"]["meals"]["slots_by_meals_per_day"][n]
        for d in {m.date for m in w.meals}:
            assert [m.slot for m in w.day(d)] == expected


def test_dislikes_and_allergies_are_respected():
    _, w = week_for(person(dislikes=("fish", "beef"), allergies=("lactose",)))
    for m in w.meals:
        assert not (BY_ID[m.recipe_id].tags & {"fish", "beef", "lactose"}), m.recipe_id


def test_a_meal_time_with_no_suitable_recipe_borrows_one_and_says_so():
    _, w = week_for(person(dislikes=("fish", "beef"), allergies=("lactose",)))  # both snacks contain dairy
    assert "slots" in w.relaxed and any(r.rule == "nutrition.meals.relaxed.slots" for r in w.reasons)
    assert all(m.slot != "snack" or "snack" not in BY_ID[m.recipe_id].slots for m in w.meals)


def test_each_recipe_suits_its_slot_and_portions_are_quarters_within_bounds():
    _, w = week_for(person(meals_per_day=5))
    mr = load_rules()["nutrition"]["meals"]
    for m in w.meals:
        assert m.slot in BY_ID[m.recipe_id].slots
        assert mr["portion_min"] <= m.portion <= mr["portion_max"] and (m.portion * 4).is_integer()


def test_variety_limits():
    _, w = week_for(person())
    mr = load_rules()["nutrition"]["meals"]
    for r in RECIPES:
        uses = [m for m in w.meals if m.recipe_id == r.id]
        limit = mr["max_uses_per_week_snack"] if all(m.slot == "snack" for m in uses) else mr["max_uses_per_week"]
        assert len(uses) <= limit, r.id
    for d in {m.date for m in w.meals}:
        ids = [m.recipe_id for m in w.day(d)]
        assert len(ids) == len(set(ids))


def test_cooking_time_is_respected_unless_the_plan_says_otherwise():
    p = person(meals_per_day=3, cooking_minutes=30, sex="female", weight_kg=62, height_cm=165)
    _, w = week_for(p)
    if "cooking" not in w.relaxed:
        for d in {m.date for m in w.meals}:
            minutes = sum((BY_ID[m.recipe_id].prep_min + BY_ID[m.recipe_id].cook_min) / BY_ID[m.recipe_id].batch for m in w.day(d))
            assert minutes <= 30 + 1e-6
    else:
        assert any(r.rule == "nutrition.meals.relaxed.cooking" for r in w.reasons)


def test_impossible_limits_are_eased_in_order_and_explained():
    _, w = week_for(person(meals_per_day=5, cooking_minutes=15))
    assert w.relaxed[:1] == ["cooking"]
    assert {f"nutrition.meals.relaxed.{s}" for s in w.relaxed} <= {r.rule for r in w.reasons}


def test_ramadan_days_use_suhoor_and_iftar():
    p = person(meals_per_day=2, fasting=("ramadan",))
    ramadan_week = dt.date(2027, 2, 13)
    assert is_ramadan(ramadan_week) and not is_ramadan(WEEK)
    assert [s for s, _ in day_slots(ramadan_week, p)] == ["suhoor", "iftar"]
    assert [s for s, _ in day_slots(WEEK, p)] == ["breakfast", "dinner"]  # outside Ramadan: normal meals
    _, w = week_for(p, start=ramadan_week)
    for m in w.meals:
        assert m.slot in ("suhoor", "iftar") and m.time in ("03:30", "18:00")


def test_banned_recipes_are_left_out():
    _, w = week_for(person(), banned=frozenset({"r_koshary", "r_ful_eggs"}))
    assert not {m.recipe_id for m in w.meals} & {"r_koshary", "r_ful_eggs"}


def test_same_answers_give_the_same_week():
    assert week_for(person())[1].meals == week_for(person())[1].meals


# ── Grocery list ──────────────────────────────────────────────────────────────
ITEMS, FOOD_MAP = grocery_from_catalogue(food_catalogue())
INGREDIENTS = {r.id: list(r.ingredients) for r in RECIPES}


def grocery(pantry=None):
    _, w = week_for(person())
    meals = [(m.recipe_id, m.portion) for m in w.meals]
    return meals, build_grocery_list(meals, INGREDIENTS, FOOD_MAP, ITEMS, pantry)


def test_totals_match_the_meal_plan():
    meals, lines = grocery()
    expected: dict[str, float] = {}
    for rid, portion in meals:
        for food, grams in BY_ID[rid].ingredients:
            item, ratio = FOOD_MAP[food]
            expected[item] = expected.get(item, 0) + grams * portion * ratio
    assert item_grams(meals, INGREDIENTS, FOOD_MAP) == pytest.approx(expected)
    factor = load_rules()["nutrition"]["grocery"]["monthly_factor"]
    for line in lines:
        want = expected[line.item_id] * (1 if line.period == "week" else factor)
        assert line.grams_needed == pytest.approx(want, abs=0.1)
        # Rounded up to whole packs, never short.
        assert line.qty * ITEMS[line.item_id].grams_per_unit >= line.grams_needed - 0.1
        packs = line.qty / ITEMS[line.item_id].pack_size
        assert math.isclose(packs, round(packs)) and line.qty / ITEMS[line.item_id].pack_size - line.grams_needed / ITEMS[line.item_id].grams_per_unit / ITEMS[line.item_id].pack_size < 1


def test_monthly_staples_never_appear_in_the_weekly_list():
    _, lines = grocery()
    for line in lines:
        assert (line.period == "week") == (ITEMS[line.item_id].shelf_life == "weekly"), line.item_id
    assert any(line.period == "month" for line in lines) and any(line.period == "week" for line in lines)


def test_pantry_items_are_marked_and_left_out_of_the_text():
    _, lines = grocery(pantry={"gi_rice": "plenty", "gi_tomatoes": "low"})
    by_id = {line.item_id: line for line in lines}
    assert by_id["gi_rice"].have_it and not by_id["gi_tomatoes"].have_it
    assert "Rice" not in as_text(lines, ITEMS, "month") and "Tomatoes" in as_text(lines, ITEMS, "week")


def test_text_is_grouped_by_category_with_generic_names_and_no_prices_or_brands():
    _, lines = grocery()
    for period in ("week", "month"):
        for lang in ("en", "ar"):
            text = as_text(lines, ITEMS, period, lang)
            assert not re.search(r"EGP|L\.E|£|\$|price|cost|budget|جنيه|سعر|ميزانية", text, re.I), text
    en = as_text(lines, ITEMS, "week")
    headings = [h for h in ("Vegetables & fruit", "Meat, chicken & fish", "Dairy & eggs", "Bread & bakery") if h in en]
    assert [en.index(h) for h in headings] == sorted(en.index(h) for h in headings)
    assert re.search(r"- Chicken breast · \d+(\.\d+)? kg", en)
    assert set(CATEGORY_ORDER) == {i.category for i in ITEMS.values()}


BRANDS = ("juhayna", "almarai", "domty", "panda", "beyti", "koki", "president", "lamar", "nestle", "heinz", "americana")


def test_grocery_catalogue_has_no_brands_and_no_prices():
    for item in ITEMS.values():
        assert not any(b in (item.name["en"] + item.name["ar"]).lower() for b in BRANDS), item.id
        assert "®" not in item.name["en"] and "™" not in item.name["en"]
    from app.food_catalogue import validate_food_catalogue
    data = food_catalogue()
    bad_item = dict(data["grocery_items"][0], price_egp=30)
    assert any("no prices or brands" in p for p in validate_food_catalogue(data["foods"], [bad_item, *data["grocery_items"][1:]], data["recipes"]))
