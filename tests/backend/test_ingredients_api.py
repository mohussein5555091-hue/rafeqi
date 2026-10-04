"""Removing an ingredient from a meal through the API: reasons, replacements, "Just this meal" / "Always", the day
rebalanced, the grocery list, essential ingredients, Undo, and later plans (regenerate, weekly review) never bringing
a removed food back.

The planned user's Monday (2026-09-28, today on the test clock): ful medames with eggs, kofta, a cheese sandwich and
lentil soup with chicken. Kofta is on 4 days of the week; parsley is only in kofta.
"""

from sqlalchemy import select

from app.models import GroceryItem, GroceryList, GroceryListItem, MealIngredientChange, MealPlan, Profile
from app.plans import current_plan
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import checkin_body, planned  # noqa: F401 (fixtures)

MONDAY = "2026-09-28"


def day(c, d=MONDAY):
    return c.get(f"/api/meals/day/{d}").json()


def meal(c, recipe, d=MONDAY):
    return next(m for m in day(c, d)["meals"] if m["recipeId"] == recipe)


def ingredient(m, food):
    return next(i for i in m["ingredients"] if i["foodId"] == food)


def remove(c, m, food, reason="unavailable", scope="meal", replacement=None, status=200):
    r = c.post(f"/api/meals/{m['id']}/ingredients/{food}/remove", json={"reason": reason, "scope": scope, "replacementFoodId": replacement})
    assert r.status_code == status, r.text
    return r.json()


def totals(d):
    return {k: sum(m[k] for m in d["meals"]) for k in ("kcal", "proteinG")}


def all_week(c):
    return [m for w in c.get("/api/meals/week").json() for m in day(c, w["date"])["meals"]]


def grocery_grams(db, user_id, item):
    """Grams of a grocery item on the current list (the newest one; older plan versions keep theirs)."""
    db.expire_all()
    mp = db.scalar(select(MealPlan).where(MealPlan.plan_id == current_plan(db, user_id).id))
    latest = db.scalar(select(GroceryList).where(GroceryList.meal_plan_id == mp.id))  # only the latest list is kept per meal plan
    rows = db.scalars(select(GroceryListItem).where(GroceryListItem.grocery_list_id == latest.id, GroceryListItem.grocery_item_id == item))
    return sum(r.grams_needed for r in rows)


def test_every_meal_lists_its_ingredients_with_the_essential_ones_marked(planned):  # noqa: F811
    soup = meal(planned.client, "r_lentil_soup_chicken")
    assert ingredient(soup, "lentils")["essential"] and not ingredient(soup, "chicken_breast")["essential"]
    assert all(i["status"] == "kept" and i["name"]["en"] and i["name"]["ar"] for i in soup["ingredients"])


def test_removing_protein_rebalances_the_day_and_keeps_protein_at_or_above_target(planned):  # noqa: F811
    c = planned.client
    plan = c.get("/api/plan").json()
    before, sunday = totals(day(c)), day(c, "2026-09-27")
    ful = meal(c, "r_ful_eggs")
    after = remove(c, ful, "egg")  # no eggs at home today
    new = next(m for m in after["meals"] if m["id"] == ful["id"])
    assert ingredient(new, "egg")["status"] == "removed" and new["proteinG"] < ful["proteinG"]
    t = totals(after)
    assert t["proteinG"] >= min(plan["proteinG"], before["proteinG"]) - 1, (t, plan["proteinG"])
    assert abs(t["kcal"] - plan["calories"]) <= plan["calories"] * 0.08
    note = after["note"]
    assert note["onTarget"] and note["lines"][0]["en"] == "Egg removed from Ful medames, eggs & baladi bread."
    assert any(line["en"].startswith("To keep the day on target") for line in note["lines"])
    assert any("portionChange" in m for m in after["meals"])  # what moved is shown on its meal
    assert t["proteinG"] < before["proteinG"] + 15  # small moves, not a new menu
    # Other days are untouched (Sunday has ful with eggs too).
    assert day(c, "2026-09-27") == sunday


def test_just_this_meal_changes_only_that_meal(planned, db):  # noqa: F811
    c = planned.client
    kofta = meal(c, "r_kofta_tahini")
    remove(c, kofta, "parsley")
    week = all_week(c)
    changed = [m for m in week if any(i["foodId"] == "parsley" and i["status"] != "kept" for i in m["ingredients"])]
    assert [m["id"] for m in changed] == [kofta["id"]]
    assert db.get(Profile, planned.id).disliked_foods == []  # "Not available" + "Just this meal": not a dislike
    assert grocery_grams(db, planned.id, "gi_parsley") > 0  # the other kofta meals still need it


def test_always_changes_every_meal_and_the_grocery_list(planned, db):  # noqa: F811
    c = planned.client
    before = grocery_grams(db, planned.id, "gi_parsley")
    assert before > 0
    remove(c, meal(c, "r_kofta_tahini"), "parsley", reason="dislike", scope="always")
    week = all_week(c)
    assert all(i["status"] == "removed" for m in week for i in m["ingredients"] if i["foodId"] == "parsley")
    assert db.get(Profile, planned.id).disliked_foods == ["parsley"]
    assert grocery_grams(db, planned.id, "gi_parsley") == 0  # no other meal needs it: off this week's list
    names = [i["name"]["en"] for i in c.get("/api/groceries").json()["items"]]
    assert db.get(GroceryItem, "gi_parsley").name_en not in names
    assert c.get("/api/groceries").json()["changeNote"]["en"] == "Updated: Parsley removed from your meals."


