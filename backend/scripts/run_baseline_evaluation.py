"""Baseline evaluation (Phase 1): cheapest-hotel-first (A), convenience-first (B) and joint optimisation (C) on the SAME seeded trips as the existing evaluations, per city and
never pooled, at the city's OWN default value of time and at multiples of it. Also: why the cheapest hotel usually wins (what the room-rate gap is up against), and whether the
missed-sight charge materially changes the hotel choice. Writes docs/baseline-results.json and docs/baseline-results.md. No network, no model, no key.
The final comparison uses one number (the optimisation score = true cost), reported next to the known monetary spend, never instead of it.
Usage (from backend/):  python scripts/run_baseline_evaluation.py [--quick]"""
import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.eval import generator  # noqa: E402
from app.money import missed_preference_penalty  # noqa: E402
from app.optimiser.baselines import convenience_minutes  # noqa: E402
from app.optimiser.hotel_compare import SolveCache, compare_hotels  # noqa: E402
from app.optimiser.solver import ObjectiveSpec  # noqa: E402
from app.schemas import nights_for  # noqa: E402

DOCS = ROOT.parent / "docs"
TOKYO_SEED, CITY_SEED = 20261013, 20261014
MULTIPLES = (0.5, 1, 2, 4)
PENALTY_FACTORS = (0, 1, 2)          # x the city's own missed-sight charge
ORDER = ["tokyo", "singapore", "seoul", "kuala_lumpur"]


def describe(xs):
    xs = list(xs)
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": round(statistics.mean(xs), 1), "median": statistics.median(xs), "min": min(xs), "max": max(xs)}


def pct(base, opt):
    """(baseline - optimised) / baseline x 100, only when the baseline is positive and the comparison is meaningful."""
    return round((base - opt) / base * 100, 2) if base and base > 0 else None


