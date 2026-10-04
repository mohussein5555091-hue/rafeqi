"""Cardio in the weekly plan (data/rules/training.yaml `cardio`), decided from the goal, experience, equipment,
health flag and injuries.

- How much: sessions and minutes by goal ([low, high]); beginners take the low end, advanced the high end
  (minutes: intermediate in between), plus a daily step target.
- What: the first option for where they train that fits the equipment and every injury. Injured legs (knee, ankle,
  shin, hip) prefer cycling, then walking, and never jumping or running; the health flag means easy and no jumping.
- When: rest days first, then after lifting, never on the day before a leg day (lower or full body), so the legs are
  fresh. If the week has no room, fewer sessions, and the plan says so.
- Calories: cardio is already part of the activity level (nutrition.yaml); it's never added on top.
"""

from dataclasses import dataclass, field

from app.engine.injuries import paused_by, ruled_out_by
from app.engine.rules import load_rules
from app.engine.types import ExerciseInfo, Person, Reason
from app.vocab import get_vocab

WEEK = ("sat", "sun", "mon", "tue", "wed", "thu", "fri")
GOALS = {"loseFat": {"en": "fat loss", "ar": "خسارة الدهون"}, "recomp": {"en": "recomposition", "ar": "إعادة تشكيل الجسم"},
         "buildMuscle": {"en": "muscle gain", "ar": "بناء العضلات"}, "strength": {"en": "strength", "ar": "القوة"}}


@dataclass
class CardioSession:
    weekday: str
    exercise_id: str
    minutes: int
    intensity: str  # easy | moderate
    when: str  # restDay | afterLifting


@dataclass
class CardioPlan:
    sessions: list[CardioSession]
    steps_per_day: int
    reasons: list[Reason] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"sessions": [{"weekday": s.weekday, "exerciseId": s.exercise_id, "minutes": s.minutes, "intensity": s.intensity,
                              "when": s.when} for s in self.sessions],
                "stepsPerDay": self.steps_per_day, "reasons": [r.as_dict() for r in self.reasons]}


def _pick(rng: list[int], experience: str, *, middle: bool) -> int:
    lo, hi = rng
    if experience == "beginner":
        return lo
    if experience == "intermediate" and middle:
        return int(round((lo + hi) / 2 / 5) * 5) if hi - lo >= 10 else (lo + hi) // 2
    return hi


def choose_type(p: Person, catalogue: dict[str, ExerciseInfo]) -> tuple[ExerciseInfo, str | None]:
    """The cardio type, and the injured leg region it was chosen around (if any)."""
    c = load_rules()["training"]["cardio"]
    vocab = get_vocab()
    eq = set(load_rules()["training"]["equipment_by_location"][p.location]) | {"bodyweight"}
    eq -= set(p.missing_equipment)
    leg = next((i.region for i in p.injuries if i.region in c["leg_regions"]), None)
    avoid = set(c["conservative_avoid"]) if p.conservative else set()
    if leg:
        avoid |= set(c["leg_injury_avoid"])
    options = [catalogue[i] for i in c["options_by_location"][p.location] if i in catalogue]
    options = [o for o in options if set(o.equipment) <= eq and o.pattern not in avoid
               and all(ruled_out_by(o, i, vocab) is None for i in p.injuries) and paused_by(o, p.injuries) is None]
    if leg:
        prefer = c["leg_injury_prefer"]
        options.sort(key=lambda o: prefer.index(o.pattern) if o.pattern in prefer else len(prefer))
    if not options:  # always something: walking needs nothing
        return catalogue["ex_brisk_walk"], leg
    return options[0], leg


def place(days: list[tuple[str, str]], count: int) -> list[tuple[str, str]]:
    """`days`: [(weekday, kind)] of lifting days. Returns [(weekday, restDay | afterLifting)], never the day before a leg day."""
    leg_kinds = set(load_rules()["training"]["cardio"]["leg_day_kinds"])
    kinds = dict(days)

    def before_leg_day(day: str) -> bool:
        return kinds.get(WEEK[(WEEK.index(day) + 1) % 7]) in leg_kinds

    rest = [d for d in WEEK if d not in kinds and not before_leg_day(d)]
    lifting = [d for d in WEEK if d in kinds and not before_leg_day(d)]
    lifting.sort(key=lambda d: kinds[d] in leg_kinds)  # upper-body days first
    # Spread rest-day sessions out: alternate from the start and the end of the free days.
    spread = [rest[i // 2] if i % 2 == 0 else rest[-(i // 2) - 1] for i in range(len(rest))]
    seen, order = set(), []
    for d in spread:
        if d not in seen:
            seen.add(d)
            order.append((d, "restDay"))
    order += [(d, "afterLifting") for d in lifting]
    chosen = order[:count]
    return sorted(chosen, key=lambda x: WEEK.index(x[0]))


def build_cardio(p: Person, days: list[tuple[str, str]], catalogue: dict[str, ExerciseInfo]) -> CardioPlan:
    c = load_rules()["training"]["cardio"]
    g = c["by_goal"][p.goal]
    sessions = _pick(g["sessions"], p.experience, middle=False)
    minutes = _pick(g["minutes"], p.experience, middle=True)
    intensity = "easy" if p.conservative else g["intensity"]
    ex, leg = choose_type(p, catalogue)
    slots = place(days, sessions)
    t, src = c["explain"], c["source"]
    names = c["intensity_names"][intensity]

    def r(key: str, **v) -> Reason:
        return Reason(f"training.cardio.{key}", t[key]["en"].format(**{k: x["en"] if isinstance(x, dict) else x for k, x in v.items()}),
                      t[key]["ar"].format(**{k: x["ar"] if isinstance(x, dict) else x for k, x in v.items()}), src)

    reasons = [r("plan", sessions=len(slots), minutes=minutes, name={"en": ex.name["en"].lower(), "ar": ex.name["ar"]}, intensity=names,
                 steps=f"{g['steps']:,}", goal=GOALS[p.goal])]
    if leg:
        reasons.append(r("legs", name=ex.name, area=load_rules()["safety"]["region_names"][leg]))
    if p.conservative:
        reasons.append(r("conservative"))
    reasons.append(r("placement"))
    if len(slots) < sessions:
        reasons.append(r("fewer", planned=len(slots), wanted=sessions))
    return CardioPlan([CardioSession(d, ex.id, minutes, intensity, when) for d, when in slots], g["steps"], reasons)
