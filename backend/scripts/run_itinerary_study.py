"""Itinerary-planning value, measured separately from hotel choice (no model, no network).

For the SAME seeded trips as the other evaluations, with the trip's own hotel fixed, every arm gets the same data, constraints, estimated travel matrix and the same scoring:
  input order      the user's listed order, filled day by day (existing baseline)
  nearest feasible nearest-neighbour heuristic a careful person with a map could follow (existing baseline)
  optimiser        the shipped planner
Reported per city (never pooled), over ALL trips with denominators, including trips where an arm fails:
  feasibility (all must-visits placed AND the independent validator reports no failed check), optional-sight coverage, estimated travel minutes, known monetary spend (admissions +
  estimated transport), generalised cost (the optimisation score; NOT money spent) and runtime.
Two comparisons are kept apart:
  full-trip outcomes      each arm's own plan, whatever sights it placed;
  matched routing         the optimiser re-solved to visit EXACTLY the sights a baseline placed, so any difference is order/day/timing only (no selection of trips where sets happened to agree).
Usage (from backend/):  python scripts/run_itinerary_study.py [--quick] [--out DIR]"""
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

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.eval import generator  # noqa: E402
from app.eval.limits import deterministic_limits  # noqa: E402
from app.money import missed_preference_penalty  # noqa: E402
from app.optimiser.baseline import baseline, nearest_neighbour  # noqa: E402
from app.optimiser.hotel_compare import _breakdown  # noqa: E402
from app.optimiser.solver import ObjectiveSpec, missed_preferences_for, solve  # noqa: E402
from app.schemas import nights_for  # noqa: E402
from app.validator.feasibility_report import build_report  # noqa: E402

DOCS = ROOT.parent / "docs"
TOKYO_SEED, CITY_SEED = 20261013, 20261014
ORDER = ["tokyo", "singapore", "seoul", "kuala_lumpur"]
ARMS = ("input_order", "nearest_feasible", "optimiser")
LABEL = {"input_order": "Input order", "nearest_feasible": "Nearest feasible", "optimiser": "Optimiser"}


def describe(xs):
    xs = list(xs)
    return {"n": 0} if not xs else {"n": len(xs), "mean": round(statistics.mean(xs), 1), "median": statistics.median(xs), "min": min(xs), "max": max(xs)}


def score(ds, prefs, hotel, res, vot):
    """None if the arm has no feasible plan; else the measured components. Feasible = status feasible and no failed independent check."""
    if res.status != "feasible":
        return None
    rep = build_report(res, ds, prefs, hotel)
    if rep.overall == "fail":
        return {"feasible": False, "failed": [c.name for c in rep.checks if c.status == "fail"]}
    scheduled = {s.attraction_id for d in res.days for s in d.stops}
    res = res.model_copy(update={"missed_preferences": missed_preferences_for(prefs, hotel, ds, scheduled)})
    nights, _ = nights_for(prefs)
    b = _breakdown(ds, prefs, hotel, res, nights, vot)
    return {"feasible": True, "sights": sorted(scheduled), "placed": len(scheduled), "omitted": len(b.missed_preferences.attraction_ids), "minutes": b.travel_minutes,
            "spend": b.rooms_jpy + b.admissions_jpy + b.transport_jpy, "money_ex_rooms": b.admissions_jpy + b.transport_jpy, "score": b.true_cost_jpy}


def run_city(ds, n, seed, quick):
    trips = generator.generate_trips(seed, n if not quick else min(n, 6), ds)
    vot = ds.city.default_value_of_time_per_hour
    spec = ObjectiveSpec("true_cost", vot, missed_preference_penalty(ds))
    rows = []
    for t in trips:
        prefs = generator.prefs_for(t, ds)
        hotel = t["hotel_id"]
        t0 = time.perf_counter()
        opt = solve(prefs, hotel, ds, objective=spec, max_seconds=3600, with_alternatives=False)
        rt = round(time.perf_counter() - t0, 3)
        results = {"input_order": baseline(prefs, hotel, ds, order=t["order"]), "nearest_feasible": nearest_neighbour(prefs, hotel, ds, order=t["order"]), "optimiser": opt}
        row = {"id": t["id"], "must": len(t["must_visit"]), "requested": len(t["order"]), "optimiser_runtime_s": rt, "arms": {}, "matched": {}}
        for k, r in results.items():
            row["arms"][k] = score(ds, prefs, hotel, r, vot) or {"feasible": False, "failed": ["no plan"]}
        for k in ("input_order", "nearest_feasible"):
            a = row["arms"][k]
            if a.get("feasible"):                      # re-solve the optimiser to visit exactly the sights this baseline placed
                S = a["sights"]
                p2 = prefs.model_copy(update={"must_visit": S, "skip": [x for x in sorted(ds.attractions) if x not in S]})
                m = solve(p2, hotel, ds, objective=spec, max_seconds=3600, with_alternatives=False)
                row["matched"][k] = score(ds, p2, hotel, m, vot)
        rows.append(row)
    return {"n_trips": len(rows), "default_value_of_time": vot, "rows": rows, "summary": summarise(rows)}


