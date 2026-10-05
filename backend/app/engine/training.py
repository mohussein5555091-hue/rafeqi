"""The training program: choose a template (data/programs/), then fit it to the person.

For every exercise in the template, in this order:
1. Equipment: not available where they train → the closest exercise with the same movement pattern that is.
2. Injuries: ruled out by an injury's painful movements or restrictions → the closest same-pattern exercise that
   avoids them (and fits the equipment). No safe substitute → removed, with the reason.
3. Paused areas (red flags): exercises loading that area are removed until it's checked.
4. Load: lighter for "recovering" injuries, load restrictions and the health flag.
5. Starting weight from body weight, experience and sex (training.yaml start_load), rounded down to the weight step
   and capped for the experience level.
6. Health flag: lower target effort (RPE) and longer rests.
Before that, the person's own "from now on" swaps replace template exercises (and the exercises they took out are never
used again). After it: every full-body day gets a leg exercise if it lost its squat and hinge; exercises are taken in
template order until the session length is full (training.yaml `session`); then the warm-up and cool-down are added
(engine/warmup.py) and the time estimate is worked out from the sets, rests, warm-up and cool-down.
Every change keeps its reason.
"""

import math
import re
from dataclasses import dataclass, field

from app.engine.cardio import CardioPlan, build_cardio
from app.engine.injuries import allowed, load_cuts, paused_by, ruled_out_by
from app.engine.rules import deload_in_tables, deload_weeks, explain, load_rules, load_templates
from app.engine.types import ExerciseInfo, Person, Reason
from app.engine.warmup import build_cooldown, build_warmup
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
    # The person's own "from now on" swaps: (from exercise, to exercise, reason code). Kept by every plan version.
    replace: tuple[tuple[str, str, str], ...] = ()


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
    swap_kind: str | None = None  # swapped (injury) | added (full-body legs) | equipment | review (marked uncomfortable) | user (the person's swap)
    user_reason: str | None = None  # user swaps: equipment | busy | cantDo | pain
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
    kind: str = "full"  # upper | lower | full (warm-up moves, cardio placement)
    warmup: dict = field(default_factory=dict)
    cooldown: dict = field(default_factory=dict)
    reasons: list[Reason] = field(default_factory=list)  # warm-up, cool-down, time estimate


@dataclass
class ProgramPlan:
    template_id: str
    name: dict
    days_per_week: int
    total_weeks: int
    deload_week: int | None
    days: list[PlannedDay]
    reasons: list[Reason]  # template choice, removed exercises, paused areas
    cardio: CardioPlan | None = None
    week: int = 1  # the program week these sessions are for


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
    # Highest score, then the program whose days are closest to theirs (max() keeps the first of what's still equal).
    best = max(candidates, key=lambda t: (score(t), -min(abs(d - p.days_per_week) for d in t["days_per_week"])))
    days = p.days_per_week if p.days_per_week in best["days_per_week"] else min(best["days_per_week"], key=lambda d: (abs(d - p.days_per_week), d))
    reasons = [_reason("training.template_choice", rules["source"], rules["explain"], name=best["name"],
                       experience=EXPERIENCE[p.experience], days=days)]
    if days != p.days_per_week:
        reasons.append(_reason("training.template_choice", rules["source"], rules["explain_days"], program_days=days, days=p.days_per_week))
    return best, days, reasons


def available_equipment(location: str, missing: tuple[str, ...] = ()) -> set[str]:
    """What the training place has, minus equipment the person said isn't available (bodyweight always is)."""
    return (set(load_rules()["training"]["equipment_by_location"][location]) - set(missing)) | {"bodyweight"}


def fits_equipment(ex: ExerciseInfo, location: str, missing: tuple[str, ...] = ()) -> bool:
    return set(ex.equipment) <= available_equipment(location, missing)


def deload_volume(sets: int, rpe: float) -> tuple[int, float]:
    """A lighter week's sets and target effort (training.yaml `deload`): weights stay the same."""
    dl = load_rules()["training"]["deload"]
    return max(1, sets - dl["sets_minus"]), rpe - dl["rpe_minus"]


def is_compound(ex: ExerciseInfo) -> bool:
    """A compound (multi-joint) lift: a squat, press, row… not a curl, leg extension or calf raise."""
    return ex.type == "strength" and len(set(ex.joints)) >= 2


