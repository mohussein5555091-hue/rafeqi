"""The "Why this plan" page: every decision in the person's current plan, with the answers it used, the rule in plain
language, its source and the result.

Built only from what the plan engine stored with the plan (plans.reasons, program_days.reasons and each program
exercise's reasons) and the rule files' `summary`, `uses`, `source`, `placeholder` and `ref` fields
(data/rules/*.yaml, checked by app/engine/rules.py). No AI text: the AI summary at the top comes in the AI phase, so
`aiSummary` is the plan's summary written by app/ai when AI is on (or its template), null while AI is off.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.rules import load_rules
from app.models import Exercise, Plan, ProgramDay, ProgramExercise, TrainingProgram
from app.vocab import get_vocab

# Page sections, in order, and the rules that belong to each. Nutrition reasons are grouped by where the engine
# stored them (calories, protein, fat, carbs, meals, cardio, review); the training ones by their rule.
GROUPS = ("calories", "protein", "carbsFat", "program", "schedule", "volume", "startWeights", "progression", "deload",
          "warmup", "cooldown", "cardio", "exercises", "meals", "review")
BY_BUCKET = {"calories": "calories", "protein": "protein", "fat": "carbsFat", "carbs": "carbsFat", "meals": "meals",
             "cardio": "cardio", "review": "review"}
BY_RULE = (  # first match wins
    ("training.template_choice", "program"), ("training.schedule", "schedule"), ("training.session", "schedule"),
    ("training.volume", "volume"), ("safety.conservative", "volume"), ("training.start_load", "startWeights"),
    ("progression", "progression"), ("training.deload", "deload"), ("training.review.deload", "deload"),
    ("training.warmup", "warmup"), ("training.cooldown", "cooldown"), ("training.cardio", "cardio"),
    ("nutrition.meals", "meals"),
)


def _matches(rule: str, prefix: str) -> bool:
    return rule == prefix or rule.startswith(prefix + ".")


def group_of(rule: str, bucket: str | None) -> str:
    if bucket in BY_BUCKET:
        return BY_BUCKET[bucket]
    return next((g for prefix, g in BY_RULE if _matches(rule, prefix)), "exercises")  # injuries, equipment, swaps…


def rule_key(rule: str) -> str:
    """The rule file section a reason belongs to, as a dotted id ("nutrition.goal.loseFat" → "nutrition.goal"): the
    page groups repeated decisions under it and counts rules by it."""
    parts = rule.split(".")
    node, key = load_rules().get(parts[0]), parts[0]
    for i in range(1, len(parts)):
        nxt = node.get(parts[i]) if isinstance(node, dict) else None
        if not isinstance(nxt, dict):
            break
        node = nxt
        if "source" in node:
            key = ".".join(parts[: i + 1])
    return key


def rule_section(rule: str) -> tuple[dict, str | None]:
    """The rule file section a reason comes from (the deepest one with a `source` along its id) and the sub-rule
    after it, e.g. "nutrition.goal.loseFat" → (nutrition.yaml goal, "loseFat")."""
    parts = rule.split(".")
    node = load_rules().get(parts[0])
    if not isinstance(node, dict):
        raise KeyError(f"no rule file for {rule}")
    best, at = (node, 1) if "source" in node else (None, 1)
    for i in range(1, len(parts)):
        nxt = node.get(parts[i]) if isinstance(node, dict) else None
        if not isinstance(nxt, dict):
            break
        node = nxt
        if "source" in node:
            best, at = node, i + 1
    if best is None:
        raise KeyError(f"no rule section with a source for {rule}")
    return best, parts[at] if at < len(parts) else None


def _pick(tree, sub: str | None):
    """A field that is either one value or one per sub-rule ({sub: value, default: value})."""
    if not isinstance(tree, dict) or "en" in tree:
        return tree
    return tree.get(sub) if sub in tree else tree.get("default", next(iter(tree.values())))


def source_out(section: dict) -> dict:
    """kind: "book" (from your books), "formula" (a standard published formula, with its original source) or
    "placeholder" (not yet from a book)."""
    placeholder = section.get("placeholder") is not False or not section.get("ref")
    kind = "placeholder" if placeholder else section.get("kind", "book")
    out = {"placeholder": placeholder, "kind": kind, "text": section["source"]}
    if not placeholder:
        ref = section["ref"]
        out |= {"book": ref["book"], "chapter": ref.get("chapter"), "page": str(ref["page"]), "quote": ref["quote"]}
    return out


def answers_out(keys: list[str], inputs: dict, injury_id: str | None = None) -> list[dict]:
    """The questionnaire answers a rule read, from the answers saved with this plan version (plans.inputs)."""
    person, injuries = inputs.get("person") or {}, inputs.get("injuries") or []
    labels = get_vocab().data["equipment"]
    out = []
    for k in keys:
        if k == "health":
            value = [h for h, yes in (person.get("health") or {}).items() if yes]
        elif k == "injuries":
            value = [{key: i.get(key) for key in ("region", "status", "severity", "painful_movements", "restrictions")}
                     for i in injuries if injury_id is None or i.get("id") == injury_id]
        elif k == "missing_equipment":
            value = [labels.get(e, {"en": e, "ar": e}) for e in person.get("missing_equipment") or []]
        elif k in ("checkin", "swaps"):
            value = None  # the weekly check-in / the person's own swap: named, not repeated
        elif k in person:
            value = person[k]
        else:
            continue
        out.append({"key": k, "value": value})
    return out


def decision(reason: dict, bucket: str | None, inputs: dict, context: dict | None = None, injury_id: str | None = None) -> dict:
    section, sub = rule_section(reason["rule"])
    return {
        "rule": reason["rule"], "ruleKey": rule_key(reason["rule"]), "group": group_of(reason["rule"], bucket), "context": context,
        "answers": answers_out(_pick(section.get("uses") or [], sub) or [], inputs, injury_id),
        "summary": _pick(section["summary"], sub),
        "source": source_out(section),
        "result": {"en": reason["en"], "ar": reason["ar"]},
    }


def plan_reasons(db: Session, plan: Plan) -> list[tuple[dict, str | None, dict | None, str | None]]:
    """Every reason stored with this plan version: (reason, bucket, context, injury id). Plan-level first, then each
    training day's, then each exercise's."""
    out = [(r, bucket, None, None) for bucket, rs in (plan.reasons or {}).items() for r in rs]
    tp = db.scalar(select(TrainingProgram).where(TrainingProgram.plan_id == plan.id, TrainingProgram.user_id == plan.user_id))
    if tp is None:
        return out
    names = {e.id: {"en": e.name_en, "ar": e.name_ar} for e in db.scalars(select(Exercise))}
    for d in db.scalars(select(ProgramDay).where(ProgramDay.program_id == tp.id, ProgramDay.user_id == plan.user_id)
                        .order_by(ProgramDay.day_index)):
        day = {"en": d.name_en, "ar": d.name_ar}
        out += [(r, None, day, None) for r in d.reasons or []]
        for e in db.scalars(select(ProgramExercise).where(ProgramExercise.program_day_id == d.id, ProgramExercise.user_id == plan.user_id)
                            .order_by(ProgramExercise.position)):
            ctx = {lang: f"{day[lang]} · {names[e.exercise_id][lang]}" for lang in ("en", "ar")}
            out += [(r, None, ctx, e.injury_id) for r in (e.swap_reason or {}).get("reasons", [])]
    return out


def why_out(db: Session, plan: Plan) -> dict:
    decisions = [decision(r, bucket, plan.inputs or {}, ctx, inj) for r, bucket, ctx, inj in plan_reasons(db, plan)]
    groups = [{"id": g, "decisions": [d for d in decisions if d["group"] == g]} for g in GROUPS]
    rules = {d["ruleKey"]: d["source"]["kind"] for d in decisions}
    return {
        "planId": plan.id, "version": plan.version, "createdAt": plan.created_at.isoformat(),
        "aiSummary": plan.ai_summary,  # app/ai (only words around the engine's numbers), or None while AI is off
        # Decisions and rules, each counted once: "X of Y rules from your books · A of B decisions".
        "total": len(decisions), "backed": sum(d["source"]["kind"] == "book" for d in decisions),
        "formulas": sum(d["source"]["kind"] == "formula" for d in decisions),
        "rules": {"total": len(rules), "fromBooks": sum(k == "book" for k in rules.values()),
                  "formulas": sum(k == "formula" for k in rules.values())},
        "groups": [g for g in groups if g["decisions"]],
    }
