"""Daily calories and macros (data/rules/nutrition.yaml, bounded by data/rules/safety.yaml).

Order: resting burn (Mifflin-St Jeor) → maintenance (× activity) → goal adjustment (a % of maintenance) →
health-flag limits → pregnancy (no deficit) → maximum weekly loss → calorie floor → estimated body fat →
protein (from lean mass) → fat (a % of calories) → carbs from the remainder.
Every step that sets or changes a number adds a reason line.
"""

import math
from dataclasses import dataclass, field

from app.engine.rules import explain, load_rules
from app.engine.types import Person, Reason

SEX = {"male": {"en": "man", "ar": "راجل"}, "female": {"en": "woman", "ar": "ست"}}
PACE = {"gentle": "gentle", "steady": "steady", "faster": "faster"}


@dataclass
class NutritionTargets:
    bmr: int
    maintenance: int
    calories: int
    protein_g: int
    fat_g: int
    carbs_g: int
    reasons: dict[str, list[Reason]] = field(default_factory=dict)

    @property
    def expected_weekly_change_kg(self) -> float:
        """Weight change a week at these calories (negative = loss)."""
        return round((self.calories - self.maintenance) * 7 / load_rules()["nutrition"]["goal"]["kcal_per_kg"], 2)


def bmr_mifflin(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "male" else -161)