def summarise(rows):
    out = {"arms": {}, "matched": {}, "optimiser_infeasible_but_baseline_feasible": sum((not r["arms"]["optimiser"].get("feasible")) and any(r["arms"][k].get("feasible") for k in ARMS[:2]) for r in rows)}
    for k in ARMS:
        ok = [r for r in rows if r["arms"][k].get("feasible")]
        out["arms"][k] = {"feasible": len(ok), "n": len(rows), "failed_validator": sum(1 for r in rows if r["arms"][k].get("failed") not in (None, ["no plan"])),
                          "no_plan": sum(1 for r in rows if r["arms"][k].get("failed") == ["no plan"]),
                          "missed_a_must_visit_where_optimiser_found_a_plan": sum(1 for r in rows if r["arms"][k].get("failed") == ["no plan"] and r["arms"]["optimiser"].get("feasible")),
                          "optional_coverage_pct": describe(100 * (r["arms"][k]["placed"] - r["must"]) / max(r["requested"] - r["must"], 1) for r in ok if r["requested"] > r["must"]),
                          "minutes": describe(r["arms"][k]["minutes"] for r in ok), "money_ex_rooms": describe(r["arms"][k]["money_ex_rooms"] for r in ok), "score": describe(r["arms"][k]["score"] for r in ok)}
    out["optimiser_runtime_s"] = describe(r["optimiser_runtime_s"] for r in rows)
    allthree = [r for r in rows if all(r["arms"][k].get("feasible") for k in ARMS)]
    out["all_three_feasible"] = len(allthree)
    for k in ARMS[:2]:
        d = [r["arms"][k]["score"] - r["arms"]["optimiser"]["score"] for r in allthree]
        out.setdefault("score_gain_vs", {})[k] = {**describe(d), "positive": sum(x > 0 for x in d), "zero": sum(x == 0 for x in d), "negative": sum(x < 0 for x in d)}
        mm = [r for r in rows if r["matched"].get(k) and r["matched"][k].get("feasible")]
        dm = [r["arms"][k]["minutes"] - r["matched"][k]["minutes"] for r in mm]
        ds_ = [r["arms"][k]["score"] - r["matched"][k]["score"] for r in mm]
        out["matched"][k] = {"baseline_feasible": sum(1 for r in rows if r["arms"][k].get("feasible")), "matched_solved": len(mm), "minutes_saved": {**describe(dm), "better": sum(x > 0 for x in dm), "equal": sum(x == 0 for x in dm), "worse": sum(x < 0 for x in dm)},
                             "score_gain": {**describe(ds_), "better": sum(x > 0 for x in ds_), "equal": sum(x == 0 for x in ds_), "worse": sum(x < 0 for x in ds_)}}
    return out


def _git():
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT.parent).stdout.strip()
        return h + (" + uncommitted changes" if dirty else "")
    except Exception:
        return "unknown"


