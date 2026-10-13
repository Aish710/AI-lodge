"""GET /data/places: read-only reference data for the UI. Never includes the untrusted `description` field."""
import json

from fastapi.testclient import TestClient

from app.main import app


def test_places_has_coordinates_provenance_and_no_descriptions():
    with TestClient(app) as c:
        r = c.get("/data/places")
    assert r.status_code == 200
    d = r.json()
    assert len(d["attractions"]) == 12 and len(d["hotels"]) == 3
    assert "description" not in json.dumps(d)
    for a in d["attractions"]:
        assert 35.4 < a["lat"] < 35.95 and 139.3 < a["lon"] < 140.0
        assert set(a["source"]) == {"record", "hours", "cost"} and "verified" not in a["source"].values()
        assert set(a["opening_hours"]) == {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    assert any(a["admission_cost"] is None for a in d["attractions"])  # unknown prices stay null, never 0
    assert d["travel_times_source"] == "estimated" and "Hotels are fictional" in d["disclaimer"]


def test_places_is_in_the_cheap_rate_tier():
    with TestClient(app) as c:
        codes = [c.get("/data/places").status_code for _ in range(60)]
    assert set(codes) == {200}  # the standard tier would have stopped at 30 per minute
