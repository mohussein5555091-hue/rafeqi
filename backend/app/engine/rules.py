"""The rule files (data/rules/*.yaml) and the program templates (data/programs/*.json).

Every rule section with numbers must say where they come from (`source`) and whether they're still placeholders.
`explain()` fills a rule's one-line explanation, in English and Arabic, with the numbers used.

For the "Why this plan" page (app/views/why.py) every rule section that explains something also has:
- `summary`: the rule in plain language ({en, ar}, or one per sub-rule, e.g. goal.summary.loseFat);
- `uses`: the questionnaire answers it reads (Person field names; `checkin` and `swaps` for the weekly check-in and the
  person's own exercise swaps), a list or one list per sub-rule;
- `ref` once it's no longer a placeholder: {book, chapter, page, quote: {en, ar}}, the quote at most 2 sentences.
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


ROOT_SECTION = ("progression",)  # files that are one rule section as a whole


def _check_sources(name: str, data: dict) -> list[str]:
    problems = []
    sections = [("(the whole file)", data)] if name in ROOT_SECTION else list(data.items())
    for key, section in sections:
        if isinstance(section, dict) and ("placeholder" in section or "explain" in section) and not section.get("source"):
            problems.append(f"{name}.yaml: '{key}' needs a source (book + chapter/page)")
        if isinstance(section, dict) and "explain" in section:
            problems += _check_explain(f"{name}.{key}", section["explain"])
            problems += _check_why(f"{name}.yaml: '{key}'", section)
    return problems


def _bilingual_tree(value: object) -> bool:
    """{en, ar}, or a dict of those (one per sub-rule)."""
    if isinstance(value, dict) and ("en" in value or "ar" in value):
        return bool(value.get("en")) and bool(value.get("ar"))
    return isinstance(value, dict) and bool(value) and all(_bilingual_tree(v) for v in value.values())


def _sentences(text: str) -> int:
    return len([s for s in text.replace("؟", ".").replace("!", ".").split(".") if s.strip()])


def _check_why(where: str, section: dict) -> list[str]:
    """What the "Why this plan" page needs: a plain-language summary, the answers used, and a book reference once the
    rule is no longer a placeholder."""
    problems = []
    if not _bilingual_tree(section.get("summary")):
        problems.append(f"{where} needs a summary in plain language (en and ar)")
    uses = section.get("uses")
    if not (isinstance(uses, list) or (isinstance(uses, dict) and all(isinstance(u, list) for u in uses.values()))):
        problems.append(f"{where} needs `uses`: the answers it reads (a list, or one list per sub-rule)")
    if section.get("placeholder") is False:
        ref = section.get("ref") or {}
        if not (ref.get("book") and ref.get("page") and _bilingual_tree(ref.get("quote"))):
            problems.append(f"{where} isn't a placeholder, so it needs `ref` with book, page and a short quote (en and ar)")
        elif any(_sentences(ref["quote"][k]) > 2 for k in ("en", "ar")):
            problems.append(f"{where}: the quote must be 1–2 sentences")
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
        if bad := [d["key"] for d in t["days"] if d.get("kind", "full") not in ("upper", "lower", "full")]:
            raise RulesError(f"{path.name}: day kind must be upper, lower or full ({bad})")
        if not t.get("source"):
            raise RulesError(f"{path.name}: needs a source")
        templates.append(t)
    if not templates:
        raise RulesError(f"no program templates in {folder}")
    return tuple(templates)
