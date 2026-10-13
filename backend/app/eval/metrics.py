"""Evaluation metrics. Pure functions over per-trip result dicts, plus the two functions that RUN a trip.

The solver, baselines, validator and hotel comparison are called directly (not through the HTTP API). Wall-clock numbers are kept
in fields named `runtime_seconds` / under metrics["machine_dependent"] so determinism checks can exclude them.
"""
import statistics
import time
from collections import Counter

from app import config
from app.data.loader import Dataset
from app.eval import independent
from app.eval.generator import prefs_for
from app.optimiser.baseline import baseline, nearest_neighbour
from app.optimiser.hotel_compare import SolveCache, compare_hotels, sensitivity
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import Preferences, SolveResult
from app.validator.feasibility_report import build_report

HOTEL_VOTS = (500, 1000, 2000)   # JPY per hour; 1000 is the product default
DEFAULT_VOT = 1000
SENSITIVITY_RANGE = (0, 3000)


# ---------------------------------------------------------------------------------------------------------------------
# Statistics helpers (no rounding here; rounding happens only at display time, see claims.py)
# ---------------------------------------------------------------------------------------------------------------------
def describe(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(xs), "mean": statistics.fmean(xs), "median": statistics.median(xs), "min": min(xs), "max": max(xs)}


def reduction(baseline_value: float, solver_value: float) -> tuple[float, float | None]:
    """(absolute reduction, percent reduction of the baseline). Positive = the solver is better. Percent is None if the baseline is 0."""
    diff = baseline_value - solver_value
    return diff, (100.0 * diff / baseline_value if baseline_value else None)


def _split(rows: list[dict]) -> dict:
    return {"better": sum(r["reduction_minutes"] > 0 for r in rows), "equal": sum(r["reduction_minutes"] == 0 for r in rows),
            "worse": sum(r["reduction_minutes"] < 0 for r in rows)}


# ---------------------------------------------------------------------------------------------------------------------
# Running one trip
# ---------------------------------------------------------------------------------------------------------------------
def _placed(res: SolveResult) -> list[str]:
    return [s.attraction_id for d in res.days for s in d.stops]


def _plan_record(res: SolveResult, ds: Dataset, prefs: Preferences, hotel: str, is_solver: bool) -> dict:
    placed = _placed(res)
    rec = {"status": res.status, "placed": placed, "stops_per_day": [len(d.stops) for d in res.days], "conflict_codes": sorted({c.code for c in res.conflicts}),
           "runtime_seconds": res.solver_meta.runtime_seconds if res.solver_meta else None,
           "solver_status": res.solver_meta.solver_status if res.solver_meta else None}
    if is_solver and res.status != "feasible":
        rec.update(travel_minutes=None, total_jpy=None, validator="no_plan", failed_checks=[])
        return rec
    # Baselines that could not place a must-visit report "infeasible" but still hold a partial plan: validate that plan as it stands.
    report = build_report(res.model_copy(update={"status": "feasible"}), ds, prefs, hotel)
    rec.update(travel_minutes=res.totals.travel_minutes, total_jpy=res.totals.total_jpy, validator=report.overall,
               failed_checks=[c.id for c in report.checks if c.status == "fail"])
    return rec


def product_spec(prefs: Preferences) -> ObjectiveSpec:
    """The objective POST /optimise runs (app/main.py): true cost at the trip's value of time. The evaluation's headline solver uses exactly this."""
    return ObjectiveSpec("true_cost", prefs.value_of_time_per_hour, config.MISSED_PREFERENCE_PENALTY_JPY)


def solver_record(trip: dict, ds: Dataset, objective: str = "product") -> dict:
    """The solver's plan record for a trip. objective: "product" (what /optimise runs) or "phase2_default" (the Phase 2 weighted
    objective, which no API route uses; secondary analysis only). Config switches such as pace_balance_off() apply as active."""
    prefs = prefs_for(trip, ds)
    spec = product_spec(prefs) if objective == "product" else None
    res = solve(prefs, trip["hotel_id"], ds, with_alternatives=False, objective=spec)
    return _plan_record(res, ds, prefs, trip["hotel_id"], True)


