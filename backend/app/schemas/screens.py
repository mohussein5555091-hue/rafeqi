"""Request bodies for the workout, meal, grocery, injury and check-in endpoints (camelCase JSON, like types.ts)."""

import datetime as dt
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.injuries import BodyRegion, InjuryIn

Scale5 = Field(ge=1, le=5)


class ExerciseResultIn(ApiModel):
    sets: int = Field(ge=0, le=20)
    reps: int = Field(ge=0, le=100)
    weight_kg: float = Field(ge=0, le=500)
    struggled: bool = False


class PainIn(ApiModel):
    injury_id: str = Field(max_length=36)
    pain: int = Field(ge=0, le=10)


class FinishWorkoutIn(ApiModel):
    effort: int = Field(ge=1, le=10)  # "How hard was today's workout?"
    pain: list[PainIn] = Field(default_factory=list, max_length=10)
    red_flags: list[Literal["sharpPain", "swelling", "numbness"]] = Field(default_factory=list, max_length=3)
    # The exercises done. Left out = every exercise not logged yet is saved as done as planned; given = the others were skipped.
    done: list[str] | None = Field(default=None, max_length=30)


class SwapExerciseIn(ApiModel):
    """Swap an exercise: to one of its alternatives, with why, for today's session only or from now on."""

    to_exercise_id: str = Field(max_length=60)
    reason: Literal["equipment", "busy", "cantDo", "pain"]
    scope: Literal["today", "always"]


class DoneIn(ApiModel):
    done: bool


class CardioDoneIn(ApiModel):
    minutes: int = Field(ge=1, le=300)


class SwapIn(ApiModel):
    recipe_id: str = Field(max_length=60)


class RemoveIngredientIn(ApiModel):
    reason: Literal["dislike", "unavailable"]  # "I don't like it" / "Not available right now"
    scope: Literal["meal", "always"]  # "Just this meal" / "Always"
    replacement_food_id: str | None = Field(default=None, max_length=60)  # one of the replacements offered, or none


class GroceryPatchIn(ApiModel):
    checked: bool | None = None
    have_it: bool | None = None


class InjurySaveIn(InjuryIn):
    status: Literal["active", "recovering", "resolved"] = "active"


# ── The weekly check-in, as the screen sends it (types.ts CheckIn). Ranges are checked again against
#    data/checkin_questions.yaml, which is the source of truth for the questions. ──

class MeasurementsIn(ApiModel):
    waist: float | None = None
    hips: float | None = None
    chest: float | None = None
    arm: float | None = None
    thigh: float | None = None


class BodyIn(ApiModel):
    weight_kg: float
    measurements_cm: MeasurementsIn = MeasurementsIn()
    photos: dict[str, str] = Field(default_factory=dict)  # photo upload comes in Phase 6; ignored for now


class FeedbackIn(ApiModel):
    exercise_id: str = Field(max_length=60)
    feel: Literal["tooEasy", "tooHard", "uncomfortable"]


class TrainingIn(ApiModel):
    sessions_done: int
    sessions_planned: int
    difficulty: int = Scale5
    soreness: int = Scale5
    exercise_feedback: list[FeedbackIn] = Field(default_factory=list, max_length=30)


class InjuryCheckIn(ApiModel):
    injury_id: str = Field(max_length=36)
    pain: int = Field(ge=0, le=10)
    trend: Literal["better", "same", "worse"]


class RedFlagsIn(ApiModel):
    sharp_pain: bool
    swelling: bool
    numbness: bool


class NutritionIn(ApiModel):
    adherence_pct: float
    hunger: int = Scale5
    meals_to_change: list[str] = Field(default_factory=list, max_length=30)
    more_of: list[str] = Field(default_factory=list, max_length=20)
    less_of: list[str] = Field(default_factory=list, max_length=20)


class LifeIn(ApiModel):
    sleep: int = Scale5
    energy: int = Scale5
    stress: int = Scale5
    days_available: int
    obstacles: list[str] = Field(default_factory=list, max_length=10)


class CheckInIn(ApiModel):
    id: str | None = None
    week_number: int | None = None
    submitted_at: str | None = None
    body: BodyIn
    training: TrainingIn
    injuries: list[InjuryCheckIn] = Field(default_factory=list, max_length=10)
    new_pain_regions: list[BodyRegion] = Field(default_factory=list, max_length=22)
    red_flags: RedFlagsIn
    nutrition: NutritionIn
    life: LifeIn
    note: str | None = Field(default=None, max_length=300)  # the one free-text answer


class MoveWorkoutIn(ApiModel):
    """Move an upcoming session to this date (this week; today for "Do this workout today")."""

    date: dt.date
