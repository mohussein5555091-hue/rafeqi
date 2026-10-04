"""The onboarding questionnaire: one PUT per step (saved as you go), then complete."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app import clock, onboarding
from app.api.deps import CurrentAuth, Db
from app.models import Profile, WeightLog
from app.schemas.onboarding import AboutIn, FoodIn, GoalIn, HealthIn, InjuriesIn, OnboardingOut, TrainingIn
from app.weights import record_weight

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("", response_model=OnboardingOut)
def get_onboarding(auth: CurrentAuth, db: Db):
    """Everything answered so far and the step to resume at."""
    return onboarding.state(db, auth.user.id)


def _save(db, user_id: str, step: str, body) -> OnboardingOut:
    onboarding.save_step(db, user_id, step, body)
    db.commit()
    return onboarding.state(db, user_id)


@router.put("/about", response_model=OnboardingOut)
def save_about(body: AboutIn, auth: CurrentAuth, db: Db):
    return _save(db, auth.user.id, "about", body)


@router.put("/goal", response_model=OnboardingOut)
def save_goal(body: GoalIn, auth: CurrentAuth, db: Db):
    return _save(db, auth.user.id, "goal", body)


@router.put("/training", response_model=OnboardingOut)
def save_training(body: TrainingIn, auth: CurrentAuth, db: Db):
    return _save(db, auth.user.id, "training", body)


@router.put("/injuries", response_model=OnboardingOut)
def save_injuries(body: InjuriesIn, auth: CurrentAuth, db: Db):
    onboarding.save_injuries(db, auth.user.id, body)
    db.commit()
    return onboarding.state(db, auth.user.id)


@router.put("/health", response_model=OnboardingOut)
def save_health(body: HealthIn, auth: CurrentAuth, db: Db):
    return _save(db, auth.user.id, "health", body)


@router.put("/food", response_model=OnboardingOut)
def save_food(body: FoodIn, auth: CurrentAuth, db: Db):
    return _save(db, auth.user.id, "food", body)


@router.post("/complete", response_model=OnboardingOut)
def complete(auth: CurrentAuth, db: Db):
    """Marks onboarding done (422 listing the missing steps otherwise). The plan is built from here in Phase 4."""
    try:
        onboarding.complete(db, auth.user.id)
    except onboarding.Incomplete as e:
        raise HTTPException(422, {"error": "onboarding_incomplete", "missing": e.missing}) from e
    # The questionnaire weight is the first point on the weight chart.
    if db.scalar(select(WeightLog.id).where(WeightLog.user_id == auth.user.id).limit(1)) is None:
        record_weight(db, auth.user.id, clock.today(), db.get(Profile, auth.user.id).weight_kg, "daily")
    db.commit()
    return onboarding.state(db, auth.user.id)
