"""Claim-safe sentences generated FROM the measured metrics dict (see metrics.aggregate). Nothing here is typed in by hand:
every number comes from `metrics`, every sentence carries its N and a caveat, and weak or negative results are stated plainly.

Rounding rule ("never round in a favourable direction"): improvements and rates that favour the product are rounded DOWN
(toward the less flattering value); failure rates, worse-than-baseline counts and costs are rounded UP. Counts are exact.
The word "significant" is never used: no statistical test is run.
"""
import statistics
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

CAVEAT = "Sample data (12 attractions, 3 fictional hotels, estimated travel times); seeded synthetic trips; not user-tested."
SMALL_AVERAGE_PERCENT = 5.0   # JUDGEMENT CALL: below this mean reduction a result is described as small
BASELINE_LABEL = {"naive": "input-order baseline", "nn": "nearest-neighbour baseline"}


def _quant(x: float, nd: int, rounding) -> Decimal:
    return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=rounding)


def down(x: float, nd: int = 1) -> str:
    """Round toward minus infinity (for values that favour the product)."""
    return f"{_quant(x, nd, ROUND_FLOOR):,}"


def up(x: float, nd: int = 1) -> str:
    """Round toward plus infinity (for values that disfavour the product)."""
    return f"{_quant(x, nd, ROUND_CEILING):,}"


def pct(k: int, n: int, favourable: bool) -> str:
    return f"{(down if favourable else up)(100.0 * k / n)}%" if n else "n/a"


def _excl(cmp: dict) -> str:
    ex = cmp["excluded"]
    reasons = ", ".join(str(v) + " " + k.replace("_", " ") for k, v in sorted(ex["reasons"].items()))
    return f"{ex['n']} excluded ({reasons})" if ex["n"] else "none excluded"


def travel_claim(cmp: dict, variant: str = "") -> str:
    """variant: text inserted after "optimised routes", used to label secondary analyses."""
    label, n, total = BASELINE_LABEL[cmp["baseline"]], cmp["n_comparable"], cmp["n_trips"]
    routes = "optimised routes" + variant
    if n == 0:
        return f"No travel-time comparison against the {label} could be made: none of the {total} generated trips had both plans schedule the same attractions ({_excl(cmp)}). {CAVEAT}"
    p = cmp["percent_reduction"]
    mean, med, lo, hi = p["mean"], p["median"], p["min"], p["max"]
    if mean > 0:
        head = f"Across {n} comparable trips (of {total}; {_excl(cmp)}), {routes} used {down(mean)}% less total travel time than the {label}"
    elif mean == 0:
        head = f"Across {n} comparable trips (of {total}; {_excl(cmp)}), {routes} used the same total travel time on average as the {label}"
    else:
        head = f"Across {n} comparable trips (of {total}; {_excl(cmp)}), {routes} used {up(-mean)}% MORE total travel time than the {label} on average"
    s = (f"{head} (mean of per-trip percentages; median {down(med)}%, range {down(lo)}% to {down(hi)}%, where positive means less travel; "
         f"better on {cmp['better']}, equal on {cmp['equal']}, worse on {cmp['worse']} of {n}).")
    if mean <= 0:
        s += " On this sample the optimiser did not reduce travel time against this baseline."
    elif mean < SMALL_AVERAGE_PERCENT:
        s += f" This is a small average difference (under {SMALL_AVERAGE_PERCENT:g}%)."
    if cmp["better"] * 2 < n:
        s += f" The optimiser was better on fewer than half ({cmp['better']} of {n}) of the comparable trips."
    return f"{s} {CAVEAT}"


def validation_claim(v: dict) -> str:
    s = v["solver"]
    plans = s["n_trips"] - s["no_plan"]
    parts = [f"The independent validator passed {s['pass'] + s['pass_with_warnings']} of {plans} solver itineraries ({s['pass_with_warnings']} with data-quality warnings) and failed {s['fail']}"]
    for key, label in (("naive", "input-order baseline"), ("nn", "nearest-neighbour baseline")):
        b = v[key]
        parts.append(f"the {label}: {b['fail']} of {b['n_trips']} plans failed validation ({b['fail_hard_constraint_beyond_missing_must_visit']} of them for a reason beyond a missing must-visit)")
    return f"{parts[0]}; {'; '.join(parts[1:])}. N = {s['n_trips']} generated trips ({s['no_plan']} had no solver plan because the request was infeasible). {CAVEAT}"


def budget_claim(b: dict) -> str:
    n = b["n_strict_trips"]
    if not n:
        return f"No generated trip had a strict budget, so budget compliance was not measured. {CAVEAT}"
    def one(k, label):
        return f"{label} {b[k]['within_budget']} of {b[k]['feasible_plans']} feasible plans within budget (trips with no feasible plan: {b[k]['no_feasible_plan']})"
    return (f"Among {n} strict-budget trips (some deliberately tight): {one('solver', 'solver')}; {one('naive', 'input-order baseline')}; "
            f"{one('nn', 'nearest-neighbour baseline')}. {CAVEAT}")


def must_visit_claim(m: dict) -> str:
    n = m["n_trips_with_must"]
    a = m["infeasible_audit"]
    def one(k, label):
        return f"{label} placed all in {m[k]['all_placed']} (reported infeasible in {m[k]['reported_infeasible']}, silently dropped one in {m[k]['silently_dropped']})"
    s = f"Among {n} trips with must-visits: {one('solver', 'the solver')}; {one('naive', 'the input-order baseline')}; {one('nn', 'the nearest-neighbour baseline')}."
    if a["n_infeasible"]:
        s += (f" Of the solver's {a['n_infeasible']} infeasible reports, every stated conflict matched an independent recomputation in {a['all_stated_conflicts_confirmed']}; "
              f"an exhaustive search agreed that no must-visit schedule exists in {a['brute_force_agrees_no_schedule']} and found a schedule in {a['brute_force_found_a_schedule']} "
              f"({a['brute_force_not_decided']} not decided).")
    return f"{s} {CAVEAT}"


