"""The onboarding questionnaire, saved step by step into `profiles` (and `injuries`).

- Each step can be saved again; `profiles.onboarding_step` remembers the furthest step reached, to resume there.
- Any health answer "yes" makes the plan conservative (lighter loads, lower effort targets, more rest).
- Completing needs every step answered. The plan itself is built by the plan engine (Phase 4).
"""

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.models import Injury, Profile
from app.schemas.onboarding import (
    STEPS, AboutIn, FoodIn, GoalIn, HealthIn, InjuriesIn, InjuryOut, OnboardingOut, TrainingIn,
)

ORDER = (*STEPS, "review")
HEALTH_FIELDS = ("heart_condition", "diabetes", "pregnancy", "recent_surgery", "exercise_medication")
FIELDS = {
    "about": ("sex", "age", "height_cm", "weight_kg", "waist_cm"),
    "goal": ("goal", "pace"),
    "training": ("experience", "days_per_week", "session_minutes", "location"),
    "health": HEALTH_FIELDS,
    "food": ("meals_per_day", "dislikes", "allergies", "fasting", "cooking_minutes"),
}
MODELS: dict[str, type[BaseModel]] = {"about": AboutIn, "goal": GoalIn, "training": TrainingIn, "health": HealthIn, "food": FoodIn}
REQUIRED = {"about": ("sex", "age", "height_cm", "weight_kg"), "food": ("meals_per_day", "cooking_minutes")}


class Incomplete(Exception):
    def __init__(self, missing: list[str]):
        super().__init__(", ".join(missing))
        self.missing = missing


def _profile(db: Session, user_id: str) -> Profile:
    p = db.get(Profile, user_id)
    if p is None:  # every account gets one at sign-up; this only covers older rows
        p = Profile(user_id=user_id, updated_at=clock.now())
        db.add(p)
        db.flush()
    return p


def _reached(p: Profile, step: str) -> bool:
    """True once the person has moved past `step` (or finished)."""
    return p.completed_at is not None or ORDER.index(p.onboarding_step) > ORDER.index(step)


def _advance(p: Profile, step: str) -> None:
    nxt = ORDER[ORDER.index(step) + 1]
    if ORDER.index(nxt) > ORDER.index(p.onboarding_step):
        p.onboarding_step = nxt
    p.updated_at = clock.now()


def save_step(db: Session, user_id: str, step: str, answers: BaseModel) -> Profile:
    """Saves one step's answers (about, goal, training, health or food)."""
    p = _profile(db, user_id)
    for field in FIELDS[step]:
        setattr(p, field, getattr(answers, field))
    if step == "health":
        p.conservative = any(getattr(answers, f) for f in HEALTH_FIELDS)
    _advance(p, step)
    db.flush()
    return p


def save_injuries(db: Session, user_id: str, answers: InjuriesIn) -> list[Injury]:
    """The injuries step sends the full list: same region → updated, new region → added, missing region → removed."""
    p = _profile(db, user_id)
    now = clock.now()
    existing = {i.region: i for i in db.scalars(select(Injury).where(Injury.user_id == user_id, Injury.status != "resolved"))}
    wanted = {i.region: i for i in answers.injuries}
    for region, row in existing.items():
        if region not in wanted:
            db.delete(row)
    for region, given in wanted.items():
        row = existing.get(region) or Injury(user_id=user_id, region=region, since=clock.today(), created_at=now)
        row.side, row.type, row.severity = given.side, given.type, given.severity
        row.painful_movements, row.restrictions, row.updated_at = given.painful_movements, given.restrictions, now
        db.add(row)
    _advance(p, "injuries")
    db.flush()
    return injuries(db, user_id)


def injuries(db: Session, user_id: str) -> list[Injury]:
    return list(db.scalars(select(Injury).where(Injury.user_id == user_id, Injury.status != "resolved").order_by(Injury.created_at)))


def missing_steps(db: Session, p: Profile) -> list[str]:
    missing = []
    for step in STEPS:
        if step == "injuries":
            if not _reached(p, "injuries"):
                missing.append(step)
        elif any(getattr(p, f) is None for f in REQUIRED.get(step, FIELDS[step])):
            missing.append(step)
    return missing


def complete(db: Session, user_id: str) -> Profile:
    p = _profile(db, user_id)
    if missing := missing_steps(db, p):
        raise Incomplete(missing)
    if p.completed_at is None:
        p.completed_at = clock.now()
    p.onboarding_step = "review"
    db.flush()
    return p


def state(db: Session, user_id: str) -> OnboardingOut:
    p = _profile(db, user_id)

    def step(name: str):
        if any(getattr(p, f) is None for f in REQUIRED.get(name, FIELDS[name])):
            return None
        return MODELS[name].model_validate({f: getattr(p, f) for f in FIELDS[name]})

    return OnboardingOut(
        step=p.onboarding_step, completed=p.completed_at is not None, missing=missing_steps(db, p),
        conservative=p.conservative, about=step("about"), goal=step("goal"), training=step("training"),
        injuries=[InjuryOut.model_validate(i) for i in injuries(db, user_id)], injuries_answered=_reached(p, "injuries"),
        health=step("health"), food=step("food"),
    )
