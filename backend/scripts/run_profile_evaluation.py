"""Do travel profiles actually change plans? (no model, no network)

For the same seeded trips as the other evaluations, each profile in frontend/src/lib/profiles.json is applied to the trip's preferences (pace, activities a day, estimated travel a day,
value of time at the profile's multiple of the CITY's own default) and solved by the shipped optimiser at the trip's hotel. Compared with the same trip with no profile.
Reported per city, with denominators: how often the plan was identical to no-profile, how often it was infeasible, and the median change in estimated travel, known spend and optional sights.
If a profile gives the same plan as no profile, that is reported as such, not hidden.  Usage (from backend/):  python scripts/run_profile_evaluation.py [--quick] [--out DIR]"""
import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.eval import generator  # noqa: E402
from app.eval.limits import deterministic_limits  # noqa: E402
from app.money import missed_preference_penalty  # noqa: E402
from app.optimiser.solver import ObjectiveSpec, solve  # noqa: E402
from run_itinerary_study import _git, describe  # noqa: E402

DOCS = ROOT.parent / "docs"
PROFILES = json.loads((ROOT.parent / "frontend" / "src" / "lib" / "profiles.json").read_text())["profiles"]
ORDER = ["tokyo", "singapore", "seoul", "kuala_lumpur"]


def apply(prefs, prof, vot_default):
    upd = {"pace": prof["pace"], "value_of_time_per_hour": round(vot_default * prof["votFactor"])}
    if prof["maxActivities"] != "":
        upd["max_activities_per_day"] = prof["maxActivities"]
    if prof["maxDailyTravel"] != "":
        upd["max_daily_travel_minutes"] = prof["maxDailyTravel"]
    return prefs.model_copy(update=upd)


def sig(res):
    return [(d.day, [(s.attraction_id, s.start) for s in d.stops]) for d in res.days]


def run_city(ds, n, seed, quick):
    trips = generator.generate_trips(seed, n if not quick else min(n, 6), ds)
    vot = ds.city.default_value_of_time_per_hour
    pen = missed_preference_penalty(ds)
    out = {"n_trips": len(trips), "profiles": {}}
    base = {}
    for t in trips:
        p = generator.prefs_for(t, ds)
        base[t["id"]] = (p, solve(p, t["hotel_id"], ds, objective=ObjectiveSpec("true_cost", p.value_of_time_per_hour, pen), max_seconds=3600, with_alternatives=False))
    for prof in PROFILES:
        rows = []
        for t in trips:
            p0, r0 = base[t["id"]]
            if r0.status != "feasible":
                continue
            p = apply(p0, prof, vot)
            r = solve(p, t["hotel_id"], ds, objective=ObjectiveSpec("true_cost", p.value_of_time_per_hour, pen), max_seconds=3600, with_alternatives=False)
            row = {"id": t["id"], "feasible": r.status == "feasible", "same_plan": r.status == "feasible" and sig(r) == sig(r0)}
            if r.status == "feasible":
                row.update(d_minutes=r.totals.travel_minutes - r0.totals.travel_minutes, d_spend=(r.totals.admissions_jpy + r.totals.transport_jpy) - (r0.totals.admissions_jpy + r0.totals.transport_jpy),
                           d_sights=r.totals.attractions_scheduled - r0.totals.attractions_scheduled)
            rows.append(row)
        ok = [r for r in rows if r["feasible"]]
        out["profiles"][prof["id"]] = {"label": prof["label"], "comparable_trips": len(rows), "feasible": len(ok), "infeasible_with_profile": len(rows) - len(ok), "same_plan_as_no_profile": sum(r["same_plan"] for r in ok),
                                       "changed_minutes": describe(r["d_minutes"] for r in ok), "changed_spend": describe(r["d_spend"] for r in ok), "changed_sights": describe(r["d_sights"] for r in ok)}
    return out


def render(res):
    L = ["# Do travel profiles change plans? (sample data)", "",
         f"Generated {res['meta']['date']} by `backend/scripts/run_profile_evaluation.py`. Code version: {res['meta']['commit']}. **Seeded synthetic trips on SAMPLE data with estimated travel times, the trip's own (fictional) hotel; not user-tested; per city, never pooled.**", "",
         "Each profile (`frontend/src/lib/profiles.json`) is applied to a trip that is feasible with no profile and re-solved by the shipped optimiser. *Same plan* means identical days, stops and start times. *Infeasible* means the profile's limits cannot be met for that trip (reported, not hidden). Differences are profile minus no-profile (negative = less).", ""]
    for c in ORDER:
        r = res["cities"].get(c)
        if not r:
            continue
        L += [f"## {c.replace('_', ' ').title()}", "", f"{r['n_trips']} trips; comparable = feasible with no profile.", "", "| Profile | Comparable | Infeasible with profile | Same plan as no profile | Median change in est. travel (min) | Median change in sight + transport spend | Median change in sights |", "|---|---|---|---|---|---|---|"]
        for p in r["profiles"].values():
            L.append(f"| {p['label']} | {p['comparable_trips']} | {p['infeasible_with_profile']} | {p['same_plan_as_no_profile']} of {p['feasible']} | {p['changed_minutes'].get('median', '-')} | {p['changed_spend'].get('median', '-')} | {p['changed_sights'].get('median', '-')} |")
        L.append("")
    L += ["## Reading this honestly", "", "- Where a profile gives the same plan for most trips, it changes the settings but not the outcome for those trips.", "- Profile values are proposals; they were not tuned to produce these numbers.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(DOCS))
    a = ap.parse_args(argv)
    ds_all = load_all_city_datasets()
    t0 = time.perf_counter()
    res = {"meta": {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "commit": _git(), "quick": a.quick, "profiles_version": json.loads((ROOT.parent / "frontend" / "src" / "lib" / "profiles.json").read_text())["version"]}, "cities": {}}
    with deterministic_limits():
        for c in ORDER:
            res["cities"][c] = run_city(ds_all[c], 60 if c == "tokyo" else 20, 20261013 if c == "tokyo" else 20261014, a.quick)
            print(c, "done", round(time.perf_counter() - t0), "s", flush=True)
    out = Path(a.out)
    (out / "profile-results.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    (out / "profile-results.md").write_text(render(res), encoding="utf-8")
    print(f"wrote {out / 'profile-results.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
