"""Removing an ingredient (app/engine/ingredients.py): same-role replacements, sized to what they replace; the day kept
on target afterwards; and later meal plans never using a food the person removed for good (app/engine/meals.py)."""

from dataclasses import replace

import pytest

from app.engine.catalogue import foods_from_catalogue
from app.engine.ingredients import Change, DayMeal, effective, per_serving, rebalance_day, replacement_grams, replacements, totals
from app.engine.meals import Targets, eligible_recipes, plan_week
from app.engine.nutrition import compute_targets
from app.engine.rules import load_rules
from engine_fixtures import food_catalogue, recipe_infos
from personas import PERSONAS

FOODS = foods_from_catalogue(food_catalogue())
RECIPES = {r.id: r for r in recipe_infos()}


# ── Replacements ──

def ids(opts):
    return [f.id for f, _ in opts]


def test_eggs_are_replaced_by_cheese_or_yogurt_never_meat_or_bread():
    opts = replacements("egg", 100, {f for f, _ in RECIPES["r_ful_eggs"].ingredients}, FOODS, set(), set())
    assert 1 <= len(opts) <= 3
    assert all(FOODS[i].role == "eggsDairy" for i in ids(opts))
    assert set(ids(opts)) <= {"white_cheese", "cottage_cheese", "yogurt"}  # egg white is already in the recipe


def test_a_replacement_gives_about_the_same_protein_carbs_or_fat():
    for food, cand, key in (("egg", "cottage_cheese", "protein"), ("chicken_breast", "fish_fillet", "protein"),
                            ("rice", "potato", "carbs"), ("olive_oil", "tahini", "fat")):
        g = replacement_grams(FOODS[food], 100, FOODS[cand])
        removed, added = getattr(FOODS[food], key) * 100 / 100, getattr(FOODS[cand], key) * g / 100
        cap = 100 * load_rules()["nutrition"]["ingredients"]["max_replacement_factor"]
        assert g % 5 == 0 and (abs(added - removed) <= max(0.15 * removed, 1.5) or g == cap), (food, cand, g)
    assert replacement_grams(FOODS["tomato"], 60, FOODS["cucumber"]) == 60  # vegetables: the same grams


def test_flavours_have_no_replacement():
    assert replacements("cumin", 1, set(), FOODS, set(), set()) == []
    assert replacements("garlic", 5, set(), FOODS, set(), set()) == []


def test_replacements_respect_allergies_dislikes_and_whats_already_there():
    opts = replacements("egg", 100, {"egg", "egg_white"}, FOODS, {"lactose", "dairy"}, set())
    assert opts == []  # every other eggs/dairy food has lactose
    opts = replacements("chicken_breast", 150, {"chicken_breast"}, FOODS, {"fish"}, {"beef_mince"})
    assert ids(opts) == []  # fish is an allergy tag here and beef was removed for good: nothing else has this role
    opts = replacements("chicken_breast", 150, {"chicken_breast", "fish_fillet"}, FOODS, set(), set())
    assert ids(opts) == ["beef_mince"]


def test_effective_ingredients_and_their_macros():
    r = RECIPES["r_ful_eggs"]
    out = effective(r.ingredients, [Change("egg"), Change("olive_oil", "tahini", 10)])
    assert "egg" not in dict(out) and dict(out)["tahini"] == 10 and len(out) == len(r.ingredients) - 1
    full, less = per_serving(list(r.ingredients), FOODS), per_serving(out, FOODS)
    assert less["protein"] < full["protein"] and full["kcal"] == pytest.approx(r.kcal)


# ── Rebalancing the day ──

def day_from(recipe_ids, portions):
    return [DayMeal(f"m{i}", RECIPES[r].name, RECIPES[r].kcal, RECIPES[r].protein, RECIPES[r].carbs, RECIPES[r].fat, p)
            for i, (r, p) in enumerate(zip(recipe_ids, portions))]


