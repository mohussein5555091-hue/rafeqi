"""The grocery list, built from the week's meals. Generic item names only; no prices, costs or brands anywhere.

1. Expand every meal into ingredients and grams (× portion), map each food to its generic grocery item
   (× grams of item per gram of food, e.g. cooked rice → dry rice), and sum per item.
2. Split by shelf life: weekly items (fresh) use the week's amount; monthly staples use it × monthly_factor (4.3).
3. Pantry: items the person has plenty of are marked "I have it" and left out of what to buy.
4. Convert grams to buying units (kg, L, pieces…) and round up to whole packs.
5. Group by category, and produce a plain-text version for WhatsApp.
"""

import math
from dataclasses import dataclass

from app.engine.rules import load_rules
from app.engine.types import GroceryItemInfo

CATEGORY_ORDER = ("produce", "meat", "dairy", "bakery", "pantry", "spices")
CATEGORY_NAMES = {
    "produce": {"en": "Vegetables & fruit", "ar": "خضار وفاكهة"},
    "meat": {"en": "Meat, chicken & fish", "ar": "لحوم وفراخ وسمك"},
    "dairy": {"en": "Dairy & eggs", "ar": "ألبان وبيض"},
    "bakery": {"en": "Bread & bakery", "ar": "عيش ومخبوزات"},
    "pantry": {"en": "Pantry staples", "ar": "أساسيات المطبخ"},
    "spices": {"en": "Spices & sauces", "ar": "توابل وصلصات"},
}
UNIT_NAMES = {"kg": {"en": "kg", "ar": "كجم"}, "g": {"en": "g", "ar": "جم"}, "L": {"en": "L", "ar": "لتر"},
              "pcs": {"en": "", "ar": ""}, "cups": {"en": "cups", "ar": "علبة"}, "jars": {"en": "jars", "ar": "برطمان"}}
HEADER = {"en": "Rafeqi grocery list — {period}", "ar": "قائمة مشتريات رفيقي — {period}"}
PERIODS = {"week": {"en": "this week", "ar": "الأسبوع ده"}, "month": {"en": "this month", "ar": "الشهر ده"}}


@dataclass(frozen=True)
class GroceryLine:
    item_id: str
    period: str  # week | month
    grams_needed: float
    qty: float  # buying units, rounded up to whole packs
    unit: str
    have_it: bool = False


def item_grams(meals: list[tuple[str, float]], recipe_ingredients: dict[str, list[tuple[str, float]]],
               food_map: dict[str, tuple[str, float]]) -> dict[str, float]:
    """meals: [(recipe_id, portion)] for the week → grams of each grocery item."""
    totals: dict[str, float] = {}
    for recipe_id, portion in meals:
        for food_id, grams in recipe_ingredients[recipe_id]:
            item_id, ratio = food_map[food_id]
            totals[item_id] = totals.get(item_id, 0.0) + grams * portion * ratio
    return totals


def to_buying_units(grams: float, item: GroceryItemInfo) -> float:
    units = grams / item.grams_per_unit
    packs = math.ceil(round(units / item.pack_size, 6))
    return round(packs * item.pack_size, 3)


def build_grocery_list(meals: list[tuple[str, float]], recipe_ingredients: dict[str, list[tuple[str, float]]],
                       food_map: dict[str, tuple[str, float]], items: dict[str, GroceryItemInfo],
                       pantry: dict[str, str] | None = None) -> list[GroceryLine]:
    factor = load_rules()["nutrition"]["grocery"]["monthly_factor"]
    pantry = pantry or {}
    lines = []
    for item_id, grams in item_grams(meals, recipe_ingredients, food_map).items():
        item = items[item_id]
        period = "week" if item.shelf_life == "weekly" else "month"
        need = grams if period == "week" else grams * factor
        lines.append(GroceryLine(item_id=item_id, period=period, grams_needed=round(need, 1), qty=to_buying_units(need, item),
                                 unit=item.unit, have_it=pantry.get(item_id) == "plenty"))
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    return sorted(lines, key=lambda line: (line.period, order[items[line.item_id].category], items[line.item_id].name["en"]))


def _qty(q: float) -> str:
    return f"{q:g}"


def as_text(lines: list[GroceryLine], items: dict[str, GroceryItemInfo], period: str, lang: str = "en") -> str:
    """Plain text for WhatsApp: what to buy (items you already have are left out), grouped by category."""
    out = [HEADER[lang].format(period=PERIODS[period][lang])]
    for cat in CATEGORY_ORDER:
        rows = [line for line in lines if line.period == period and not line.have_it and items[line.item_id].category == cat]
        if not rows:
            continue
        out += ["", CATEGORY_NAMES[cat][lang]]
        for line in rows:
            unit = UNIT_NAMES[line.unit][lang]
            out.append(f"- {items[line.item_id].name[lang]} · {_qty(line.qty)}{' ' + unit if unit else ''}")
    return "\n".join(out)