def evaluate_trip(trip: dict, ds: Dataset) -> dict:
    prefs, hotel, order = prefs_for(trip, ds), trip["hotel_id"], trip["order"]
    solver = solve(prefs, hotel, ds, with_alternatives=False, objective=product_spec(prefs))
    naive = baseline(prefs, hotel, ds, order=order)
    nn = nearest_neighbour(prefs, hotel, ds, order=order)
    vis = [a for a in order if independent.visitable(ds, prefs, a)]
    rec = {"id": trip["id"], "hotel_id": hotel, "days": trip["days"], "n_requested": len(order), "n_must": len(trip["must_visit"]),
           "must_visit": list(trip["must_visit"]), "budget_kind": trip["budget_kind"], "budget": trip["budget"],
           "budget_factor": trip["budget_factor"], "visitable": vis,
           "solver": _plan_record(solver, ds, prefs, hotel, True), "naive": _plan_record(naive, ds, prefs, hotel, False),
           "nn": _plan_record(nn, ds, prefs, hotel, False), "audit": None}
    cap = {"relaxed": 2, "balanced": 3, "packed": 4}[prefs.pace]
    rec["trivially_easy"] = (solver.status == "feasible" and set(_placed(solver)) == set(vis) and cap * prefs.days - len(vis) >= cap
                             and trip["budget_kind"] != "strict")
    if solver.status != "feasible":
        brute = independent.musts_schedulable(ds, prefs, hotel)
        confirms = [{"code": c.code, "confirmed": independent.confirm_conflict(c.code, c.attraction_ids, ds, prefs, hotel, order)}
                    for c in solver.conflicts]
        rec["audit"] = {"conflicts": confirms, "brute_force_says_schedulable": brute}
    return rec


def evaluate_hotel_value(trip: dict, ds: Dataset, vots=HOTEL_VOTS, with_sensitivity: bool = True) -> dict:
    prefs, hotels = prefs_for(trip, ds), sorted(ds.hotels)
    out = {"id": trip["id"], "by_vot": {}, "flip": None}
    for v in vots:
        comp = compare_hotels(prefs.model_copy(update={"value_of_time_per_hour": v}), hotels, ds, time_limit=3600)
        statuses = {r.hotel_id: r.status for r in comp.results}
        entry = {"solver_status": {r.hotel_id: r.solver_status for r in comp.results}, "cheapest_by_rate": comp.cheapest_by_rate,
                 "best_by_true_cost": comp.best_by_true_cost, "eligible": all(s == "feasible" for s in statuses.values()),
                 "ineligible_reason": None, "partial": comp.partial, "approximate": comp.approximate}
        if not entry["eligible"]:
            entry["ineligible_reason"] = "hotel_" + "+".join(sorted(set(s for s in statuses.values() if s != "feasible")))
        else:
            rank = {r.hotel_id: r for r in comp.ranking}[comp.cheapest_by_rate]
            entry.update(differs=comp.rate_winner_differs_from_true_winner, gap_jpy=rank.gap_to_winner_jpy,
                         gap_travel_hours=rank.gap_to_winner_travel_hours,
                         same_nice_set=not any(w.startswith("Not like-for-like") for w in comp.warnings),
                         true_cost={r.hotel_id: r.breakdown.true_cost_jpy for r in comp.results})
        out["by_vot"][str(v)] = entry
    if with_sensitivity and out["by_vot"][str(DEFAULT_VOT)]["eligible"]:
        s = sensitivity(prefs, hotels, ds, SENSITIVITY_RANGE, cache=SolveCache(), deadline=time.monotonic() + 3600)
        first = s.flips[0] if s.flips else None
        out["flip"] = {"n_flips": len(s.flips), "first_flip_vot": first.value_of_time_per_hour if first else None,
                       "method": first.method if first else None, "approximate": s.approximate,
                       "winner_at_min": s.grid[0].winner, "winner_at_max": s.grid[-1].winner, "solves": s.solves}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------------------------------------------------
