"""The week's meals: pick a recipe and a portion for every meal slot with an optimizer (scipy MILP / HiGHS).

Hard limits (data/rules/nutrition.yaml `meals`):
- every day within ±calorie_tolerance_pct of the calorie target, and at least the protein target;
- no recipe containing a disliked food or an allergen; only recipes that suit the slot (breakfast, iftar…);
- each day's cooking time within the cooking minutes answered (a batch-cooked recipe counts its time once per batch);
- a recipe at most max_uses_per_week times a week (snacks: max_uses_per_week_snack) and once a day; portions in quarter steps.
Minimised: distance from the carb and fat targets (and calories inside the band), plus recipes already eaten this week.
Solved one day at a time (each day is a small model), so a week takes well under a second.
If nothing fits, limits are eased one at a time (cooking → variety → meal times → protein → calories) and the plan says which.
There is no price or budget logic anywhere.
"""

import datetime as dt
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from app.engine.rules import load_rules
from app.engine.types import Person, Reason, RecipeInfo, week_dates


class NoMealPlan(Exception):
    pass


@dataclass(frozen=True)
class MealChoice:
    date: dt.date
    slot: str
    time: str
    recipe_id: str
    portion: float
    kcal: int
    protein: int
    carbs: int
    fat: int


@dataclass
class WeekMeals:
    meals: list[MealChoice]
    relaxed: list[str] = field(default_factory=list)
    reasons: list[Reason] = field(default_factory=list)

    def day(self, d: dt.date) -> list[MealChoice]:
        return [m for m in self.meals if m.date == d]

    def totals(self, d: dt.date) -> dict[str, int]:
        ms = self.day(d)
        return {k: sum(getattr(m, k) for m in ms) for k in ("kcal", "protein", "carbs", "fat")}


@dataclass(frozen=True)
class Targets:
    calories: int
    protein: int
    carbs: int
    fat: int


def is_ramadan(d: dt.date) -> bool:
    return any(r["start"] <= d <= r["end"] for r in load_rules()["nutrition"]["meals"]["ramadan"])


def day_slots(d: dt.date, p: Person) -> list[tuple[str, str]]:
    """[(slot, time)] for that day: Ramadan slots on Ramadan days for people who fast it; intermittent times otherwise."""
    m = load_rules()["nutrition"]["meals"]
    if "ramadan" in p.fasting and is_ramadan(d):
        return [(s, m["ramadan_times"][s]) for s in m["ramadan_slots_by_meals_per_day"][p.meals_per_day]]
    times = m["intermittent_times"] if "intermittent" in p.fasting else m["times"]
    return [(s, times[s]) for s in m["slots_by_meals_per_day"][p.meals_per_day]]


def eligible_recipes(recipes: list[RecipeInfo], p: Person, banned: frozenset[str] = frozenset()) -> list[RecipeInfo]:
    """Recipes without disliked or allergy foods. A food the person removed with "I don't like it" / "Always"
    (p.disliked_foods) is left out of every recipe that has it, and a recipe it is essential to is left out entirely."""
    avoid, drop = p.avoided_food_tags, frozenset(p.disliked_foods)
    out = []
    for r in sorted(recipes, key=lambda r: r.id):
        if r.id in banned or r.tags & avoid or r.essential & drop:
            continue
        out.append(without_foods(r, drop) if drop & {f for f, _ in r.ingredients} else r)
    return out


def without_foods(r: RecipeInfo, drop: frozenset[str]) -> RecipeInfo:
    """The recipe minus some (non-essential) foods, with its calories and macros worked out again."""
    keep = [(ing, n) for ing, n in zip(r.ingredients, r.per100) if ing[0] not in drop]
    mac = {k: sum(n[j] * g / 100 for (_, g), n in keep) for j, k in enumerate(("kcal", "protein", "carbs", "fat"))}
    return replace(r, ingredients=tuple(i for i, _ in keep), per100=tuple(n for _, n in keep), **mac)


