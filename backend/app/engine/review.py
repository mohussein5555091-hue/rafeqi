"""The weekly review: from the check-in answers, the workout logs and the weight trend, decide small, bounded changes.

Order:
1. Red flags (sharp pain, swelling, numbness, pain getting worse, or pain at the pause level) → skip the normal review:
   pause those areas and show "see a doctor or physiotherapist".
2. Calories (at most every 2 weeks, nutrition.yaml review): this week's average weight against last week's; when the
   change is clearly faster or slower than planned and meals were followed well enough, calories move 100-250 kcal down
   or 100-500 kcal up, sized by how far off the trend is. The new number still goes through every safety bound
   (nutrition.compute_targets).
3. Lifts: a deload week (one set less, lower effort) when sessions felt too hard; "too easy" / "too hard" exercises
   move one weight step for their next session; "uncomfortable" ones are swapped for the closest alternative.
4. Pain went up (without a red flag): that area's exercises get lighter (training.yaml review.pain_up_load_step).
5. Meals the person wants changed are replaced by other recipes that fit the same targets; the grocery list follows.
Every change has a reason. The engine decides; the LLM (next session) only writes the summary text.
"""

from dataclasses import dataclass, field

from app.engine.checkin import red_flags
from app.engine.rules import load_rules
from app.engine.types import ExerciseInfo, Person, Reason


@dataclass(frozen=True)
class ReviewInput:
    person: Person
    calories: int
    maintenance: int
    expected_weekly_change_kg: float
    weights_this_week: tuple[float, ...]   # daily weights, this week (7-day window)
    weights_last_week: tuple[float, ...]   # daily weights, the week before
    answers: dict
    avg_effort: float | None               # workout_logs.effort this week (1-10)
    program_exercise_ids: tuple[str, ...]
    previous_pain: dict[str, int]          # injury_id → last pain before this check-in
    plan_recipe_ids: frozenset[str] = frozenset()
    sessions_planned: int = 0
    days_since_calorie_change: int = 10_000  # since the current calorie target started (app/plans.py)


@dataclass
class Change:
    kind: str  # calories | exercise | injury | meals
    what: dict
    why: dict
    rule: str
    source: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "what": self.what, "why": self.why, "rule": self.rule, "source": self.source}


@dataclass
class ReviewResult:
    status: str  # onTrack | attention | warning
    red_flag: bool = False
    changes: list[Change] = field(default_factory=list)
    calories: int | None = None              # new calorie target (before safety bounds), or None = unchanged
    deload: bool = False
    weight_offsets: dict[str, float] = field(default_factory=dict)  # exercise_id → kg for its next session
    avoid_exercises: set[str] = field(default_factory=set)          # marked uncomfortable
    injury_factors: dict[str, float] = field(default_factory=dict)  # injury_id → extra load factor
    pause_injuries: list[str] = field(default_factory=list)
    ban_recipes: set[str] = field(default_factory=set)


