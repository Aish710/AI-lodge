"""Tier 2: an explanation that asserts something the data cannot support (accessibility, quiet or crowds, safety, children or families, diet, weather, queue times) is rejected and the
template is shown, unless the term appears verbatim in the facts. Terms live in a data file in English, Malay, Korean and Chinese. Mock models only."""
import json
import sys
from pathlib import Path

import pytest

import app.llm.explain as explain_mod
from app.data.loader import load_dataset
from app.llm.claims import LANGS, load_terms, unsupported_claims
from app.llm.explain import explain
from llm_mock import MockLLM

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_llm_explain import faithful, replan_result  # noqa: E402

DS = load_dataset()
GROUPS = ["accessibility", "quiet_crowds", "safety", "children_family", "dietary", "weather", "queues"]
TERMS = [(g, lang, t) for g, by in load_terms().items() for lang in LANGS for t in by[lang]]


def test_the_term_file_has_the_seven_groups_each_in_four_languages():
    assert list(load_terms()) == GROUPS
    for g, by in load_terms().items():
        for lang in LANGS:
            assert by[lang], (g, lang)


@pytest.mark.parametrize("group,lang,term", TERMS, ids=[f"{g}-{lang}-{t}" for g, lang, t in TERMS])
def test_every_term_in_every_language_is_caught_in_a_sentence(group, lang, term):
    stem = term.rstrip("*")
    sentence = {"en": f"The plan is {stem} for everyone.", "ms": f"Rancangan ini {stem} untuk semua.", "ko": f"이 계획은 {stem} 입니다.", "zh": f"这个行程{stem}。"}[lang]
    assert (group, stem) in unsupported_claims(sentence, "")


def test_a_term_that_the_facts_state_verbatim_is_allowed_but_only_that_term():
    assert unsupported_claims("The route is quiet.", "Day 1: a quiet temple walk") == []
    assert unsupported_claims("The route is quiet and wheelchair accessible.", "Day 1: a quiet temple walk") == [("accessibility", "wheelchair"), ("accessibility", "accessible")]


@pytest.mark.parametrize("text", ["After removing Shinjuku Gyoen the true cost went from 41,000 JPY to 39,500 JPY.", "A relaxed pace with 3 stops a day and 92 minutes of travel.",
                                  "Hotel Lantern is 2,000 JPY more per night but saves 0.8 h of travel.", "Gardens by the Bay is closed on Wednesday: it will not be scheduled.",
                                  "Tokyo Skytree, Senso-ji and Meiji Jingu fit in day 1 and day 2.", "Okutama and Bukit Bintang are place names, not claims.", "东京三天行程，费用较低。"])
def test_ordinary_explanations_are_not_flagged(text):
    assert unsupported_claims(text, "") == []


@pytest.mark.parametrize("claim", ["This plan is wheelchair accessible.", "The places are quiet and never crowded.", "The route is very safe at night.", "It is kid-friendly.",
                                    "Every stop has vegetarian and halal food.", "The weather will be sunny.", "There are no queues."])
def test_an_explanation_with_such_a_claim_is_replaced_by_the_template_and_says_why(claim):
    r = replan_result()
    e = explain(r, DS, MockLLM([faithful(r) + " " + claim]))
    assert e.source == "template" and e.reason and "claim the data cannot support" in e.reason
    assert any(t.startswith("claim:") for t in e.grounding.rejected_tokens)
    assert claim not in e.text


def test_a_faithful_explanation_is_still_accepted_so_the_guard_is_not_a_blanket_block():
    r = replan_result()
    e = explain(r, DS, MockLLM([faithful(r)]))
    assert e.source == "llm" and e.grounding.rejected_tokens == []


def test_mutation_with_the_guard_disabled_the_claim_is_shown_and_these_tests_fail(monkeypatch):
    r = replan_result()
    monkeypatch.setattr(explain_mod, "unsupported_claims", lambda *a, **k: [])
    e = explain(r, DS, MockLLM([faithful(r) + " This plan is wheelchair accessible."]))
    assert e.source == "llm" and "wheelchair accessible" in e.text            # exactly what the tests above would catch


def test_the_twelve_user_requests_are_in_the_injection_fixture_in_four_languages():
    inj = json.loads((Path(__file__).parent / "fixtures" / "injection_prompts.json").read_text())
    claims = [c for c in inj if c["id"].startswith("claim_")]
    assert len(claims) == 12 and {c["id"].split("_")[1] for c in claims} == {"en", "ms", "ko", "zh"}
    assert all(any(c["id"].startswith(f"claim_{l}_") for c in claims) for l in ("en", "ms", "ko", "zh"))
