"""The AI layer (backend/app/ai) with a fake Claude client: nothing here calls the real API.

Two tasks (plan explanation, weekly review), per-task models, at most N runs per person per week, a monthly spending
cap tracked in llm_calls, the number check (the AI may only use the engine's numbers) and the template fallback.
"""

import json

import pytest

from app.ai import tasks
from app.ai.checks import allowed_numbers, numbers_in, unknown_numbers
from app.ai.client import AnthropicClient, Completion, LlmError
from app.ai.config import AiConfig, cost_usd
from app.ai.prompts import parse
from app.ai.retrieval import NoRetriever, Passage
from app.models import LlmCall, Plan, WeeklyReview
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import checkin_body, planned  # noqa: F401 (fixtures)

ON = AiConfig(enabled=True, models={"plan_explanation": "claude-haiku-4-5-20251001", "weekly_review": "claude-sonnet-5-5"},
              runs_per_week=2, monthly_limit_usd=5.0, api_key="test")


class FakeClient:
    """Answers with whatever the test sets; remembers what it was asked."""

    def __init__(self, reply=None, error: Exception | None = None, tokens=(1200, 300)):
        self.reply, self.error, self.tokens, self.calls = reply, error, tokens, []

    def complete(self, *, model, system, user, max_tokens):
        self.calls.append({"model": model, "system": system, "user": json.loads(user), "max_tokens": max_tokens})
        if self.error:
            raise self.error
        text = self.reply(json.loads(user)["facts"]) if callable(self.reply) else self.reply
        return Completion(text, self.tokens[0], self.tokens[1], 850)


def good_plan_reply(facts):
    t = facts["daily_targets"]
    return json.dumps({"en": f"You'll eat about {t['calories_kcal']} kcal with {t['protein_g']} g of protein a day.",
                       "ar": f"هتاكل حوالي {t['calories_kcal']} سعرة فيها {t['protein_g']} جم بروتين في اليوم."}, ensure_ascii=False)


def plan_of(db, user_id) -> Plan:
    db.expire_all()
    return db.query(Plan).filter_by(user_id=user_id, status="active").one()


# ── The number check ──

def test_numbers_are_read_in_every_way_they_are_written():
    assert numbers_in("2,250 kcal, 87.5 kg, 87,5 kg, ٢٢٥٠ سعرة, ٨٧٫٥ كجم, 3.0 sets") == ["2250", "87.5", "87.5", "2250", "87.5", "3"]
    facts = {"calories": 2250, "weight": 87.5, "reasons": ["Week 5 of 8 is lighter"]}
    allowed = allowed_numbers(facts)
    assert {"2250", "87.5", "5", "8"} <= allowed
    assert unknown_numbers("About ٢٢٥٠ calories and 87.5 kg in week 5.", allowed) == []
    assert unknown_numbers("About 2300 calories and 160 g protein.", allowed) == ["2300", "160"]


def test_parse_wants_both_languages():
    assert parse('Sure! {"en": "Hi", "ar": "أهلا"}') == {"en": "Hi", "ar": "أهلا"}
    assert parse('{"en": "Hi"}') is None and parse("no json") is None and parse('{"en": "", "ar": "x"}') is None


# ── The plan explanation ──

def test_ai_off_runs_nothing(planned, db):  # noqa: F811
    out = tasks.explain_plan(db, plan_of(db, planned.id), cfg=AiConfig(enabled=False), client=FakeClient(good_plan_reply))
    assert (out.source, out.why) == ("template", "off") and db.query(LlmCall).count() == 0
    assert planned.client.get("/api/plan/why").json()["aiSummary"] is None  # and the API never ran it by itself


