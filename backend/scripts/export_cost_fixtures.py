"""Writes frontend/tests/fixtures/optimise-cost-<city>.json: a REAL /optimise response (with the server-side cost_summary) per city, so the
frontend card tests assert against numbers the backend produced, not numbers typed by hand. Run from backend/:  python scripts/export_cost_fixtures.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import Preferences  # noqa: E402

OUT = ROOT.parent / "frontend" / "tests" / "fixtures"

if __name__ == "__main__":
    with TestClient(app) as c:
        for city, ds in load_all_city_datasets().items():
            prefs = Preferences(days=3, pace="packed", budget=int(ds.city.default_value_of_time_per_hour * 40), day_start=ds.city.default_day_start, day_end=ds.city.default_day_end,
                                value_of_time_per_hour=ds.city.default_value_of_time_per_hour)
            hotel = next(iter(ds.hotels))
            r = c.post("/optimise", json={"city_id": city, "preferences": prefs.model_dump(), "hotel_id": hotel}).json()
            r["_request"] = {"preferences": prefs.model_dump(), "hotel_id": hotel}
            (OUT / f"optimise-cost-{city}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
            print("wrote", city, r["cost_summary"]["trip"]["cash_total"], r["cost_summary"]["currency"])
