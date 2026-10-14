"""Write real /data/places responses for every city into frontend/tests/fixtures/places-<city>.json (in-process, no network).
Run from backend/:  python scripts/export_frontend_fixtures.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "frontend" / "tests" / "fixtures"

with TestClient(app) as c:
    for city in c.get("/data/cities").json()["cities"]:
        body = c.get("/data/places", params={"city_id": city["id"]}).json()
        (OUT / f"places-{city['id']}.json").write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n")
        print("wrote", city["id"], len(body["attractions"]), "sights", len(body["hotels"]), "hotels")
