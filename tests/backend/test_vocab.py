"""Movement and joint tags must come from data/vocab/movements.yaml: on injuries, exercises and in the frontend."""

import copy
import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.catalogue import CatalogueError, read_exercises, seed_exercises, validate_exercises
from app.config import get_settings
from app.models import Exercise, ExerciseSubstitution
from app.schemas.injuries import InjuryIn
from app.vocab import CATEGORIES, Vocab, VocabError, get_vocab

ROOT = Path(__file__).resolve().parents[2]


def raw_vocab() -> dict:
    return yaml.safe_load(get_settings().vocab_file.read_text(encoding="utf-8"))


def test_vocab_file_is_complete_and_bilingual():
    v = get_vocab()  # raises if any label is missing or an `excludes` points at an unknown tag
    for cat in CATEGORIES:
        assert v.ids(cat), cat
        for tag in v.ids(cat):
            assert re.fullmatch(r"[a-z][A-Za-z]*", tag), f"{cat}.{tag}: ids are camelCase letters"


def test_vocab_rejects_a_reference_to_an_unknown_tag():
    data = raw_vocab()
    data["painful_movements"]["squat"]["excludes"]["movement_patterns"] = ["squatt"]
    with pytest.raises(VocabError, match="unknown movement_patterns 'squatt'"):
        Vocab(data)


def test_vocab_rejects_a_missing_arabic_label():
    data = raw_vocab()
    del data["joints"]["knee"]["ar"]
    with pytest.raises(VocabError, match="joints.knee"):
        Vocab(data)


def test_frontend_options_only_use_vocab_ids():
    src = (ROOT / "frontend" / "src" / "constants.ts").read_text(encoding="utf-8")

    def ids(const: str) -> set[str]:
        body = re.search(rf"export const {const} = \[(.*?)\]", src, re.S).group(1)
        return set(re.findall(r"'([^']+)'", body))

    v = get_vocab()
    assert ids("MOVEMENTS") <= v.ids("painful_movements"), ids("MOVEMENTS") - v.ids("painful_movements")
    assert ids("RESTRICTIONS") <= v.ids("restrictions"), ids("RESTRICTIONS") - v.ids("restrictions")


# ── Injuries: checked when saved ────────────────────────────────────────────────
GOOD_INJURY = {"region": "shoulderL", "side": "left", "type": "tendon", "severity": 3,
               "painfulMovements": ["overheadPress", "benchPress"], "restrictions": ["noOverhead"]}


def test_injury_with_known_tags_is_accepted():
    inj = InjuryIn.model_validate(GOOD_INJURY)
    assert inj.painful_movements == ["overheadPress", "benchPress"]


@pytest.mark.parametrize("field,value", [("painfulMovements", ["overheadPres"]), ("restrictions", ["noJumping"])])
def test_injury_with_unknown_tag_is_rejected_naming_the_tag(field, value):
    with pytest.raises(ValidationError, match=value[0]):
        InjuryIn.model_validate(GOOD_INJURY | {field: value})


# ── Exercise catalogue: checked when loaded ─────────────────────────────────────
def catalogue() -> list[dict]:
    return read_exercises(get_settings().catalogue_dir / "exercises.yaml", get_vocab())


def test_catalogue_file_is_valid():
    items = catalogue()
    assert len(items) >= 7


@pytest.mark.parametrize("field,bad", [
    ("movement_pattern", "pressing"), ("joints_loaded", ["shoulder", "elbw"]),
    ("range_of_motion", "huge"), ("equipment", ["kettlebel"]),
])
def test_catalogue_with_unknown_tag_is_refused_naming_exercise_and_tag(field, bad):
    items = copy.deepcopy(catalogue())
    items[0][field] = bad
    problems = validate_exercises(items, get_vocab())
    wrong = bad if isinstance(bad, str) else bad[-1]
    assert any(items[0]["id"] in p and wrong in p for p in problems), problems


def test_catalogue_other_checks():
    items = copy.deepcopy(catalogue())
    items[1]["cues"] = items[1]["cues"][:2]
    items[2]["name"] = {"en": "Only English"}
    items[3]["id"] = items[4]["id"]
    problems = "\n".join(validate_exercises(items, get_vocab()))
    assert "needs 3 to 5 cues" in problems and "name needs en and ar" in problems and "duplicate id" in problems


def test_an_alternative_that_needs_no_equipment_is_labelled_so():
    """Arm circles for a band pull-apart is "No equipment needed", not "Other equipment"."""
    items = copy.deepcopy(catalogue())
    band = next(e for e in items if e["id"] == "ex_band_pull_apart")
    assert band["alternatives"][0] == band["alternatives"][0] | {"exercise_id": "ex_arm_circles", "kind": "noEquipment"}
    band["alternatives"][0]["kind"] = "equipment"
    problems = "\n".join(validate_exercises(items, get_vocab()))
    assert "ex_band_pull_apart" in problems and "ex_arm_circles needs no equipment" in problems


def test_bad_catalogue_writes_nothing(tmp_path, db):
    items = copy.deepcopy(catalogue())
    items[0]["movement_pattern"] = "pressing"
    bad = tmp_path / "exercises.yaml"
    bad.write_text(yaml.safe_dump({"exercises": items}, allow_unicode=True), encoding="utf-8")
    with pytest.raises(CatalogueError):
        read_exercises(bad, get_vocab())
    assert db.query(Exercise).count() == 0


def test_seeding_twice_gives_the_same_rows(db):
    items = catalogue()
    seed_exercises(db, items)
    db.commit()
    seed_exercises(db, items)
    db.commit()
    assert db.query(Exercise).count() == len(items)
    assert db.query(ExerciseSubstitution).count() == sum(len(e.get("alternatives", [])) for e in items)
    press = db.get(Exercise, "ex_landmine_press")
    assert press.movement_pattern == "verticalPush" and press.media_source["license"].startswith("Unlicense")
