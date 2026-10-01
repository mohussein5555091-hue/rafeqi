"""The training program: choose a template (data/programs/), then fit it to the person.

For every exercise in the template, in this order:
1. Equipment: not available where they train → the closest exercise with the same movement pattern that is.
2. Injuries: ruled out by an injury's painful movements or restrictions → the closest same-pattern exercise that
   avoids them (and fits the equipment). No safe substitute → removed, with the reason.
3. Paused areas (red flags): exercises loading that area are removed until it's checked.
4. Load: lighter for "recovering" injuries, load restrictions and the health flag.
5. Starting weight from body weight, experience and sex (training.yaml start_load), rounded down to the weight step.
6. Health flag: lower target effort (RPE) and longer rests.
Every change keeps its reason.
"""

import math
from dataclasses import dataclass, field

from app.engine.injuries import allowed, load_cuts, paused_by, ruled_out_by
from app.engine.rules import explain, load_rules, load_templates
from app.engine.types import ExerciseInfo, InjuryInfo, Person, Reason
from app.vocab import get_vocab

LEVELS = {"beginner": 0, "intermediate": 1, "advanced": 2}
EXPERIENCE = {"beginner": {"en": "beginner", "ar": "مبتدئ"}, "intermediate": {"en": "intermediate", "ar": "متوسط"},
              "advanced": {"en": "advanced", "ar": "متقدم"}}
STATUS = {"recovering": {"en": "recovering", "ar": "لسه بيتعافى"}, "active": {"en": "injured", "ar": "مصاب"}}


@dataclass(frozen=True)
class Adjustments:
    """Changes from weekly reviews (engine/review.py), applied on top of the template."""

    avoid: frozenset[str] = frozenset()                     # exercises marked uncomfortable → swapped
    injury_factors: tuple[tuple[str, float], ...] = ()      # (injury_id, extra load factor) where pain went up
    deload: bool = False                                    # one set less, effort 1 lower, this week only
    weight_offsets: tuple[tuple[str, float], ...] = ()      # (exercise_id, kg) for the next session only


@dataclass
class PlannedExercise:
    exercise_id: str
    position: int
    sets: int
    reps: str
    rest_sec: int
    target_rpe: float
    weight_step_kg: float
    start_weight_kg: float
    load_factor: float = 1.0
    weight_offset_kg: float = 0.0
    replaced_exercise_id: str | None = None
    injury_id: str | None = None
    swap_kind: str | None = None  # swapped (injury) | equipment
    reasons: list[Reason] = field(default_factory=list)


@dataclass
class PlannedDay:
    day_index: int
    weekday: str
    key: str
    name: dict
    est_minutes: int
    warmup_minutes: int
    exercises: list[PlannedExercise]


@dataclass
class ProgramPlan:
    template_id: str
    name: dict
    days_per_week: int
    total_weeks: int
    deload_week: int | None
    days: list[PlannedDay]
    reasons: list[Reason]  # template choice, removed exercises, paused areas


def _bi(t: dict, **v) -> Reason | dict:
    return {"en": t["en"].format(**{k: (x["en"] if isinstance(x, dict) else x) for k, x in v.items()}),
            "ar": t["ar"].format(**{k: (x["ar"] if isinstance(x, dict) else x) for k, x in v.items()})}


def _reason(rule: str, source: str, template: dict, **v) -> Reason:
    t = _bi(template, **v)
    return Reason(rule=rule, en=t["en"], ar=t["ar"], source=source)


def choose_template(p: Person, templates: tuple[dict, ...] | None = None) -> tuple[dict, int, list[Reason]]:
    """The best-matching template and the number of days to use from it."""
    rules = load_rules()["training"]["template_choice"]
    pts = rules["points"]

    def score(t: dict) -> int:
        return (pts["experience"] * (p.experience in t["experience"]) + pts["days"] * (p.days_per_week in t["days_per_week"])
                + pts["goal"] * (p.goal in t["goals"]) + pts["location"] * (p.location in t["locations"]))

    templates = templates or load_templates()
    # Only templates made for where they train (any template if none is).
    candidates = [t for t in templates if p.location in t["locations"]] or list(templates)
    best = max(candidates, key=score)  # max() keeps the first of equal scores
    days = p.days_per_week if p.days_per_week in best["days_per_week"] else min(best["days_per_week"], key=lambda d: (abs(d - p.days_per_week), d))
    reasons = [_reason("training.template_choice", rules["source"], rules["explain"], name=best["name"],
                       experience=EXPERIENCE[p.experience], days=days)]
    if days != p.days_per_week:
        reasons.append(_reason("training.template_choice", rules["source"], rules["explain_days"], program_days=days, days=p.days_per_week))
    return best, days, reasons


