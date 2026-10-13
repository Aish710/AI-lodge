"""Build backend/app/data/travel_times.json. Deterministic: same inputs -> identical output.

ESTIMATE, not real transit data. Every entry is computed from straight-line distance:
  minutes = ceil(haversine_km * DETOUR_FACTOR / SPEED_KMH * 60) + PER_LEG_OVERHEAD_MIN
  fare    = round_to_10(BASE_FARE_JPY + FARE_PER_KM_JPY * haversine_km * DETOUR_FACTOR)
Run:  python backend/scripts/build_travel_matrix.py
"""
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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def leg(a: dict, b: dict) -> tuple[int, int]:
    road_km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * DETOUR_FACTOR
    minutes = math.ceil(road_km / SPEED_KMH * 60) + PER_LEG_OVERHEAD_MIN
    fare = int(round((BASE_FARE_JPY + FARE_PER_KM_JPY * road_km) / 10.0)) * 10
    return minutes, fare


def build() -> dict:
    places = json.loads((DATA_DIR / "attractions.json").read_text()) + json.loads(
        (DATA_DIR / "hotels.json").read_text()
    )
    places.sort(key=lambda p: p["id"])
    ids = [p["id"] for p in places]
    minutes = {a: {b: 0 for b in ids} for a in ids}
    fare = {a: {b: 0 for b in ids} for a in ids}
    for i, a in enumerate(places):
        for b in places[i + 1:]:
            m, f = leg(a, b)
            minutes[a["id"]][b["id"]] = minutes[b["id"]][a["id"]] = m
            fare[a["id"]][b["id"]] = fare[b["id"]][a["id"]] = f
    return {
        "_meta": {
            "source_status": "estimated",
            "note": "ESTIMATE, not real transit data. All entries computed from straight-line distance.",
            "formula_minutes": "ceil(haversine_km * detour_factor / speed_kmh * 60) + per_leg_overhead_min",
            "formula_fare_jpy": "round_to_10(base_fare_jpy + fare_per_km_jpy * haversine_km * detour_factor)",
            "detour_factor": DETOUR_FACTOR,
            "speed_kmh": SPEED_KMH,
            "per_leg_overhead_min": PER_LEG_OVERHEAD_MIN,
            "base_fare_jpy": BASE_FARE_JPY,
            "fare_per_km_jpy": FARE_PER_KM_JPY,
        },
        "nodes": ids,
        "minutes": minutes,
        "fare_jpy": fare,
    }


if __name__ == "__main__":
    out = DATA_DIR / "travel_times.json"
    out.write_text(json.dumps(build(), indent=1) + "\n")
    print(f"wrote {out}")
