"""Server-built sentences use the SELECTED city's currency code and never another city's (a Seoul sentence must not say JPY)."""
import json

import pytest

from app.data.loader import load_all_city_datasets
from app.llm.explain import explain
from app.money import code, display_amount, money, per_hour, signed
from app.optimiser.hotel_compare import compare_hotels
from app.optimiser.replan import ChangeBudgetOp, RemoveOp, SwitchHotelOp, replan
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import Preferences
from app.validator.feasibility_report import build_report
from app import config

DATASETS = load_all_city_datasets()
CITIES = sorted(DATASETS)
CODES = {c: DATASETS[c].city.currency_code for c in CITIES}


def _prefs(ds, **kw):
    c = ds.city
    return Preferences(days=2, day_start=c.default_day_start, day_end=c.default_day_end, value_of_time_per_hour=c.default_value_of_time_per_hour, **kw)


def _strings(obj):
    """Every string in a (nested) result."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def _assert_only_own_currency(city, texts):
    foreign = [v for c, v in CODES.items() if v != CODES[city]] + ["yen"]
    blob = "\n".join(texts)
    for f in foreign:
        assert f not in blob, f"{city}: found '{f}' in: " + next(t for t in texts if f in t)[:300]


def test_money_helpers_print_the_cities_own_code():
    for city in CITIES:
        ds = DATASETS[city]
        c = CODES[city]
        assert money(1500, ds) == f"1,500 {c}"
        assert signed(-2413, ds) == f"-2,413 {c}" and signed(2413, ds) == f"+2,413 {c}" and signed(5, ds, "min") == "+5 min"
        assert per_hour(1000, ds) == f"1,000 {c}/h"
        assert display_amount(1500, ds).startswith("about ") and "SAMPLE rate" in display_amount(1500, ds)
    assert money(1500, DATASETS["tokyo"]) == "1,500 JPY" and money(1500, DATASETS["seoul"]) == "1,500 KRW"
    assert display_amount(11000, DATASETS["tokyo"]) == "about S$100 at the SAMPLE rate"


@pytest.mark.parametrize("city", CITIES)
def test_hotel_comparison_sentences_and_explanation_use_the_cities_currency(city):
    ds = DATASETS[city]
    hotels = list(ds.hotels)[:2]
    comp = compare_hotels(_prefs(ds, must_visit=[next(iter(ds.attractions))]), hotels, ds, include_sensitivity=True,
                          vot_range=(0, ds.city.default_value_of_time_per_hour * 3), time_limit=30)
    texts = [comp.insight, comp.sensitivity.flip_summary, *comp.warnings, explain(comp, ds, None).text]
    assert CODES[city] in "\n".join(texts), "the city's own code should appear somewhere in the comparison sentences"
    _assert_only_own_currency(city, texts)


@pytest.mark.parametrize("city", CITIES)
def test_optimise_report_and_conflict_sentences_use_the_cities_currency(city):
    ds = DATASETS[city]
    hotel = next(iter(ds.hotels))
    first = next(iter(ds.attractions))
    ok = _prefs(ds, budget=10_000_000)
    res = solve(ok, hotel, ds, objective=ObjectiveSpec("true_cost", ok.value_of_time_per_hour, config.MISSED_PREFERENCE_PENALTY_JPY), max_seconds=20)
    texts = [c.message for c in build_report(res, ds, ok, hotel).checks]
    # a strict budget nobody can meet -> a conflict sentence with amounts
    tight = _prefs(ds, budget=1, strict_budget=True, must_visit=[first])
    bad = solve(tight, hotel, ds, max_seconds=10)
    texts += [c.message for c in bad.conflicts] + bad.notes
    # a soft budget exceeded -> a note with an amount
    soft = _prefs(ds, budget=1, must_visit=[first])
    texts += solve(soft, hotel, ds, max_seconds=10).notes
    joined = "\n".join(texts)
    assert CODES[city] in joined
    _assert_only_own_currency(city, texts)


@pytest.mark.parametrize("city", CITIES)
def test_replan_summary_diff_warnings_and_explanation_use_the_cities_currency(city):
    ds = DATASETS[city]
    hotels = list(ds.hotels)
    atts = list(ds.attractions)
    p = _prefs(ds, must_visit=[atts[0]])
    cur = solve(p, hotels[0], ds, objective=ObjectiveSpec("true_cost", p.value_of_time_per_hour, config.MISSED_PREFERENCE_PENALTY_JPY), max_seconds=20)
    r = replan(p, cur, [SwitchHotelOp(op="switch_hotel", hotel_id=hotels[1]), ChangeBudgetOp(op="change_budget", budget=5_000_000, strict=False)], ds, max_seconds=20)
    assert r.status == "applied", r.summary
    texts = [*_strings(r.model_dump()), explain(r, ds, None).text]
    assert f" {CODES[city]}" in "\n".join(texts)
    _assert_only_own_currency(city, texts)
    # and an infeasible replan (strict budget of 1)
    inf = replan(p, cur, [ChangeBudgetOp(op="change_budget", budget=1, strict=True)], ds, max_seconds=20)
    _assert_only_own_currency(city, [*_strings(inf.model_dump()), explain(inf, ds, None).text])


def test_the_api_responses_carry_no_foreign_code_either():
    from fastapi.testclient import TestClient

    from app.hardening.config import HConfig
    from app.main import create_app

    app = create_app(HConfig(rate_expensive_per_min=10_000, rate_standard_per_min=10_000, rate_cheap_per_min=10_000))
    with TestClient(app) as c:
        for city in CITIES:
            ds = DATASETS[city]
            body = {"city_id": city, "preferences": json.loads(_prefs(ds, budget=5_000_000).model_dump_json()), "hotel_ids": list(ds.hotels)[:2], "explain": True}
            out = c.post("/compare-hotels", json=body).json()
            # the labelled FX sentence legitimately names the city's own pair, e.g. "1 SGD = 110 JPY" for Tokyo: skip fx labels
            texts = [out["insight"], *out["warnings"], out["explanation"]["text"]]
            _assert_only_own_currency(city, texts)
