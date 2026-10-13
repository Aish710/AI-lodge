import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data import loader
from app.data.loader import DataError, is_open, load_attractions_file, load_dataset
from app.main import app
from app.schemas import Attraction, Preferences, WEEKDAYS, to_minutes

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


def test_dataset_validates_and_counts(ds):
    assert len(ds.attractions) == 12
    assert len(ds.hotels) == 3


def test_no_record_is_verified(ds):
    provs = []
    for a in ds.attractions.values():
        provs += [a.provenance, a.hours_provenance, a.cost_provenance]
    provs += [h.provenance for h in ds.hotels.values()]
    assert all(p.source_status == "sample" for p in provs)
    assert ds.matrix_meta["source_status"] == "estimated"


def test_data_includes_required_edge_cases(ds):
    atts = list(ds.attractions.values())
    assert any(a.advance_booking_required for a in atts)
    assert any(a.admission_cost is None for a in atts)
    assert any(all(v == "unknown" for v in a.opening_hours.values()) for a in atts)
    assert sum(any(v is None for v in a.opening_hours.values()) for a in atts) >= 2  # weekly closing days
    assert {a.indoor for a in atts} == {True, False}


def test_hotel_names_are_marked_fictional(ds):
    assert all("fictional" in h.name.lower() for h in ds.hotels.values())


def test_matrix_properties(ds):
    ids = set(ds.attractions) | set(ds.hotels)
    for table in (ds.minutes, ds.fare_jpy):
        assert set(table) == ids
        for a in ids:
            assert set(table[a]) == ids  # complete
            assert table[a][a] == 0  # zero diagonal
            for b in ids:
                assert table[a][b] == table[b][a]  # symmetric
                if a != b:
                    assert table[a][b] > 0
    assert "ESTIMATE" in ds.matrix_meta["note"]


def test_matrix_is_reproducible(ds, tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_travel_matrix

    rebuilt = build_travel_matrix.build()
    on_disk = json.loads((loader.DATA_DIR / "travel_times.json").read_text())
    assert rebuilt == on_disk


def test_opening_hours_are_valid_ranges_closed_or_unknown(ds):
    for a in ds.attractions.values():
        assert set(a.opening_hours) == set(WEEKDAYS)
        for day in a.opening_hours.values():
            assert day is None or day == "unknown" or all(to_minutes(c) > to_minutes(o) for o, c in day)


def test_is_open_unknown_is_never_open(ds):
    akiba = ds.attractions["akihabara"]
    assert is_open(akiba, "sat", "12:00") == "unknown"
    assert is_open(akiba, "sat", "12:00") is not True


def test_is_open_known_hours(ds):
    museum = ds.attractions["tokyo_national_museum"]
    assert is_open(museum, "tue", "10:00") is True
    assert is_open(museum, "tue", "17:00") is False  # closing time is exclusive
    assert is_open(museum, "tue", "09:00") is False
    assert is_open(museum, "mon", "12:00") is False  # weekly closing day


def test_travel_lookup(ds):
    assert loader.travel_minutes(ds, "senso_ji", "senso_ji") == 0
    assert loader.travel_minutes(ds, "senso_ji", "tokyo_skytree") > 0
    assert loader.travel_fare(ds, "senso_ji", "tokyo_skytree") > 0
    with pytest.raises(DataError):
        loader.travel_minutes(ds, "senso_ji", "nowhere")


def test_cheap_hotel_transport_can_erase_saving(ds):
    # Sanity check on the demo data: the cheapest hotel is the farthest from the sight cluster.
    def avg_minutes(h):
        return sum(ds.minutes[h][a] for a in ds.attractions) / len(ds.attractions)

    cheapest = min(ds.hotels.values(), key=lambda h: h.nightly_rate)
    others = [h for h in ds.hotels.values() if h.id != cheapest.id]
    assert cheapest.area == "Odaiba"
    assert all(avg_minutes(cheapest.id) > avg_minutes(h.id) for h in others)


def test_loader_rejects_nonexistent_must_visit_id(ds):
    with pytest.raises(DataError, match="atlantis"):
        loader.validate_must_visit(ds, ["senso_ji", "atlantis"])
    loader.validate_must_visit(ds, ["senso_ji"])  # valid ids pass


def test_loader_error_names_bad_record(tmp_path):
    bad = json.loads((loader.DATA_DIR / "attractions.json").read_text())
    bad[3]["duration_minutes"] = 0
    for name in ("hotels.json", "travel_times.json"):
        (tmp_path / name).write_text((loader.DATA_DIR / name).read_text())
    (tmp_path / "attractions.json").write_text(json.dumps(bad))
    with pytest.raises(DataError, match=bad[3]["id"]):
        load_dataset(tmp_path)


def test_strict_schema_rejects_coercion_and_bad_values():
    rec = json.loads((loader.DATA_DIR / "attractions.json").read_text())[0]
    Attraction.model_validate_json(json.dumps(rec))
    for field, value in [("duration_minutes", "90"), ("lat", 51.5), ("admission_cost", 0.5), ("extra", 1)]:
        bad = {**rec, field: value}
        with pytest.raises(Exception):
            Attraction.model_validate_json(json.dumps(bad))


def test_preferences_validators():
    Preferences(days=2)
    with pytest.raises(Exception):
        Preferences(days=8)
    with pytest.raises(Exception):
        Preferences(days=2, day_start="18:00", day_end="09:00")
    with pytest.raises(Exception):
        Preferences(days=2, strict_budget=True)  # strict budget needs a budget
    with pytest.raises(Exception):
        Preferences(days="2")  # no silent coercion


def test_poisoned_description_is_plain_data_and_not_in_real_dataset(ds):
    loaded = load_attractions_file(FIXTURES / "poisoned_attraction.json")
    poisoned = loaded["poisoned_test_place"]
    assert "Ignore previous instructions" in poisoned.description  # kept verbatim, as data
    assert isinstance(poisoned.description, str)
    assert poisoned.opening_hours["mon"] == [["09:00", "17:00"]]  # the text changed nothing
    assert "poisoned_test_place" not in ds.attractions
    assert not any("ignore previous" in a.description.lower() for a in ds.attractions.values())


def test_health_and_summary():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok" and r.json()["mode"] in ("llm", "sample")
        s = client.get("/data/summary").json()
        assert s["counts"] == {"attractions": 12, "hotels": 3, "matrix_nodes": 15}
        assert s["provenance"]["attractions"] == {"sample": 12}
        assert s["data_quality"]["verified_records"] == 0
        assert s["data_quality"]["attractions_with_unknown_hours"] == 1
        assert s["data_quality"]["attractions_with_unknown_cost"] == 1


def test_cors_allows_localhost_only():
    with TestClient(app) as client:
        ok = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
        bad = client.get("/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in bad.headers
