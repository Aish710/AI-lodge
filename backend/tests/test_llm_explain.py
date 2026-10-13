"""Phase 5 (output side): the grounding checker and grounded explanations. Mock LLM only."""
from decimal import Decimal

import pytest

from app import config
from app.data.loader import load_dataset
from app.llm.client import LLMUnavailable
from app.llm.explain import build_facts, explain
from app.llm.grounding import check_grounding, extract_tokens
from app.llm.prompts import EXPLAIN_SYSTEM
from app.optimiser.hotel_compare import compare_hotels
from app.optimiser.replan import ChangeBudgetOp, LockOp, RemoveOp, replan
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import Preferences
from llm_mock import MockLLM

DS = load_dataset()
ASA = "hotel_lantern_asakusa"
SPEC = ObjectiveSpec("true_cost", 1000, config.MISSED_PREFERENCE_PENALTY_JPY)

ALLOWED = ("True cost 1,500 JPY (about S$14 at the SAMPLE rate). Change -2,413 JPY. Departs 14:00. "
           "Travel 92 min (1h 32m). 3 activities moved. Discount 20%.")


def g(text, allowed=ALLOWED, forms=None, every=None):
    return check_grounding(text, allowed, [], forms or set(), every or {})


# ---- grounding checker (unit) ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "The cost is 1,500 JPY.", "It costs ¥1,500.", "About JPY 1,500 in total.", "Roughly S$14.", "A change of −2,413 JPY.",
    "A change of +2,413 JPY.", "Down 2413 yen.", "Leaving at 14:00.", "Travel was 1h 32m.", "That is 92 minutes.", "3 activities moved.",
    "About 1.5k JPY.", "Exactly 2,413.00 JPY.", "Three activities moved.", "A 20% discount.",
])
def test_formatting_variants_present_in_the_facts_are_accepted(text):
    r = g(text)
    assert r.ok, r.rejected_tokens


@pytest.mark.parametrize("text,bad", [
    ("It costs 1,501 JPY.", "1,501"), ("Leaving at 15:00.", "15:00"), ("Travel was 2h 32m.", "2"), ("About 12% cheaper.", "12%"),
    ("It saves about 50 minutes.", "50"), ("Roughly ninety minutes.", "ninety minutes"), ("Four activities moved.", "Four activities"),
    ("Around one hundred JPY.", "one hundred JPY"), ("A 25% discount.", "25%"), ("Cost 0.5k JPY.", "0.5k"),
    ("Twenty percent off.", "Twenty percent"), ("Leaving at 9:30.", "9:30"),
])
def test_numbers_not_in_the_facts_are_rejected_including_derived_ones(text, bad):
    r = g(text)
    assert not r.ok and any(bad in t for t in r.rejected_tokens), r.rejected_tokens


def test_time_tokens_do_not_leak_into_number_checks_and_vice_versa():
    assert g("Leaving at 14:00 and again at 14:00.").ok
    assert not g("Leaving at 92:00.").ok  # 92:00 is not a time; "92" and "00" are numbers, and 0 is not allowed


def test_extract_tokens_parses_signs_separators_and_decimals():
    t = extract_tokens("−2,413.50 JPY, +1,000, 7%, 09:05, 3.5k")
    assert t.numbers == {Decimal("2413.5"), Decimal(1000), Decimal(3500)} and t.percents == {Decimal(7)} and t.times == {"09:05"}


def test_name_not_in_facts_is_rejected_and_alias_of_a_fact_name_is_accepted():
    every = {"tokyo tower": "Tokyo Tower", "senso ji": "Senso-ji", "sensoji": "Senso-ji"}
    allowed_forms = {"senso ji", "sensoji"}
    assert g("Senso-ji and Sensoji moved.", forms=allowed_forms, every=every).ok
    r = g("Tokyo Tower was added.", forms=allowed_forms, every=every)
    assert not r.ok and "name:Tokyo Tower" in r.rejected_tokens


# ---- explanations (integration with real computed results) ---------------------------------------------------------------
def replan_result():
    p = Preferences(days=2, must_visit=["senso_ji", "shibuya_sky"], start_weekday=2, skip=["teamlab_planets"])
    cur = solve(p, ASA, DS, with_alternatives=False, objective=SPEC)
    return replan(p, cur, [RemoveOp(op="remove", attraction_id="shinjuku_gyoen"),
                           LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="14:00")], DS)


def faithful(r):
    d = r.diff
    return (f"After removing Shinjuku Gyoen and locking Senso-ji at 14:00, the true cost went from {d.true_cost_jpy.before:,} JPY to "
            f"{d.true_cost_jpy.after:,} JPY, a change of {d.true_cost_jpy.delta:+,} JPY. Travel time went from {d.travel_minutes.before} to "
            f"{d.travel_minutes.after} minutes, and {d.disruption_count} activity was moved unnecessarily.")


