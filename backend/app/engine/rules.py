"""The rule files (data/rules/*.yaml) and the program templates (data/programs/*.json).

Every rule section with numbers must say where they come from (`source`) and whether they're still placeholders.
`explain()` fills a rule's one-line explanation, in English and Arabic, with the numbers used.
"""

import json
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import get_settings
from app.engine.types import Reason

FILES = ("nutrition", "training", "safety", "progression")


class RulesError(ValueError):
    pass


def _check_sources(name: str, data: dict) -> list[str]:
    problems = []
    for key, section in data.items():
        if isinstance(section, dict) and ("placeholder" in section or "explain" in section) and not section.get("source"):
            problems.append(f"{name}.yaml: '{key}' needs a source (book + chapter/page)")
        if isinstance(section, dict) and "explain" in section:
            problems += _check_explain(f"{name}.{key}", section["explain"])
    return problems


def _check_explain(where: str, explain: dict) -> list[str]:
    if "en" in explain or "ar" in explain:
        return [] if explain.get("en") and explain.get("ar") else [f"{where}: explain needs en and ar"]
    problems = []
    for k, v in explain.items():
        problems += _check_explain(f"{where}.{k}", v) if isinstance(v, dict) else [f"{where}.{k}: explain needs en and ar"]
    return problems


@lru_cache
def load_rules() -> dict[str, dict]:
    folder = get_settings().rules_dir
    rules, problems = {}, []
    for name in FILES:
        rules[name] = yaml.safe_load((folder / f"{name}.yaml").read_text(encoding="utf-8")) or {}
        problems += _check_sources(name, rules[name])
    if problems:
        raise RulesError("\n".join(problems))
    return rules


def rules_version() -> str:
    r = load_rules()
    return "+".join(f"{n}:v{r[n].get('version', 0)}" for n in FILES)


def explain(section: dict, rule: str, template: dict | None = None, **values) -> Reason:
    """One reason line from a rule section, e.g. explain(rules["nutrition"]["fat"], "nutrition.fat", fat=70, …)."""
    t = template or section["explain"]
    return Reason(rule=rule, en=t["en"].format(**values), ar=t["ar"].format(**values), source=section.get("source", ""))


@lru_cache
def load_templates() -> tuple[dict, ...]:
    folder: Path = get_settings().programs_dir
    templates = []
    for path in sorted(folder.glob("*.json")):
        t = json.loads(path.read_text(encoding="utf-8"))
        keys = {d["key"] for d in t["days"]}
        for n, rotation in t["rotation"].items():
            if int(n) not in t["days_per_week"] or not set(rotation) <= keys or len(rotation) != int(n):
                raise RulesError(f"{path.name}: rotation for {n} days doesn't match its days")
        if not t.get("source"):
            raise RulesError(f"{path.name}: needs a source")
        templates.append(t)
    if not templates:
        raise RulesError(f"no program templates in {folder}")
    return tuple(templates)
