"""Room cost and the modelled cash total as explanation evidence (the false rejection of 280 and 495), and the two grounding bypasses found while investigating it."""
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.llm.client import get_llm_client
from app.llm.explain import CASH_WORDS, ROOM_WORDS, SIGHT_WORDS, ExplainFacts, OptimiseView, build_facts, explain, role_mismatch
from app.llm.grounding import check_grounding, extract_tokens
from app.main import app
from app.optimiser.solver import solve
from app.schemas import Preferences
from app.validator.feasibility_report import build_report
from llm_mock import MockLLM

KL = load_all_city_datasets()["kuala_lumpur"]
H = "hotel_bangsar_edge"
P = Preferences(days=3, must_visit=["petronas_twin_towers", "batu_caves"], start_weekday=2)


def facts_with(rooms=280, cash=495, sights=215):
    """The figures the person saw: two nights of rooms 280, sights and transport 215, modelled cash total 495."""
    lines = ["Rooms: 280 MYR (140 MYR x 2 nights; demo hotel at its sample rate, not a quote)",
             "Modelled cash total including rooms: 495 MYR (sights and transport 215 MYR + rooms 280 MYR); 1 admission price(s) are unknown and are excluded, not free",
             "Totals: admissions 172 MYR, estimated transport 43 MYR, total 215 MYR, travel 286 min"]
    return ExplainFacts("optimise", lines, set(), {H}, [], "t", roles=[(Decimal(rooms), ROOM_WORDS, "the rooms cost"), (Decimal(cash), CASH_WORDS, "the modelled total spending including rooms"), (Decimal(sights), SIGHT_WORDS, "the cost of sights and transport")])


@pytest.mark.parametrize("sentence", ["The two-night room total is RM280.", "Rooms for the two nights cost 280 MYR.", "Modelled total spending including rooms is RM495.",
                                      "The modelled cash total including rooms comes to 495 MYR.", "Sights and transport come to RM215."])
def test_valid_uses_of_280_and_495_are_accepted(sentence):
    assert role_mismatch(sentence, facts_with()) is None


@pytest.mark.parametrize("sentence,wrong", [("Rooms cost RM495.", "495"), ("The room total is 495 MYR.", "495"), ("Total spending is RM280.", "280"), ("The modelled cash total is 280 MYR.", "280"),
                                            ("Sights and transport cost RM495.", "495"), ("You will pay RM280 for the whole trip.", "280")])
def test_correct_numbers_used_for_the_wrong_thing_are_rejected(sentence, wrong):
    out = role_mismatch(sentence, facts_with())
    assert out and out.startswith(wrong)


def test_numbers_that_are_not_facts_are_still_rejected_by_the_grounding_checker():
    f = facts_with()
    allowed = "\n".join(f.lines)
    assert check_grounding("The rooms cost 280 MYR.", allowed, [], set(), {}).ok
    assert not check_grounding("The rooms cost 290 MYR.", allowed, [], set(), {}).ok
    assert not check_grounding("The total is 496 MYR.", allowed, [], set(), {}).ok


@pytest.mark.parametrize("text", ["RM999", "SGD999", "KRW999", "JPY999", "MYR999", "saves RM999", "S$999", "RM999.50"])
def test_a_fabricated_amount_glued_to_a_currency_code_is_now_checked_not_skipped(text):
    assert Decimal("999") in {v for _, k, v in extract_tokens(text).raw if k == "num"} or Decimal("999.5") in {v for _, k, v in extract_tokens(text).raw}
    assert not check_grounding(f"The trip {text}.", "Totals: 280 MYR", [], set(), {}).ok


def test_thousands_separators_are_read_whole():
    assert [v for _, _, v in extract_tokens("RM1,234.50").raw] == [Decimal("1234.5")]
    assert check_grounding("It costs RM1,234.50.", "Total 1,234.50 MYR", [], set(), {}).ok


def test_the_real_plans_facts_carry_rooms_and_the_modelled_cash_total_with_their_parts():
    r = solve(P, H, KL, with_alternatives=False)
    f = build_facts(OptimiseView(r, build_report(r, KL, P, H), H, False, 2), KL)
    text = "\n".join(f.lines)
    assert "Rooms: 280 MYR" in text and "Modelled cash total including rooms:" in text and "excluded, not free" in text
    rooms, cash, sights = (a for a, _, _ in f.roles)
    assert cash == rooms + sights                                                    # the evidence is internally consistent: cash total = sights and transport + rooms
    assert "generalised" not in text.lower() and "true cost" not in text.lower()   # the score is a different fact and is not mixed in


def cited(*items):
    return json.dumps({"sentences": [{"text": t, "fact_ids": ids} for t, ids in items]})


def ids_of(f, prefix):
    return next(i for i, (k, l) in enumerate(f.numbered(), 1) if l.startswith(prefix)), None


def run(sentences):
    r = solve(P, H, KL, with_alternatives=False)
    v = OptimiseView(r, build_report(r, KL, P, H), H, False, 2)
    f = build_facts(v, KL)
    rooms_id = f"F{ids_of(f, 'Rooms:')[0]}"
    cash_id = f"F{ids_of(f, 'Modelled cash total')[0]}"
    rooms, cash, _ = (int(a) for a, _, _ in f.roles)
    mk = {"{R}": str(rooms), "{C}": str(cash), "{RID}": rooms_id, "{CID}": cash_id}
    items = []
    for t, ids in sentences:
        for a, b in mk.items():
            t = t.replace(a, b)
            ids = [i.replace(a, b) for i in ids]
        items.append((t, ids))
    return explain(v, KL, MockLLM([cited(*items)]), None, {"kuala_lumpur": KL})


def test_an_explanation_that_states_the_room_and_cash_totals_correctly_is_accepted_with_its_citations():
    e = run([("The two nights of rooms cost RM{R}.", ["{RID}"]), ("Modelled total spending including rooms is RM{C}.", ["{CID}"]), ("The plan is validated against the sample data.", ["F4"])])
    assert e.source == "llm" and e.cited and len(e.sentences) == 3 and e.dropped == 0


def test_the_same_numbers_used_for_the_wrong_items_are_dropped_and_the_safe_fallback_is_used():
    e = run([("The rooms cost RM{C}.", ["{CID}"]), ("Total spending is RM{R}.", ["{RID}"]), ("The plan is validated against the sample data.", ["F4"])])
    assert e.source == "template" and e.dropped >= 2 and any("wrong item" in t for t in e.grounding.rejected_tokens)


def test_a_fabricated_total_is_still_rejected():
    e = run([("The rooms cost RM{R}.", ["{RID}"]), ("Modelled total spending including rooms is RM9999.", ["{CID}"])])
    assert e.source == "template"


def test_the_api_returns_the_safe_fallback_with_a_truthful_account_of_the_attempt():
    app.dependency_overrides[get_llm_client] = lambda: MockLLM([cited(("The rooms cost RM999.", ["F10"]), ("Spending is RM1.", ["F11"]))])
    with TestClient(app) as api:
        j = api.post("/optimise", json={"city_id": "kuala_lumpur", "preferences": P.model_dump(), "hotel_id": H, "explain": True}).json()
    app.dependency_overrides.pop(get_llm_client, None)
    ex = j["explanation"]
    assert ex["source"] == "template" and ex["call_count"] == 1 and ex["reason"]                    # a call WAS made; its text was NOT accepted