def test_faithful_explanation_passes_grounding_and_is_marked_llm():
    r = replan_result()
    mock = MockLLM([faithful(r)])
    e = explain(r, DS, mock)
    assert e.source == "llm" and e.call_count == 1 and e.grounding.rejected_tokens == [] and e.grounding.checked > 5
    assert faithful(r) in e.text and len(mock.calls) == 1
    assert mock.calls[0]["system"] == EXPLAIN_SYSTEM and mock.calls[0]["messages"][0]["content"].startswith("<facts>")


def test_explanation_with_a_fabricated_number_is_rejected_and_replaced_by_the_template():
    r = replan_result()
    e = explain(r, DS, MockLLM([faithful(r) + " It also saves 9,999 JPY on food."]))
    assert e.source == "template" and "9,999" in e.grounding.rejected_tokens and e.text.startswith("Replan applied")
    assert "9,999" not in e.text and e.reason


def test_invented_percentage_is_rejected():
    r = replan_result()
    e = explain(r, DS, MockLLM([faithful(r) + " That saves about 12%."]))
    assert e.source == "template" and "12%" in e.grounding.rejected_tokens


def test_attraction_not_in_the_facts_is_rejected():
    r = replan_result()
    assert "Tokyo Tower" not in build_facts(r, DS).allowed_text()
    e = explain(r, DS, MockLLM([faithful(r) + " Tokyo Tower would be a nice addition."]))
    assert e.source == "template" and "name:Tokyo Tower" in e.grounding.rejected_tokens


def test_spelled_out_number_with_unit_not_in_the_facts_is_flagged():
    r = replan_result()
    assert Decimal(90) not in extract_tokens(build_facts(r, DS).allowed_text()).numbers  # precondition: 90 is not one of the facts
    e = explain(r, DS, MockLLM([faithful(r) + " It saves about ninety minutes of walking."]))
    assert e.source == "template" and any("ninety" in t for t in e.grounding.rejected_tokens)


def test_warnings_are_appended_by_code_even_when_the_model_omits_them():
    r = replan_result()
    assert r.diff.warnings and r.diff.warnings[0].startswith("Not like-for-like")
    e = explain(r, DS, MockLLM([faithful(r)]))
    assert e.source == "llm"
    assert r.diff.warnings[0] in e.text and e.text.index("Warnings:") > e.text.index("true cost")
    assert e.warnings == build_facts(r, DS).warnings
    assert all(w in explain(r, DS, MockLLM([faithful(r) + " Fake 9,999"])).text for w in r.diff.warnings)  # also on the template path


def test_llm_unavailable_falls_back_to_the_template_without_raising():  # scenario 15
    r = replan_result()
    e = explain(r, DS, MockLLM([LLMUnavailable("timeout")]))
    assert e.source == "template" and e.call_count == 0 and "unavailable" in e.reason and e.text.startswith("Replan applied")
    s = explain(r, DS, None)
    assert s.source == "template" and "sample mode" in s.reason


def test_empty_or_overlong_output_uses_the_template_and_only_one_call_is_ever_made():
    r = replan_result()
    mock = MockLLM(["", faithful(r)])
    e = explain(r, DS, mock)
    assert e.source == "template" and len(mock.calls) == 1 == config.LLM_MAX_CALLS_EXPLAIN
    long = explain(r, DS, MockLLM([" ".join(["word"] * (config.EXPLAIN_MAX_WORDS + 5))]))
    assert long.source == "template"


def test_infeasible_replan_facts_and_template_carry_the_conflicts():
    p = Preferences(days=2, must_visit=["senso_ji", "shibuya_sky"], start_weekday=2, skip=["teamlab_planets"])
    cur = solve(p, ASA, DS, with_alternatives=False, objective=SPEC)
    r = replan(p, cur, [ChangeBudgetOp(op="change_budget", budget=1000, strict=True)], DS)
    e = explain(r, DS, None)
    assert r.status == "infeasible" and "original plan is unchanged" in e.text and "exceeds the strict budget" in e.text


def test_comparison_explanation_grounded_and_template_ranking():
    p = Preferences(days=2, pace="balanced", must_visit=["senso_ji", "shibuya_sky"], start_weekday=5, value_of_time_per_hour=1000)
    comp = compare_hotels(p, list(DS.hotels), DS, time_limit=60)
    best = comp.results[[x.hotel_id for x in comp.results].index(comp.best_by_true_cost)]
    text = (f"{best.hotel_name} has the lowest true cost at {best.breakdown.true_cost_jpy:,} JPY with {best.breakdown.travel_minutes} minutes of travel, "
            f"using {comp.nights_used} night of rooms at {comp.value_of_time_per_hour:,} JPY per hour of time.")
    e = explain(comp, DS, MockLLM([text]))
    assert e.source == "llm", e.grounding.rejected_tokens
    assert comp.warnings and all(w in e.text for w in comp.warnings)
    bad = explain(comp, DS, MockLLM([text + " That is 7% better."]))
    assert bad.source == "template" and "Ranking by true cost" in bad.text


def test_explain_prompts_never_contain_attraction_descriptions():
    r = replan_result()
    mock = MockLLM([faithful(r)])
    explain(r, DS, mock)
    for a in DS.attractions.values():
        assert a.description not in mock.all_prompt_text
