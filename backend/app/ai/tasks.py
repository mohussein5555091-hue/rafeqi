"""The two AI tasks, with every safety net:

- plan_explanation: after onboarding and "Regenerate my plan", a short summary of the plan (the "Why this plan" page).
- weekly_review: after each check-in, the review's summary text.

Each run: AI must be turned on (config.py) → at most `runs_per_week` runs per person per week → the month's AI spend
under `monthly_limit_usd` → the model writes from the engine's facts only → the reply must be {"en", "ar"} JSON → every
number in it must be one of the facts' numbers (checks.py). Every call is recorded in llm_calls (task, model, tokens,
latency, cost, status). If anything fails, the template (built from the same facts, no model) is used instead.
AI turned off (the default): nothing runs and the screens keep their own wording.
"""

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import clock
from app.ai.checks import allowed_numbers, unknown_numbers
from app.ai.client import AnthropicClient, LlmClient, LlmError
from app.ai.config import AiConfig, cost_usd, load_config
from app.ai.prompts import build, parse
from app.ai.retrieval import NoRetriever, Retriever
from app.models import LlmCall, Plan, ProgramDay, TrainingProgram, WeeklyReview
from app.plans import week_start

TEMPLATE = "template"


@dataclass(frozen=True)
class Outcome:
    text: dict  # {en, ar}
    source: str  # "ai" or "template"
    why: str  # ok | off | weekly_limit | monthly_limit | error | invalid | numbers


# ── Limits ──

def runs_this_week(db: Session, user_id: str, today: dt.date | None = None) -> int:
    start = week_start(today or clock.today())
    since = dt.datetime.combine(start, dt.time(), tzinfo=dt.UTC)
    return db.scalar(select(func.count()).select_from(LlmCall).where(LlmCall.user_id == user_id, LlmCall.created_at >= since)) or 0


def spent_this_month(db: Session, today: dt.date | None = None) -> float:
    first = (today or clock.today()).replace(day=1)
    since = dt.datetime.combine(first, dt.time(), tzinfo=dt.UTC)
    return float(db.scalar(select(func.coalesce(func.sum(LlmCall.cost_usd), 0.0)).where(LlmCall.created_at >= since)) or 0.0)


# ── The facts each task writes from (numbers only from the engine) ──

def plan_facts(db: Session, plan: Plan) -> dict:
    tp = db.scalar(select(TrainingProgram).where(TrainingProgram.plan_id == plan.id))
    days = list(db.scalars(select(ProgramDay).where(ProgramDay.program_id == tp.id).order_by(ProgramDay.day_index))) if tp else []
    person = (plan.inputs or {}).get("person") or {}
    return {
        "goal": person.get("goal"), "experience": person.get("experience"),
        "daily_targets": {"calories_kcal": plan.calories, "protein_g": plan.protein_g, "carbs_g": plan.carbs_g, "fat_g": plan.fat_g,
                          "maintenance_kcal": plan.maintenance_calories},
        "program": {"name": {"en": tp.name_en, "ar": tp.name_ar} if tp else None, "days_per_week": tp.days_per_week if tp else 0,
                    "sessions": [{"day": d.weekday, "name": d.name_en, "minutes": d.est_minutes} for d in days]},
        "reasons": [r["en"] for key in ("calories", "protein", "training") for r in (plan.reasons or {}).get(key, [])][:12],
    }


def review_facts(review: WeeklyReview, stats: dict) -> dict:
    return {"week": review.week_number, "status": review.status, "red_flag": review.red_flag, "stats": stats,
            "changes": [{"what": c["what"]["en"], "why": c["why"]["en"]} for c in review.changes]}


# ── Templates (no model): the fallback, from the same facts ──

def plan_template(f: dict) -> dict:
    t, p = f["daily_targets"], f["program"]
    name = p["name"] or {"en": "your program", "ar": "برنامجك"}
    minutes = max((s["minutes"] for s in p["sessions"]), default=0)
    return {
        "en": (f"Your plan: {t['calories_kcal']} kcal a day with {t['protein_g']} g protein, {t['carbs_g']} g carbs and {t['fat_g']} g fat. "
               f"{name['en']}: {p['days_per_week']} training days a week, about {minutes} minutes each. Every number below comes with its reason."),
        "ar": (f"خطتك: {t['calories_kcal']} سعرة في اليوم، فيها {t['protein_g']} جم بروتين و{t['carbs_g']} جم كربوهيدرات و{t['fat_g']} جم دهون. "
               f"{name['ar']}: {p['days_per_week']} أيام تمرين في الأسبوع، حوالي {minutes} دقيقة كل مرة. كل رقم تحت معاه السبب بتاعه."),
    }