def _solve_day(slots: list[tuple[str, str]], recipes: list[RecipeInfo], t: Targets, p: Person, used: dict[str, int], *,
               tol: float, protein_pct: float, cooking: bool, max_uses: int, any_slot: bool = False) -> list[tuple[int, RecipeInfo, float]] | None:
    """One day: [(slot index, recipe, portion)], or None if nothing fits these limits."""
    m = load_rules()["nutrition"]["meals"]
    q = round(1 / m["portion_step"])
    kmin, kmax = round(m["portion_min"] * q), round(m["portion_max"] * q)
    w = m["weights"]
    snack_max = max(max_uses, m["max_uses_per_week_snack"])
    cells = [(j, r) for j, (slot, _) in enumerate(slots) for r in recipes
             if (any_slot or slot in r.slots) and used.get(r.id, 0) < (snack_max if slot == "snack" else max_uses)]
    nc = len(cells)
    # Variables: x (choose) | k (quarter portions) | deviations kcal± carbs± fat±
    n = 2 * nc + 6
    rows, lo, hi = [], [], []

    def add(coefs: dict[int, float], low: float, high: float) -> None:
        row = np.zeros(n)
        for i, v in coefs.items():
            row[i] += v
        rows.append(row)
        lo.append(low)
        hi.append(high)

    for j in range(len(slots)):
        cs = [c for c, (j_, _) in enumerate(cells) if j_ == j]
        if not cs:
            return None
        add({c: 1 for c in cs}, 1, 1)  # one recipe per slot
    for c in range(nc):
        add({nc + c: 1, c: -kmin}, 0, np.inf)   # k ≥ kmin·x
        add({nc + c: 1, c: -kmax}, -np.inf, 0)  # k ≤ kmax·x
    add({nc + c: r.kcal / q for c, (_, r) in enumerate(cells)}, t.calories * (1 - tol / 100), t.calories * (1 + tol / 100))
    add({nc + c: r.protein / q for c, (_, r) in enumerate(cells)}, t.protein * protein_pct / 100, np.inf)
    for kind, attr, target in ((0, "kcal", t.calories), (1, "carbs", t.carbs), (2, "fat", t.fat)):
        coefs = {nc + c: getattr(r, attr) / q for c, (_, r) in enumerate(cells)}
        coefs[2 * nc + 2 * kind] = -1
        coefs[2 * nc + 2 * kind + 1] = 1
        add(coefs, target, target)  # value − dev⁺ + dev⁻ = target
    for r in {r.id: r for _, r in cells}.values():
        same = [c for c, (_, rr) in enumerate(cells) if rr.id == r.id]
        if len(same) > 1:
            add({c: 1 for c in same}, -np.inf, 1)  # once a day
    if cooking:
        add({c: (r.prep_min + r.cook_min) / r.batch for c, (_, r) in enumerate(cells)}, -np.inf, p.cooking_minutes)

    cost = np.zeros(n)
    for c, (_, r) in enumerate(cells):
        cost[c] = w["variety"] * used.get(r.id, 0)  # prefer recipes not eaten yet this week
    for kind, target, weight in ((0, t.calories, w["kcal"]), (1, t.carbs, w["carbs"]), (2, t.fat, w["fat"])):
        cost[2 * nc + 2 * kind] = cost[2 * nc + 2 * kind + 1] = weight * 100 / max(target, 1)
    integrality = np.zeros(n)
    integrality[: 2 * nc] = 1
    upper = np.full(n, np.inf)
    upper[:nc] = 1
    upper[nc: 2 * nc] = kmax
    res = milp(cost, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality,
               bounds=Bounds(np.zeros(n), upper), options={"time_limit": 10})
    if res.x is None:
        return None
    return [(j, r, round(res.x[nc + c]) / q) for c, (j, r) in enumerate(cells) if res.x[c] > 0.5]


def plan_week(week_start: dt.date, p: Person, t: Targets, recipes: list[RecipeInfo], banned: frozenset[str] = frozenset()) -> WeekMeals:
    rules = load_rules()["nutrition"]
    m = rules["meals"]
    dates = week_dates(week_start)
    slots_by_day = [day_slots(d, p) for d in dates]
    pool = eligible_recipes(recipes, p, banned)
    tol, uses = m["calorie_tolerance_pct"], m["max_uses_per_week"]
    ladder = [  # eased one at a time, in this order; calories and protein last
        ("", dict(tol=tol, protein_pct=100, cooking=True, max_uses=uses)),
        ("cooking", dict(tol=tol, protein_pct=100, cooking=False, max_uses=uses)),
        ("variety", dict(tol=tol, protein_pct=100, cooking=False, max_uses=7)),
        ("slots", dict(tol=tol, protein_pct=100, cooking=False, max_uses=7, any_slot=True)),
        ("protein", dict(tol=tol, protein_pct=m["relax_protein_pct"], cooking=False, max_uses=7, any_slot=True)),
        ("calories", dict(tol=m["relax_calorie_pct"], protein_pct=m["relax_protein_pct"], cooking=False, max_uses=7, any_slot=True)),
    ]
    relaxed: list[str] = []
    used: dict[str, int] = {}
    meals = []
    for d, slots in zip(dates, slots_by_day):
        for step, kwargs in ladder:
            chosen = _solve_day(slots, pool, t, p, used, **kwargs)
            if chosen is not None:
                break
        else:
            raise NoMealPlan(f"no combination of the available recipes fits these targets on {d}")
        for name, _ in ladder[1: [s for s, _ in ladder].index(step) + 1]:
            if name not in relaxed:
                relaxed.append(name)
        for j, r, portion in sorted(chosen, key=lambda x: x[0]):
            used[r.id] = used.get(r.id, 0) + 1
            slot, time = slots[j]
            meals.append(MealChoice(date=d, slot=slot, time=time, recipe_id=r.id, portion=portion,
                                    kcal=round(r.kcal * portion), protein=round(r.protein * portion),
                                    carbs=round(r.carbs * portion), fat=round(r.fat * portion)))
    src = m["source"]
    reasons = [Reason("nutrition.meals", m["explain"]["en"].format(meals=p.meals_per_day, tol=m["calorie_tolerance_pct"], calories=t.calories, protein=t.protein),
                      m["explain"]["ar"].format(meals=p.meals_per_day, tol=m["calorie_tolerance_pct"], calories=t.calories, protein=t.protein), src)]
    vals = {"pct": m["relax_protein_pct"]}
    for step in relaxed:
        text = m["relaxed"][step]
        v = {"protein": vals, "calories": {"pct": m["relax_calorie_pct"], "tol": m["calorie_tolerance_pct"]}}.get(step, {})
        reasons.append(Reason(f"nutrition.meals.relaxed.{step}", text["en"].format(**v), text["ar"].format(**v), src))
    by_id = {r.id: r for r in pool}
    reasons += portion_reasons(meals, by_id)
    return WeekMeals(meals=meals, relaxed=relaxed, reasons=reasons)


