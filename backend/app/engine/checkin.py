"""The weekly check-in questions (data/checkin_questions.yaml) and checks for the answers.

Answers are {question_id: value}. `check_answers` lists every problem (empty list = fine); `red_flags` lists the
answers that skip the normal review and show "see a doctor or physiotherapist".
"""

from functools import lru_cache
from pathlib import Path

import yaml

from app.config import DATA_DIR

TYPES = {"number", "scale", "choice", "multi", "yesno", "text", "per_injury", "per_exercise", "regions"}
REGIONS = {"head", "neck", "chest", "abdomen", "upperBack", "lowerBack", "shoulderL", "shoulderR", "armL", "armR", "forearmL",
           "forearmR", "hipL", "hipR", "thighL", "thighR", "kneeL", "kneeR", "shinL", "shinR", "ankleL", "ankleR"}


class QuestionsError(ValueError):
    pass


def questions_path() -> Path:
    return DATA_DIR / "checkin_questions.yaml"


def validate_questions(data: dict) -> list[str]:
    problems, seen = [], set()
    steps = data.get("steps") or []
    for q in data.get("questions") or []:
        where = f"question {q.get('id')}"
        if q.get("id") in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(q.get("id"))
        if q.get("type") not in TYPES:
            problems.append(f"{where}: type must be one of {sorted(TYPES)}")
        if q.get("step") not in steps:
            problems.append(f"{where}: step must be one of {steps}")
        if not (q.get("en") and q.get("ar")):
            problems.append(f"{where}: needs en and ar text")
        if q.get("type") in ("number", "scale") and "min" not in q:
            problems.append(f"{where}: needs min")
        if q.get("type") in ("number", "scale") and "max" not in q and "max_from" not in q:
            problems.append(f"{where}: needs max (or max_from)")
        if q.get("type") in ("choice", "multi") and not (q.get("options") or q.get("options_from")):
            problems.append(f"{where}: needs options (or options_from)")
        if q.get("type") == "text" and not q.get("max_length"):
            problems.append(f"{where}: needs max_length")
    if "note" in seen and next(q for q in data["questions"] if q["id"] == "note").get("max_length", 0) > 300:
        problems.append("question note: the note is at most 300 characters")
    return problems


@lru_cache
def load_questions() -> dict:
    data = yaml.safe_load(questions_path().read_text(encoding="utf-8")) or {}
    if problems := validate_questions(data):
        raise QuestionsError("\n".join(problems))
    return data


def check_answers(answers: dict, *, sessions_planned: int, injury_ids: set[str], exercise_ids: set[str],
                  recipe_ids: set[str], data: dict | None = None) -> list[str]:
    data = data or load_questions()
    problems = []
    questions = {q["id"]: q for q in data["questions"]}
    for qid in answers:
        if qid not in questions:
            problems.append(f"{qid}: not a check-in question")
    for qid, q in questions.items():
        if qid not in answers or answers[qid] is None:
            if q.get("required"):
                problems.append(f"{qid}: required")
            continue
        v, t = answers[qid], q["type"]
        hi = sessions_planned if q.get("max_from") == "sessions_planned" else q.get("max")
        if t in ("number", "scale"):
            ok = isinstance(v, (int, float)) and not isinstance(v, bool) and q["min"] <= v <= hi and (t != "scale" or float(v).is_integer())
            if not ok:
                problems.append(f"{qid}: must be {'a whole number ' if t == 'scale' else ''}between {q['min']} and {hi}")
        elif t == "yesno" and not isinstance(v, bool):
            problems.append(f"{qid}: must be true or false")
        elif t == "text" and (not isinstance(v, str) or len(v) > q["max_length"]):
            problems.append(f"{qid}: at most {q['max_length']} characters")
        elif t in ("choice", "multi"):
            allowed = set(q.get("options") or []) | (recipe_ids if q.get("options_from") == "plan_recipes" else set())
            values = [v] if t == "choice" else v
            if not isinstance(values, list) or any(x not in allowed for x in values):
                problems.append(f"{qid}: must be from {sorted(allowed)}")
        elif t == "regions" and (not isinstance(v, list) or any(x not in REGIONS for x in v)):
            problems.append(f"{qid}: unknown body area")
        elif t == "per_exercise":
            if not isinstance(v, list) or any(not isinstance(x, dict) or x.get("exercise_id") not in exercise_ids
                                              or x.get("feel") not in q["options"] for x in v):
                problems.append(f"{qid}: each entry needs an exercise from your program and a feel from {q['options']}")
        elif t == "per_injury":
            if not isinstance(v, list) or any(not isinstance(x, dict) or x.get("injury_id") not in injury_ids
                                              or not isinstance(x.get("pain"), int) or not q["min"] <= x["pain"] <= q["max"]
                                              or x.get("trend") not in q["trend_options"] for x in v):
                problems.append(f"{qid}: each entry needs one of your injuries, pain {q['min']}-{q['max']} and a trend")
    return problems


def red_flags(answers: dict, data: dict | None = None) -> list[str]:
    """Question ids answered "yes" that are red flags (sharp pain, swelling, numbness)."""
    data = data or load_questions()
    return [q["id"] for q in data["questions"] if q.get("red_flag") and answers.get(q["id"]) is True]
