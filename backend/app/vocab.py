"""The controlled vocabulary of movement and joint tags (data/vocab/movements.yaml).

Every exercise tag and injury tag must be an id from this file. `check_*` functions raise
VocabError naming the bad value, and are used when saving injuries and loading the catalogue.
"""

from functools import lru_cache
from pathlib import Path

import yaml

from app.config import get_settings

CATEGORIES = ("movement_patterns", "joints", "ranges_of_motion", "equipment", "painful_movements", "restrictions")
EXCLUDE_KEYS = {"movement_patterns", "ranges_of_motion", "joint_of_injury"}


class VocabError(ValueError):
    pass


class Vocab:
    def __init__(self, data: dict):
        self.data = data
        missing = [c for c in CATEGORIES if not isinstance(data.get(c), dict) or not data[c]]
        if missing:
            raise VocabError(f"vocab file is missing categories: {', '.join(missing)}")
        for cat in CATEGORIES:
            for tag, entry in data[cat].items():
                if not isinstance(entry, dict) or not entry.get("en") or not entry.get("ar"):
                    raise VocabError(f"{cat}.{tag} needs both an English (en) and an Arabic (ar) label")
        # Painful movements finish the sentence "it involves …" in the reasons.
        for tag, entry in data["painful_movements"].items():
            phrase = entry.get("phrase") or {}
            if not phrase.get("en") or not phrase.get("ar"):
                raise VocabError(f"painful_movements.{tag} needs a phrase (en and ar) for the reasons")
        # Injury tags may only point at tags that exist.
        for cat in ("painful_movements", "restrictions"):
            for tag, entry in data[cat].items():
                excludes = entry.get("excludes") or {}
                unknown = set(excludes) - EXCLUDE_KEYS
                if unknown:
                    raise VocabError(f"{cat}.{tag}.excludes has unknown keys: {sorted(unknown)}")
                for ref_cat in ("movement_patterns", "ranges_of_motion"):
                    for ref in excludes.get(ref_cat, []):
                        if ref not in data[ref_cat]:
                            raise VocabError(f"{cat}.{tag} refers to unknown {ref_cat} '{ref}'")

    def injury_tag(self, tag: str) -> tuple[str, dict]:
        """("painful", its phrase) or ("restriction", its label): how a reason names what ruled an exercise out."""
        if tag in self.data["painful_movements"]:
            return "painful", self.data["painful_movements"][tag]["phrase"]
        label = self.data["restrictions"][tag]
        return "restriction", {"en": label["en"], "ar": label["ar"]}

    def ids(self, category: str) -> set[str]:
        return set(self.data[category])

    def check(self, category: str, values: str | list[str], where: str) -> None:
        values = [values] if isinstance(values, str) else list(values)
        unknown = [v for v in values if v not in self.data[category]]
        if unknown:
            raise VocabError(f"{where}: unknown {category} {unknown}. Allowed: {sorted(self.data[category])}")

    def check_injury(self, painful_movements: list[str], restrictions: list[str], where: str = "injury") -> None:
        self.check("painful_movements", painful_movements, where)
        self.check("restrictions", restrictions, where)

    def check_exercise(self, ex: dict) -> None:
        where = f"exercise {ex.get('id', '?')}"
        self.check("movement_patterns", ex["movement_pattern"], where)
        self.check("joints", ex["joints_loaded"], where)
        self.check("ranges_of_motion", ex["range_of_motion"], where)
        self.check("equipment", ex["equipment"], where)


def load_vocab(path: Path) -> Vocab:
    with open(path, encoding="utf-8") as f:
        return Vocab(yaml.safe_load(f))


@lru_cache
def get_vocab() -> Vocab:
    return load_vocab(get_settings().vocab_file)