def render(res):
    L = ["# Itinerary-planning value, separate from hotel choice (sample data)", "",
         f"Generated {res['meta']['date']} by `backend/scripts/run_itinerary_study.py`. Code version: {res['meta']['commit']}. **Seeded synthetic trips on SAMPLE data, estimated straight-line travel times, the trip's own (fictional) hotel fixed; not user-tested; each city reported separately, never pooled.**", "",
         "Every arm uses the same data, constraints, travel matrix and scoring. *Feasible* means every must-visit is placed and the independent validator reports no failed check. *Optional coverage* is the share of the requested optional sights an arm placed. *Known spend* is admissions plus estimated transport; the *score* is the optimisation score (spending + monetised travel time + a charge per optional sight left out) and **is not money spent**. Denominators are all trips; trips where an arm has no plan are counted, not dropped.", ""]
    for c in ORDER:
        r = res["cities"].get(c)
        if not r:
            continue
        s = r["summary"]
        L += [f"## {c.replace('_', ' ').title()}", "", f"{r['n_trips']} trips at the city's default value of time ({r['default_value_of_time']:,} an hour).", "",
              "| Arm | Feasible | No plan | of which optimiser found a plan | Failed a check | Optional coverage (median %, N) | Median est. travel min | Median known spend ex rooms | Median score |", "|---|---|---|---|---|---|---|---|---|"]
        for k in ARMS:
            a = s["arms"][k]
            L.append(f"| {LABEL[k]} | {a['feasible']} of {a['n']} | {a['no_plan']} | {a['missed_a_must_visit_where_optimiser_found_a_plan']} | {a['failed_validator']} | {a['optional_coverage_pct'].get('median', '-')} (N={a['optional_coverage_pct']['n']}) | {a['minutes'].get('median', '-')} | {a['money_ex_rooms'].get('median', '-')} | {a['score'].get('median', '-')} |")
        L += ["", f"Trips where all three arms are feasible: {s['all_three_feasible']}. Trips where the optimiser has no plan but a baseline does (would indicate a problem): {s['optimiser_infeasible_but_baseline_feasible']}.", ""]
        for k in ARMS[:2]:
            g, m = s["score_gain_vs"][k], s["matched"][k]
            L += [f"**Optimiser vs {LABEL[k].lower()}, full plans** (score gain, N={g['n']}): better in {g.get('positive', 0)}, equal in {g.get('zero', 0)}, worse in {g.get('negative', 0)}; median gain {g.get('median', '-')}.",
                  f"**Matched routing vs {LABEL[k].lower()}** (optimiser forced to the same sights; {m['matched_solved']} of {m['baseline_feasible']} feasible baseline plans): estimated travel minutes saved better/equal/worse = {m['minutes_saved']['better']}/{m['minutes_saved']['equal']}/{m['minutes_saved']['worse']} (median {m['minutes_saved'].get('median', '-')}, max {m['minutes_saved'].get('max', '-')}); score gain better/equal/worse = {m['score_gain']['better']}/{m['score_gain']['equal']}/{m['score_gain']['worse']}.", ""]
        L += [f"Optimiser runtime per trip (s): median {round(s['optimiser_runtime_s'].get('median', 0), 2)}, max {round(s['optimiser_runtime_s'].get('max', 0), 2)} (machine-dependent).", ""]
    L += ["## Reading this honestly", "", "- A baseline that places every must-visit and passes the validator is a legitimate plan; where the optimiser ties it, that is reported as a tie.",
          "- *Matched routing* isolates ordering and day assignment. *Full plans* also reflect which optional sights the optimiser chose to leave out, so lower travel there is not a pure saving.",
          "- The scenarios, data and baselines were not modified to produce these numbers.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(DOCS))
    a = ap.parse_args(argv)
    ds_all = load_all_city_datasets()
    t0 = time.perf_counter()
    res = {"meta": {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "commit": _git(), "seeds": {"tokyo": TOKYO_SEED, "others": CITY_SEED}, "quick": a.quick,
                    "label": "seeded synthetic trips on SAMPLE data; estimated travel times; trip's own fictional hotel fixed"}, "cities": {}}
    with deterministic_limits():
        for c in ORDER:
            res["cities"][c] = run_city(ds_all[c], 60 if c == "tokyo" else 20, TOKYO_SEED if c == "tokyo" else CITY_SEED, a.quick)
            print(c, "done", round(time.perf_counter() - t0), "s", flush=True)
    res["meta"]["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    out = Path(a.out)
    slim = json.loads(json.dumps(res))
    for c in slim["cities"].values():
        for r in c["rows"]:
            for arm in list(r["arms"].values()) + list(r["matched"].values()):
                if arm:
                    arm.pop("sights", None)
    (out / "itinerary-study.json").write_text(json.dumps(slim, indent=1) + "\n", encoding="utf-8")
    (out / "itinerary-study.md").write_text(render(res), encoding="utf-8")
    print(f"wrote {out / 'itinerary-study.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
