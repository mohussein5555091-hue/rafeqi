"""What the model is told. It only ever gets the engine's facts (numbers already decided, with their reasons) and writes
words around them, in English and Egyptian Arabic. It is never asked to decide anything, and there is no chat."""

import json

SYSTEM = """You write short explanations for Rafeqi, a fitness and Egyptian-food coaching app.
Rules:
- Use only the facts you are given. Never add, change, round or calculate a number: copy numbers exactly as they appear in the facts, or leave them out.
- Do not give new advice, change the plan, or diagnose anything. For any pain or red flag, only repeat that the person should see a doctor or physiotherapist.
- Warm, plain, encouraging language. No emojis. No markdown.
- English: at most {words} words. Arabic: Egyptian Arabic (عامية مصرية), the same content.
- Reply with JSON only: {{"en": "...", "ar": "..."}}"""

TASK = {
    "plan_explanation": "Explain this new plan in a few sentences: what the daily targets are, what the training week looks like, and why it fits the person's answers.",
    "weekly_review": "Summarise this week's review in a few sentences: how the week went and what changes next week and why.",
}


def build(task: str, facts: dict, passages: list[dict] | None = None, words: int = 90) -> tuple[str, str]:
    """(system prompt, user message) for one task."""
    user = {"task": TASK[task], "facts": facts}
    if passages:
        user["book_passages"] = passages  # filled once the books are indexed (app/ai/retrieval.py)
    return SYSTEM.format(words=words), json.dumps(user, ensure_ascii=False)


def parse(text: str) -> dict | None:
    """The model's {"en", "ar"}, or None if it isn't that."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("en"), str) or not isinstance(data.get("ar"), str):
        return None
    if not data["en"].strip() or not data["ar"].strip():
        return None
    return {"en": data["en"].strip(), "ar": data["ar"].strip()}