def weight_step(ex: ExerciseInfo) -> float:
    steps = load_rules()["training"]["weight_step_kg"]
    return max((steps.get(e, 0) for e in ex.equipment), default=0)


def closest_substitute(ex: ExerciseInfo, p: Person, catalogue: dict[str, ExerciseInfo], taken: set[str],
                       avoid: frozenset[str] = frozenset()) -> ExerciseInfo | None:
    """Same movement pattern (or a related leg pattern), fits the equipment, avoids every injury; the lowest penalty
    wins (ties: id order). A loaded exercise only becomes a bodyweight one when nothing loaded fits."""
    inj = load_rules()["training"]["injuries"]
    pen, related = inj["substitute_penalty"], inj.get("related_patterns", {})
    patterns = {ex.pattern, *related.get(ex.pattern, ())}
    vocab = get_vocab()
    loaded = weight_step(ex) > 0
    best, best_score = None, math.inf
    for c in sorted(catalogue.values(), key=lambda c: c.id):
        if c.id == ex.id or c.id in taken or c.id in avoid or c.pattern not in patterns or c.type != "strength":
            continue
        if not fits_equipment(c, p.location, p.missing_equipment) or not allowed(c, p.injuries, vocab):
            continue
        s = (pen["different_range"] * (c.rom != ex.rom)
             + pen["different_equipment"] * (not set(c.equipment) & set(ex.equipment))
             + pen["per_difficulty_step"] * abs(LEVELS[c.difficulty] - LEVELS[ex.difficulty])
             + pen["harder_than_you"] * (LEVELS[c.difficulty] > LEVELS[p.experience])
             + pen["different_pattern"] * (c.pattern != ex.pattern)
             + pen["lose_load"] * (loaded and weight_step(c) == 0)
             + pen.get("different_joints", 0) * (set(c.joints) != set(ex.joints))
             + pen.get("unloaded", 0) * (weight_step(c) == 0))
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
    caps = sl["max_kg"][p.experience]
    cap = min((caps[e] for e in ex.equipment if e in caps), default=math.inf)
    kg = min(kg, cap)
    return max(step, math.floor(kg / step) * step)


def lifting_minutes(exercises: list[PlannedExercise]) -> float:
    """Every set's work and rest, plus changing exercise (training.yaml `session`)."""
    s = load_rules()["training"]["session"]
    sec = sum(e.sets * (s["work_sec_per_set"] + e.rest_sec) + s["change_exercise_sec"] for e in exercises)
    return sec / 60


def exercise_range(minutes: int) -> dict:
    by = load_rules()["training"]["session"]["exercises_by_minutes"]
    return by[min(by, key=lambda m: (abs(m - minutes), m))]


def _leg_exercise(p: Person, catalogue: dict[str, ExerciseInfo], taken: set[str], avoid: frozenset[str]) -> ExerciseInfo | None:
    """The leg exercise a full-body day gets when injuries or equipment took its squat and hinge away."""
    vocab = get_vocab()
    for pattern in load_rules()["training"]["full_body_legs"]["patterns"]:
        options = [c for c in catalogue.values() if c.pattern == pattern and c.type == "strength" and c.id not in taken and c.id not in avoid
                   and fits_equipment(c, p.location, p.missing_equipment) and allowed(c, p.injuries, vocab) and paused_by(c, p.injuries) is None]
        if options:
            return min(options, key=lambda c: (abs(LEVELS[c.difficulty] - LEVELS[p.experience]), c.id))
    return None


def program_week(template: dict, weeks_done: int) -> int:
    """The program's week for someone who has done `weeks_done` weeks of it: 1…total_weeks, then from week 1 again
    (the books suggest running a program again once it's finished)."""
    return weeks_done % template["total_weeks"] + 1


def template_days(template: dict, week: int) -> dict[str, dict]:
    """Day key → the day with its exercises for that week. A real program has every week's exercises (`weeks`); a
    sample program has one week that repeats (`days[].exercises`)."""
    if "weeks" not in template:
        return {d["key"]: d for d in template["days"]}
    w = template["weeks"][(week - 1) % len(template["weeks"])]
    return {d["key"]: {**d, "exercises": w["days"][d["key"]]} for d in template["days"]}