def test_plan_explanation_written_by_the_model_and_recorded(planned, db):  # noqa: F811
    fake = FakeClient(good_plan_reply)
    plan = plan_of(db, planned.id)
    out = tasks.explain_plan(db, plan, cfg=ON, client=fake)
    db.commit()
    assert (out.source, out.why) == ("ai", "ok") and str(plan.calories) in out.text["en"]
    call = fake.calls[0]
    assert call["model"] == "claude-haiku-4-5-20251001" and "Never add, change, round or calculate a number" in call["system"]
    assert call["user"]["facts"]["daily_targets"]["calories_kcal"] == plan.calories
    row = db.query(LlmCall).one()
    assert (row.task, row.status, row.prompt_tokens, row.completion_tokens, row.latency_ms) == ("plan_explanation", "ok", 1200, 300, 850)
    assert row.cost_usd == pytest.approx(cost_usd("claude-haiku-4-5-20251001", 1200, 300)) and row.plan_id == plan.id
    assert planned.client.get("/api/plan/why").json()["aiSummary"] == out.text


@pytest.mark.parametrize("reply,error,why,status", [
    (lambda f: json.dumps({"en": "Eat 3000 kcal a day.", "ar": "كُل ٣٠٠٠ سعرة."}), None, "numbers", "rejected"),
    ("I can't answer in JSON today.", None, "invalid", "invalid"),
    (None, LlmError("http 529"), "error", "error"),
])
def test_anything_wrong_falls_back_to_the_template(planned, db, reply, error, why, status):  # noqa: F811
    plan = plan_of(db, planned.id)
    out = tasks.explain_plan(db, plan, cfg=ON, client=FakeClient(reply, error))
    assert (out.source, out.why) == ("template", why)
    assert out.text == tasks.plan_template(tasks.plan_facts(db, plan)) and plan.ai_model == "template"
    assert f"{plan.calories} kcal a day" in out.text["en"] and str(plan.calories) in out.text["ar"]
    assert db.query(LlmCall).one().status == status


def test_the_template_itself_passes_the_number_check(planned, db):  # noqa: F811
    facts = tasks.plan_facts(db, plan_of(db, planned.id))
    t = tasks.plan_template(facts)
    assert unknown_numbers(t["en"], allowed_numbers(facts)) == [] and unknown_numbers(t["ar"], allowed_numbers(facts)) == []


# ── Limits ──

def test_two_runs_per_person_per_week(planned, db, clock):  # noqa: F811
    fake = FakeClient(good_plan_reply)
    plan = plan_of(db, planned.id)
    assert [tasks.explain_plan(db, plan, cfg=ON, client=fake).source for _ in range(3)] == ["ai", "ai", "template"]
    assert len(fake.calls) == 2 and tasks.explain_plan(db, plan, cfg=ON, client=fake).why == "weekly_limit"
    clock.advance(days=7)  # a new week
    assert tasks.explain_plan(db, plan, cfg=ON, client=fake).source == "ai"


def test_monthly_spending_cap(planned, db):  # noqa: F811
    fake = FakeClient(good_plan_reply, tokens=(400_000, 100_000))  # an expensive call
    plan = plan_of(db, planned.id)
    cap = AiConfig(**{**ON.__dict__, "monthly_limit_usd": cost_usd("claude-haiku-4-5-20251001", 400_000, 100_000), "runs_per_week": 10})
    assert tasks.explain_plan(db, plan, cfg=cap, client=fake).source == "ai"
    out = tasks.explain_plan(db, plan, cfg=cap, client=fake)
    assert (out.source, out.why) == ("template", "monthly_limit") and len(fake.calls) == 1
    assert tasks.spent_this_month(db) == pytest.approx(cap.monthly_limit_usd)


# ── The weekly review ──

def checked_in(c, clock):
    clock.advance(days=3)
    _, body = checkin_body(c)
    r = c.post("/api/checkins", json=body)
    assert r.status_code == 201, r.text
    return r.json()["reviewId"]


