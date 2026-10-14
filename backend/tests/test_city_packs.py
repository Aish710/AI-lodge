import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.data.loader import CITIES_DIR, load_all_city_datasets
from app.llm.extract import extract_preferences
from app.main import app
from app.optimiser.solver import solve
from app.schemas import Preferences, WEEKDAYS, to_minutes
from app.validator.feasibility_report import build_report
from llm_mock import MockLLM, extraction

ROOT = Path(__file__).resolve().parents[1]


def _prefs(ds, must):
    return Preferences(
        days=2,
        must_visit=must,
        pace="balanced",
        day_start=ds.city.default_day_start,
        day_end=ds.city.default_day_end,
        value_of_time_per_hour=ds.city.default_value_of_time_per_hour,
    )


def test_city_packs_have_required_sample_integrity():
    datasets = load_all_city_datasets()
    assert set(datasets) == {"tokyo", "singapore", "seoul"}
    for city_id, ds in datasets.items():
        atts = list(ds.attractions.values())
        assert len(atts) >= (12 if city_id == "tokyo" else 10)
        assert len(ds.hotels) == 3
        assert all(a.provenance.source_status == "sample" for a in atts)
        assert all(a.hours_provenance.source_status == "sample" for a in atts)
        assert all(a.cost_provenance.source_status == "sample" for a in atts)
        assert all(h.provenance.source_status == "sample" and "fictional" in h.name.lower() for h in ds.hotels.values())
        assert ds.matrix_meta["source_status"] == "estimated"
        assert any(a.advance_booking_required for a in atts)
        assert any(a.admission_cost is None for a in atts)
        assert any(all(v == "unknown" for v in a.opening_hours.values()) for a in atts)
        assert sum(any(v is None for v in a.opening_hours.values()) for a in atts) >= 2
        assert {a.indoor for a in atts} == {True, False}
        for a in atts:
            if city_id != "tokyo":
                assert a.aliases
            assert set(a.opening_hours) == set(WEEKDAYS)
            for day in a.opening_hours.values():
                assert day is None or day == "unknown" or all(to_minutes(c) > to_minutes(o) for o, c in day)


def test_city_matrices_are_generated_complete_symmetric_and_reproducible():
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_travel_matrix

    for city_id, ds in load_all_city_datasets().items():
        ids = set(ds.attractions) | set(ds.hotels)
        for table in (ds.minutes, ds.fare_jpy):
            assert set(table) == ids
            for a in ids:
                assert set(table[a]) == ids
                assert table[a][a] == 0
                for b in ids:
                    assert table[a][b] == table[b][a]
                    if a != b:
                        assert table[a][b] > 0
        if city_id != "tokyo":
            assert build_travel_matrix.build(CITIES_DIR / city_id) == json.loads((CITIES_DIR / city_id / "travel_times.json").read_text())


def test_data_routes_select_city_and_list_counts():
    with TestClient(app) as c:
        cities = c.get("/data/cities").json()["cities"]
        assert {x["id"] for x in cities} == {"tokyo", "singapore", "seoul"}
        sg = c.get("/data/places", params={"city_id": "singapore"}).json()
        assert sg["city"]["currency_code"] == "SGD"
        assert len(sg["attractions"]) == 10 and len(sg["hotels"]) == 3
        assert "description" not in json.dumps(sg)
        summary = c.get("/data/summary", params={"city_id": "seoul"}).json()
        assert summary["counts"] == {"attractions": 10, "hotels": 3, "matrix_nodes": 13}
        assert c.get("/data/places", params={"city_id": "atlantis"}).status_code == 422
        assert {c.get("/data/cities").status_code for _ in range(60)} == {200}


def test_cross_city_ids_are_rejected_by_optimise_and_replan():
    with TestClient(app) as c:
        tokyo_prefs = {"days": 2, "must_visit": ["gyeongbokgung"], "day_start": "09:00", "day_end": "19:00"}
        bad = c.post("/optimise", json={"city_id": "tokyo", "preferences": tokyo_prefs, "hotel_id": "hotel_lantern_asakusa"})
        assert bad.status_code == 200
        assert bad.json()["result"]["status"] == "infeasible"

        seoul_prefs = {"days": 2, "must_visit": ["gyeongbokgung"], "day_start": "09:00", "day_end": "19:00", "value_of_time_per_hour": 15000}
        seoul = c.post("/optimise", json={"city_id": "seoul", "preferences": seoul_prefs, "hotel_id": "hotel_jongno_garden"}).json()["result"]
        mixed = c.post("/replan", json={"city_id": "tokyo", "preferences": seoul_prefs, "current_result": seoul, "operations": []})
        assert mixed.status_code == 422
        assert mixed.json()["error"]["code"] == "invalid_schedule"


def test_display_fx_is_city_specific_and_hand_computed():
    with TestClient(app) as c:
        p = {"days": 2, "must_visit": ["gardens_by_the_bay"], "value_of_time_per_hour": 18}
        out = c.post("/compare-hotels", json={"city_id": "singapore", "preferences": p, "hotel_ids": ["hotel_river_rochore", "hotel_bay_lantern"]}).json()
    assert out["display_currency"] == "USD"
    hid = out["results"][0]["hotel_id"]
    true_cost = out["results"][0]["breakdown"]["true_cost_jpy"]
    assert out["display_values"][hid]["true_cost"] == round(true_cost * 0.74, 2)


def test_solver_and_validator_smoke_per_city():
    for city_id, ds in load_all_city_datasets().items():
        must = [next(iter(ds.attractions))]
        hotel_id = next(iter(ds.hotels))
        prefs = _prefs(ds, must)
        res = solve(prefs, hotel_id, ds, max_seconds=5)
        assert res.status == "feasible"
        assert build_report(res, ds, prefs, hotel_id).overall != "fail"


def test_cross_city_name_gets_switch_city_hint_in_mock_llm_path():
    from app.llm.extract import resolve_list

    datasets = load_all_city_datasets()
    resolved, unresolved, ambiguities = resolve_list(["Gyeongbokgung"], datasets["tokyo"], all_datasets=datasets)
    assert not resolved and not ambiguities
    assert unresolved and "switch city" in unresolved[0].message.lower() and "Seoul" in unresolved[0].message


def test_city_descriptions_never_reach_extraction_prompt():
    for ds in load_all_city_datasets().values():
        mock = MockLLM([extraction(must_visit_names=[next(iter(ds.attractions.values())).name])])
        extract_preferences("2 days", ds, mock)
        for a in ds.attractions.values():
            assert a.description not in mock.all_prompt_text