# The standard RPE chart (Tuchscherer, The Reactive Training Manual, 2008): % of a one-rep max you can lift for
# N reps to failure, N = 1…15. A set of `reps` with r reps left in reserve (RPE 10 − r) is CHART[reps + r].
RPE_CHART = (100, 95.5, 92.2, 89.2, 86.3, 83.7, 81.1, 78.6, 76.2, 73.9, 70.7, 68.0, 65.3, 62.6, 59.9)


def rpe_from_pct(reps: str, pct: float) -> float:
    """The effort (RPE, to the nearest 0.5, between 5 and 10) of a set of `reps` at `pct`% of one-rep max."""
    m = re.search(r"\d+", reps)
    low = int(m.group()) if m else 1  # the first rep count ("8–10" → 8; "max" → 1)
    to_failure = len(RPE_CHART)
    for i in range(len(RPE_CHART) - 1):  # where pct falls in the chart, in reps to failure (interpolated)
        hi, lo = RPE_CHART[i], RPE_CHART[i + 1]
        if lo <= pct <= hi:
            to_failure = i + 1 + (hi - pct) / (hi - lo)
            break
    else:
        to_failure = 1 if pct >= RPE_CHART[0] else len(RPE_CHART)
    rpe = 10 - max(0.0, to_failure - low)
    return min(10.0, max(5.0, round(rpe * 2) / 2))