def hotel_claims(h: dict) -> list[str]:
    out, caveat = [], f"Hotels and rates are FICTIONAL and were tuned for the demo, so this measures the model's behaviour on sample data, not real hotel markets. {CAVEAT}"
    v = h["vots"].get("1000")
    if v and v["n_eligible"]:
        k, n = v["cheapest_by_rate_not_best"], v["n_eligible"]
        g = v["gap_jpy"]
        s = (f"At the default value of time (1,000 JPY/h), the hotel with the lowest nightly rate was not the best by true cost in {k} of {n} trips where all three hotels were feasible ({pct(k, n, True)}); "
             f"choosing by rate alone cost a mean {down(g['mean'], 0)} JPY more in true cost (median {down(g['median'], 0)}, max {down(g['max'], 0)} JPY).")
        if k == 0:
            s = f"At the default value of time (1,000 JPY/h), the hotel with the lowest nightly rate was also the best by true cost in all {n} trips where all three hotels were feasible; on this sample, choosing by rate alone never cost extra."
        out.append(f"{s} {caveat}")
    others = [(x, h["vots"][x]) for x in ("500", "2000") if x in h["vots"] and h["vots"][x]["n_eligible"]]
    if others:
        bits = [f"{x} JPY/h: {e['cheapest_by_rate_not_best']} of {e['n_eligible']}" for x, e in others]
        out.append(f"Lowest-rate hotel not best by true cost, at other values of time: {'; '.join(bits)}. {caveat}")
    f = h.get("flip")
    if f:
        if f["n_with_flip"]:
            fv = f["first_flip_vot"]
            out.append(f"In {f['n_with_flip']} of {f['n_analysed']} analysed trips the best hotel changed somewhere between 0 and 3,000 JPY/h; the median first change was at about {down(fv['median'], 0)} JPY/h "
                       f"({f['exact_crossing']} exact crossings, {f['bisection_estimate']} bisection estimates, so approximate). {caveat}")
        else:
            out.append(f"In none of {f['n_analysed']} analysed trips did the best hotel change between 0 and 3,000 JPY/h. {caveat}")
    return out


def replan_claim(r: dict | None) -> str:
    if not r or not r["n_both_applied"]:
        return f"Replanning was not compared: no scenario produced an applied plan under both strategies. {CAVEAT}"
    am, nm = r["aware"]["moved"], r["naive"]["moved"]
    extra = r["extra_cost_of_stability_jpy"]
    return (f"Across {r['n_both_applied']} replanning scenarios where both strategies produced a plan (of {r['n_scenarios']}), disruption-aware replanning moved fewer activities than a naive full re-solve in "
            f"{r['aware_fewer_moves']}, the same number in {r['same_moves']} and more in {r['aware_more_moves']}; mean unnecessarily moved per applied replan "
            f"{up(statistics.fmean(am))} (aware, N={len(am)}) vs {down(statistics.fmean(nm))} (naive, N={len(nm)}); its final true cost was a mean {up(statistics.fmean(extra), 0)} JPY higher than the naive plan's. {CAVEAT}")


def solver_status_claim(s: dict) -> str:
    t = s["trip_solves"]
    ran = t.get("OPTIMAL", 0) + t.get("FEASIBLE", 0)
    skipped = t.get("NOT_RUN", 0)
    tail = f", and {skipped} were not solved because the request was already infeasible" if skipped else ""
    return (f"Of {ran} solver runs on generated trips, {t.get('OPTIMAL', 0)} ended OPTIMAL and {t.get('FEASIBLE', 0)} FEASIBLE (not proven optimal){tail}. {CAVEAT}")


def placement_claim(p: dict) -> str:
    return (f"Among {p['n_trips']} trips where the solver produced a plan, it scheduled {p['solver']['placed']} of {p['requested']} requested attractions ({p['visitable']} were visitable at all); "
            f"the input-order baseline scheduled {p['naive']['placed']} and the nearest-neighbour baseline {p['nn']['placed']}. {CAVEAT}")


def generate_claims(metrics: dict) -> list[tuple[str, str]]:
    """[(claim id, sentence)] in a fixed order."""
    out = [("travel_vs_input_order", travel_claim(metrics["travel"]["naive"])), ("travel_vs_nearest_neighbour", travel_claim(metrics["travel"]["nn"])),
           ("placement", placement_claim(metrics["placement"])), ("validator", validation_claim(metrics["validation"])),
           ("budget", budget_claim(metrics["budget"])), ("must_visits", must_visit_claim(metrics["must_visit"]))]
    sec = (metrics.get("secondary_objectives") or {}).get("variants", {})
    if "phase2_default" in sec:
        variant = " (using the Phase 2 weighted objective, which no API route uses; a secondary analysis added after seeing the results)"
        out += [("secondary_phase2_objective_vs_input_order", travel_claim(sec["phase2_default"]["naive"], variant)),
                ("secondary_phase2_objective_vs_nearest_neighbour", travel_claim(sec["phase2_default"]["nn"], variant))]
    out += [(f"hotel_value_{i + 1}", s) for i, s in enumerate(hotel_claims(metrics["hotel_value"]))]
    out += [("replanning", replan_claim(metrics.get("replan"))), ("solver_status", solver_status_claim(metrics["solver_status"]))]
    return out