def run_city(ds, n: int, seed: int, quick: bool) -> dict:
    trips = generator.generate_trips(seed, n if not quick else min(n, 6), ds)
    hotels = sorted(ds.hotels)
    default_vot = ds.city.default_value_of_time_per_hour
    out = {"n_trips": len(trips), "default_value_of_time": default_vot, "by_multiple": {}, "decomposition": [], "penalty": {}}
    for m in MULTIPLES:
        vot = round(default_vot * m)
        rows = []
        for t in trips:
            prefs = generator.prefs_for(t, ds).model_copy(update={"value_of_time_per_hour": vot})
            comp = compare_hotels(prefs, hotels, ds, time_limit=3600)
            e = {x.key: x for x in comp.baselines.entries}
            ok = all(x.feasible for x in e.values()) and all(r.feasible for r in comp.results)
            rows.append({"id": t["id"], "eligible": ok, "A": e["cheapest_rate"].hotel_id, "B": e["convenience_first"].hotel_id, "C": e["joint"].hotel_id,
                         **({k: {"score": x.score_jpy, "spend": x.known_spend_jpy, "minutes": x.travel_minutes, "omitted": len(x.omitted_optional)} for k, x in zip("ABC", e.values())} if ok else {})})
        el = [r for r in rows if r["eligible"]]

        a_diff = sum(r["A"] != r["C"] for r in el)
        b_diff = sum(r["B"] != r["C"] for r in el)
        out["by_multiple"][str(m)] = {
            "value_of_time_per_hour": vot, "n_trips": len(rows), "n_eligible": len(el), "ineligible": len(rows) - len(el),
            "joint_differs_from_cheapest": a_diff, "joint_differs_from_convenience": b_diff,
            "cheapest_equals_convenience": sum(r["A"] == r["B"] for r in el), "all_three_agree": sum(r["A"] == r["B"] == r["C"] for r in el),
            "score_gain_vs_cheapest": describe(r["A"]["score"] - r["C"]["score"] for r in el),
            "score_gain_vs_convenience": describe(r["B"]["score"] - r["C"]["score"] for r in el),
            "percent_gain_vs_cheapest": describe(p for p in (pct(r["A"]["score"], r["C"]["score"]) for r in el) if p is not None),
            "percent_gain_vs_convenience": describe(p for p in (pct(r["B"]["score"], r["C"]["score"]) for r in el) if p is not None),
            "known_spend_joint_minus_cheapest": describe(r["C"]["spend"] - r["A"]["spend"] for r in el),
            "travel_minutes_saved_vs_cheapest": describe(r["A"]["minutes"] - r["C"]["minutes"] for r in el),
            "omitted_sights_saved_vs_cheapest": describe(r["A"]["omitted"] - r["C"]["omitted"] for r in el),
            "no_gain_vs_cheapest": sum(r["A"]["score"] == r["C"]["score"] for r in el),
            "no_gain_vs_convenience": sum(r["B"]["score"] == r["C"]["score"] for r in el),
            "joint_worse_than_a_baseline": sum(r["C"]["score"] > min(r["A"]["score"], r["B"]["score"]) for r in el),
        }
    # why the cheapest hotel usually wins: at the city's default value of time, what the room-rate gap is up against
    nights_cache = {}
    vot = default_vot
    cache = SolveCache()
    pen_default = missed_preference_penalty(ds)
    solved = {}
    for t in trips:
        prefs = generator.prefs_for(t, ds).model_copy(update={"value_of_time_per_hour": vot})
        nights, _ = nights_for(prefs)
        nights_cache[t["id"]] = nights
        solved[t["id"]] = {}
        for h in hotels:
            solved[t["id"]][h] = cache.solve(prefs, h, ds, ObjectiveSpec("true_cost", vot, pen_default), 3600)
    for t in trips:
        res = solved[t["id"]]
        if not all(r.status == "feasible" for r in res.values()):
            continue
        prefs = generator.prefs_for(t, ds).model_copy(update={"value_of_time_per_hour": vot})
        cheapest = min(hotels, key=lambda h: (ds.hotels[h].nightly_rate, h))
        tmin = min(hotels, key=lambda h: (res[h].totals.travel_minutes, ds.hotels[h].nightly_rate, h))
        nights = nights_cache[t["id"]]
        d_rooms = (ds.hotels[tmin].nightly_rate - ds.hotels[cheapest].nightly_rate) * nights          # extra money for the least-travel hotel
        d_min = res[cheapest].totals.travel_minutes - res[tmin].totals.travel_minutes                  # minutes it saves
        d_time = round(d_min * vot / 60)
        d_charge = (len(res[cheapest].missed_preferences) - len(res[tmin].missed_preferences)) * pen_default
        out["decomposition"].append({"id": t["id"], "least_travel_is_cheapest": tmin == cheapest, "extra_rooms": d_rooms, "minutes_saved": d_min, "time_value_saved": d_time, "charge_saved": d_charge,
                                     "break_even_vot": round(d_rooms / (d_min / 60)) if d_min > 0 and d_rooms > 0 else None})
    # does the missed-sight charge matter? (hotel chosen with the charge off, at the city's own level, at twice it)
    pen_rows = []
    for t in trips:
        prefs = generator.prefs_for(t, ds).model_copy(update={"value_of_time_per_hour": vot})
        nights = nights_cache[t["id"]]
        choice, feas = {}, True
        for f in PENALTY_FACTORS:
            pen = pen_default * f
            scores = {}
            for h in hotels:
                r = cache.solve(prefs, h, ds, ObjectiveSpec("true_cost", vot, pen), 3600)
                if r.status != "feasible":
                    feas = False
                    break
                scores[h] = ds.hotels[h].nightly_rate * nights + r.totals.admissions_jpy + r.totals.transport_jpy + (r.totals.travel_minutes * vot + 30) // 60 + pen * len(r.missed_preferences)
            if not feas:
                break
            choice[f] = min(hotels, key=lambda h: (scores[h], ds.hotels[h].nightly_rate, h))
        if feas:
            pen_rows.append(choice)
    out["penalty"] = {"n_eligible": len(pen_rows), "changes_when_charge_removed": sum(c[0] != c[1] for c in pen_rows), "changes_when_charge_doubled": sum(c[2] != c[1] for c in pen_rows),
                      "joint_pick_is_cheapest_with_no_charge": sum(c[0] == min(hotels, key=lambda h: (ds.hotels[h].nightly_rate, h)) for c in pen_rows),
                      "joint_pick_is_cheapest_at_default_charge": sum(c[1] == min(hotels, key=lambda h: (ds.hotels[h].nightly_rate, h)) for c in pen_rows)}
    rates = sorted(h.nightly_rate for h in ds.hotels.values())
    out["data"] = {"hotels": len(hotels), "attractions": len(ds.attractions), "nightly_rates": rates, "rate_ratio_max_over_min": round(rates[-1] / rates[0], 2),
                   "default_penalty_per_missed_sight": pen_default, "currency": ds.city.currency_code}
    dec = out["decomposition"]
    out["decomposition_summary"] = {"n": len(dec), "least_travel_hotel_is_also_cheapest": sum(d["least_travel_is_cheapest"] for d in dec),
                                    "extra_rooms": describe(d["extra_rooms"] for d in dec if not d["least_travel_is_cheapest"]),
                                    "time_value_saved": describe(d["time_value_saved"] for d in dec if not d["least_travel_is_cheapest"]),
                                    "charge_saved": describe(d["charge_saved"] for d in dec if not d["least_travel_is_cheapest"]),
                                    "minutes_saved": describe(d["minutes_saved"] for d in dec if not d["least_travel_is_cheapest"]),
                                    "break_even_value_of_time": describe(d["break_even_vot"] for d in dec if d["break_even_vot"] is not None),
                                    "trips_where_hotels_differ_by_under_15_minutes": sum(1 for d in dec if abs(d["minutes_saved"]) < 15)}
    return out


