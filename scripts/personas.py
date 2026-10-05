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
from app.engine.warmup import ramp_up  # noqa: E402

LEG_PATTERNS = {"squat", "hinge", "lunge", "kneeExtension", "kneeFlexion"}
from engine_fixtures import exercise_catalogue, food_catalogue, recipe_infos  # noqa: E402
from personas import PERSONAS, run, why_counts  # noqa: E402

CAT = exercise_catalogue()
RECIPES = {r.id: r for r in recipe_infos()}
ITEMS, _ = grocery_from_catalogue(food_catalogue())
WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def kg(x: float) -> str:
    return f"{x:g} kg" if x else "bodyweight"


def why_line(r) -> str:
    c = why_counts(r)
    return (f"{c['rules']['fromBooks']} of {c['rules']['total']} rules from your books · "
            f"{c['backed']} of {c['total']} decisions · {c['rules']['formulas']} standard formula")


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
        f"**Why this plan:** {why_line(r)}", "",
        "### Targets", "",
        "| | Value | Why |", "|---|---|---|",
        f"| Calories | **{t.calories} kcal** (maintenance {t.maintenance}, {t.expected_weekly_change_kg:+.2f} kg/week) | "
        + "<br>".join(x.en for x in t.reasons["calories"]) + " |",
        f"| Protein | **{t.protein_g} g** | " + "<br>".join(x.en for x in t.reasons['protein']) + " |",
        f"| Fat | **{t.fat_g} g** | {t.reasons['fat'][0].en} |",
        f"| Carbs | **{t.carbs_g} g** | {t.reasons['carbs'][0].en} |", "",
        "### Training", "",
    ]
    out += [f"- {x.en}" for x in r.program.reasons] + [""]
    for d in r.program.days:
        w, c = d.warmup, d.cooldown
        moves = ", ".join(f"{CAT[m['id']].name['en']} ({m['amount']['en']})" for m in w["moves"])
        ramp = ", ".join(f"{s['pct']}% × {s['reps']} @ {kg(s['weightKg'])}" for s in ramp_up(
            next((e.start_weight_kg for e in d.exercises if e.exercise_id == w["ramp"]["id"]), 0),
            next((e.weight_step_kg for e in d.exercises if e.exercise_id == w["ramp"]["id"]), 0))) or "none (bodyweight)"
        stretches = ", ".join(f"{CAT[s['id']].name['en']} {s['seconds']} s{' each side' if s['eachSide'] else ''}" for s in c["stretches"])
        out += [f"**{d.weekday.capitalize()} · {d.name['en']}** ({d.kind}, {d.est_minutes} min)", "",
                f"- Warm-up ({w['minutes']} min): {w['general']['minutes']} min {CAT[w['general']['id']].name['en'].lower()}; {moves}; "
                f"ramp-up of {CAT[w['ramp']['id']].name['en'] if w['ramp']['id'] else '—'}: {ramp}"
                + "".join(f"<br>  {s['why']['en']}" for s in w["skipped"]),
                f"- Cool-down ({c['minutes']} min): {stretches}; {c['breathing']['minutes']} min slow breathing",
                f"- {next(x.en for x in d.reasons if x.rule == 'training.session')}", "",
                "| Exercise | Sets × reps | Start weight | Rest | RPE | Notes |", "|---|---|---|---|---|---|"]
        for e in d.exercises:
            notes = "<br>".join(x.en for x in e.reasons if x.rule != "training.start_load")
            out.append(f"| {CAT[e.exercise_id].name['en']} | {e.sets} × {e.reps} | {kg(e.start_weight_kg)} | {e.rest_sec} s | {e.target_rpe:g} | {notes} |")
        out.append("")
    cardio = r.program.cardio
    out += ["### Cardio", ""] + [f"- {x.en}" for x in cardio.reasons] + [""]
    out += ["| Day | Type | Minutes | Intensity | When |", "|---|---|---|---|---|"]
    out += [f"| {s.weekday.capitalize()} | {CAT[s.exercise_id].name['en']} | {s.minutes} | {s.intensity} | {s.when} |" for s in cardio.sessions]
    out += [f"| Every day | Steps | about {cardio.steps_per_day:,} | | |", ""]
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
    max_loss = s["max_weekly_loss"]["max_kg_per_week"]
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
    full_legs = all(any(CAT[e.exercise_id].pattern in LEG_PATTERNS for e in d.exercises) for d in r.program.days if d.kind == "full")
    checks.append(("Every full-body day trains the legs", full_legs))
    checks.append(("Session time within the chosen length (+15 min at most)", all(d.est_minutes <= p.session_minutes + 15 for d in r.program.days)))
    caps = load_rules()["training"]["start_load"]["max_kg"][p.experience]
    checks.append((f"Starting weights within the {p.experience} caps", all(e.start_weight_kg <= min([caps[q] for q in CAT[e.exercise_id].equipment if q in caps] or [999])
                                                                          for d in r.program.days for e in d.exercises)))
    kinds = {d.weekday: d.kind for d in r.program.days}
    week = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]
    checks.append(("No cardio the day before a leg day", all(kinds.get(week[(week.index(s.weekday) + 1) % 7]) not in ("lower", "full") for s in cardio.sessions)))
    checks.append(("Every warm-up move and stretch is safe for the injuries",
                   all(allowed(CAT[m["id"]], p.injuries) for d in r.program.days for m in d.warmup["moves"])
                   and all(allowed(CAT[x["id"]], p.injuries) for d in r.program.days for x in d.cooldown["stretches"])))
    checks.append(("Limits eased for meals", not r.meals.relaxed))
    out += ["### Safety checks", ""] + [f"- {'✅' if ok else ('⚠️' if 'eased' in name else '❌')} {name}"
                                         + (f": {', '.join(r.meals.relaxed)}" if 'eased' in name and r.meals.relaxed else "") for name, ok in checks]
    return out + ["", "---", ""]


def main() -> None:
    lines = ["# The 5 test personas", "",
             "Generated by `npm run personas` from the plan engine (`backend/app/engine/`). The same plans are checked against",
             "the safety bounds by `tests/backend/test_personas.py`. Rule values come from the books where `data/rules/*.yaml` gives a",
             "`ref` (the rest are marked placeholders; `data/REVIEW.md`); the 10 recipes and 2 program templates are still samples.", "",
             f"Rules: `{rules_version()}`", ""]
    for key in PERSONAS:
        lines += persona_md(key)
    path = ROOT / "docs" / "personas.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
