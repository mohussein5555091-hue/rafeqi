"""The onboarding questionnaire, one model per step. Ranges match the frontend's pickers.
Food and allergy ids must match frontend/src/constants.ts (FOODS, ALLERGIES); tests/backend/test_onboarding.py checks."""

from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import ApiModel
from app.schemas.injuries import BodyRegion, InjuryIn

STEPS = ("about", "goal", "training", "injuries", "health", "food")  # then "review" (frontend only)
FOODS = ("liver", "eggplant", "okra", "fish", "mushrooms", "lentils", "beef", "dairy")
ALLERGIES = ("none", "nuts", "lactose", "gluten", "eggs", "shellfish", "sesame")

Goal = Literal["loseFat", "buildMuscle", "recomp", "strength"]
Pace = Literal["gentle", "steady", "faster"]
Experience = Literal["beginner", "intermediate", "advanced"]
Location = Literal["gym", "homeDumbbells", "bodyweight"]
# Outside training: mostly sitting / on my feet part of the day / a physically active job (the recomposition guide's
# activity levels, Table 5B: data/rules/nutrition.yaml activity).
DailyActivity = Literal["sitting", "onFeet", "active"]


class AboutIn(ApiModel):
    sex: Literal["male", "female"]
    age: int
    height_cm: float = Field(ge=130, le=220)
    weight_kg: float = Field(ge=35, le=250)
    waist_cm: float | None = Field(default=None, ge=50, le=180)

    @field_validator("age")
    @classmethod
    def _adult(cls, v: int) -> int:
        if v < 18:
            raise ValueError("must_be_adult")
        if v > 90:
            raise ValueError("age_out_of_range")
        return v


class GoalIn(ApiModel):
    goal: Goal
    pace: Pace


class TrainingIn(ApiModel):
    experience: Experience
    days_per_week: int = Field(ge=2, le=6)
    session_minutes: Literal[45, 60, 75, 90]
    location: Location
    daily_activity: DailyActivity  # required whenever the step is saved (onboarding, or editing it from Profile)


class TrainingOut(TrainingIn):
    """The saved answers: daily_activity is empty for people who answered before the question existed."""

    daily_activity: DailyActivity | None = None


class InjuriesIn(ApiModel):
    """The full list: regions left out are removed. An empty list means "no injuries"."""

    injuries: list[InjuryIn] = Field(default_factory=list, max_length=10)

    @field_validator("injuries")
    @classmethod
    def _one_per_region(cls, v: list[InjuryIn]) -> list[InjuryIn]:
        regions = [i.region for i in v]
        if len(regions) != len(set(regions)):
            raise ValueError("one_injury_per_region")
        return v


class HealthIn(ApiModel):
    heart_condition: bool
    diabetes: bool
    pregnancy: bool
    recent_surgery: bool
    exercise_medication: bool


class FoodIn(ApiModel):
    meals_per_day: int = Field(ge=2, le=5)
    dislikes: list[str] = Field(default_factory=list, max_length=len(FOODS))
    allergies: list[str] = Field(default_factory=list, max_length=len(ALLERGIES))
    fasting: list[Literal["ramadan", "intermittent"]] = Field(default_factory=list, max_length=2)
    cooking_minutes: Literal[15, 30, 60]

    @field_validator("dislikes")
    @classmethod
    def _foods(cls, v: list[str]) -> list[str]:
        if bad := [x for x in v if x not in FOODS]:
            raise ValueError(f"unknown_food: {', '.join(bad)}")
        return list(dict.fromkeys(v))

    @field_validator("allergies")
    @classmethod
    def _allergies(cls, v: list[str]) -> list[str]:
        if bad := [x for x in v if x not in ALLERGIES]:
            raise ValueError(f"unknown_allergy: {', '.join(bad)}")
        if "none" in v and len(v) > 1:
            raise ValueError("none_with_allergies")
        return list(dict.fromkeys(v))

    @field_validator("fasting")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class InjuryOut(ApiModel):
    id: str
    region: BodyRegion
    side: str
    type: str
    severity: int
    status: str
    painful_movements: list[str]
    restrictions: list[str]


class OnboardingOut(ApiModel):
    """Everything answered so far (null = not answered yet), and where to pick up."""

    step: str  # the next step to show
    completed: bool
    missing: list[str]  # steps that must be answered before completing
    conservative: bool  # any health answer "yes": lighter loads, lower effort, more rest
    about: AboutIn | None
    goal: GoalIn | None
    training: TrainingOut | None
    injuries: list[InjuryOut]
    injuries_answered: bool
    health: HealthIn | None
    food: FoodIn | None