def available_equipment(location: str) -> set[str]:
    return set(load_rules()["training"]["equipment_by_location"][location]) | {"bodyweight"}


def fits_equipment(ex: ExerciseInfo, location: str) -> bool:
    return set(ex.equipment) <= available_equipment(location)


def weight_step(ex: ExerciseInfo) -> float:
    steps = load_rules()["training"]["weight_step_kg"]
    return max((steps.get(e, 0) for e in ex.equipment), default=0)


def closest_substitute(ex: ExerciseInfo, p: Person, catalogue: dict[str, ExerciseInfo], taken: set[str],
                       avoid: frozenset[str] = frozenset()) -> ExerciseInfo | None:
    """Same movement pattern, fits the equipment, avoids every injury; the lowest penalty wins (ties: id order)."""
    pen = load_rules()["training"]["injuries"]["substitute_penalty"]
    vocab = get_vocab()
    best, best_score = None, math.inf
    for c in sorted(catalogue.values(), key=lambda c: c.id):
        if c.id == ex.id or c.id in taken or c.id in avoid or c.pattern != ex.pattern:
            continue
        if not fits_equipment(c, p.location) or not allowed(c, p.injuries, vocab):
            continue
        s = (pen["different_range"] * (c.rom != ex.rom)
             + pen["different_equipment"] * (not set(c.equipment) & set(ex.equipment))
             + pen["per_difficulty_step"] * abs(LEVELS[c.difficulty] - LEVELS[ex.difficulty])
             + pen["harder_than_you"] * (LEVELS[c.difficulty] > LEVELS[p.experience]))
        if s < best_score:
            best, best_score = c, s
    return best


def start_weight(ex: ExerciseInfo, p: Person, load_factor: float) -> float:
    sl = load_rules()["training"]["start_load"]
    ratio = sl["ratio"].get(ex.id, 0)
    step = weight_step(ex)
    if not ratio or not step:
        return 0.0
    kg = p.weight_kg * ratio * sl["experience_factor"][p.experience] * sl["sex_factor"][p.sex] * load_factor
    return max(step, math.floor(kg / step) * step)