def test_removing_protein_triggers_a_rebalance_that_keeps_protein_at_or_above_target():
    meals = day_from(["r_ful_eggs", "r_kofta_tahini", "r_cheese_sandwich", "r_lentil_soup_chicken"], [1, 0.75, 0.75, 1.25])
    before = totals(meals, {m.id: m.planned for m in meals})
    calories, protein = round(before["kcal"]), round(before["protein"]) - 2  # the plan was on target
    # Take the eggs out of the ful (eggs aren't available today).
    ful = RECIPES["r_ful_eggs"]
    less = per_serving(effective(ful.ingredients, [Change("egg")]), FOODS)
    meals[0] = replace(meals[0], kcal=less["kcal"], protein=less["protein"], carbs=less["carbs"], fat=less["fat"])
    assert totals(meals, {m.id: m.planned for m in meals})["protein"] < protein  # the day fell short
    rb = rebalance_day(meals, calories, protein, before)
    after = totals(meals, rb.portions)
    assert rb.on_target and after["protein"] >= protein - 0.5
    tol = load_rules()["nutrition"]["meals"]["calorie_tolerance_pct"] / 100
    assert calories * (1 - tol) - 0.5 <= after["kcal"] <= calories * (1 + tol) + 0.5
    step, most = load_rules()["nutrition"]["meals"]["portion_step"], load_rules()["nutrition"]["ingredients"]["max_portion_change"]
    for m in meals:  # small, quarter-step changes only
        assert abs(rb.portions[m.id] - m.planned) <= most + 1e-9 and (rb.portions[m.id] / step) == int(rb.portions[m.id] / step)
    changed = [r for r in rb.reasons if r.rule == "nutrition.ingredients.rebalanced"]
    assert changed and all(r.en.startswith("To keep the day on target") for r in changed)


def test_a_day_still_on_target_keeps_its_portions():
    meals = day_from(["r_ful_eggs", "r_koshary"], [1, 1])
    before = totals(meals, {m.id: 1 for m in meals})
    rb = rebalance_day(meals, round(before["kcal"]), round(before["protein"]), before)
    assert rb.portions == {"m0": 1, "m1": 1} and rb.reasons[0].rule == "nutrition.ingredients.on_target"


def test_eaten_meals_never_move_and_a_snack_is_suggested_when_portions_cant_close_the_gap():
    meals = day_from(["r_ful_eggs", "r_koshary"], [1, 1])
    meals = [replace(m, locked=True) for m in meals]
    before = totals(meals, {m.id: 1 for m in meals})
    snacks = [r for r in recipe_infos() if "snack" in r.slots]
    rb = rebalance_day(meals, round(before["kcal"]) + 300, round(before["protein"]) + 15, before | {"protein": before["protein"] + 15}, snacks)
    assert rb.portions == {"m0": 1, "m1": 1} and not rb.on_target
    assert rb.snack and rb.snack["protein"] >= 14 and rb.reasons[0].rule == "nutrition.ingredients.snack"
    assert rb.reasons[0].en.startswith("Still 15 g protein short: add ")


# ── Later plans never bring a removed food back ──

def test_a_disliked_food_is_left_out_and_recipes_it_is_essential_to_are_dropped():
    p = replace(PERSONAS["beginner_woman"][1], disliked_foods=("egg", "lentils"))
    pool = {r.id: r for r in eligible_recipes(list(recipe_infos()), p)}
    assert "r_lentil_soup_chicken" not in pool and "r_koshary" not in pool  # lentils are essential there
    assert "r_shakshuka" not in pool  # so are eggs
    ful = pool["r_ful_eggs"]
    assert "egg" not in dict(ful.ingredients) and ful.protein < RECIPES["r_ful_eggs"].protein


@pytest.mark.parametrize("key", sorted(PERSONAS))
def test_a_regenerated_week_never_uses_a_disliked_food(key):
    _, p, start = PERSONAS[key]
    p = replace(p, disliked_foods=("egg", "tomato"))
    t = compute_targets(p)
    week = plan_week(start, p, Targets(t.calories, t.protein_g, t.carbs_g, t.fat_g), list(recipe_infos()))
    pool = {r.id: r for r in eligible_recipes(list(recipe_infos()), p)}
    for m in week.meals:
        assert not {"egg", "tomato"} & set(dict(pool[m.recipe_id].ingredients)), (key, m.recipe_id)
