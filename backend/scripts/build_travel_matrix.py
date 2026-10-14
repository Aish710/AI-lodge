"""Build travel_times.json. Deterministic: same inputs -> identical output.

ESTIMATE, not real transit data. Every entry is computed from straight-line distance:
  minutes = ceil(haversine_km * DETOUR_FACTOR / SPEED_KMH * 60) + PER_LEG_OVERHEAD_MIN
  fare    = round_to_10(BASE_FARE_JPY + FARE_PER_KM_JPY * haversine_km * DETOUR_FACTOR)
Run:
  python backend/scripts/build_travel_matrix.py
  python backend/scripts/build_travel_matrix.py --city singapore
"""
import argparse
import json
import math
from pathlib import Path

# ---- constants (also written to _meta in the output) ----
DETOUR_FACTOR = 1.3        # real routes are longer than straight lines
SPEED_KMH = 20.0           # average door-to-door urban transit speed
PER_LEG_OVERHEAD_MIN = 10  # walking to station, waiting, transfers
BASE_FARE_JPY = 150
FARE_PER_KM_JPY = 20
EARTH_RADIUS_KM = 6371.0088

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"
CITIES_DIR = DATA_DIR / "cities"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def leg(a: dict, b: dict, model: dict | None = None) -> tuple[int, int]:
    if model is None:
        detour = DETOUR_FACTOR
        speed = SPEED_KMH
        overhead = PER_LEG_OVERHEAD_MIN
        base = BASE_FARE_JPY
        per_km = FARE_PER_KM_JPY
        round_to = 10
    else:
        detour = model["detour_factor"]
        speed = model["speed_kmh"]
        overhead = model["per_leg_overhead_min"]
        base = model["base_fare"]
        per_km = model["fare_per_km"]
        round_to = 1
    road_km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * detour
    minutes = math.ceil(road_km / speed * 60) + overhead
    fare = int(round((base + per_km * road_km) / round_to)) * round_to
    return minutes, fare


def build(data_dir: Path = DATA_DIR) -> dict:
    data_dir = Path(data_dir)
    city_path = data_dir / "city.json"
    city = json.loads(city_path.read_text()) if city_path.exists() else None
    model = city["transit_model"] if city else None
    places = json.loads((data_dir / "attractions.json").read_text()) + json.loads((data_dir / "hotels.json").read_text())
    places.sort(key=lambda p: p["id"])
    ids = [p["id"] for p in places]
    minutes = {a: {b: 0 for b in ids} for a in ids}
    fare = {a: {b: 0 for b in ids} for a in ids}
    for i, a in enumerate(places):
        for b in places[i + 1:]:
            m, f = leg(a, b, model)
            minutes[a["id"]][b["id"]] = minutes[b["id"]][a["id"]] = m
            fare[a["id"]][b["id"]] = fare[b["id"]][a["id"]] = f
    return {
        "_meta": {
            **({"city_id": city["id"], "currency_code": city["currency_code"]} if city else {}),
            "source_status": "estimated",
            "note": "ESTIMATE, not real transit data. All entries computed from straight-line distance.",
            "formula_minutes": "ceil(haversine_km * detour_factor / speed_kmh * 60) + per_leg_overhead_min",
            "formula_fare_jpy": ("round(base_fare + fare_per_km * haversine_km * detour_factor)"
                                 if model else "round_to_10(base_fare_jpy + fare_per_km_jpy * haversine_km * detour_factor)"),
            "detour_factor": model["detour_factor"] if model else DETOUR_FACTOR,
            "speed_kmh": model["speed_kmh"] if model else SPEED_KMH,
            "per_leg_overhead_min": model["per_leg_overhead_min"] if model else PER_LEG_OVERHEAD_MIN,
            "base_fare_jpy": model["base_fare"] if model else BASE_FARE_JPY,
            "fare_per_km_jpy": model["fare_per_km"] if model else FARE_PER_KM_JPY,
        },
        "nodes": ids,
        "minutes": minutes,
        "fare_jpy": fare,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", help="city pack id under backend/app/data/cities")
    args = parser.parse_args()
    data_dir = CITIES_DIR / args.city if args.city else DATA_DIR
    out = data_dir / "travel_times.json"
    out.write_text(json.dumps(build(data_dir), indent=1) + "\n")
    print(f"wrote {out}")
