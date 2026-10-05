"""The "Why this plan" page (GET /api/plan/why, app/views/why.py): every reason stored with the plan appears as a
decision with the answers it used, the rule in plain language, its source (or the placeholder flag) and the result.

The planned user (test_screens_api.planned): intermediate, 4 days, gym, losing fat, a left shoulder injury.
"""

from collections import Counter

import pytest

from app.engine.rules import _check_sources, load_rules
from app.views.why import GROUPS, counts, decision, rule_section, source_out
from personas import PERSONAS, run
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import planned  # noqa: F401 (fixtures)


def stored_reasons(plan: dict) -> list[dict]:
    """Every reason in GET /api/plan: plan-level, each day's and each exercise's."""
    out = [r for rs in plan["reasons"].values() for r in rs]
    for d in plan["program"]["days"]:
        out += d["reasons"]
        out += [r for e in d["exercises"] for r in e["reasons"]]
    return out


def key(r: dict) -> tuple:
    return r["rule"], r["en"], r["ar"]


def test_every_reason_in_the_plan_is_on_the_page_with_its_source_or_the_placeholder_flag(planned):  # noqa: F811
    c = planned.client
    plan, why = c.get("/api/plan").json(), c.get("/api/plan/why").json()
    reasons = stored_reasons(plan)
    decisions = [d for g in why["groups"] for d in g["decisions"]]
    shown = Counter((d["rule"], d["result"]["en"], d["result"]["ar"]) for d in decisions)
    assert shown == Counter(key(r) for r in reasons)  # every one, once each, nothing else
    assert why["total"] == len(reasons) and why["planId"] == plan["id"]
    for d in decisions:
        assert d["summary"]["en"] and d["summary"]["ar"], d["rule"]
        assert d["source"]["text"], d["rule"]
        if not d["source"]["placeholder"]:
            assert d["source"]["book"] and d["source"]["page"] and d["source"]["quote"]["en"] and d["source"]["quote"]["ar"]
    assert why["backed"] == sum(d["source"]["kind"] == "book" for d in decisions)
    assert why["aiSummary"] is None  # comes in the AI phase


def test_four_kinds_of_source_and_the_counts(planned):  # noqa: F811
    """Rules from the books are "From your books" with their reference; the body-fat estimate is a "Standard formula" with
    its original source (Relative Fat Mass here: the planned user gave a waist); Rafeqi's own safety rules are labelled
    as such; the rest are "Not yet from a book"."""
    why = planned.client.get("/api/plan/why").json()
    decisions = [d for g in why["groups"] for d in g["decisions"]]
    kinds = {d["source"]["kind"] for d in decisions}
    assert {"book", "formula", "placeholder"} <= kinds <= {"book", "formula", "safety", "placeholder"}
    formula = [d for d in decisions if d["source"]["kind"] == "formula"]
    assert [d["rule"] for d in formula] == ["nutrition.body_fat"] and why["formulas"] == 1
    assert formula[0]["source"]["page"] == "10980" and "Scientific Reports" in formula[0]["source"]["book"]
    books = {d["ruleKey"] for d in decisions if d["source"]["kind"] == "book"}
    assert {"nutrition.bmr", "nutrition.goal", "nutrition.protein", "nutrition.fat", "nutrition.carbs"} <= books
    assert all(d["source"]["book"] and d["source"]["page"] for d in decisions if d["source"]["kind"] == "book")
    assert all("PLACEHOLDER" in d["source"]["text"] for d in decisions if d["source"]["kind"] == "placeholder")
    assert all("book" not in d["source"] for d in decisions if d["source"]["placeholder"])
    keys = {d["ruleKey"]: d["source"]["kind"] for d in decisions}
    assert why["rules"] == {"total": len(keys), "fromBooks": len(books), "formulas": 1,
                            "safety": sum(k == "safety" for k in keys.values())}
    assert why["backed"] == sum(d["source"]["kind"] == "book" for d in decisions)
    assert len(keys) < len(decisions)  # many decisions share a rule (one starting weight per exercise…)


def test_a_rafeqi_safety_rule_is_labelled_as_one_not_as_a_book_or_a_placeholder():
    for key in ("safety.red_flags", "safety.conservative", "safety.pregnancy", "training.injury_load"):
        section, _ = rule_section(key)
        out = source_out(section)
        assert out == {"placeholder": False, "kind": "safety", "text": section["source"]}, key
        assert out["text"].startswith("Rafeqi safety rule:")
    assert counts([{"ruleKey": "safety.red_flags", "source": {"kind": "safety"}}])["rules"]["safety"] == 1


def test_a_rule_from_a_book_counts_as_from_your_books(planned, monkeypatch):  # noqa: F811
    from app.engine import rules

    before = planned.client.get("/api/plan/why").json()
    real = rules.load_rules()
    fake = {**real, "training": {**real["training"], "start_load": {**real["training"]["start_load"], "placeholder": False,
            "ref": {"book": "Fundamentals Hypertrophy Program", "chapter": "Week 1", "page": 12,
                    "quote": {"en": "Start light.", "ar": "ابدأ خفيف."}}}}}
    monkeypatch.setattr("app.views.why.load_rules", lambda: fake)
    why = planned.client.get("/api/plan/why").json()
    decisions = [d for g in why["groups"] for d in g["decisions"]]
    start = [d for d in decisions if d["ruleKey"] == "training.start_load"]
    assert start and all(d["source"]["kind"] == "book" for d in start)
    assert why["backed"] == before["backed"] + len(start)
    assert why["rules"]["fromBooks"] == before["rules"]["fromBooks"] + 1


