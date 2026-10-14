"""Small per-city evaluation for non-Tokyo sample packs.

Tokyo remains covered by scripts/run_evaluation.py --full so its headline claims
stay comparable. This script writes a separate, labelled smaller-sample report
for the added cities and a data-integrity block for every city.
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.eval import generator, metrics  # noqa: E402
from app.eval.limits import deterministic_limits  # noqa: E402

DOCS = ROOT.parent / "docs"


def _git(*args) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except Exception:
        return None


def code_version() -> str:
    head = _git("rev-parse", "--short", "HEAD")
    if head is None:
        return "unavailable"
    return head + (" + uncommitted changes" if _git("status", "--porcelain") else "")


def _describe(xs):
    if not xs:
        return {"n": 0, "mean": None, "min": None, "max": None}
    return {"n": len(xs), "mean": statistics.fmean(xs), "min": min(xs), "max": max(xs)}


def integrity(ds) -> dict:
    atts = list(ds.attractions.values())
    ids = set(ds.attractions) | set(ds.hotels)
    matrix_ok = (
        set(ds.minutes) == ids
        and set(ds.fare_jpy) == ids
        and all(set(ds.minutes[a]) == ids and set(ds.fare_jpy[a]) == ids for a in ids)
        and all(ds.minutes[a][a] == 0 and ds.fare_jpy[a][a] == 0 for a in ids)
        and all(ds.minutes[a][b] == ds.minutes[b][a] and ds.fare_jpy[a][b] == ds.fare_jpy[b][a] for a in ids for b in ids)
    )
    return {
        "city_id": ds.city.id,
        "display_name": ds.city.display_name,
        "country": ds.city.country,
        "currency_code": ds.city.currency_code,
        "display_currency_code": ds.city.display_currency_code,
        "counts": {"attractions": len(ds.attractions), "hotels": len(ds.hotels), "matrix_nodes": len(ds.minutes)},
        "provenance": {
            "attractions": dict(Counter(a.provenance.source_status for a in atts)),
            "hours": dict(Counter(a.hours_provenance.source_status for a in atts)),
            "costs": dict(Counter(a.cost_provenance.source_status for a in atts)),
            "hotels": dict(Counter(h.provenance.source_status for h in ds.hotels.values())),
            "travel_matrix": ds.matrix_meta["source_status"],
        },
        "edge_cases": {
            "unknown_hours": sum(any(v == "unknown" for v in a.opening_hours.values()) for a in atts),
            "unknown_price": sum(a.admission_cost is None for a in atts),
            "advance_booking": sum(a.advance_booking_required for a in atts),
            "weekly_closure_records": sum(any(v is None for v in a.opening_hours.values()) for a in atts),
            "indoor": sum(a.indoor for a in atts),
            "outdoor": sum(not a.indoor for a in atts),
        },
        "matrix_complete_symmetric": matrix_ok,
        "sample_fx_label": ds.city.sample_fx_label,
        "provenance_note": ds.city.provenance,
    }


def evaluate_city(ds, seed: int, n: int) -> dict:
    scenario = json.loads(generator.scenario_file_text(seed, n, ds))
    trips = scenario["trips"]
    trip_results = [metrics.evaluate_trip(t, ds) for t in trips]
    hotel_rows = [metrics.evaluate_hotel_value(t, ds, with_sensitivity=False) for t in trips]
    agg = metrics.aggregate(trip_results, hotel_rows, replan=None, variants=None)
    return {"scenario": scenario, "trips": trip_results, "hotel_value": hotel_rows, "metrics": agg}


def render(raw: dict) -> str:
    lines = [
        "# Multi-city evaluation",
        "",
        f"Generated {raw['meta']['date']} by `backend/scripts/run_city_evaluation.py`. Code version: {raw['meta']['commit']}.",
        "",
        "Singapore and Seoul use smaller seeded samples than Tokyo. They are reported separately and are not pooled into headline claims.",
        "All city data is sample data; hotels are fictional; travel times, prices and hours must be verified before real use.",
        "",
        "## Data integrity",
        "",
        "| City | Attractions | Hotels | Matrix | Provenance | Edge cases |",
        "|---|---:|---:|---|---|---|",
    ]
    for c in raw["integrity"]:
        e = c["edge_cases"]
        lines.append(
            f"| {c['display_name']} | {c['counts']['attractions']} | {c['counts']['hotels']} | "
            f"{'pass' if c['matrix_complete_symmetric'] else 'fail'} | {c['provenance']} | "
            f"unknown hours {e['unknown_hours']}; unknown price {e['unknown_price']}; booking {e['advance_booking']}; closures {e['weekly_closure_records']} |"
        )
    lines += ["", "## Smaller-sample city results", ""]
    for city_id, block in raw["cities"].items():
        m = block["metrics"]
        nn = m["travel"]["nn"]
        naive = m["travel"]["naive"]
        val = m["validation"]["solver"]
        hv = m["hotel_value"]["vots"]
        default_vot = sorted(hv, key=int)[len(hv) // 2]
        lines += [
            f"### {block['city']['display_name']}",
            "",
            f"- Sample size: {m['n_trips']} generated trips (smaller sample, not a headline).",
            f"- Solver plans checked independently: {val['pass'] + val['pass_with_warnings']} of {val['n_trips']} had a plan/check result; {val['fail']} failed.",
            f"- Like-for-like vs input-order baseline: {naive['n_comparable']} comparable trips; mean minutes reduction {_describe([r['reduction_minutes'] for r in naive['rows']])['mean']}.",
            f"- Like-for-like vs nearest-neighbour baseline: {nn['n_comparable']} comparable trips; mean minutes reduction {_describe([r['reduction_minutes'] for r in nn['rows']])['mean']}.",
            f"- Hotel value at the middle tested value-of-time ({default_vot} local units/hour): cheapest nightly rate was not best in {hv[default_vot]['cheapest_by_rate_not_best']} of {hv[default_vot]['n_eligible']} eligible trips.",
            "",
        ]
    lines += [
        "## What these numbers do not show",
        "",
        "- They do not verify live opening hours, prices, exchange rates or hotel rates.",
        "- They do not measure a live LLM; the LLM remains covered by mocked safety tests unless the opt-in live eval is run.",
        "- They do not prove statistical significance.",
        "- They do not compare cities against each other.",
        "- They do not replace Tokyo's full 60-trip evaluation.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--trips", type=int, default=20)
    ap.add_argument("--out-dir", type=Path, default=DOCS)
    args = ap.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    datasets = load_all_city_datasets()
    t0 = time.perf_counter()
    with deterministic_limits():
        cities = {
            cid: {"city": {"id": ds.city.id, "display_name": ds.city.display_name, "currency_code": ds.city.currency_code},
                  **evaluate_city(ds, args.seed, args.trips)}
            for cid, ds in datasets.items() if cid != "tokyo"
        }
    raw = {
        "meta": {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "commit": code_version(),
                 "seed": args.seed, "trips_per_added_city": args.trips, "elapsed_seconds": round(time.perf_counter() - t0, 1)},
        "integrity": [integrity(ds) for ds in datasets.values()],
        "cities": cities,
    }
    (args.out_dir / "city-eval-results.json").write_text(json.dumps(raw, indent=1, ensure_ascii=False, default=str) + "\n")
    (args.out_dir / "city-eval-results.md").write_text(render(raw))
    print(f"City evaluation: {len(cities)} added cities x {args.trips} trips; wrote {args.out_dir} in {raw['meta']['elapsed_seconds']} s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
