"""Plain inputs and outputs shared by the engine modules."""

import datetime as dt
from dataclasses import dataclass, field

Text = dict[str, str]  # {"en": …, "ar": …}


@dataclass(frozen=True)
class Reason:
    """One line explaining a decision: which rule, from which source, in both languages."""

    rule: str
    en: str
    ar: str
    source: str = ""

    def as_dict(self) -> dict:
        return {"rule": self.rule, "en": self.en, "ar": self.ar, "source": self.source}


@dataclass(frozen=True)
class Health:
    heart_condition: bool = False
    diabetes: bool = False
    pregnancy: bool = False
    recent_surgery: bool = False
    exercise_medication: bool = False

    def yes(self) -> list[str]:
        return [k for k, v in self.__dict__.items() if v]


@dataclass(frozen=True)
class InjuryInfo:
    id: str
    region: str
    status: str = "active"  # active | recovering | resolved
    severity: int = 2
    painful_movements: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    paused: bool = False  # a red flag paused this area


@dataclass(frozen=True)
class Person:
    """The questionnaire answers the engine needs."""

    sex: str
    age: int
    height_cm: float
    weight_kg: float
    goal: str
    pace: str
    experience: str
    days_per_week: int
    session_minutes: int
    location: str
    meals_per_day: int
    cooking_minutes: int
    health: Health = field(default_factory=Health)
    dislikes: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    fasting: tuple[str, ...] = ()
    injuries: tuple[InjuryInfo, ...] = ()
    missing_equipment: tuple[str, ...] = ()  # "Equipment not available" from an exercise swap

    @property
    def conservative(self) -> bool:
        return bool(self.health.yes())

    @property
    def avoided_food_tags(self) -> set[str]:
        return set(self.dislikes) | (set(self.allergies) - {"none"})


@dataclass(frozen=True)
class ExerciseInfo:
    id: str
    name: Text
    pattern: str
    joints: tuple[str, ...]
    rom: str
    equipment: tuple[str, ...]
    difficulty: str
    type: str = "strength"  # strength | cardio | mobility | stretch
    muscles: tuple[str, ...] = ()  # primary muscles (body regions)


@dataclass(frozen=True)
class RecipeInfo:
    id: str
    name: Text
    slots: tuple[str, ...]
    prep_min: int
    cook_min: int
    batch: int
    tags: frozenset[str]
    kcal: float  # per serving
    protein: float
    carbs: float
    fat: float
    ingredients: tuple[tuple[str, float], ...]  # (food_id, grams per serving)


@dataclass(frozen=True)
class GroceryItemInfo:
    id: str
    name: Text
    category: str
    shelf_life: str
    unit: str
    pack_size: float
    grams_per_unit: float


def week_dates(start: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range(7)]