def build_program(p: Person, catalogue: dict[str, ExerciseInfo], templates: tuple[dict, ...] | None = None,
                  adjust: Adjustments = Adjustments(), weeks_done: int = 0) -> ProgramPlan:
    """The program for one week: `weeks_done` is how many weeks of the program the person has done (0 for a new
    plan), which picks the program's week."""
    rules = load_rules()
    tr, safety = rules["training"], rules["safety"]
    inj_rules = tr["injuries"]
    vocab = get_vocab()
    regions = safety["region_names"]
    template, days, plan_reasons = choose_template(p, templates)
    week = program_week(template, weeks_done)
    weekdays = tr["schedules"][days]
    by_key = template_days(template, week)
    techniques = template.get("techniques") or {}
    replace = {f: (t, why) for f, t, why in adjust.replace}
    removed_by_person = frozenset(replace) | adjust.avoid  # never put back
    planned_days: list[PlannedDay] = []
    sw = tr["swaps"]

    def name(ex_id: str) -> dict:
        return catalogue[ex_id].name

    def swap_why(code: str, from_ex: ExerciseInfo) -> dict:
        t = sw["reasons"][code]
        missing = [e for e in from_ex.equipment if e in p.missing_equipment] or list(from_ex.equipment)
        label = vocab.data["equipment"][missing[0]] if missing else {"en": "equipment", "ar": "الأداة"}
        return {"en": t["en"].format(equipment=label["en"].lower()), "ar": t["ar"].format(equipment=label["ar"])}

    for index, (weekday, key) in enumerate(zip(weekdays, template["rotation"][str(days)])):
        tday = by_key[key]
        kind = tday.get("kind", "full")
        taken: set[str] = set()
        exercises: list[PlannedExercise] = []
        def plan_one(t: dict, quiet: bool = False) -> None:
            """Fits one template exercise to the person and adds it to `exercises` (or explains why it's left out)."""
            if t.get("choose") and t["exercise"] in taken:  # a weak-point slot: the book's next option (program_meta.yaml)
                options = (template.get("weak_points") or {}).get(t["choose"], [])
                pick = next((o for o in options if o in catalogue and o not in taken), None)
                if pick is None:
                    return
                t = {k: v for k, v in t.items() if k != "technique"} | {"exercise": pick}
            ex = catalogue[t["exercise"]]
            if ex.id in taken:
                return
            reasons: list[Reason] = []
            note = (lambda r: None) if quiet else plan_reasons.append
            replaced, injury_id, swap_kind, user_reason = None, None, None, None

            if ex.id in replace:  # the person's own swap comes first
                to_id, code = replace[ex.id]
                to = catalogue.get(to_id)
                if to is not None and to_id not in taken and fits_equipment(to, p.location, p.missing_equipment) and allowed(to, p.injuries, vocab):
                    reasons.append(_reason("training.swaps", sw["source"], sw["explain"], **{"from": name(ex.id), "to": to.name, "why": swap_why(code, ex)}))
                    replaced, swap_kind, user_reason, ex = ex.id, "user", code, to

            if not fits_equipment(ex, p.location, p.missing_equipment):
                sub = closest_substitute(ex, p, catalogue, taken, removed_by_person)
                if sub is None:
                    note(_reason("training.equipment", tr["equipment"]["source"], inj_rules["equipment_removed"], **{"from": name(ex.id)}))
                    return
                reasons.append(_reason("training.equipment", tr["equipment"]["source"], inj_rules["equipment"], **{"from": name(ex.id), "to": sub.name}))
                replaced, swap_kind, ex = replaced or ex.id, swap_kind or "equipment", sub

            blocking = next(((i, tag) for i in p.injuries if (tag := ruled_out_by(ex, i, vocab))), None)
            if blocking:
                inj, tag = blocking
                kind_, why = vocab.injury_tag(tag)
                sub = closest_substitute(ex, p, catalogue, taken, removed_by_person)
                if sub is None:
                    note(_reason("training.injuries", inj_rules["source"], inj_rules["explain"]["removed" if kind_ == "painful" else "removed_restriction"],
                                                **{"from": name(ex.id), "why": why, "area": regions[inj.region]}))
                    return
                wording = inj_rules["explain"]["swapped" if kind_ == "painful" else "swapped_restriction"]
                reasons.append(_reason("training.injuries", inj_rules["source"], wording,
                                       **{"from": name(ex.id), "to": sub.name, "why": why, "area": regions[inj.region]}))
                replaced, injury_id, swap_kind, ex = replaced or ex.id, inj.id, "swapped", sub

            if ex.id in adjust.avoid or (ex.id in replace and swap_kind != "user"):
                sub = closest_substitute(ex, p, catalogue, taken, removed_by_person)
                if sub is None:
                    note(Reason("training.review.uncomfortable", f"{name(ex.id)['en']} kept: you marked it uncomfortable, but nothing "
                                               "in the catalogue does the same movement yet. Go lighter or skip it.",
                                               f"{name(ex.id)['ar']} فاضل: قلت إنه مش مريح، بس لسه مفيش تمرين بنفس الحركة. خفّف الوزن أو اتخطاه.",
                                               tr["review"]["source"]))
                else:
                    reasons.append(Reason("training.review.uncomfortable", f"{name(ex.id)['en']} → {sub.name['en']}: you marked it uncomfortable.",
                                          f"{name(ex.id)['ar']} ← {sub.name['ar']}: قلت إنه مش مريح.", tr["review"]["source"]))
                    # "review", not "swapped": the badge "Swapped for your <area>" is only for injury swaps.
                    replaced, swap_kind, ex = replaced or ex.id, swap_kind or "review", sub

            if ex.id in taken:  # a substitute already used earlier in this session
                return
            if (inj := paused_by(ex, p.injuries)) is not None:
                note(_reason("safety.red_flags", safety["red_flags"]["source"], inj_rules["explain"]["paused"],
                                            name=name(ex.id), area=regions[inj.region], message=safety["red_flags"]["message"]))
                return

            factor = 1.0
            for cut in load_cuts(ex, p.injuries, vocab):
                factor *= cut.factor
                injury_id = injury_id or cut.injury.id
                status = STATUS["recovering"] if cut.why == "recovering" else STATUS["active"]
                reasons.append(_reason("training.injury_load", tr["injury_load"]["source"], tr["injury_load"]["explain"], name=ex.name,
                                       pct=round(cut.factor * 100), area=regions[cut.injury.region], status=status))
            for iid, extra in adjust.injury_factors:
                inj = next((i for i in p.injuries if i.id == iid), None)
                if inj is not None and set(ex.joints) & set(load_rules()["safety"]["region_joints"].get(inj.region, [])):
                    factor *= extra
                    injury_id = injury_id or iid
                    reasons.append(_reason("training.review.pain_up", tr["review"]["source"], tr["injury_load"]["explain"], name=ex.name,
                                           pct=round(extra * 100), area=regions[inj.region], status=STATUS["active"]))
            rest, sets = t["rest_sec"], t["sets"]
            if "rpe" in t:
                rpe = t["rpe"]
            else:  # %1RM in the program: the effort it means, from the standard RPE chart
                rpe = rpe_from_pct(t["reps"], t["pct_1rm"])
                f = tr["pct_1rm"]
                reasons.append(_reason("training.pct_1rm", f["source"], f["explain"], name=ex.name, sets=sets, reps=t["reps"],
                                       pct=f"{t['pct_1rm']:g}", rpe=f"{rpe:g}"))
            if t.get("choose"):
                v = tr["volume"]["explain_choose"]
                reasons.append(Reason("training.volume", v["en"].format(name=ex.name["en"]), v["ar"].format(name=ex.name["ar"]),
                                      tr["volume"]["source"]))
            if t.get("technique") in techniques:
                tq = techniques[t["technique"]]
                v = tr["volume"]["explain_technique"]
                reasons.append(Reason("training.volume", v["en"].format(name=ex.name["en"], technique=tq["en"]),
                                      v["ar"].format(name=ex.name["ar"], technique=tq["ar"]), tr["volume"]["source"]))
            if adjust.deload:
                sets, rpe = deload_volume(sets, rpe)
            if p.conservative:
                c = safety["conservative"]["training"]
                factor *= c["load_factor"]
                rpe, rest = rpe - c["rpe_minus"], rest + c["extra_rest_sec"]
                reasons.append(Reason("safety.conservative", f"Lighter ({round(c['load_factor'] * 100)}% load), effort RPE {rpe} and "
                                      f"{rest} s rest because of your health answers.",
                                      f"أخف ({round(c['load_factor'] * 100)}% من الوزن)، ومجهود {rpe} وراحة {rest} ثانية بسبب إجاباتك عن الصحة.",
                                      safety["conservative"]["source"]))
            factor = max(tr["injury_load"]["min_load_factor"], round(factor, 3))
            kg = start_weight(ex, p, factor)
            if kg:
                ratio = tr["start_load"]["ratio"][ex.id]
                reasons.append(explain(tr["start_load"], "training.start_load", kg=kg, ratio=ratio))
            taken.add(ex.id)
            exercises.append(PlannedExercise(
                exercise_id=ex.id, position=len(exercises) + 1, sets=sets, reps=t["reps"], rest_sec=rest, target_rpe=rpe,
                weight_step_kg=weight_step(ex), start_weight_kg=kg, load_factor=factor,
                weight_offset_kg=dict(adjust.weight_offsets).get(ex.id, 0.0), replaced_exercise_id=replaced,
                injury_id=injury_id, swap_kind=swap_kind, user_reason=user_reason, reasons=reasons))

        for t in tday["exercises"]:
            plan_one(t)
        rng = exercise_range(p.session_minutes)
        # Too few left after injuries and equipment: top up from the program's other days of the same kind.
        for other in by_key.values():
            if len(exercises) >= rng["min"]:
                break
            if other["key"] != key and other.get("kind", "full") == kind:
                for t in other["exercises"]:
                    if len(exercises) < rng["min"]:
                        plan_one(t, quiet=True)

        # Every full-body day trains the legs.
        day_reasons: list[Reason] = []
        if kind == "full" and not any(catalogue[e.exercise_id].pattern in ("squat", "hinge") for e in exercises):
            leg = _leg_exercise(p, catalogue, taken, removed_by_person)
            if leg is not None and not any(catalogue[e.exercise_id].pattern == leg.pattern for e in exercises):
                fl = tr["full_body_legs"]
                why = _reason("training.full_body_legs", fl["source"], fl["explain"], name=leg.name)
                injury_id = next((i.id for i in p.injuries if any(ruled_out_by(catalogue[x["exercise"]], i, vocab) for x in tday["exercises"]
                                                                  if catalogue[x["exercise"]].pattern in ("squat", "hinge"))), None)
                kg = start_weight(leg, p, 1.0)
                exercises.insert(0, PlannedExercise(exercise_id=leg.id, position=1, sets=3, reps="10–12", rest_sec=90, target_rpe=7,
                                                    weight_step_kg=weight_step(leg), start_weight_kg=kg, injury_id=injury_id, swap_kind="added",
                                                    reasons=[why]))
                taken.add(leg.id)

        # A full-body day's leg exercise always makes the cut: it moves to the front if it's further down.
        leg_patterns = set(tr["full_body_legs"]["patterns"])
        if kind == "full" and not any(catalogue[e.exercise_id].pattern in leg_patterns for e in exercises[: rng["min"]]):
            first_leg = next((e for e in exercises if catalogue[e.exercise_id].pattern in leg_patterns), None)
            if first_leg is not None:
                exercises.remove(first_leg)
                exercises.insert(0, first_leg)

        # As many exercises as the session length allows (template order), then warm-up and cool-down.
        # Ramp-up sets go on the first main compound lift (several joints, with a weight), never an isolation exercise.
        first_main = next((e for e in exercises if e.weight_step_kg > 0 and e.start_weight_kg > 0 and is_compound(catalogue[e.exercise_id])), None)
        warm = build_warmup(kind, p, catalogue, first_main.exercise_id if first_main else None, first_main.start_weight_kg if first_main else 0)
        kept: list[PlannedExercise] = []
        for e in exercises:
            if len(kept) >= rng["max"]:
                break
            trial = kept + [e]
            cool = build_cooldown(_trained(trial, catalogue), p, catalogue)
            if len(kept) >= rng["min"] and warm.minutes + lifting_minutes(trial) + cool.minutes > p.session_minutes:
                break
            kept.append(e)
        for n, e in enumerate(kept, start=1):
            e.position = n
        cool = build_cooldown(_trained(kept, catalogue), p, catalogue)
        lift = lifting_minutes(kept)
        est = round(warm.minutes + lift + cool.minutes)
        s = tr["session"]
        day_reasons += warm.reasons + cool.reasons
        day_reasons.append(Reason("training.session", s["explain"]["en"].format(minutes=est, warmup=warm.minutes, exercises=len(kept), lifting=round(lift),
                                                                                cooldown=cool.minutes),
                                  s["explain"]["ar"].format(minutes=est, warmup=warm.minutes, exercises=len(kept), lifting=round(lift), cooldown=cool.minutes),
                                  s["source"]))
        day_reasons.append(volume_reason(tday["name"], kept))
        planned_days.append(PlannedDay(index, weekday, key, tday["name"], est, warm.minutes, kept, kind, warm.as_dict(), cool.as_dict(), day_reasons))

    cardio = build_cardio(p, [(d.weekday, d.kind) for d in planned_days], catalogue)
    plan_reasons.insert(1, schedule_reason(p, weekdays))
    plan_reasons += [progression_reason(planned_days, catalogue), deload_reason(template)]
    lighter = deload_weeks(template)
    return ProgramPlan(template_id=template["id"], name=template["name"], days_per_week=days, total_weeks=template["total_weeks"],
                       deload_week=next((w for w in lighter if w >= week), lighter[0] if lighter else None), days=planned_days,
                       reasons=plan_reasons, cardio=cardio, week=week)


