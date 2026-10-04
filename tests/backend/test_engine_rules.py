"""The rule files and program templates: every rule says where it comes from, placeholders are marked, and the
program templates only use exercises from the catalogue."""

import json

import pytest
import yaml

from app.config import get_settings
from app.engine.rules import FILES, RulesError, _check_sources, load_rules, load_templates, rules_version
from engine_fixtures import exercise_catalogue


def test_rule_files_load_and_every_rule_has_a_source():
    rules = load_rules()
    assert set(rules) == set(FILES)
    for name in ("nutrition", "training", "safety"):
        for key, section in rules[name].items():
            if isinstance(section, dict) and ("placeholder" in section or "explain" in section):
                assert section["source"], f"{name}.{key}"
    assert rules_version().startswith("nutrition:v1")


def test_placeholders_are_clearly_marked():
    """Until the values are extracted from the books, every book-based number says so."""
    rules = load_rules()
    marked = [f"{n}.{k}" for n in ("nutrition", "training", "safety") for k, s in rules[n].items()
              if isinstance(s, dict) and s.get("placeholder")]
    assert {"nutrition.activity", "nutrition.protein", "safety.calorie_floor", "training.start_load"} <= set(marked)
    for n in ("nutrition", "training", "safety"):
        for k, s in rules[n].items():
            if isinstance(s, dict) and s.get("placeholder"):
                assert "PLACEHOLDER" in s["source"], f"{n}.{k}: placeholder sources start with PLACEHOLDER"


def test_a_rule_without_a_source_is_refused():
    assert _check_sources("nutrition", {"fat": {"placeholder": True, "min_g_per_kg": 1}}) == [
        "nutrition.yaml: 'fat' needs a source (book + chapter/page)"]
    assert "explain needs en and ar" in _check_sources("x", {"y": {"source": "s", "explain": {"en": "only English"}}})[0]


def test_program_templates_only_use_catalogue_exercises():
    catalogue = exercise_catalogue()
    for t in load_templates():
        assert t["placeholder"] is True and "PLACEHOLDER" in t["source"]
        for day in t["days"]:
            for ex in day["exercises"]:
                assert ex["exercise"] in catalogue, f"{t['id']}: {ex['exercise']}"


def test_a_template_with_a_broken_rotation_is_refused(tmp_path, monkeypatch):
    bad = json.loads((get_settings().programs_dir / "sample_full_body.json").read_text(encoding="utf-8"))
    bad["rotation"]["3"] = ["A", "B", "C"]
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(get_settings(), "programs_dir", tmp_path)
    load_templates.cache_clear()
    try:
        with pytest.raises(RulesError, match="rotation for 3 days"):
            load_templates()
    finally:
        load_templates.cache_clear()


def test_schedules_cover_every_answerable_number_of_days():
    tr = load_rules()["training"]
    for days in range(2, 7):
        assert len(tr["schedules"][days]) == days and "fri" not in tr["schedules"][days]


def test_safety_names_every_body_area():
    s = load_rules()["safety"]
    from app.engine.checkin import REGIONS
    assert set(s["region_joints"]) == REGIONS == set(s["region_names"])


def test_checkin_questions_file_is_valid():
    from app.engine.checkin import load_questions
    data = load_questions()
    assert [q["id"] for q in data["questions"] if q.get("red_flag")] == ["sharp_pain", "swelling", "numbness"]
    raw = yaml.safe_load((get_settings().rules_dir.parent / "checkin_questions.yaml").read_text(encoding="utf-8"))
    assert raw == data
