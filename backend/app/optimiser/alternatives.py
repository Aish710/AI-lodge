"""Budget/time alternatives: a bounded set of real optimiser plans, filtered by dominance.

Candidate generation (documented, bounded): for each candidate hotel and each of VOT_FACTORS times the traveller's value of time, the shipped optimiser (`solve`) is run once with the
SAME constraints. Each candidate is measured on three things that are not mixed into one weight:
  money      rooms + admissions + estimated transport (known prices only; the score and monetised time are NOT money)
  minutes    estimated travel minutes (straight-line based)
  coverage   optional sights placed
A candidate is DOMINATED if another has no more money, no more minutes and no fewer optional sights, and is strictly better on at least one. Identical plans (same hotel and the same
schedule) are shown once. What remains is the non-dominated set of THESE candidates: it is not claimed to be the complete Pareto frontier of all possible plans.
"""
import time

from app.data.loader import Dataset
from app.fingerprint import plan_fingerprint
from app.money import missed_preference_penalty
from app.optimiser.hotel_compare import _breakdown
from app.optimiser.solver import ObjectiveSpec, missed_preferences_for, solve
from app.schemas import Preferences, nights_for
from app.validator.feasibility_report import build_report

VOT_FACTORS = (0, 0.5, 1, 2, 4, 8)


def dominates(a: dict, b: dict) -> bool:
    ge = a["money"] <= b["money"] and a["minutes"] <= b["minutes"] and a["coverage"] >= b["coverage"]
    gt = a["money"] < b["money"] or a["minutes"] < b["minutes"] or a["coverage"] > b["coverage"]
    return ge and gt


def pareto(cands: list[dict]) -> list[dict]:
    return [c for c in cands if not any(dominates(o, c) for o in cands if o is not c)]


def _signature(res) -> tuple:
    return tuple((d.day, tuple((s.attraction_id, s.start) for s in d.stops)) for d in res.days)


def explore(prefs: Preferences, hotel_ids: list[str], ds: Dataset, *, max_seconds: float, budget_seconds: float = 12.0) -> dict:
    t0 = time.monotonic()
    nights, _ = nights_for(prefs)
    base_vot = prefs.value_of_time_per_hour
    pen = missed_preference_penalty(ds)
    cands: list[dict] = []
    seen: set = set()
    tried = 0
    stopped_early = False
    for h in hotel_ids:
        for f in VOT_FACTORS:
            if time.monotonic() - t0 > budget_seconds:
                stopped_early = True
                break
            vot = round(base_vot * f)
            p = prefs.model_copy(update={"value_of_time_per_hour": vot})
            res = solve(p, h, ds, objective=ObjectiveSpec("true_cost", vot, pen), max_seconds=max_seconds, with_alternatives=False)
            tried += 1
            if res.status != "feasible" or build_report(res, ds, p, h).overall == "fail":
                continue
            sig = (h, _signature(res))
            if sig in seen:
                continue
            seen.add(sig)
            scheduled = {s.attraction_id for d in res.days for s in d.stops}
            res = res.model_copy(update={"missed_preferences": missed_preferences_for(p, h, ds, scheduled)})
            b_own = _breakdown(ds, p, h, res, nights, base_vot)          # scored at the TRAVELLER's value of time, whatever value generated the plan
            optional_placed = len(scheduled - set(prefs.must_visit))
            cands.append({"hotel_id": h, "hotel_name": ds.hotels[h].name, "generated_at_value_of_time": vot, "factor": f,
                          "money": b_own.rooms_jpy + b_own.admissions_jpy + b_own.transport_jpy, "rooms": b_own.rooms_jpy, "admissions": b_own.admissions_jpy,
                          "transport": b_own.transport_jpy, "minutes": b_own.travel_minutes, "coverage": optional_placed, "omitted": len(b_own.missed_preferences.attraction_ids),
                          "score_at_your_value_of_time": b_own.true_cost_jpy, "fingerprint": plan_fingerprint(p, h, ds)})
    front = pareto(cands)
    if not front:
        return {"candidates_tried": tried, "feasible_candidates": len(cands), "alternatives": [], "stopped_early": stopped_early, "method": _METHOD}
    picks: list[tuple[str, str, dict]] = []
    picks.append(("lowest_money", "Lowest spending", min(front, key=lambda c: (c["money"], c["minutes"], -c["coverage"], c["hotel_id"]))))
    picks.append(("least_travel", "Least estimated travel", min(front, key=lambda c: (c["minutes"], c["money"], -c["coverage"], c["hotel_id"]))))
    picks.append(("most_sights", "Most optional sights", min(front, key=lambda c: (-c["coverage"], c["money"], c["minutes"], c["hotel_id"]))))
    picks.append(("best_score", "Best overall at your value of time", min(front, key=lambda c: (c["score_at_your_value_of_time"], c["money"], c["hotel_id"]))))
    out, used = [], {}
    for key, label, c in picks:                                   # one card per distinct plan; a plan that wins several roles lists them all
        sig = (c["hotel_id"], c["fingerprint"])
        if sig in used:
            used[sig]["roles"].append(label)
            continue
        item = {**c, "key": key, "roles": [label]}
        used[sig] = item
        out.append(item)
    return {"candidates_tried": tried, "feasible_candidates": len(cands), "non_dominated": len(front), "alternatives": out, "stopped_early": stopped_early, "method": _METHOD}


_METHOD = ("A bounded search: the optimiser was run once per hotel and per value of time in " + ", ".join(f"{f}x" for f in VOT_FACTORS) + " your value of time. Plans that cost more, take longer "
           "and cover fewer optional sights than another are removed. The result is the non-dominated set of these plans, not a complete Pareto frontier. Money is rooms + admissions + estimated transport; "
           "the score is not money spent.")
