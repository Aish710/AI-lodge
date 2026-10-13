"""Reproducible evaluation (Phase 7). Run from backend/:

    python scripts/run_evaluation.py            # --full: 15 scenarios + 60 generated trips + replanning (a few minutes)
    python scripts/run_evaluation.py --quick    # 10 trips, 1 replan per edit type (well under a minute)
    python scripts/run_evaluation.py --seed 7 --out-dir /tmp/eval

Calls the solver, baselines, validator and hotel comparison DIRECTLY (not through the HTTP API) with a fixed seed, one worker and only
a deterministic-time limit (wall-clock limits are lifted, see app/eval/limits.py). No network, no API key, no real language model:
scenarios 13-15 use a scripted mock. Every number in the output files is computed here; nothing is typed in by hand.

Writes (default: ../docs): eval-results.md, eval-results.json, eval-scenarios.json, README-claims.md, eval-travel-minutes.csv,
eval-hotel-gaps.csv, and backend/tests/results/evaluation-scenarios.md. With --out-dir everything goes under that directory instead.
"""
import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import run_replan_evaluation as replan_eval  # noqa: E402  (reused, not re-implemented)
from app import config  # noqa: E402
from app.data.loader import load_dataset  # noqa: E402
from app.eval import claims, generator, metrics, report  # noqa: E402
from app.eval.limits import deterministic_limits, pace_balance_off  # noqa: E402
from app.eval.scenarios import run_all  # noqa: E402

DEFAULT_SEED = replan_eval.SEED
FULL_TRIPS, QUICK_TRIPS = 60, 10
DOCS = ROOT.parent / "docs"


def _git(*args) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - not a git checkout, or git missing
        return None


def code_version() -> str:
    head = _git("rev-parse", "--short", "HEAD")
    if head is None:
        return "unavailable (not a git checkout)"
    return head + (" + uncommitted changes (this hash does not identify the exact code)" if _git("status", "--porcelain") else "")


