"""PROPOSALS ONLY: evaluates candidate edits to the cheap hotel on in-memory copies of the dataset.
Nothing in app/data is modified. Run from backend/:  python scripts/propose_hotel_adjustments.py
Output is printed (and quoted in docs/BUILD_NOTES.md); the owner decides whether to apply any of it.
"""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_travel_matrix as bm  # noqa: E402
from app.data.loader import load_dataset  # noqa: E402
from app.optimiser.hotel_compare import compare_hotels  # noqa: E402
from run_hotel_comparison import TRIPS  # noqa: E402

CHEAP = "hotel_harbour_odaiba"
CANDIDATES = [
    ("Current data (baseline)", {}),
    ("P1 rate only: Odaiba 8,000 -> 9,500 JPY", {"nightly_rate": 9500}),
    ("P2 location only: move to Wakasu/Shin-Kiba shore (35.6130, 139.8310)", {"lat": 35.6130, "lon": 139.8310}),
    ("P3 both: Wakasu/Shin-Kiba shore + rate 8,000 -> 8,500 JPY", {"lat": 35.6130, "lon": 139.8310, "nightly_rate": 8500}),
]


def variant(ds, changes):
    hotels = dict(ds.hotels)
    hotels[CHEAP] = ds.hotels[CHEAP].model_copy(update=changes)
    minutes = {a: dict(row) for a, row in ds.minutes.items()}
    fares = {a: dict(row) for a, row in ds.fare_jpy.items()}
    if "lat" in changes:
        h = hotels[CHEAP].model_dump()
        for aid, att in list(ds.attractions.items()) + [(k, v) for k, v in hotels.items() if k != CHEAP]:
            m, f = bm.leg(h, att.model_dump())
            minutes[CHEAP][aid] = minutes[aid][CHEAP] = m
            fares[CHEAP][aid] = fares[aid][CHEAP] = f
    return replace(ds, hotels=hotels, minutes=minutes, fare_jpy=fares)


def main():
    base = load_dataset()
    hotels = list(base.hotels)
    for label, changes in CANDIDATES:
        ds = variant(base, changes)
        print(f"\n### {label}")
        for title, prefs in TRIPS:
            c = compare_hotels(prefs, hotels, ds, include_sensitivity=True, time_limit=120)
            s = c.sensitivity
            costs = {r.hotel_id[6:]: r.breakdown.true_cost_jpy for r in c.results if r.breakdown}
            flips = [(f.from_winner[6:], f.to_winner[6:], f.value_of_time_per_hour, f.method) for f in s.flips]
            print(f"- {title}: true cost @1000 JPY/h {costs}; winner {c.best_by_true_cost[6:]}; flips {flips or 'none'}; approximate {s.approximate}")


if __name__ == "__main__":
    main()