def test_every_kind_of_decision_is_covered(planned):  # noqa: F811
    why = planned.client.get("/api/plan/why").json()
    groups = [g["id"] for g in why["groups"]]
    assert groups == [g for g in GROUPS if g in groups]  # in page order
    assert {"calories", "protein", "carbsFat", "program", "schedule", "volume", "startWeights", "progression", "deload",
            "warmup", "cooldown", "cardio", "exercises", "meals"} <= set(groups)
    rules = {d["rule"] for g in why["groups"] for d in g["decisions"]}
    assert {"nutrition.activity", "nutrition.goal.loseFat", "nutrition.protein", "nutrition.fat", "nutrition.carbs",
            "training.template_choice", "training.schedule", "training.session", "training.volume", "training.start_load",
            "progression", "training.deload", "training.warmup", "training.cooldown", "training.cardio.plan",
            "training.injuries", "nutrition.meals", "nutrition.meals.portions"} <= rules


def test_answers_used_come_from_the_plan_inputs(planned):  # noqa: F811
    why = planned.client.get("/api/plan/why").json()
    by_rule = {d["rule"]: d for g in why["groups"] for d in g["decisions"]}
    bmr = {a["key"]: a["value"] for a in by_rule["nutrition.bmr"]["answers"]}
    assert set(bmr) == {"sex", "age", "height_cm", "weight_kg"} and bmr["sex"] in ("male", "female")
    sched = {a["key"]: a["value"] for a in by_rule["training.schedule"]["answers"]}
    assert sched == {"days_per_week": 4, "session_minutes": 60}
    # An injury swap shows the injury it was for, with its painful movements.
    injury = by_rule["training.injuries"]
    inj = next(a["value"] for a in injury["answers"] if a["key"] == "injuries")
    assert [i["region"] for i in inj] == ["shoulderL"] and inj[0]["painful_movements"]
    assert injury["context"]["en"].count(" · ") == 1  # "Upper A · Neutral-grip dumbbell floor press"


def test_no_plan_yet_is_404(onboarded):  # noqa: F811
    assert onboarded.client.get("/api/plan/why").status_code == 404


@pytest.mark.parametrize("key_", sorted(PERSONAS))
def test_every_reason_the_engine_makes_has_a_rule_with_a_summary(key_):
    """For all 5 personas: each reason resolves to a rule section with a source, a plain-language summary and the
    answers it reads, in English and Arabic."""
    pp = run(key_)
    inputs = {"person": {"sex": pp.person.sex, "age": pp.person.age}, "injuries": []}
    reasons = [r for rs in pp.targets.reasons.values() for r in rs] + pp.program.reasons + pp.meals.reasons
    reasons += (pp.program.cardio.reasons if pp.program.cardio else [])
    reasons += [r for d in pp.program.days for r in d.reasons + [x for e in d.exercises for x in e.reasons]]
    for r in reasons:
        section, _ = rule_section(r.rule)
        assert section["source"] == r.source, f"{r.rule}: the reason's source is its rule's source"
        d = decision(r.as_dict(), None, inputs)
        assert d["summary"]["en"] and d["summary"]["ar"] and d["group"] in GROUPS, r.rule


def test_sub_rules_get_their_own_summary():
    goal, sub = rule_section("nutrition.goal.loseFat")
    assert sub == "loseFat" and goal is load_rules()["nutrition"]["goal"]
    assert decision({"rule": "nutrition.goal.recomp", "en": "x", "ar": "y"}, "calories", {})["summary"]["en"].startswith("For recomposition")
    assert decision({"rule": "training.review.deload", "en": "x", "ar": "y"}, "review", {})["summary"]["en"].startswith("A lighter week")
    with pytest.raises(KeyError):
        rule_section("nowhere.at_all")


def test_rule_files_need_what_the_why_page_shows():
    good = {"source": "PLACEHOLDER: x", "placeholder": True, "uses": [], "summary": {"en": "a", "ar": "b"}, "explain": {"en": "e", "ar": "f"}}
    assert _check_sources("nutrition", {"fat": good}) == []
    assert "needs a summary" in _check_sources("nutrition", {"fat": good | {"summary": {"en": "only English"}}})[0]
    assert "needs `uses`" in _check_sources("nutrition", {"fat": {k: v for k, v in good.items() if k != "uses"}})[0]
    assert "kind must be book, formula or safety" in _check_sources("nutrition", {"fat": good | {"kind": "guess"}})[0]
    assert "isn't a placeholder" in _check_sources("nutrition", {"fat": good | {"kind": "formula"}})[0]
    backed = good | {"placeholder": False}
    assert "needs `ref` with book, page" in _check_sources("nutrition", {"fat": backed})[0]
    ref = {"book": "B", "page": 12, "quote": {"en": "One. Two. Three.", "ar": "واحد. اتنين."}}
    assert "1–2 sentences" in _check_sources("nutrition", {"fat": backed | {"ref": ref}})[0]
    assert _check_sources("nutrition", {"fat": backed | {"ref": ref | {"quote": {"en": "One. Two.", "ar": "واحد."}}}}) == []