def test_a_replacement_is_added_to_the_grocery_list(planned, db):  # noqa: F811
    c = planned.client
    sandwich = meal(c, "r_cheese_sandwich")
    opts = c.get(f"/api/meals/{sandwich['id']}/ingredients/white_cheese/replacements").json()
    assert not opts["essential"] and 1 <= len(opts["options"]) <= 3
    pick = opts["options"][0]
    item_of = {"yogurt": "gi_yogurt", "egg": "gi_eggs"}  # the eggs/dairy foods the sandwich doesn't have
    assert pick["foodId"] in item_of
    cheese, extra = grocery_grams(db, planned.id, "gi_white_cheese"), grocery_grams(db, planned.id, item_of[pick["foodId"]])
    after = remove(c, sandwich, "white_cheese", replacement=pick["foodId"])
    row = ingredient(next(m for m in after["meals"] if m["id"] == sandwich["id"]), "white_cheese")
    assert row["status"] == "replaced" and row["replacement"]["foodId"] == pick["foodId"] and row["replacement"]["grams"] == pick["grams"]
    assert grocery_grams(db, planned.id, "gi_white_cheese") < cheese  # this meal no longer needs it
    assert grocery_grams(db, planned.id, item_of[pick["foodId"]]) > extra  # the replacement is bought instead
    # Only the replacements offered are accepted.
    remove(c, meal(c, "r_ful_eggs"), "olive_oil", replacement="chicken_breast", status=422)


def test_an_essential_ingredient_suggests_swapping_the_meal(planned):  # noqa: F811
    c = planned.client
    soup = meal(c, "r_lentil_soup_chicken")
    opts = c.get(f"/api/meals/{soup['id']}/ingredients/lentils/replacements").json()
    assert opts["essential"] is True and opts["options"] == []
    r = c.post(f"/api/meals/{soup['id']}/ingredients/lentils/remove", json={"reason": "dislike", "scope": "meal"})
    assert r.status_code == 409 and r.json()["detail"] == "essential_ingredient"
    assert c.get(f"/api/meals/{soup['id']}/swap-options").json()  # what the screen offers instead
    assert c.get(f"/api/meals/{soup['id']}/ingredients/not_in_it/replacements").status_code == 404


def test_undo_puts_everything_back(planned, db):  # noqa: F811
    c = planned.client
    start, grams = day(c), grocery_grams(db, planned.id, "gi_parsley")
    kofta = meal(c, "r_kofta_tahini")
    remove(c, meal(c, "r_ful_eggs"), "egg")
    remove(c, kofta, "parsley", reason="dislike", scope="always")
    c.delete(f"/api/meals/{meal(c, 'r_ful_eggs')['id']}/ingredients/egg")
    after = c.delete(f"/api/meals/{kofta['id']}/ingredients/parsley").json()
    assert [(m["id"], m["kcal"], m["proteinG"]) for m in after["meals"]] == [(m["id"], m["kcal"], m["proteinG"]) for m in start["meals"]]
    assert "note" not in after and all(i["status"] == "kept" for m in all_week(c) for i in m["ingredients"])
    assert db.get(Profile, planned.id).disliked_foods == []
    assert grocery_grams(db, planned.id, "gi_parsley") == grams
    assert db.scalars(select(MealIngredientChange).where(MealIngredientChange.user_id == planned.id)).first() is None
    assert c.delete(f"/api/meals/{kofta['id']}/ingredients/parsley").status_code == 404  # nothing left to undo


def test_always_never_comes_back_in_a_regenerated_plan(planned, db):  # noqa: F811
    c = planned.client
    remove(c, meal(c, "r_ful_eggs"), "egg", reason="dislike", scope="always")
    assert c.post("/api/plan").status_code == 200  # "regenerate my plan"
    week = all_week(c)
    assert not any(i["foodId"] == "egg" and i["status"] == "kept" for m in week for i in m["ingredients"])
    assert "r_shakshuka" not in {m["recipeId"] for m in week}  # eggs make shakshuka: it's left out
    # Eggs are still bought for the egg whites only (1 g of egg white needs 1.75 g of whole egg).
    whites = sum(round(ing[1]) for m in week for ing in [(i["foodId"], i["grams"]) for i in m["ingredients"]] if ing[0] == "egg_white")
    assert abs(grocery_grams(db, planned.id, "gi_eggs") - whites * 1.75) <= 0.01 * whites * 1.75 + 5
    egg_rows = [i for m in week for i in m["ingredients"] if i["foodId"] == "egg"]
    assert all(i["status"] == "removed" and i["change"]["reason"] == "dislike" for i in egg_rows)


def test_the_weekly_review_keeps_disliked_foods_out(planned, clock):  # noqa: F811
    c = planned.client
    remove(c, meal(c, "r_kofta_tahini"), "tahini", reason="dislike", scope="meal")  # "I don't like it": for good
    clock.advance(days=3)
    _, body = checkin_body(c)
    assert c.post("/api/checkins", json=body).status_code == 201
    assert c.get("/api/plan").json()["version"] == 2
    week = all_week(c)
    assert not any(i["foodId"] == "tahini" and i["status"] == "kept" for m in week for i in m["ingredients"])


def test_ingredient_changes_survive_a_rebuild_that_keeps_the_meals(planned):  # noqa: F811
    """A "from now on" exercise swap makes a new plan version with the same meals: the removed egg stays removed."""
    from test_screens_api import today_session
    from test_swaps_api import alt, swap

    c = planned.client
    after = remove(c, meal(c, "r_ful_eggs"), "egg")
    s = today_session(c)
    ex = s["exercises"][0]["exerciseId"]
    swap(c, s, ex, alt(c, s, ex)[0]["exerciseId"], scope="always")
    assert c.get("/api/plan").json()["version"] == 2
    again = day(c)
    assert ingredient(meal(c, "r_ful_eggs"), "egg")["status"] == "removed"
    assert totals(again) == totals(after) and again["note"] == after["note"]
