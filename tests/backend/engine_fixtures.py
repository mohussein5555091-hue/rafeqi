"""Shared inputs for the plan engine tests: the exercise catalogue read straight from the YAML file."""

from functools import lru_cache

from app.catalogue import read_exercises
from app.config import get_settings
from app.engine.types import ExerciseInfo
from app.vocab import get_vocab


@lru_cache
def exercise_catalogue() -> dict[str, ExerciseInfo]:
    items = read_exercises(get_settings().catalogue_dir / "exercises.yaml", get_vocab())
    return {e["id"]: ExerciseInfo(id=e["id"], name=e["name"], pattern=e["movement_pattern"], joints=tuple(e["joints_loaded"]),
                                  rom=e["range_of_motion"], equipment=tuple(e["equipment"]), difficulty=e["difficulty"],
                                  type=e.get("type", "strength"), muscles=tuple(e.get("primary_muscles") or ()))
            for e in items}


@lru_cache
def food_catalogue() -> dict:
    from app.food_catalogue import read_food_catalogue

    return read_food_catalogue(get_settings().catalogue_dir)


@lru_cache
def recipe_infos() -> tuple:
    from app.engine.catalogue import recipes_from_catalogue

    return tuple(recipes_from_catalogue(food_catalogue()))