SEP = {"en": ", ", "ar": "، "}


def schedule_reason(p: Person, weekdays: list[str]) -> Reason:
    sc = load_rules()["training"]["schedule"]
    names = {lang: SEP[lang].join(sc["day_names"][d][lang] for d in weekdays) for lang in ("en", "ar")}
    return _reason("training.schedule", sc["source"], sc["explain"], days=len(weekdays), names=names, minutes=p.session_minutes)


def _span(values: list) -> str:
    lo, hi = min(values), max(values)
    return f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g}"


def volume_reason(day_name: dict, exercises: list[PlannedExercise]) -> Reason:
    """One line per day: how many sets, the rep range, effort and rest (the numbers come from the template, after
    any deload or health-flag change)."""
    v = load_rules()["training"]["volume"]
    reps = [int(x) for e in exercises for x in str(e.reps).replace("-", "–").split("–") if x.strip().isdigit()]
    return _reason("training.volume", v["source"], v["explain"], name=day_name, exercises=len(exercises),
                   sets=sum(e.sets for e in exercises), reps=_span(reps) if reps else "—",
                   rpe=_span([e.target_rpe for e in exercises]), rest=_span([e.rest_sec for e in exercises]))


def progression_reason(days: list[PlannedDay], catalogue: dict[str, ExerciseInfo]) -> Reason:
    """How targets move from session to session (data/rules/progression.yaml, used by app/progression.py), with the
    weight steps of the equipment in this program."""
    pr = load_rules()["progression"]
    labels = get_vocab().data["equipment"]
    steps: dict[str, float] = {}
    for d in days:
        for e in d.exercises:
            if e.weight_step_kg > 0:
                eq = next((x for x in catalogue[e.exercise_id].equipment if x in labels and x != "bench"), None)
                if eq:
                    steps.setdefault(eq, e.weight_step_kg)
    text = {lang: SEP[lang].join(f"{kg:g} kg {labels[eq]['en'].lower()}" if lang == "en" else f"{kg:g} كجم {labels[eq]['ar']}" for eq, kg in steps.items())
            or ("bodyweight: more reps" if lang == "en" else "وزن الجسم: عدات أكتر") for lang in ("en", "ar")}
    return _reason("progression", pr["source"], pr["explain"], steps=text, reps=pr["reps_per_step"])