def body_fat_pct(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Deurenberg et al. (1991): an estimate from BMI, age and sex (nutrition.yaml body_fat), kept within its limits."""
    r = load_rules()["nutrition"]["body_fat"]
    bmi = weight_kg / (height_cm / 100) ** 2
    bf = 1.20 * bmi + 0.23 * age - 10.8 * (1 if sex == "male" else 0) - 5.4
    return min(max(bf, r["min_pct"]), r["max_pct"])


def slide(x: float, x_range: list[float], y_range: list[float]) -> float:
    """A straight line from y_range[0] at x_range[0] to y_range[1] at x_range[1], flat outside the range (the book's
    Figures 8B and 8E)."""
    (x0, x1), (y0, y1) = x_range, y_range
    t = min(max((x - x0) / (x1 - x0), 0.0), 1.0)
    return y0 + t * (y1 - y0)


def _both(t: dict, **v) -> dict:
    """Fills an {en, ar} template where some values differ by language."""
    return {"en": t["en"].format(**{k: (x["en"] if isinstance(x, dict) else x) for k, x in v.items()}),
            "ar": t["ar"].format(**{k: (x["ar"] if isinstance(x, dict) else x) for k, x in v.items()})}


def _reason(section: dict, rule: str, template: dict | None = None, **values) -> Reason:
    filled = _both(template or section["explain"], **values)
    return Reason(rule=rule, en=filled["en"], ar=filled["ar"], source=section.get("source", ""))


def round_to(x: float, step: int) -> int:
    return int(step * round(x / step))


def compute_targets(p: Person, calories_override: int | None = None) -> NutritionTargets:
    """`calories_override` is used by the weekly review: the new calories still go through every safety bound."""
    n, s = load_rules()["nutrition"], load_rules()["safety"]
    cal_lines: list[Reason] = []

    bmr = bmr_mifflin(p.sex, p.weight_kg, p.height_cm, p.age)
    cal_lines.append(_reason(n["bmr"], "nutrition.bmr", bmr=round(bmr), sex=SEX[p.sex], age=p.age,
                             height=round(p.height_cm), weight=round(p.weight_kg, 1)))
    factor = n["activity"]["factor_by_training_days"][p.days_per_week]
    tdee = bmr * factor
    maintenance = round_to(tdee, 10)
    cal_lines.append(explain(n["activity"], "nutrition.activity", tdee=maintenance, factor=factor, days=p.days_per_week))

    goal = n["goal"]
    bf = body_fat_pct(p.sex, p.weight_kg, p.height_cm, p.age)
    if calories_override is not None:
        calories = float(calories_override)
    elif p.goal == "loseFat":
        lf = goal["loseFat"]
        pct = lf["deficit_pct"][p.pace]
        if p.pace == "faster" and bf >= lf["high_body_fat"][p.sex]:
            pct = lf["faster_high_body_fat_pct"]
        deficit = tdee * pct / 100
        calories = tdee - deficit
        cal_lines.append(explain(goal, "nutrition.goal.loseFat", goal["explain"]["loseFat"], calories=round_to(calories, 10),
                                 pct=pct, deficit=round_to(deficit, 10), rate=round(deficit * 7 / goal["kcal_per_kg"], 2),
                                 pace=p.pace))
    elif p.goal == "recomp":
        pct = goal["recomp"]["deficit_pct"]
        calories = tdee * (1 - pct / 100)
        cal_lines.append(explain(goal, "nutrition.goal.recomp", goal["explain"]["recomp"], calories=round_to(calories, 10), pct=pct))
    else:
        pct = goal[p.goal]["surplus_pct"][p.experience]
        surplus = tdee * pct / 100
        calories = tdee + surplus
        cal_lines.append(_reason(goal, f"nutrition.goal.{p.goal}", goal["explain"][p.goal], calories=round_to(calories, 10),
                                 pct=pct, surplus=round_to(surplus, 10), level=goal["experience_names"][p.experience]))

    # Health flag: smaller deficit or surplus.
    if p.conservative:
        c = s["conservative"]
        lowest, highest = tdee * (1 - c["max_deficit_pct"] / 100), tdee + c["max_surplus_kcal"]
        bounded = min(max(calories, lowest), highest)
        detail = {"en": f"deficit at most {c['max_deficit_pct']}%, surplus at most {c['max_surplus_kcal']} kcal",
                  "ar": f"النقص {c['max_deficit_pct']}% بالأكتر، والزيادة {c['max_surplus_kcal']} سعرة بالأكتر"}
        cal_lines.append(_reason(c, "safety.conservative", detail=detail))
        calories = bounded

    # Pregnant or recently gave birth: no deficit.
    if p.health.pregnancy and calories < tdee:
        calories = tdee
        cal_lines.append(explain(s["pregnancy"], "safety.pregnancy", calories=round_to(calories, 10)))

    # Never lose faster than the maximum weekly rate.
    mx = s["max_weekly_loss"]
    max_kg = mx["max_kg_per_week"]
    lowest = tdee - max_kg * goal["kcal_per_kg"] / 7
    if calories < lowest:
        calories = lowest
        cal_lines.append(explain(mx, "safety.max_weekly_loss", calories=round_to(calories, 10), max_kg=max_kg))

    # Never below the calorie floor.
    floor = s["calorie_floor"]["kcal"][p.sex]
    if calories < floor:
        calories = floor
        cal_lines.append(explain(s["calorie_floor"], "safety.calorie_floor", floor=floor))

    calories_i = round_to(calories, 10)
    if any(r.rule.startswith("safety.") for r in cal_lines) or calories_override is not None:
        cal_lines.append(explain(goal, "nutrition.goal.final", goal["explain"]["final"], calories=calories_i))

    # Estimated body fat → protein from lean mass (Figure 8B) and fat as a share of calories (Figure 8E).
    bmi = p.weight_kg / (p.height_cm / 100) ** 2
    bf_line = explain(n["body_fat"], "nutrition.body_fat", bf=round(bf), bmi=round(bmi, 1))

    pr = n["protein"]
    g = pr["g_per_lb_lean_mass"]
    per_lb = round(slide(bf, pr["body_fat_range"][p.sex], [g["lean"], g["high_fat"]]), 2)
    lean_kg = p.weight_kg * (1 - bf / 100)
    protein = round(per_lb * lean_kg / pr["kg_per_lb"])

    fr = n["fat"]
    fat_pct = max(fr["min_pct_of_calories"], round(slide(bf, fr["body_fat_range"][p.sex], fr["pct_range"])))
    fat = round(fat_pct / 100 * calories_i / 9)
    fat_min = round(fr["min_pct_of_calories"] / 100 * calories_i / 9)

    cr = n["carbs"]
    carbs = math.floor((calories_i - 4 * protein - 9 * fat) / 4)
    carb_lines = []
    if carbs < cr["min_g"]:
        # Not enough room: keep the carb minimum and trim fat (never below 20% of calories).
        carbs = cr["min_g"]
        fat = max(fat_min, math.floor((calories_i - 4 * protein - 4 * carbs) / 9))
        fat_pct = round(fat * 9 / calories_i * 100)
    carb_lines.append(explain(cr, "nutrition.carbs", carbs=carbs))

    return NutritionTargets(
        bmr=round(bmr), maintenance=maintenance, calories=calories_i, protein_g=protein, fat_g=fat, carbs_g=carbs,
        reasons={
            "calories": cal_lines,
            "protein": [bf_line, explain(pr, "nutrition.protein", protein=protein, per_lb=per_lb, lean=round(lean_kg, 1),
                                         bf=round(bf))],
            "fat": [explain(fr, "nutrition.fat", fat=fat, pct=fat_pct, bf=round(bf))],
            "carbs": carb_lines,
        },
    )


def add_cardio_reason(targets: NutritionTargets, p: Person, sessions: int, minutes: int) -> None:
    """Cardio is part of the activity level, never added on top: the calorie reasons say so (nutrition.yaml cardio_counted)."""
    if sessions <= 0:
        return
    n = load_rules()["nutrition"]
    factor = n["activity"]["factor_by_training_days"][p.days_per_week]
    targets.reasons["calories"].insert(2, explain(n["cardio_counted"], "nutrition.cardio_counted", sessions=sessions, minutes=minutes, factor=factor))