def review_template(review: WeeklyReview) -> dict:
    from app.views.body import SUMMARY  # the review page's own wording

    if review.red_flag:
        return dict(SUMMARY["red_flag"])
    n = len(review.changes)
    return {k: v.format(n=n) for k, v in SUMMARY["some" if n else "none"].items()}


# ── Running a task ──

def _record(db: Session, user_id: str, task: str, model: str, status: str, *, plan_id=None, review_id=None, c=None, error=None) -> None:
    db.add(LlmCall(user_id=user_id, plan_id=plan_id, weekly_review_id=review_id, task=task, model=model, status=status, error=error,
                   prompt_tokens=c.prompt_tokens if c else 0, completion_tokens=c.completion_tokens if c else 0,
                   latency_ms=c.latency_ms if c else 0, cost_usd=cost_usd(model, c.prompt_tokens, c.completion_tokens) if c else 0.0,
                   created_at=clock.now()))
    db.flush()


def run(db: Session, user_id: str, task: str, facts: dict, fallback: dict, *, cfg: AiConfig, client: LlmClient | None,
        retriever: Retriever | None = None, plan_id: str | None = None, review_id: str | None = None) -> Outcome:
    if not cfg.enabled or client is None:
        return Outcome(fallback, TEMPLATE, "off")
    if runs_this_week(db, user_id) >= cfg.runs_per_week:
        return Outcome(fallback, TEMPLATE, "weekly_limit")
    if spent_this_month(db) >= cfg.monthly_limit_usd:
        return Outcome(fallback, TEMPLATE, "monthly_limit")
    model = cfg.models[task]
    passages = [p.__dict__ for p in (retriever or NoRetriever()).search(task, k=3)]
    system, user = build(task, facts, passages)
    ids = {"plan_id": plan_id, "review_id": review_id}
    try:
        c = client.complete(model=model, system=system, user=user, max_tokens=cfg.max_tokens)
    except LlmError as e:
        _record(db, user_id, task, model, "error", error=str(e)[:500], **ids)
        return Outcome(fallback, TEMPLATE, "error")
    data = parse(c.text)
    if data is None:
        _record(db, user_id, task, model, "invalid", c=c, error="not {en, ar} JSON", **ids)
        return Outcome(fallback, TEMPLATE, "invalid")
    allowed = allowed_numbers(facts)
    bad = unknown_numbers(data["en"], allowed) + unknown_numbers(data["ar"], allowed)
    if bad:
        _record(db, user_id, task, model, "rejected", c=c, error=f"numbers not in the facts: {sorted(set(bad))[:10]}", **ids)
        return Outcome(fallback, TEMPLATE, "numbers")
    _record(db, user_id, task, model, "ok", c=c, **ids)
    return Outcome(data, "ai", "ok")


def default_client(cfg: AiConfig) -> LlmClient | None:
    return AnthropicClient(cfg.api_key, cfg.timeout_s) if cfg.enabled else None


def explain_plan(db: Session, plan: Plan, *, cfg: AiConfig | None = None, client: LlmClient | None = None,
                 retriever: Retriever | None = None) -> Outcome:
    """Writes the plan's summary (plans.ai_summary) for "Why this plan". Only call with AI turned on."""
    cfg = cfg or load_config()
    facts = plan_facts(db, plan)
    out = run(db, plan.user_id, "plan_explanation", facts, plan_template(facts), cfg=cfg,
              client=client if client is not None else default_client(cfg), retriever=retriever, plan_id=plan.id)
    plan.ai_summary = out.text
    plan.ai_model = cfg.models["plan_explanation"] if out.source == "ai" else TEMPLATE
    db.flush()
    return out


def write_review(db: Session, review: WeeklyReview, stats: dict, *, cfg: AiConfig | None = None, client: LlmClient | None = None,
                 retriever: Retriever | None = None) -> Outcome:
    """Writes the weekly review's summary (weekly_reviews.ai_summary_en/ar). Red flags always use the fixed safety text.
    Only call with AI turned on."""
    cfg = cfg or load_config()
    fallback = review_template(review)
    if review.red_flag:  # the safety message is never rewritten by a model
        out = Outcome(fallback, TEMPLATE, "red_flag")
    else:
        out = run(db, review.user_id, "weekly_review", review_facts(review, stats), fallback, cfg=cfg,
                  client=client if client is not None else default_client(cfg), retriever=retriever, review_id=review.id)
    review.ai_summary_en, review.ai_summary_ar = out.text["en"], out.text["ar"]
    review.model_used = cfg.models["weekly_review"] if out.source == "ai" else TEMPLATE
    db.flush()
    return out