def deload_reason(template: dict) -> Reason:
    dl, when = load_rules()["training"]["deload"], load_rules()["training"]["review"]["deload_when"]
    v = {"difficulty": when["difficulty_at_least"], "soreness": when["soreness_at_least"], "effort": when["avg_effort_at_least"]}
    weeks = deload_weeks(template)
    if weeks and deload_in_tables(template):  # the program's own lighter weeks, already in its tables
        listed = {lang: SEP[lang].join(str(w) for w in weeks) for lang in ("en", "ar")}
        return _reason("training.deload", dl["source"], dl["explain_program"], weeks=listed, total=template["total_weeks"], **v)
    if weeks:
        return _reason("training.deload", dl["source"], dl["explain"], week=weeks[0], total=template["total_weeks"], **v)
    return _reason("training.deload", dl["source"], dl["explain_none"], **v)


def _trained(exercises: list[PlannedExercise], catalogue: dict[str, ExerciseInfo]) -> dict[str, int]:
    """Body region → sets that worked it as a primary muscle."""
    out: dict[str, int] = {}
    for e in exercises:
        for m in catalogue[e.exercise_id].muscles:
            out[m] = out.get(m, 0) + e.sets
    return out


def alternatives(ex: ExerciseInfo, p: Person, catalogue: dict[str, ExerciseInfo], *, preferred: list[str] = (),
                 taken: set[str] = frozenset(), reason: str = "cantDo", missing: tuple[str, ...] = ()) -> list[ExerciseInfo]:
    """2–4 exercises to swap `ex` for: the same movement pattern first (then the same muscles), that fit the equipment
    (minus anything missing) and every active injury, and aren't already in the session. The catalogue's own
    substitutions (`preferred`) come first. "Machine is busy" prefers other equipment."""
    vocab = get_vocab()
    gone = tuple(p.missing_equipment) + tuple(missing)
    limit = load_rules()["training"]["swaps"]["max_alternatives"]
    pen = load_rules()["training"]["injuries"]["substitute_penalty"]

    def usable(c: ExerciseInfo) -> bool:
        return (c.id != ex.id and c.id not in taken and c.type == "strength" and fits_equipment(c, p.location, gone)
                and allowed(c, p.injuries, vocab) and paused_by(c, p.injuries) is None)

    def score(c: ExerciseInfo) -> tuple:
        same_eq = bool(set(c.equipment) & set(ex.equipment) - {"bodyweight", "bench"})
        return (preferred.index(c.id) if c.id in preferred else len(preferred),
                -len(set(c.muscles) & set(ex.muscles)),
                (same_eq if reason == "busy" else 0),
                pen["per_difficulty_step"] * abs(LEVELS[c.difficulty] - LEVELS[p.experience]) + pen["different_range"] * (c.rom != ex.rom),
                c.id)

    same = sorted((c for c in catalogue.values() if c.pattern == ex.pattern and usable(c)), key=score)
    out = same[:limit]
    if len(out) < 2:  # few with the same movement: add exercises for the same main muscles, in the same direction
        way = direction(ex.pattern)
        more = sorted((c for c in catalogue.values() if c.pattern != ex.pattern and way is not None and direction(c.pattern) == way
                       and set(c.muscles) & set(ex.muscles) and usable(c)), key=score)
        out += more[: limit - len(out)]
    return out


def direction(pattern: str) -> str | None:
    """push, pull, kneeDominant, hipDominant… (training.yaml `swaps.directions`); None for patterns without one."""
    return next((d for d, patterns in load_rules()["training"]["swaps"]["directions"].items() if pattern in patterns), None)