def build_program(p: Person, catalogue: dict[str, ExerciseInfo], templates: tuple[dict, ...] | None = None,
                  adjust: Adjustments = Adjustments()) -> ProgramPlan:
    rules = load_rules()
    tr, safety = rules["training"], rules["safety"]
    inj_rules = tr["injuries"]
    vocab = get_vocab()
    regions = safety["region_names"]
    template, days, plan_reasons = choose_template(p, templates)
    weekdays = tr["schedules"][days]
    by_key = {d["key"]: d for d in template["days"]}
    planned_days: list[PlannedDay] = []

    def name(ex_id: str) -> dict:
        return catalogue[ex_id].name

    for index, (weekday, key) in enumerate(zip(weekdays, template["rotation"][str(days)])):
        tday = by_key[key]
        taken: set[str] = set()
        exercises: list[PlannedExercise] = []
        for t in tday["exercises"]:
            ex = catalogue[t["exercise"]]
            reasons: list[Reason] = []
            replaced, injury_id, swap_kind = None, None, None

            if not fits_equipment(ex, p.location):
                sub = closest_substitute(ex, p, catalogue, taken, adjust.avoid)
                if sub is None:
                    plan_reasons.append(_reason("training.equipment", tr["start_load"]["source"], inj_rules["equipment_removed"], **{"from": name(ex.id)}))
                    continue
                reasons.append(_reason("training.equipment", tr["start_load"]["source"], inj_rules["equipment"], **{"from": name(ex.id), "to": sub.name}))
                replaced, swap_kind, ex = ex.id, "equipment", sub

            blocking = next(((i, tag) for i in p.injuries if (tag := ruled_out_by(ex, i, vocab))), None)
            if blocking:
                inj, tag = blocking
                kind = "painful_movements" if tag in vocab.data["painful_movements"] else "restrictions"
                label = vocab.data[kind][tag]
                why = {"en": label["en"].lower() if kind == "painful_movements" else label["en"], "ar": label["ar"]}
                sub = closest_substitute(ex, p, catalogue, taken, adjust.avoid)
                if sub is None:
                    plan_reasons.append(_reason("training.injuries", inj_rules["source"], inj_rules["explain"]["removed"],
                                                **{"from": name(ex.id), "why": why, "area": regions[inj.region]}))
                    continue
                wording = inj_rules["explain"]["swapped" if kind == "painful_movements" else "swapped_restriction"]
                reasons.append(_reason("training.injuries", inj_rules["source"], wording,
                                       **{"from": name(ex.id), "to": sub.name, "why": why, "area": regions[inj.region]}))
                replaced, injury_id, swap_kind, ex = replaced or ex.id, inj.id, "swapped", sub

            if ex.id in adjust.avoid:
                sub = closest_substitute(ex, p, catalogue, taken, adjust.avoid)
                if sub is None:
                    plan_reasons.append(Reason("training.review.uncomfortable", f"{name(ex.id)['en']} kept: you marked it uncomfortable, but nothing "
                                               "in the catalogue does the same movement yet. Go lighter or skip it.",
                                               f"{name(ex.id)['ar']} فاضل: قلت إنه مش مريح، بس لسه مفيش تمرين بنفس الحركة. خفّف الوزن أو اتخطاه.",
                                               tr["review"]["source"]))
                else:
                    reasons.append(Reason("training.review.uncomfortable", f"{name(ex.id)['en']} → {sub.name['en']}: you marked it uncomfortable.",
                                          f"{name(ex.id)['ar']} ← {sub.name['ar']}: قلت إنه مش مريح.", tr["review"]["source"]))
                    replaced, swap_kind, ex = replaced or ex.id, swap_kind or "swapped", sub

            if (inj := paused_by(ex, p.injuries)) is not None:
                plan_reasons.append(_reason("safety.red_flags", safety["red_flags"]["source"], inj_rules["explain"]["paused"],
                                            name=name(ex.id), area=regions[inj.region], message=safety["red_flags"]["message"]))
                continue

            factor = 1.0
            for cut in load_cuts(ex, p.injuries, vocab):
                factor *= cut.factor
                injury_id = injury_id or cut.injury.id
                status = STATUS["recovering"] if cut.why == "recovering" else STATUS["active"]
                reasons.append(_reason("training.injuries", inj_rules["source"], inj_rules["explain"]["load"], name=ex.name,
                                       pct=round(cut.factor * 100), area=regions[cut.injury.region], status=status))
            for iid, extra in adjust.injury_factors:
                inj = next((i for i in p.injuries if i.id == iid), None)
                if inj is not None and set(ex.joints) & set(load_rules()["safety"]["region_joints"].get(inj.region, [])):
                    factor *= extra
                    injury_id = injury_id or iid
                    reasons.append(_reason("training.review.pain_up", tr["review"]["source"], inj_rules["explain"]["load"], name=ex.name,
                                           pct=round(extra * 100), area=regions[inj.region], status=STATUS["active"]))
            rpe, rest, sets = t["rpe"], t["rest_sec"], t["sets"]
            if adjust.deload:
                sets, rpe = max(1, sets - 1), rpe - 1
            if p.conservative:
                c = safety["conservative"]["training"]
                factor *= c["load_factor"]
                rpe, rest = rpe - c["rpe_minus"], rest + c["extra_rest_sec"]
                reasons.append(Reason("safety.conservative", f"Lighter ({round(c['load_factor'] * 100)}% load), effort RPE {rpe} and "
                                      f"{rest} s rest because of your health answers.",
                                      f"أخف ({round(c['load_factor'] * 100)}% من الوزن)، ومجهود {rpe} وراحة {rest} ثانية بسبب إجاباتك عن الصحة.",
                                      safety["conservative"]["source"]))
            factor = max(inj_rules["min_load_factor"], round(factor, 3))
            kg = start_weight(ex, p, factor)
            if kg:
                ratio = tr["start_load"]["ratio"][ex.id]
                reasons.append(explain(tr["start_load"], "training.start_load", kg=kg, ratio=ratio))
            taken.add(ex.id)
            exercises.append(PlannedExercise(
                exercise_id=ex.id, position=len(exercises) + 1, sets=sets, reps=t["reps"], rest_sec=rest, target_rpe=rpe,
                weight_step_kg=weight_step(ex), start_weight_kg=kg, load_factor=factor,
                weight_offset_kg=dict(adjust.weight_offsets).get(ex.id, 0.0), replaced_exercise_id=replaced,
                injury_id=injury_id, swap_kind=swap_kind, reasons=reasons))
        planned_days.append(PlannedDay(index, weekday, key, tday["name"], tday["est_minutes"], tday["warmup_minutes"], exercises))

    return ProgramPlan(template_id=template["id"], name=template["name"], days_per_week=days, total_weeks=template["total_weeks"],
                       deload_week=template.get("deload_week"), days=planned_days, reasons=plan_reasons)
