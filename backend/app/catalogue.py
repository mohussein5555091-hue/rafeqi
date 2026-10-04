"""Loads the shared catalogue from data/catalogue/ into the database.

    uv run python -m app.catalogue          (or: npm run db:seed)

Everything is validated first (tags against data/vocab/movements.yaml, both languages present,
3 to 5 cues…). If anything is wrong nothing is written, and every problem is listed.
Safe to run again: existing rows are updated in place.
"""

import sys
from pathlib import Path

import yaml
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Exercise, ExerciseSubstitution
from app.vocab import Vocab, VocabError, get_vocab

DIFFICULTIES = {"beginner", "intermediate", "advanced"}
ALT_KINDS = {"easier", "injuryFriendly", "equipment"}
TYPES = {"strength", "cardio", "mobility", "stretch"}


class CatalogueError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def _bilingual(value: object) -> bool:
    return isinstance(value, dict) and bool(str(value.get("en", "")).strip()) and bool(str(value.get("ar", "")).strip())


def validate_exercises(items: list[dict], vocab: Vocab) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    ids = {e.get("id") for e in items}
    for e in items:
        where = f"exercise {e.get('id', '?')}"
        if e.get("id") in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(e.get("id"))
        try:
            vocab.check_exercise(e)
        except (VocabError, KeyError) as err:
            problems.append(str(err) if isinstance(err, VocabError) else f"{where}: missing {err}")
        for field in ("name", "description", "muscle_names"):
            if not _bilingual(e.get(field)):
                problems.append(f"{where}: {field} needs en and ar")
        for field in ("instructions", "cues", "mistakes"):
            lst = e.get(field) or []
            if not lst or not all(_bilingual(x) for x in lst):
                problems.append(f"{where}: {field} must be a non-empty list of {{en, ar}}")
        if not 3 <= len(e.get("cues") or []) <= 5:
            problems.append(f"{where}: needs 3 to 5 cues, has {len(e.get('cues') or [])}")
        if e.get("type", "strength") not in TYPES:
            problems.append(f"{where}: type must be one of {sorted(TYPES)}")
        if e.get("difficulty") not in DIFFICULTIES:
            problems.append(f"{where}: difficulty must be one of {sorted(DIFFICULTIES)}")
        for alt in e.get("alternatives") or []:
            if alt.get("kind") not in ALT_KINDS:
                problems.append(f"{where}: alternative kind must be one of {sorted(ALT_KINDS)}")
            if alt.get("exercise_id") and alt["exercise_id"] not in ids:
                problems.append(f"{where}: alternative points at unknown exercise {alt['exercise_id']}")
    return problems


def read_exercises(path: Path, vocab: Vocab) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        items = (yaml.safe_load(f) or {}).get("exercises") or []
    problems = validate_exercises(items, vocab)
    if problems:
        raise CatalogueError(problems)
    return items


def seed_exercises(db: Session, items: list[dict]) -> int:
    for e in items:
        row = db.get(Exercise, e["id"]) or Exercise(id=e["id"])
        row.name_en, row.name_ar = e["name"]["en"], e["name"]["ar"]
        row.description_en, row.description_ar = e["description"]["en"], e["description"]["ar"]
        row.movement_pattern, row.joints_loaded = e["movement_pattern"], e["joints_loaded"]
        row.range_of_motion, row.equipment, row.difficulty = e["range_of_motion"], e["equipment"], e["difficulty"]
        row.primary_muscles, row.secondary_muscles = e.get("primary_muscles", []), e.get("secondary_muscles", [])
        row.muscle_names_en, row.muscle_names_ar = e["muscle_names"]["en"], e["muscle_names"]["ar"]
        row.instructions, row.cues, row.mistakes = e["instructions"], e["cues"], e["mistakes"]
        row.image_url, row.image_frames, row.video_url = e.get("image_url"), e.get("image_frames", []), e.get("video_url")
        row.media_source, row.source = e.get("media_source"), e.get("source", "")
        row.type = e.get("type", "strength")
        db.merge(row)
    db.flush()
    # Substitutions are rebuilt from the file each time.
    db.execute(delete(ExerciseSubstitution).where(ExerciseSubstitution.exercise_id.in_([e["id"] for e in items])))
    for e in items:
        for priority, alt in enumerate(e.get("alternatives") or []):
            db.add(ExerciseSubstitution(exercise_id=e["id"], substitute_id=alt.get("exercise_id"), kind=alt["kind"],
                                        name_en=alt["name"]["en"], name_ar=alt["name"]["ar"], priority=priority))
    return len(items)


def main() -> int:
    from app.db import SessionLocal

    path = get_settings().catalogue_dir / "exercises.yaml"
    try:
        items = read_exercises(path, get_vocab())
    except CatalogueError as err:
        print(f"Catalogue not loaded. Fix these in {path}:", file=sys.stderr)
        for p in err.problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    from app.food_catalogue import read_food_catalogue, seed_food_catalogue

    try:
        food = read_food_catalogue(get_settings().catalogue_dir)
    except CatalogueError as err:
        print(f"Food catalogue not loaded. Fix these in {get_settings().catalogue_dir}:", file=sys.stderr)
        for p in err.problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        n = seed_exercises(db, items)
        foods, grocery, recipes = seed_food_catalogue(db, food)
        db.commit()
    print(f"Loaded {n} exercises, {foods} foods, {grocery} grocery items and {recipes} recipes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