def _mean(xs: tuple[float, ...]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _bi(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


def review_week(inp: ReviewInput, catalogue: dict[str, ExerciseInfo]) -> ReviewResult:
    rules = load_rules()
    nut, tr, safety = rules["nutrition"]["review"], rules["training"]["review"], rules["safety"]
    a = inp.answers
    regions = safety["region_names"]
    injuries = {i.id: i for i in inp.person.injuries}
    pain_entries = a.get("injury_pain") or []

    # 1. Red flags skip the normal review.
    flags = red_flags(a)
    pause_at = safety["red_flags"]["pause_at_pain"]
    flagged = {e["injury_id"] for e in pain_entries if e["trend"] == "worse" or e["pain"] >= pause_at}
    if flags or flagged:
        res = ReviewResult(status="warning", red_flag=True)
        to_pause = flagged | ({e["injury_id"] for e in pain_entries if e["pain"] > 0} if flags else set())
        res.pause_injuries = sorted(i for i in to_pause if i in injuries)
        msg = safety["red_flags"]["message"]
        for iid in res.pause_injuries:
            area = regions[injuries[iid].region]
            res.changes.append(Change("injury", _bi(f"Exercises for your {area['en']} are paused", f"تمارين {area['ar']} متوقفة"),
                                      msg, "safety.red_flags", safety["red_flags"]["source"]))
        if not res.pause_injuries:
            res.changes.append(Change("injury", _bi("Training paused until you're checked", "التمرين متوقف لحد ما تتكشف"),
                                      msg, "safety.red_flags", safety["red_flags"]["source"]))
        return res

    res = ReviewResult(status="onTrack")

    # 2. Calories from the weight trend.
    adherence = a.get("adherence_pct", 0)
    now, before = _mean(inp.weights_this_week), _mean(inp.weights_last_week)
    expected = inp.expected_weekly_change_kg
    if now is not None and before is not None and abs(expected) > 0.01:
        actual = round(now - before, 2)
        direction = 1 if expected > 0 else -1  # +1 gaining, −1 losing
        too_fast = direction * actual > direction * expected * nut["too_fast_factor"] + nut["slack_kg"]
        too_slow = direction * actual < direction * expected * nut["too_slow_factor"]
        vals = dict(before=inp.calories, actual=f"{actual:+.2f}", expected=f"{expected:+.2f}", adherence=adherence)
        waiting = nut["min_days_between_changes"] - inp.days_since_calorie_change
        if waiting > 0 and (too_fast or too_slow):
            t = nut["explain"]["wait"]
            res.changes.append(Change("calories", _bi(f"Calories stay at {inp.calories} kcal", f"السعرات تفضل {inp.calories} سعرة"),
                                      _bi(t["en"].format(calories=inp.calories, days=waiting), t["ar"].format(calories=inp.calories, days=waiting)),
                                      "nutrition.review", nut["source"]))
        elif adherence < nut["min_adherence_pct"] and (too_fast or too_slow):
            t = nut["explain"]["low_adherence"]
            res.changes.append(Change("calories", _bi(f"Calories stay at {inp.calories} kcal", f"السعرات تفضل {inp.calories} سعرة"),
                                      _bi(t["en"].format(calories=inp.calories, adherence=adherence), t["ar"].format(calories=inp.calories, adherence=adherence)),
                                      "nutrition.review", nut["source"]))
            res.status = "attention"
        elif too_fast or too_slow:
            # Up when gaining too slowly or losing too fast, down otherwise; sized by the gap, within the book's range.
            up = (direction > 0) != too_fast
            gap = abs(actual - expected) * rules["nutrition"]["goal"]["kcal_per_kg"] / 7
            low, high = nut["step_up" if up else "step_down"]
            step = int(10 * round(min(max(gap, low), high) / 10))
            after = inp.calories + step if up else inp.calories - step
            t = nut["explain"]["too_fast" if too_fast else "too_slow"]
            vals["after"] = after
            res.calories = after
            res.changes.append(Change("calories", _bi(f"{inp.calories} → {after} kcal", f"{inp.calories} ← {after} سعرة"),
                                      _bi(t["en"].format(**vals), t["ar"].format(**vals)), "nutrition.review", nut["source"]))

    # 3. Lifts: deload, per-exercise feedback.
    dw = tr["deload_when"]
    signals = sum([a.get("difficulty", 0) >= dw["difficulty_at_least"], a.get("soreness", 0) >= dw["soreness_at_least"],
                   (inp.avg_effort or 0) >= dw["avg_effort_at_least"]])
    if signals >= 2:
        res.deload = True
        res.changes.append(Change("exercise", _bi("Lighter week: one set less on every exercise, effort 1 lower",
                                                   "أسبوع أخف: مجموعة أقل في كل تمرين، والمجهود أقل بدرجة"),
                                  _bi("Sessions felt very hard and you're sore; a lighter week lets you recover and come back stronger.",
                                      "الجلسات كانت صعبة أوي وعندك ألم عضلات؛ أسبوع أخف بيخليك تتعافى وترجع أقوى."),
                                  "training.review.deload", tr["source"]))
    steps = rules["training"]["weight_step_kg"]
    for fb in a.get("exercise_feedback") or []:
        ex = catalogue.get(fb["exercise_id"])
        if ex is None or ex.id not in inp.program_exercise_ids:
            continue
        step_kg = max((steps.get(e, 0) for e in ex.equipment), default=0)
        name = ex.name
        if fb["feel"] in ("tooEasy", "tooHard") and step_kg:
            sign = 1 if fb["feel"] == "tooEasy" else -1
            res.weight_offsets[ex.id] = sign * step_kg
            res.changes.append(Change("exercise",
                                      _bi(f"{name['en']}: {'+' if sign > 0 else '−'}{step_kg:g} kg next session", f"{name['ar']}: {'+' if sign > 0 else '−'}{step_kg:g} كجم المرة الجاية"),
                                      _bi(f"You marked it \"{'too easy' if sign > 0 else 'too hard'}\".", f"قلت إنه \"{'سهل أوي' if sign > 0 else 'صعب أوي'}\"."),
                                      "training.review.feedback", tr["source"]))
        elif fb["feel"] == "uncomfortable":
            res.avoid_exercises.add(ex.id)
            res.changes.append(Change("exercise", _bi(f"{name['en']} swapped for a similar exercise", f"{name['ar']} اتبدّل بتمرين شبهه"),
                                      _bi("You marked it uncomfortable, so it's replaced by the closest exercise with the same movement.",
                                          "قلت إنه مش مريح، فاتبدّل بأقرب تمرين بنفس الحركة."), "training.review.uncomfortable", tr["source"]))

    # 4. Pain went up (no red flag): lighter loads for that area.
    for e in pain_entries:
        prev = inp.previous_pain.get(e["injury_id"])
        if e["injury_id"] in injuries and prev is not None and e["pain"] > prev:
            factor = round(1 - tr["pain_up_load_step"], 2)
            res.injury_factors[e["injury_id"]] = factor
            area = regions[injuries[e["injury_id"]].region]
            res.changes.append(Change("injury", _bi(f"Exercises for your {area['en']} at {round(factor * 100)}% load",
                                                    f"تمارين {area['ar']} بـ {round(factor * 100)}% من الوزن"),
                                      _bi(f"Pain went from {prev} to {e['pain']} this week.", f"الألم زاد من {prev} لـ {e['pain']} الأسبوع ده."),
                                      "training.review.pain_up", tr["source"]))
            res.status = "attention"

    # 5. Meals to change.
    for rid in a.get("meals_to_change") or []:
        if rid in inp.plan_recipe_ids:
            res.ban_recipes.add(rid)
    if res.ban_recipes:
        res.changes.append(Change("meals", _bi(f"{len(res.ban_recipes)} meal(s) replaced", f"{len(res.ban_recipes)} وجبة اتغيرت"),
                                  _bi("You asked to change them; the new ones fit the same calories and protein. Your grocery list is updated.",
                                      "طلبت تغييرهم؛ الجديدة على نفس السعرات والبروتين. قائمة المشتريات اتحدّثت."),
                                  "nutrition.review.meals", nut["source"]))

    if inp.sessions_planned and a.get("sessions_done", 0) * 2 < inp.sessions_planned:
        res.status = "attention"  # fewer than half the sessions: nothing changes in training, but it's flagged
    return res


def as_reasons(changes: list[Change]) -> list[Reason]:
    return [Reason(c.rule, f"{c.what['en']}: {c.why['en']}", f"{c.what['ar']}: {c.why['ar']}", c.source) for c in changes]