def portion_reasons(meals: list[MealChoice], recipes: dict[str, RecipeInfo]) -> list[Reason]:
    """One line per recipe chosen this week: how often, at which meals, and how big a portion (the "Why this plan"
    page's meal choices and portions). Rule: nutrition.meals.portions."""
    m = load_rules()["nutrition"]["meals"]
    t, names = m["explain_portions"], m["slot_names"]
    out = []
    for rid in dict.fromkeys(x.recipe_id for x in meals):
        r, mine = recipes[rid], [x for x in meals if x.recipe_id == rid]

        def span(vals: list, fmt=lambda v: f"{v:g}") -> str:
            lo, hi = min(vals), max(vals)
            return fmt(lo) if lo == hi else f"{fmt(lo)}–{fmt(hi)}"
        slots = list(dict.fromkeys(x.slot for x in mine))
        v = dict(times=len(mine), portion=span([x.portion for x in mine]), kcal=span([x.kcal for x in mine]),
                 protein=span([x.protein for x in mine]), minutes=r.prep_min + r.cook_min)
        out.append(Reason("nutrition.meals.portions",
                          t["en"].format(name=r.name["en"], slots=", ".join(names[s]["en"] for s in slots), **v),
                          t["ar"].format(name=r.name["ar"], slots="، ".join(names[s]["ar"] for s in slots), **v), m["source"]))
    return out


def swap_options(day: list[MealChoice], index: int, t: Targets, p: Person, recipes: list[RecipeInfo],
                 banned: frozenset[str] = frozenset(), limit: int = 4) -> list[MealChoice]:
    """Other recipes for one meal of a day (the "Swap" sheet), each with the portion that keeps the whole day inside the
    same limits as the plan: within ±calorie_tolerance_pct of the calorie target and at least the protein target.

    Same meal time, no disliked foods or allergens, not already eaten that day, within the cooking minutes.
    Closest to the current meal's calories and protein first.
    """
    m = load_rules()["nutrition"]["meals"]
    q = round(1 / m["portion_step"])
    kmin, kmax = round(m["portion_min"] * q), round(m["portion_max"] * q)
    tol = m["calorie_tolerance_pct"]
    current = day[index]
    others = [x for i, x in enumerate(day) if i != index]
    kcal_rest, protein_rest = sum(x.kcal for x in others), sum(x.protein for x in others)
    taken = {x.recipe_id for x in day}
    found: list[tuple[float, MealChoice]] = []
    for r in eligible_recipes(recipes, p, banned):
        if r.id in taken or current.slot not in r.slots or (r.prep_min + r.cook_min) / r.batch > p.cooking_minutes:
            continue
        best: tuple[float, MealChoice] | None = None
        for k in range(kmin, kmax + 1):
            portion = k / q
            c = MealChoice(date=current.date, slot=current.slot, time=current.time, recipe_id=r.id, portion=portion,
                           kcal=round(r.kcal * portion), protein=round(r.protein * portion),
                           carbs=round(r.carbs * portion), fat=round(r.fat * portion))
            day_kcal = kcal_rest + c.kcal
            if abs(day_kcal - t.calories) > t.calories * tol / 100 or protein_rest + c.protein < t.protein:
                continue
            score = abs(c.kcal - current.kcal) / max(current.kcal, 1) + abs(c.protein - current.protein) / max(current.protein, 1)
            if best is None or score < best[0]:
                best = (score, c)
        if best is not None:
            found.append(best)
    return [c for _, c in sorted(found, key=lambda x: (x[0], x[1].recipe_id))[:limit]]