def test_weekly_review_text(planned, db, clock):  # noqa: F811
    review_id = checked_in(planned.client, clock)
    review = db.get(WeeklyReview, review_id)
    stats = planned.client.get(f"/api/reviews/{review_id}").json()["stats"]
    fake = FakeClient(lambda f: json.dumps({"en": f"Week {f['week']} went well: {f['stats']['sessionsDone']} sessions done.",
                                             "ar": f"الأسبوع {f['week']} كان كويس: {f['stats']['sessionsDone']} جلسات."}, ensure_ascii=False))
    out = tasks.write_review(db, review, stats, cfg=ON, client=fake)
    db.commit()
    assert out.source == "ai" and fake.calls[0]["model"] == "claude-sonnet-5-5"
    shown = planned.client.get(f"/api/reviews/{review_id}").json()
    assert shown["summary"] == out.text and review.model_used == "claude-sonnet-5-5"


def test_a_red_flag_review_never_goes_to_the_model(planned, db, clock):  # noqa: F811
    review_id = checked_in(planned.client, clock)
    review = db.get(WeeklyReview, review_id)
    review.red_flag = True
    fake = FakeClient(good_plan_reply)
    out = tasks.write_review(db, review, {}, cfg=ON, client=fake)
    assert out.why == "red_flag" and fake.calls == [] and "doctor or physiotherapist" in out.text["en"]


# ── Wired into the app (only when AI is on) ──

def test_the_app_runs_both_tasks_after_the_answer_when_ai_is_on(onboarded, db, clock, monkeypatch):  # noqa: F811
    from app.ai import hooks

    fake = FakeClient(lambda f: good_plan_reply(f) if "daily_targets" in f else json.dumps({"en": "A steady week.", "ar": "أسبوع ثابت."}, ensure_ascii=False))
    monkeypatch.setattr(hooks, "load_config", lambda: ON)
    monkeypatch.setattr(tasks, "load_config", lambda: ON)
    monkeypatch.setattr(tasks, "default_client", lambda cfg: fake)
    c = onboarded.client
    assert c.post("/api/plan").status_code == 200  # the summary is written after the answer (a background task)
    why = c.get("/api/plan/why").json()
    assert why["aiSummary"]["en"].startswith("You'll eat about")
    review_id = checked_in(c, clock)
    assert c.get(f"/api/reviews/{review_id}").json()["summary"] == {"en": "A steady week.", "ar": "أسبوع ثابت."}
    assert [x["user"]["task"].split(":")[0][:7] for x in fake.calls] == ["Explain", "Summari"]


# ── The real client and retrieval (no network: the request is faked) ──

def test_anthropic_client_request_and_reply(monkeypatch):
    seen = {}

    class Reply:
        status_code = 200

        @staticmethod
        def json():
            return {"content": [{"type": "text", "text": '{"en": "Hi", "ar": "أهلا"}'}], "usage": {"input_tokens": 10, "output_tokens": 5}}

    def fake_post(url, **kw):
        seen.update(url=url, **kw)
        return Reply()

    monkeypatch.setattr("app.ai.client.httpx.post", fake_post)
    out = AnthropicClient("sk-test").complete(model="claude-sonnet-5-5", system="S", user="U", max_tokens=50)
    assert (out.text, out.prompt_tokens, out.completion_tokens) == ('{"en": "Hi", "ar": "أهلا"}', 10, 5)
    assert seen["url"] == "https://api.anthropic.com/v1/messages" and seen["headers"]["x-api-key"] == "sk-test"
    assert seen["json"] == {"model": "claude-sonnet-5-5", "max_tokens": 50, "system": "S", "messages": [{"role": "user", "content": "U"}]}


def test_retrieval_is_an_empty_interface_until_the_books_phase(planned, db):  # noqa: F811
    assert NoRetriever().search("protein") == []

    class Books:
        def search(self, query, k=3):
            return [Passage("Fundamentals Hypertrophy Program", "Week 1", "12", "Start light.")]

    fake = FakeClient(good_plan_reply)
    tasks.explain_plan(db, plan_of(db, planned.id), cfg=ON, client=fake, retriever=Books())
    assert fake.calls[0]["user"]["book_passages"][0]["book"] == "Fundamentals Hypertrophy Program"