def _csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help=f"about {QUICK_TRIPS} generated trips (CI / fast demo)")
    mode.add_argument("--full", action="store_true", help=f"{FULL_TRIPS} generated trips (default)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out-dir", type=Path, default=None, help="write all outputs here (default: ../docs and tests/results)")
    args = ap.parse_args(argv)
    quick = args.quick
    n = QUICK_TRIPS if quick else FULL_TRIPS
    out_dir = args.out_dir or DOCS
    tests_dir = (args.out_dir / "tests-results") if args.out_dir else ROOT / "tests" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    ds = load_dataset()
    scenario_text = generator.scenario_file_text(args.seed, n, ds)
    trips = json.loads(scenario_text)["trips"]
    with deterministic_limits() as limits:
        scenarios = run_all(ds)
        trip_results = [metrics.evaluate_trip(t, ds) for t in trips]
        hotel_rows = [metrics.evaluate_hotel_value(t, ds) for t in trips]
        variants = {"phase2_default": [metrics.solver_record(t, ds, "phase2_default") for t in trips]}   # secondary analysis only (section A2)
        with pace_balance_off():
            variants["phase2_default_pace_balance_off"] = [metrics.solver_record(t, ds, "phase2_default") for t in trips]
        replan_rows = replan_eval.collect(ds, seed=args.seed, per_edit=1 if quick else replan_eval.PER_EDIT, max_seconds=3600)
    replan_summary = replan_eval.summarise(replan_rows)
    m = metrics.aggregate(trip_results, hotel_rows, replan_summary, variants)
    elapsed = round(time.perf_counter() - t0, 1)

    meta = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "mode": "quick" if quick else "full", "commit": code_version(),
            "live_eval_exists": (DOCS / "llm-live-eval.md").exists(), "elapsed_seconds": elapsed}
    import ortools
    params = {"seed": args.seed, "n_trips": n, "rows": [
        ["Seed (generator and replanning scenarios)", args.seed], ["Generated trips", f"{n} ({'quick' if quick else 'full'} mode)"],
        ["Replanning scenarios", f"{replan_summary['n_scenarios']} ({'1' if quick else replan_eval.PER_EDIT} per edit type: {', '.join(replan_eval.EDITS)})"],
        ["Solver", f"OR-Tools CP-SAT {ortools.__version__}, seed {limits['solver_seed']}, {limits['solver_workers']} worker, max deterministic time {limits['max_deterministic_time']}"],
        ["Wall-clock limits (lifted for evaluation; shipped values: 20 s solve, 5 s probe, 10 s hotel comparison, 5 s replan)", f"{limits['solver_max_seconds']:g} s each"],
        ["Objective for trip solves (A-D)", f"true cost at the trip's value of time (default {metrics.DEFAULT_VOT:,} JPY/h), missed-preference penalty {config.MISSED_PREFERENCE_PENALTY_JPY} JPY: the objective POST /optimise runs (pinned by a test)"],
        ["Objective for hotel and replan solves", f"same true cost; replanning adds a disruption weight of {config.W_DISRUPTION} JPY per moved activity (move threshold {config.MOVE_THRESHOLD_MINUTES} min)"],
        ["Values of time tested (hotel value)", ", ".join(f"{v:,}" for v in metrics.HOTEL_VOTS) + f" JPY/h (default {metrics.DEFAULT_VOT:,}); flip search range {metrics.SENSITIVITY_RANGE[0]}-{metrics.SENSITIVITY_RANGE[1]:,} JPY/h"],
        ["Generator", f"version {generator.GENERATOR_VERSION}; see `docs/eval-scenarios.json` for all constants"],
        ["Secondary analysis (section A2, added after seeing results)", "same trips re-solved with the Phase 2 weighted objective (which no API route uses), and with its W_PACE = 0; never used for headline numbers"],
        ["'Small average difference' threshold in generated sentences", f"{claims.SMALL_AVERAGE_PERCENT:g}% (judgement call)"],
        ["Rounding", "values that favour the product round down, values that disfavour it round up; counts are exact"],
        ["Python", platform.python_version()], ["Platform", f"{platform.system()} {platform.machine()}"]]}

    (out_dir / "eval-scenarios.json").write_text(scenario_text, encoding="utf-8")
    raw = {"meta": meta, "parameters": params["rows"], "limits": limits,
           "scenarios": [r.__dict__ for r in scenarios], "trips": trip_results, "hotel_value": hotel_rows,
           "secondary_objective_solvers": {k: [{"id": t["id"], "solver": a} for t, a in zip(trips, v)] for k, v in variants.items()}, "metrics": m}
    (out_dir / "eval-results.json").write_text(json.dumps(raw, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    md = report.render_results(metrics=m, scenarios=scenarios, trips=trip_results, meta=meta, params=params)
    (out_dir / "eval-results.md").write_text(md + "\n", encoding="utf-8")
    (out_dir / "README-claims.md").write_text(report.render_claims(claims.generate_claims(m), meta, params) + "\n", encoding="utf-8")

    comparable = {k: {r["id"] for r in m["travel"][k]["rows"]} for k in ("naive", "nn")}
    _csv(out_dir / "eval-travel-minutes.csv",
         ["trip", "hotel", "days", "requested", "must", "budget_kind", "solver_status", "solver_travel_min", "input_order_travel_min", "nearest_neighbour_travel_min",
          "phase2_objective_travel_min_secondary", "phase2_objective_pace_off_travel_min_diagnostic", "solver_placed", "input_order_placed", "nearest_neighbour_placed", "comparable_vs_input_order", "comparable_vs_nearest_neighbour"],
         [[t["id"], t["hotel_id"], t["days"], t["n_requested"], t["n_must"], t["budget_kind"], t["solver"]["solver_status"], t["solver"]["travel_minutes"],
           t["naive"]["travel_minutes"], t["nn"]["travel_minutes"], a["travel_minutes"], b["travel_minutes"], len(t["solver"]["placed"]), len(t["naive"]["placed"]), len(t["nn"]["placed"]),
           t["id"] in comparable["naive"], t["id"] in comparable["nn"]] for t, a, b in zip(trip_results, variants["phase2_default"], variants["phase2_default_pace_balance_off"])])
    _csv(out_dir / "eval-hotel-gaps.csv", ["trip", "vot_jpy_per_h", "eligible", "cheapest_by_rate", "best_by_true_cost", "lowest_rate_not_best", "true_cost_gap_jpy", "travel_hours_gap"],
         [[h["id"], v, e["eligible"], e["cheapest_by_rate"], e["best_by_true_cost"], e.get("differs"), e.get("gap_jpy"), e.get("gap_travel_hours")]
          for h in hotel_rows for v, e in h["by_vot"].items()])
    lines = ["# Scenario results (generated by scripts/run_evaluation.py)", "", f"{sum(r.passed for r in scenarios)} of {len(scenarios)} PASS. Generated {meta['date']}.", "",
             "| # | Scenario | Result | Observed |", "|---|---|---|---|"]
    lines += [f"| {r.num} | {r.name} | {'PASS' if r.passed else 'FAIL'} | {r.observed}{' (mocked LLM: verifies the pipeline, not the model)' if r.mocked_llm else ''} |" for r in scenarios]
    (tests_dir / "evaluation-scenarios.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Evaluation ({meta['mode']}): {sum(r.passed for r in scenarios)}/{len(scenarios)} scenarios PASS; {n} trips; wrote {out_dir} in {elapsed} s.")
    return 0 if all(r.passed for r in scenarios) else 1


if __name__ == "__main__":
    sys.exit(main())
