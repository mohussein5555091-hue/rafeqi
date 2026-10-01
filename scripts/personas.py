"""Writes docs/personas.md: the plan the engine builds for each of the 5 test personas, in readable form.

    npm run personas

Same code and inputs as tests/backend/test_personas.py (which checks every plan against the safety bounds).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests" / "backend")]

from app.engine.catalogue import grocery_from_catalogue  # noqa: E402
from app.engine.grocery import as_text  # noqa: E402
from app.engine.injuries import allowed  # noqa: E402
from app.engine.rules import load_rules, rules_version  # noqa: E402
from app.engine.training import fits_equipment  # noqa: E402
from engine_fixtures import exercise_catalogue, food_catalogue, recipe_infos  # noqa: E402
from personas import PERSONAS, run  # noqa: E402

CAT = exercise_catalogue()
RECIPES = {r.id: r for r in recipe_infos()}
ITEMS, _ = grocery_from_catalogue(food_catalogue())
WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def kg(x: float) -> str:
    return f"{x:g} kg" if x else "bodyweight"


def persona_md(key: str) -> list[str]:
    title, p, start = PERSONAS[key]
    r = run(key)
    t = r.targets
    s = load_rules()["safety"]
    out = [f"## {title}", ""]
    inj = "; ".join(f"{i.region} ({i.status}" + (f", painful: {', '.join(i.painful_movements)}" if i.painful_movements else "")
                    + (f", restrictions: {', '.join(i.restrictions)}" if i.restrictions else "") + ")" for i in p.injuries) or "none"
    out += [
        f"**Answers:** {p.sex}, {p.age} years, {p.height_cm:g} cm, {p.weight_kg:g} kg · goal {p.goal} ({p.pace}) · {p.experience}, "
        f"{p.days_per_week} days × {p.session_minutes} min at {p.location} · {p.meals_per_day} meals/day, {p.cooking_minutes} min cooking"
        f" · dislikes: {', '.join(p.dislikes) or 'none'} · allergies: {', '.join(a for a in p.allergies if a != 'none') or 'none'}"
        f" · fasting: {', '.join(p.fasting) or 'none'} · health flags: {', '.join(p.health.yes()) or 'none'} · injuries: {inj}",
        f"**Plan week:** {start.isoformat()} (Saturday)", "",
        "### Targets", "",
        "| | Value | Why |", "|---|---|---|",
        f"| Calories | **{t.calories} kcal** (maintenance {t.maintenance}, {t.expected_weekly_change_kg:+.2f} kg/week) | "
        + "<br>".join(x.en for x in t.reasons["calories"]) + " |",
        f"| Protein | **{t.protein_g} g** | {t.reasons['protein'][0].en} |",
        f"| Fat | **{t.fat_g} g** | {t.reasons['fat'][0].en} |",
        f"| Carbs | **{t.carbs_g} g** | {t.reasons['carbs'][0].en} |", "",
        "### Training", "",
    ]
    out += [f"- {x.en}" for x in r.program.reasons] + [""]
    for d in r.program.days:
        out += [f"**{d.weekday.capitalize()} · {d.name['en']}** ({d.est_minutes} min)", "",
                "| Exercise | Sets × reps | Start weight | Rest | RPE | Notes |", "|---|---|---|---|---|---|"]
        for e in d.exercises:
            notes = "<br>".join(x.en for x in e.reasons if x.rule != "training.start_load")
            out.append(f"| {CAT[e.exercise_id].name['en']} | {e.sets} × {e.reps} | {kg(e.start_weight_kg)} | {e.rest_sec} s | {e.target_rpe:g} | {notes} |")
        out.append("")
    out += ["### Meals", ""]
    out += [f"- {x.en}" for x in r.meals.reasons] + [""]
    out += ["| Day | Meals (portion) | kcal | Protein | Carbs | Fat |", "|---|---|---|---|---|---|"]
    for d in sorted({m.date for m in r.meals.meals}):
        tot = r.meals.totals(d)
        meals = "<br>".join(f"{m.slot} {m.time}: {RECIPES[m.recipe_id].name['en']} ×{m.portion:g}" for m in r.meals.day(d))
        out.append(f"| {WEEKDAY[d.weekday()]} {d.isoformat()} | {meals} | {tot['kcal']} | {tot['protein']} g | {tot['carbs']} g | {tot['fat']} g |")
    out += [f"| **Target** | | **{t.calories}** (±5%) | **≥ {t.protein_g} g** | {t.carbs_g} g | {t.fat_g} g |", "",
            "### Grocery list", "", "```", as_text(r.grocery, ITEMS, "week"), "", as_text(r.grocery, ITEMS, "month"), "```", ""]

    checks = []
    checks.append((f"Calories ≥ floor ({s['calorie_floor']['kcal'][p.sex]})", t.calories >= s["calorie_floor"]["kcal"][p.sex]))
    max_loss = s["max_weekly_loss"]["pct_of_body_weight"] / 100 * p.weight_kg
    checks.append((f"Weekly loss ≤ {max_loss:.2f} kg", t.expected_weekly_change_kg >= -max_loss - 0.01))
    if p.conservative:
        checks.append(("Health flag: deficit ≤ 15%, lighter loads, lower RPE",
                       t.calories >= t.maintenance * 0.85 - 10 and all(e.load_factor <= 0.85 for d in r.program.days for e in d.exercises)))
    days_ok = all(abs(r.meals.totals(d)["kcal"] - t.calories) <= t.calories * 0.05 + 5 and r.meals.totals(d)["protein"] >= t.protein_g - 2
                  for d in {m.date for m in r.meals.meals})
    checks.append(("Every day within ±5% calories and ≥ protein target", days_ok))
    checks.append(("No disliked or allergenic food", all(not RECIPES[m.recipe_id].tags & p.avoided_food_tags for m in r.meals.meals)))
    checks.append(("Every exercise is safe for the injuries", all(allowed(CAT[e.exercise_id], p.injuries) for d in r.program.days for e in d.exercises)))
    checks.append(("Every exercise fits the equipment", all(fits_equipment(CAT[e.exercise_id], p.location) for d in r.program.days for e in d.exercises)))
    checks.append(("Limits eased for meals", not r.meals.relaxed))
    out += ["### Safety checks", ""] + [f"- {'✅' if ok else ('⚠️' if 'eased' in name else '❌')} {name}"
                                         + (f": {', '.join(r.meals.relaxed)}" if 'eased' in name and r.meals.relaxed else "") for name, ok in checks]
    return out + ["", "---", ""]


def main() -> None:
    lines = ["# The 5 test personas", "",
             "Generated by `npm run personas` from the plan engine (`backend/app/engine/`). The same plans are checked against",
             "the safety bounds by `tests/backend/test_personas.py`. **All rule values are placeholders** (see `data/rules/*.yaml`) until",
             "the real values are extracted from the books; the 10 recipes and 2 program templates are samples.", "",
             f"Rules: `{rules_version()}`", ""]
    for key in PERSONAS:
        lines += persona_md(key)
    path = ROOT / "docs" / "personas.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
