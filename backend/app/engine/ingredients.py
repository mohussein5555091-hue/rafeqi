"""Removing (or replacing) an ingredient of a meal, and keeping the day on target afterwards.

Rules: data/rules/nutrition.yaml `ingredients` (portion limits from `meals`). Everything here is plain Python on the
engine's inputs, so it's tested without a database (tests/backend/test_engine_ingredients.py).

1. `replacements()`: 1–3 foods with the same role (eggs → cheese or yogurt), none the person avoids (dislike/allergy
   tags or foods they removed before), none already in the recipe, closest first. Each is sized to give about what the
   removed food gave (`replacement_grams()`): its protein for a protein, carbs for a carb, fat for a fat, the same grams
   for vegetables and fruit. Flavours (garlic, cumin, lemon…) have no replacement.
2. `effective()`: a recipe's ingredients after the person's changes; `per_serving()`: their calories and macros.
3. `rebalance_day()`: if the change left the day under its targets (protein ≥ target, calories within ±tolerance;
   never asking for more than the day had before the change), the other meals' portions move by at most
   `max_portion_change`, in the usual quarter steps and limits, as little as possible (a small MILP); if that can't,
   calories may be within `meals.relax_calorie_pct` instead (as the meal planner does). If it still can't,
   `snack_for()` suggests a snack that closes the protein gap.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from app.engine.rules import load_rules
from app.engine.types import FoodInfo, Reason, RecipeInfo

MACROS = ("kcal", "protein", "carbs", "fat")


def _rules() -> dict:
    return load_rules()["nutrition"]["ingredients"]


def _source() -> str:
    return _rules()["source"]


def replacement_grams(removed: FoodInfo, grams: float, candidate: FoodInfo) -> float:
    """Grams of `candidate` that give about what `grams` of `removed` gave (by the removed food's role)."""
    r = _rules()
    key = r["match_by_role"][removed.role]
    if key == "none":
        return 0.0
    g = grams if key == "grams" else grams * getattr(removed, key) / max(getattr(candidate, key), 0.1)
    step = r["replacement_round_g"]
    g = min(g, grams * r["max_replacement_factor"])
    return float(max(step, round(g / step) * step))


def _distance(removed: FoodInfo, grams: float, cand: FoodInfo, cand_grams: float) -> float:
    """How different the replacement is, relative to what the removed food gave (calories and every macro)."""
    a = {k: getattr(removed, k) * grams / 100 for k in MACROS}
    b = {k: getattr(cand, k) * cand_grams / 100 for k in MACROS}
    return sum(abs(a[k] - b[k]) / max(a[k], 1 if k != "kcal" else 10) for k in MACROS)


def replacements(food_id: str, grams: float, recipe_foods: set[str], foods: dict[str, FoodInfo],
                 avoid_tags: set[str], disliked: set[str]) -> list[tuple[FoodInfo, float]]:
    """Up to `max_replacements` (food, grams per serving) with the same role, closest first."""
    removed = foods[food_id]
    if _rules()["match_by_role"].get(removed.role, "none") == "none":
        return []
    out = []
    for c in foods.values():
        if c.role != removed.role or c.id == food_id or c.id in recipe_foods or c.id in disliked or c.tags & avoid_tags:
            continue
        g = replacement_grams(removed, grams, c)
        out.append((_distance(removed, grams, c, g), c.id, c, g))
    return [(c, g) for _, _, c, g in sorted(out)][: _rules()["max_replacements"]]


@dataclass(frozen=True)
class Change:
    food_id: str
    replacement_id: str | None = None
    replacement_grams: float | None = None


def effective(ingredients: tuple[tuple[str, float], ...], changes: list[Change]) -> list[tuple[str, float]]:
    """The recipe's (food, grams per serving) after the person's changes: removed foods out, replacements in."""
    by_food = {c.food_id: c for c in changes}
    out = []
    for food, grams in ingredients:
        c = by_food.get(food)
        if c is None:
            out.append((food, grams))
        elif c.replacement_id:
            out.append((c.replacement_id, float(c.replacement_grams or 0)))
    return out


def per_serving(ingredients: list[tuple[str, float]], foods: dict[str, FoodInfo]) -> dict[str, float]:
    return {k: sum(getattr(foods[f], k) * g / 100 for f, g in ingredients) for k in MACROS}


@dataclass
class DayMeal:
    """One meal of the day, with its recipe's calories and macros per serving after any ingredient changes."""

    id: str
    name: dict
    kcal: float
    protein: float
    carbs: float
    fat: float
    planned: float  # the planned portion (the optimizer's, or a meal swap's)
    locked: bool = False  # already eaten: its portion doesn't move


@dataclass
class Rebalance:
    portions: dict[str, float]
    reasons: list[Reason] = field(default_factory=list)
    snack: dict | None = None  # {recipeId, name, portion, kcal, protein}
    on_target: bool = True


def totals(meals: list[DayMeal], portions: dict[str, float]) -> dict[str, float]:
    return {k: sum(getattr(m, k) * portions[m.id] for m in meals) for k in MACROS}


def _ok(t: dict[str, float], floor_protein: float, band: tuple[float, float]) -> bool:
    return t["protein"] >= floor_protein - 0.5 and band[0] - 0.5 <= t["kcal"] <= band[1] + 0.5


def rebalance_day(meals: list[DayMeal], calories: int, protein: int, before: dict[str, float],
                  snacks: list[RecipeInfo] = ()) -> Rebalance:
    """Portions for the day after an ingredient change. `before`: the day's totals with the planned portions and the
    original recipes, so the day is never asked for more than it had (a plan that was already a little off stays as
    it was). Returns the planned portions when the day is still on target."""
    m = load_rules()["nutrition"]["meals"]
    tol = m["calorie_tolerance_pct"] / 100
    floor_protein = min(protein, before["protein"])
    band = (min(calories * (1 - tol), before["kcal"]), max(calories * (1 + tol), before["kcal"]))
    planned = {x.id: x.planned for x in meals}
    t = _rules()["explain"]
    now = totals(meals, planned)
    if _ok(now, floor_protein, band):
        return Rebalance(planned, [Reason("nutrition.ingredients.on_target", t["on_target"]["en"].format(kcal=round(now["kcal"]), protein=round(now["protein"])),
                                          t["on_target"]["ar"].format(kcal=round(now["kcal"]), protein=round(now["protein"])), _source())])
    portions = _solve(meals, calories, floor_protein, band)
    if portions is None:  # as the meal planner does: calories may then be within relax_calorie_pct (protein never gives)
        wide = m["relax_calorie_pct"] / 100
        band = (min(calories * (1 - wide), before["kcal"]), max(calories * (1 + wide), before["kcal"]))
        portions = _solve(meals, calories, floor_protein, band)
    if portions is not None:
        reasons = []
        for x in meals:
            if portions[x.id] != x.planned:
                v = {"from": f"{x.planned:g}", "to": f"{portions[x.id]:g}"}
                reasons.append(Reason("nutrition.ingredients.rebalanced", t["rebalanced"]["en"].format(meal=x.name["en"], **v),
                                      t["rebalanced"]["ar"].format(meal=x.name["ar"], **v), _source()))
        return Rebalance(portions, reasons)
    short = max(0, round(floor_protein - now["protein"]))
    snack = snack_for(snacks, now, floor_protein, band)
    if snack:
        v = {"short": short, "portion": f"{snack['portion']:g}", "kcal": snack["kcal"], "protein": snack["protein"]}
        reason = Reason("nutrition.ingredients.snack", t["snack"]["en"].format(name=snack["name"]["en"], **v),
                        t["snack"]["ar"].format(name=snack["name"]["ar"], **v), _source())
    else:
        reason = Reason("nutrition.ingredients.short", t["short"]["en"].format(short=short), t["short"]["ar"].format(short=short), _source())
    return Rebalance(planned, [reason], snack, on_target=False)


def _solve(meals: list[DayMeal], calories: int, floor_protein: float, band: tuple[float, float]) -> dict[str, float] | None:
    """Quarter-step portions within ±max_portion_change of the plan (and the usual limits) that meet the protein floor
    and the calorie band, changing as little as possible, then staying close to the calorie target."""
    m = load_rules()["nutrition"]["meals"]
    q = round(1 / m["portion_step"])
    kmin, kmax = round(m["portion_min"] * q), round(m["portion_max"] * q)
    d = round(_rules()["max_portion_change"] * q)
    n_m = len(meals)
    # Variables: k (quarter portions) | change⁺ change⁻ per meal | kcal⁺ kcal⁻
    n = 3 * n_m + 2
    rows, lo, hi = [], [], []

    def add(coefs: dict[int, float], low: float, high: float) -> None:
        row = np.zeros(n)
        for i, v in coefs.items():
            row[i] = v
        rows.append(row)
        lo.append(low)
        hi.append(high)

    lower, upper = np.zeros(n), np.full(n, np.inf)
    for i, x in enumerate(meals):
        k0 = round(x.planned * q)
        lower[i], upper[i] = (k0, k0) if x.locked else (max(kmin, k0 - d), min(kmax, k0 + d))
        add({i: 1, n_m + 2 * i: -1, n_m + 2 * i + 1: 1}, k0, k0)  # k − change⁺ + change⁻ = planned
    add({i: x.protein / q for i, x in enumerate(meals)}, floor_protein, np.inf)
    add({i: x.kcal / q for i, x in enumerate(meals)}, band[0], band[1])
    add({**{i: x.kcal / q for i, x in enumerate(meals)}, 3 * n_m: -1, 3 * n_m + 1: 1}, calories, calories)
    cost = np.zeros(n)
    cost[n_m: 3 * n_m] = 100  # every quarter step moved costs much more than a few kcal off target
    cost[3 * n_m:] = 1 / max(calories, 1)
    integrality = np.zeros(n)
    integrality[:n_m] = 1
    res = milp(cost, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality, bounds=Bounds(lower, upper))
    if res.status != 0 or res.x is None:
        return None
    return {x.id: round(res.x[i]) / q for i, x in enumerate(meals)}


def snack_for(snacks: list[RecipeInfo], now: dict[str, float], floor_protein: float, band: tuple[float, float]) -> dict | None:
    """The snack (and smallest portion, in quarter steps) that brings protein up to the floor without going over the
    calorie band; fewest calories first."""
    m = load_rules()["nutrition"]["meals"]
    q = round(1 / m["portion_step"])
    best = None
    for r in snacks:
        for k in range(round(m["portion_min"] * q), round(m["portion_max"] * q) + 1):
            portion = k / q
            if now["protein"] + r.protein * portion >= floor_protein - 0.5 and now["kcal"] + r.kcal * portion <= band[1] + 0.5:
                cand = {"recipeId": r.id, "name": r.name, "portion": portion, "kcal": round(r.kcal * portion), "protein": round(r.protein * portion)}
                if best is None or (cand["kcal"], cand["recipeId"]) < (best["kcal"], best["recipeId"]):
                    best = cand
                break
    return best