def _git() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        return h + (" + uncommitted changes" if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip() else "")
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(DOCS))
    a = ap.parse_args(argv)
    ds_all = load_all_city_datasets()
    t0 = time.perf_counter()
    res = {"meta": {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "commit": _git(), "seeds": {"tokyo": TOKYO_SEED, "others": CITY_SEED}, "multiples_of_default_value_of_time": list(MULTIPLES),
                    "penalty_factors": list(PENALTY_FACTORS), "quick": a.quick, "label": "seeded synthetic trips on SAMPLE data with made-up hotels; estimated travel times"}, "cities": {}}
    for c in ORDER:
        res["cities"][c] = run_city(ds_all[c], 60 if c == "tokyo" else 20, TOKYO_SEED if c == "tokyo" else CITY_SEED, a.quick)
        print(c, "done", round(time.perf_counter() - t0), "s", flush=True)
    res["meta"]["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    out = Path(a.out)
    (out / "baseline-results.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    (out / "baseline-results.md").write_text(render(res, ds_all), encoding="utf-8")
    print(f"wrote {out / 'baseline-results.md'}")
    return 0


def render(res: dict, ds_all) -> str:
    L = ["# Baseline comparison (sample data)", "",
         f"Generated {res['meta']['date']} by `backend/scripts/run_baseline_evaluation.py`. Code version: {res['meta']['commit']}. **Seeded synthetic trips on SAMPLE data with made-up hotels and estimated travel times; not user-tested; each city reported separately, never pooled.**", "",
         "Three strategies, all using the same candidate hotels, constraints, estimated travel times, itinerary optimiser and objective (`app/optimiser/baselines.py`): **A** cheapest hotel first, **B** convenience-first (the hotel with the smallest total estimated travel time to the target sights, a documented rule that looks only at hotel-to-sight times), **C** joint optimisation (the hotel whose optimised itinerary has the lowest optimisation score). The score is true cost = rooms + admissions + estimated transport + monetised travel time + a charge per optional sight left out. **It is not money spent**: the known monetary spend is reported next to it.", "",
         "The value of time is varied as multiples of each city's OWN default (the earlier city evaluation used the same number, 1000, in every currency, which is not like-for-like).", ""]
    for c in ORDER:
        r = res["cities"][c]
        d = ds_all[c].city
        L += [f"## {d.display_name} ({d.currency_code})", "", f"{r['n_trips']} trips; own default value of time {r['default_value_of_time']:,} {d.currency_code} an hour; {r['data']['hotels']} hotels with nightly rates {r['data']['nightly_rates']} (highest is {r['data']['rate_ratio_max_over_min']}x the lowest); {r['data']['attractions']} sights.", "",
              "| Value of time | Eligible trips | C differs from A (cheapest) | C differs from B (convenience) | A equals B | Median score gain vs A | Mean gain vs A (%) | Median gain vs B | Cases with no gain vs A | Median known spend, C minus A | Median minutes saved vs A |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for m, x in r["by_multiple"].items():
            g = lambda k, f="median": (x[k].get(f, "n/a") if x[k]["n"] else "n/a")  # noqa: E731
            L.append(f"| {m}x ({x['value_of_time_per_hour']:,}) | {x['n_eligible']} of {x['n_trips']} | {x['joint_differs_from_cheapest']} | {x['joint_differs_from_convenience']} | {x['cheapest_equals_convenience']} | {g('score_gain_vs_cheapest')} | {g('percent_gain_vs_cheapest', 'mean')} | {g('score_gain_vs_convenience')} | {x['no_gain_vs_cheapest']} | {g('known_spend_joint_minus_cheapest')} | {g('travel_minutes_saved_vs_cheapest')} |")
        s, p = r["decomposition_summary"], r["penalty"]
        L += ["", f"**Why the cheapest hotel usually wins here (at the default value of time, {s['n']} trips where all three hotels are feasible).** In {s['least_travel_hotel_is_also_cheapest']} of {s['n']} the hotel with the least travel is also the cheapest. In the others the least-travel hotel costs a median of {s['extra_rooms'].get('median', 'n/a')} more in rooms and saves a median of {s['minutes_saved'].get('median', 'n/a')} minutes (worth a median of {s['time_value_saved'].get('median', 'n/a')} at this value of time) and {s['charge_saved'].get('median', 'n/a')} in missed-sight charges. The value of time at which the extra rooms would pay for themselves through time alone had a median of {s['break_even_value_of_time'].get('median', 'n/a')} (n = {s['break_even_value_of_time']['n']}; the default is {r['default_value_of_time']:,}). In {s['trips_where_hotels_differ_by_under_15_minutes']} of {s['n']} trips the hotels differ by under 15 minutes of travel.", "",
              f"**Does the missed-sight charge matter?** ({p['n_eligible']} trips, charge {r['data']['default_penalty_per_missed_sight']:,} {d.currency_code} per missed sight by default.) The chosen hotel changed in {p['changes_when_charge_removed']} of {p['n_eligible']} when the charge was removed and in {p['changes_when_charge_doubled']} of {p['n_eligible']} when it was doubled. The joint choice was the cheapest-rate hotel in {p['joint_pick_is_cheapest_at_default_charge']} of {p['n_eligible']} at the default charge and {p['joint_pick_is_cheapest_with_no_charge']} of {p['n_eligible']} with no charge.", ""]
    L += ["## How to read this", "", "- A hotel change is not a success metric. The question is whether the joint choice gives a lower score, less travel or fewer omitted sights, and what it costs in known spend. Cases with no gain are counted, not hidden.",
          "- A lower score can come with MORE known spend (a pricier hotel, more admissions because more sights fit). Read the spend and score columns together.",
          "- Hotels, rates, sights and travel times are sample data. The result says how the optimiser behaves on this sample, not how real hotel markets behave.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