def compare_travel(trips: list[dict], base: str) -> dict:
    """Solver vs one baseline ('naive' or 'nn') on the LIKE-FOR-LIKE subset: trips where both schedule exactly the same attractions."""
    rows, excluded = [], Counter()
    for t in trips:
        s, b = t["solver"], t[base]
        if s["status"] != "feasible":
            excluded["solver_infeasible"] += 1
            continue
        ss, bs = set(s["placed"]), set(b["placed"])
        if ss != bs:
            excluded["baseline_dropped_sights" if bs < ss else "solver_dropped_sights" if ss < bs else "different_sets"] += 1
            continue
        if b["travel_minutes"] == 0:
            excluded["zero_baseline_travel"] += 1
            continue
        diff, pct = reduction(b["travel_minutes"], s["travel_minutes"])
        rows.append({"id": t["id"], "solver_minutes": s["travel_minutes"], "baseline_minutes": b["travel_minutes"],
                     "reduction_minutes": diff, "reduction_percent": pct})
    ordered = sorted(rows, key=lambda r: (r["baseline_minutes"], r["id"]))
    n, terciles = len(ordered), []
    for k, name in enumerate(("lowest third", "middle third", "highest third")):
        grp = ordered[k * n // 3:(k + 1) * n // 3]
        if grp:
            terciles.append({"group": name, "n": len(grp), "baseline_minutes_range": [grp[0]["baseline_minutes"], grp[-1]["baseline_minutes"]],
                             "percent_reduction": describe([r["reduction_percent"] for r in grp]), **_split(grp)})
    sm, bm = sum(r["solver_minutes"] for r in rows), sum(r["baseline_minutes"] for r in rows)
    return {"baseline": base, "n_trips": len(trips), "n_comparable": n, "excluded": {"n": sum(excluded.values()), "reasons": dict(excluded)},
            "minutes_reduction": describe([r["reduction_minutes"] for r in rows]), "percent_reduction": describe([r["reduction_percent"] for r in rows]),
            **_split(rows), "pooled": {"solver_minutes": sm, "baseline_minutes": bm, "percent": reduction(bm, sm)[1] if bm else None},
            "terciles": terciles, "rows": rows}


def _validation(trips: list[dict], key: str) -> dict:
    verdicts = Counter(t[key]["validator"] for t in trips)
    failed = Counter(c for t in trips for c in t[key]["failed_checks"])
    other = sum(1 for t in trips if set(t[key]["failed_checks"]) - {"must_visits"})
    return {"n_trips": len(trips), "pass": verdicts["pass"], "pass_with_warnings": verdicts["pass_with_warnings"], "fail": verdicts["fail"],
            "no_plan": verdicts["no_plan"], "failed_checks": dict(failed), "fail_hard_constraint_beyond_missing_must_visit": other}


def _budget(trips: list[dict]) -> dict:
    strict = [t for t in trips if t["budget_kind"] == "strict"]
    out = {"n_strict_trips": len(strict)}
    for key in ("solver", "naive", "nn"):
        plans = [t for t in strict if t[key]["status"] == "feasible"]
        out[key] = {"feasible_plans": len(plans), "within_budget": sum(t[key]["total_jpy"] <= t["budget"] for t in plans),
                    "no_feasible_plan": len(strict) - len(plans)}
    return out


def _must_visits(trips: list[dict]) -> dict:
    with_must = [t for t in trips if t["n_must"]]
    out = {"n_trips_with_must": len(with_must)}
    for key in ("solver", "naive", "nn"):
        out[key] = {"all_placed": sum(t[key]["status"] == "feasible" and set(t["must_visit"]) <= set(t[key]["placed"]) for t in with_must),
                    "reported_infeasible": sum(t[key]["status"] == "infeasible" for t in with_must),
                    "silently_dropped": sum(t[key]["status"] == "feasible" and not set(t["must_visit"]) <= set(t[key]["placed"]) for t in with_must)}
    infeasible = [t for t in trips if t["solver"]["status"] != "feasible"]
    by_code: dict[str, dict] = {}
    for t in infeasible:
        for c in t["audit"]["conflicts"]:
            e = by_code.setdefault(c["code"], {"n": 0, "confirmed": 0, "contradicted": 0, "not_checkable": 0})
            e["n"] += 1
            e["confirmed" if c["confirmed"] is True else "contradicted" if c["confirmed"] is False else "not_checkable"] += 1
    out["infeasible_audit"] = {
        "n_infeasible": len(infeasible),
        "all_stated_conflicts_confirmed": sum(all(c["confirmed"] is True for c in t["audit"]["conflicts"]) and bool(t["audit"]["conflicts"]) for t in infeasible),
        "brute_force_agrees_no_schedule": sum(t["audit"]["brute_force_says_schedulable"] is False for t in infeasible),
        "brute_force_found_a_schedule": sum(t["audit"]["brute_force_says_schedulable"] is True for t in infeasible),
        "brute_force_not_decided": sum(t["audit"]["brute_force_says_schedulable"] is None for t in infeasible),
        "by_code": by_code}
    return out


def _placement(trips: list[dict]) -> dict:
    ok = [t for t in trips if t["solver"]["status"] == "feasible"]
    out = {"n_trips": len(ok), "requested": sum(t["n_requested"] for t in ok), "visitable": sum(len(t["visitable"]) for t in ok)}
    for key in ("solver", "naive", "nn"):
        out[key] = {"placed": sum(len(t[key]["placed"]) for t in ok)}
    return out


def _hotel_value(hotel_rows: list[dict]) -> dict:
    out = {"vots": {}, "flip": None}
    for v in sorted({v for h in hotel_rows for v in h["by_vot"]}, key=int):
        entries = [h["by_vot"][v] for h in hotel_rows if v in h["by_vot"]]
        elig = [e for e in entries if e["eligible"]]
        like = [e for e in elig if e["same_nice_set"]]
        out["vots"][v] = {"n_trips": len(entries), "n_eligible": len(elig),
                          "ineligible_reasons": dict(Counter(e["ineligible_reason"] for e in entries if not e["eligible"])),
                          "cheapest_by_rate_not_best": sum(e["differs"] for e in elig),
                          "gap_jpy": describe([e["gap_jpy"] for e in elig]), "gap_travel_hours": describe([e["gap_travel_hours"] for e in elig]),
                          "n_same_nice_set": len(like), "cheapest_by_rate_not_best_same_nice_set": sum(e["differs"] for e in like),
                          "gap_jpy_same_nice_set": describe([e["gap_jpy"] for e in like]),
                          "not_proven_optimal": sum(e["approximate"] for e in entries)}
    flips = [h["flip"] for h in hotel_rows if h["flip"] is not None]
    if flips:
        with_flip = [f for f in flips if f["n_flips"]]
        out["flip"] = {"n_analysed": len(flips), "n_with_flip": len(with_flip),
                       "first_flip_vot": describe([f["first_flip_vot"] for f in with_flip]),
                       "exact_crossing": sum(f["method"] == "exact_crossing" for f in with_flip),
                       "bisection_estimate": sum(f["method"] == "bisection_estimate" for f in with_flip),
                       "analysis_flagged_approximate": sum(f["approximate"] for f in flips)}
    return out


def _spread(rec: dict) -> int | None:
    d = rec["stops_per_day"]
    return max(d) - min(d) if d else None


def _secondary_objectives(trips: list[dict], variants: dict[str, list[dict]]) -> dict:
    """POST-HOC secondary analysis: the same trips solved with other (non-headline) solver settings, compared with the same baselines."""
    ids_ok = {t["id"] for t in trips if t["solver"]["status"] == "feasible"}

    def mean_spread(pairs):
        xs = [_spread(r) for t, r in pairs if t["id"] in ids_ok and _spread(r) is not None]
        return {"n": len(xs), "mean_busiest_minus_quietest_day": statistics.fmean(xs) if xs else None}
    out = {"variants": {}, "stops_per_day_spread": {"solver_product_objective": mean_spread([(t, t["solver"]) for t in trips]),
                                                    "input_order": mean_spread([(t, t["naive"]) for t in trips]),
                                                    "nearest_neighbour": mean_spread([(t, t["nn"]) for t in trips])}}
    for name, recs in variants.items():
        swapped = [dict(t, solver=a) for t, a in zip(trips, recs)]
        out["variants"][name] = {"naive": compare_travel(swapped, "naive"), "nn": compare_travel(swapped, "nn"),
                                 "placed_in_trips_with_a_product_plan": sum(len(a["placed"]) for t, a in zip(trips, recs) if t["id"] in ids_ok)}
        out["stops_per_day_spread"]["solver_" + name] = mean_spread(list(zip(trips, recs)))
    return out


def aggregate(trips: list[dict], hotel_rows: list[dict], replan: dict | None, variants: dict[str, list[dict]] | None = None) -> dict:
    infeasible = [t for t in trips if t["solver"]["status"] != "feasible"]
    status_counts = {"trip_solves": Counter(t["solver"]["solver_status"] for t in trips),
                     "hotel_compare_solves": Counter(s for h in hotel_rows for e in h["by_vot"].values() for s in e["solver_status"].values()),
                     "replan_solves": Counter(replan["solver_status"]) if replan else Counter()}
    rt = [t["solver"]["runtime_seconds"] for t in trips if t["solver"]["runtime_seconds"] is not None]
    return {
        "n_trips": len(trips),
        "generation": {"infeasible": len(infeasible), "infeasible_by_code": dict(Counter(c for t in infeasible for c in t["solver"]["conflict_codes"])),
                       "trivially_easy": sum(t["trivially_easy"] for t in trips),
                       "strict_budget": sum(t["budget_kind"] == "strict" for t in trips),
                       "tight_strict_budget": sum(t["budget_kind"] == "strict" and t["budget_factor"] < 0.7 for t in trips),
                       "with_must_visits": sum(bool(t["n_must"]) for t in trips),
                       "by_hotel": dict(Counter(t["hotel_id"] for t in trips))},
        "travel": {"naive": compare_travel(trips, "naive"), "nn": compare_travel(trips, "nn")},
        "placement": _placement(trips),
        "validation": {k: _validation(trips, k) for k in ("solver", "naive", "nn")},
        "budget": _budget(trips),
        "must_visit": _must_visits(trips),
        "hotel_value": _hotel_value(hotel_rows),
        "replan": replan,
        "secondary_objectives": _secondary_objectives(trips, variants) if variants else None,
        "solver_status": {k: dict(v) for k, v in status_counts.items()},
        "machine_dependent": {"solver_runtime_seconds": {"n": len(rt), "mean": statistics.fmean(rt) if rt else None, "max": max(rt) if rt else None}},
    }
