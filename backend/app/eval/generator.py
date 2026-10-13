"""Seeded generator of evaluation trips. Same seed + same dataset => byte-identical scenario file (docs/eval-scenarios.json).

Every constant below is a JUDGEMENT CALL that shapes the sample; they are written into the JSON file so a reader can see them.
The 12 attractions in the sample dataset are the pool, so "scattered" or "easy" depends entirely on this small, tuned dataset.
"""
import json
import random

from app.data.loader import Dataset
from app.schemas import Preferences

GENERATOR_VERSION = 1
DAYS_RANGE = (2, 4)
ATTRACTIONS_RANGE = (3, 9)
MUST_RANGE = (0, 3)
BUDGET_KIND_WEIGHTS = {"none": 3, "soft": 3, "strict": 4}   # relative weights
STRICT_FACTOR_RANGE = (0.25, 1.4)   # multiple of the reference spend; below ~0.7 is deliberately tight
SOFT_FACTOR_RANGE = (0.4, 1.5)
FARE_REFERENCE_JPY_PER_LEG = 250    # rough reference only, to size budgets; NOT used by the optimiser
PACE = "balanced"                   # fixed: the default; pace is not varied
PARAMETERS = {"days_range": list(DAYS_RANGE), "attractions_range": list(ATTRACTIONS_RANGE), "must_range": list(MUST_RANGE),
              "budget_kind_weights": BUDGET_KIND_WEIGHTS, "strict_factor_range": list(STRICT_FACTOR_RANGE),
              "soft_factor_range": list(SOFT_FACTOR_RANGE), "fare_reference_jpy_per_leg": FARE_REFERENCE_JPY_PER_LEG, "pace": PACE,
              "hotel_assignment": "round-robin over the sorted hotel ids (each hotel is the base in turn)",
              "input_order": "uniformly shuffled order of the requested attractions (no geographic ordering)"}


def generate_trips(seed: int, n: int, ds: Dataset) -> list[dict]:
    rng = random.Random(seed)
    pool = sorted(ds.attractions)
    hotels = sorted(ds.hotels)
    kinds, weights = zip(*sorted(BUDGET_KIND_WEIGHTS.items()))
    trips = []
    for i in range(n):
        days = rng.randint(*DAYS_RANGE)
        requested = rng.sample(pool, rng.randint(*ATTRACTIONS_RANGE))  # already in random order
        k = min(rng.randint(*MUST_RANGE), len(requested))
        musts = set(rng.sample(requested, k))
        weekday = rng.randrange(7)
        kind = rng.choices(kinds, weights=weights)[0]
        budget, factor = None, None
        if kind != "none":
            lo, hi = STRICT_FACTOR_RANGE if kind == "strict" else SOFT_FACTOR_RANGE
            factor = round(rng.uniform(lo, hi), 3)
            ref = sum(ds.attractions[a].admission_cost or 0 for a in requested) + FARE_REFERENCE_JPY_PER_LEG * (len(requested) + days)
            budget = max(100, int(round(ref * factor / 100.0)) * 100)
        trips.append({"id": f"T{i + 1:03d}", "hotel_id": hotels[i % len(hotels)], "days": days, "start_weekday": weekday,
                      "order": requested, "must_visit": [a for a in requested if a in musts],
                      "budget_kind": kind, "budget": budget, "budget_factor": factor})
    return trips


def prefs_for(trip: dict, ds: Dataset) -> Preferences:
    """Everything not requested is skipped, so the solver's candidate set equals the baselines' pool."""
    return Preferences(days=trip["days"], pace=PACE, must_visit=list(trip["must_visit"]), start_weekday=trip["start_weekday"],
                       skip=[a for a in sorted(ds.attractions) if a not in trip["order"]],
                       budget=trip["budget"], strict_budget=trip["budget_kind"] == "strict")


def scenario_file_text(seed: int, n: int, ds: Dataset) -> str:
    doc = {"generator_version": GENERATOR_VERSION, "seed": seed, "n": n, "parameters": PARAMETERS,
           "note": "SAMPLE data and synthetic trips. Attraction ids refer to backend/app/data/attractions.json; hotels are FICTIONAL.",
           "trips": generate_trips(seed, n, ds)}
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
