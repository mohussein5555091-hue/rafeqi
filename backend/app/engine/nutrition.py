"""Daily calories and macros (data/rules/nutrition.yaml, bounded by data/rules/safety.yaml).

Order: resting burn (Mifflin-St Jeor) → maintenance (× activity) → goal adjustment → health-flag limits →
pregnancy (no deficit) → maximum weekly loss → calorie floor → protein → fat → carbs from the remainder.
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
    if calories_override is not None:
        calories = float(calories_override)
    elif p.goal == "loseFat":
        rate = goal["loseFat"]["kg_per_week"][p.pace]
        deficit = rate * goal["kcal_per_kg"] / 7
        calories = tdee - deficit
        cal_lines.append(explain(goal, "nutrition.goal.loseFat", goal["explain"]["loseFat"], calories=round_to(calories, 10),
                                 deficit=round_to(deficit, 10), rate=rate, pace=p.pace))
    elif p.goal == "recomp":
        pct = goal["recomp"]["deficit_pct"]
        calories = tdee * (1 - pct / 100)
        cal_lines.append(explain(goal, "nutrition.goal.recomp", goal["explain"]["recomp"], calories=round_to(calories, 10), pct=pct))
    else:
        surplus = goal[p.goal]["surplus_kcal"][p.experience]
        calories = tdee + surplus
        cal_lines.append(explain(goal, f"nutrition.goal.{p.goal}", goal["explain"][p.goal], calories=round_to(calories, 10), surplus=surplus))

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
    max_kg = mx["pct_of_body_weight"] / 100 * p.weight_kg
    lowest = tdee - max_kg * goal["kcal_per_kg"] / 7
    if calories < lowest:
        calories = lowest
        cal_lines.append(explain(mx, "safety.max_weekly_loss", calories=round_to(calories, 10), max_kg=round(max_kg, 2),
                                 pct=mx["pct_of_body_weight"]))

    # Never below the calorie floor.
    floor = s["calorie_floor"]["kcal"][p.sex]
    if calories < floor:
        calories = floor
        cal_lines.append(explain(s["calorie_floor"], "safety.calorie_floor", floor=floor))

    calories_i = round_to(calories, 10)
    if any(r.rule.startswith("safety.") for r in cal_lines) or calories_override is not None:
        cal_lines.append(explain(goal, "nutrition.goal.final", goal["explain"]["final"], calories=calories_i))

    # Protein from body weight (or from the weight at the reference BMI, above the BMI threshold).
    pr = n["protein"]
    per_kg = pr["g_per_kg"][p.goal]
    bmi = p.weight_kg / (p.height_cm / 100) ** 2
    basis = p.weight_kg if bmi < pr["bmi_from"] else pr["reference_bmi"] * (p.height_cm / 100) ** 2
    protein = round(per_kg * basis)

    fr = n["fat"]
    fat = round(max(fr["min_g_per_kg"] * p.weight_kg, fr["min_pct_of_calories"] / 100 * calories_i / 9))

    cr = n["carbs"]
    carbs = math.floor((calories_i - 4 * protein - 9 * fat) / 4)
    carb_lines = []
    if carbs < cr["min_g"]:
        # Not enough room: keep the carb minimum and trim fat (never below its per-kg minimum).
        carbs = cr["min_g"]
        fat = max(round(fr["min_g_per_kg"] * p.weight_kg), math.floor((calories_i - 4 * protein - 4 * carbs) / 9))
    carb_lines.append(explain(cr, "nutrition.carbs", carbs=carbs))

    return NutritionTargets(
        bmr=round(bmr), maintenance=maintenance, calories=calories_i, protein_g=protein, fat_g=fat, carbs_g=carbs,
        reasons={
            "calories": cal_lines,
            "protein": [explain(pr, "nutrition.protein", protein=protein, per_kg=per_kg, basis=round(basis, 1))],
            "fat": [explain(fr, "nutrition.fat", fat=fat, per_kg=fr["min_g_per_kg"], pct=fr["min_pct_of_calories"])],
            "carbs": carb_lines,
        },
    )
