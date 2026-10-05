"""The number check: an AI text may only contain numbers the engine produced.

Every number in the text (Western or Arabic-Indic digits, with "." "," "٫" or "٬") must be one of the facts' numbers.
Anything else (a calorie count, weight or percentage the model made up or worked out itself) rejects the whole text,
and the template is used instead. The plan's numbers come from tested code, never from the model.
"""

import re

ARABIC = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def _canon(token: str) -> str:
    """'2,250' → '2250', '87.50' → '87.5', '3.0' → '3' (thousands commas go; a lone decimal comma is a point)."""
    t = token
    if "," in t and "." not in t and not re.fullmatch(r"\d{1,3}(,\d{3})+", t):
        t = t.replace(",", ".")  # "87,5" written the European / Arabic way
    t = t.replace(",", "")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t.lstrip("0") or "0"


def numbers_in(text: str) -> list[str]:
    return [_canon(m) for m in NUMBER.findall(text.translate(ARABIC))]


def allowed_numbers(facts: object) -> set[str]:
    """Every number that appears anywhere in the facts (dicts, lists, strings, numbers)."""
    out: set[str] = set()
    if isinstance(facts, dict):
        for v in facts.values():
            out |= allowed_numbers(v)
    elif isinstance(facts, list | tuple):
        for v in facts:
            out |= allowed_numbers(v)
    elif isinstance(facts, bool):
        pass
    elif isinstance(facts, int | float):
        out.add(_canon(f"{facts:g}" if isinstance(facts, float) else str(facts)))
    elif isinstance(facts, str):
        out |= set(numbers_in(facts))
    return out


def unknown_numbers(text: str, allowed: set[str]) -> list[str]:
    """The numbers in `text` that aren't in `allowed` (empty = the text passes)."""
    return [n for n in numbers_in(text) if n not in allowed]
