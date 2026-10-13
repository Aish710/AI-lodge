"""Replanning evaluation: disruption-aware replan vs naive full re-solve, on seeded random scenarios.

Run from backend/:  python scripts/run_replan_evaluation.py
Writes ../docs/replan-results.md. Every number in that file comes from this run (seed below).
Scenario = random attraction subset (5-8 sights, 2 must-visits), 2-4 days, random hotel and start weekday;
initial plan solved with the true-cost objective; then ONE random edit (remove / lock / move / switch hotel).
Strategies: (a) disruption_aware (warm start + disruption penalty), (b) naive (same operations, no disruption term).
"Unnecessarily moved" = unchanged activities whose day changed or whose start shifted by more than the threshold.
"""
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.data.loader import load_dataset  # noqa: E402
from app.optimiser.replan import LockOp, MoveOp, RemoveOp, ReplanError, SwitchHotelOp, replan  # noqa: E402
from app.optimiser.solver import ObjectiveSpec, solve  # noqa: E402
from app.schemas import Preferences  # noqa: E402

SEED = 20261013
PER_EDIT = 6
EDITS = ["remove", "lock", "move", "switch_hotel"]
DOCS = ROOT.parent / "docs"


def make_scenario(rng, ds, edit):
    hotels = list(ds.hotels)
    spec = ObjectiveSpec("true_cost", 1000, config.MISSED_PREFERENCE_PENALTY_JPY)
    for _ in range(50):
        pool = [a for a in ds.attractions if a != "akihabara"]  # unknown hours: never schedulable by default
        subset = rng.sample(pool, rng.randint(5, 8))
        musts = rng.sample(subset, 2)
        days = rng.choice([2, 3, 4])
        prefs = Preferences(days=days, pace="balanced", must_visit=musts, start_weekday=rng.randrange(7),
                            skip=[a for a in ds.attractions if a not in subset], value_of_time_per_hour=1000)
        hotel = rng.choice(hotels)
        cur = solve(prefs, hotel, ds, with_alternatives=False, objective=spec)
        if cur.status != "feasible":
            continue
        stops = [(d.day, s) for d in cur.days for s in d.stops]
        optional = [(d, s) for d, s in stops if s.attraction_id not in musts]
        if edit == "remove" and optional:
            ops = [RemoveOp(op="remove", attraction_id=rng.choice(optional)[1].attraction_id)]
        elif edit == "lock":
            d, s = rng.choice(stops)
            ops = [LockOp(op="lock", attraction_id=s.attraction_id, day=d, start_time=s.start)]
        elif edit == "move":
            d, s = rng.choice(stops)
            h, m = divmod(rng.randrange(9 * 60, 15 * 60 + 1, 15), 60)
            ops = [MoveOp(op="move", attraction_id=s.attraction_id, day=rng.randint(1, days), start_time=f"{h:02d}:{m:02d}")]
        elif edit == "switch_hotel":
            ops = [SwitchHotelOp(op="switch_hotel", hotel_id=rng.choice([x for x in hotels if x != hotel]))]
        else:
            continue
        return prefs, hotel, cur, ops
    raise RuntimeError("could not generate a scenario")


def run_one(prefs, cur, ops, ds, strategy, max_seconds=None):
    try:
        r = replan(prefs, cur, ops, ds, strategy=strategy, max_seconds=max_seconds)
    except ReplanError as e:
        return {"status": "rejected", "why": e.code}
    out = {"status": r.status, "runtime": r.runtime_seconds, "solver_status": r.solver_status}
    if r.status == "applied":
        out.update(moved=r.diff.disruption_count, delta=r.diff.true_cost_jpy.delta, after=r.diff.true_cost_jpy.after,
                   user_moved=sum(m.reason == "user" for m in r.diff.moved), dropped=sum(x.reason == "dropped_by_optimiser" for x in r.diff.removed),
                   added=len(r.diff.added), like=any(w.startswith("Not like-for-like") for w in r.diff.warnings))
    return out


def stat(xs):
    return f"mean {statistics.mean(xs):.2f}, min {min(xs)}, max {max(xs)}, N={len(xs)}" if xs else "n/a (N=0)"


def collect(ds, seed=SEED, per_edit=PER_EDIT, max_seconds=None):
    """Generate and run the scenarios; returns rows (edit, index, days, hotel, n_stops, aware_result, naive_result).
    Imported by scripts/run_evaluation.py so the evaluation reuses exactly this logic (max_seconds lifts the wall-clock limit there)."""
    rng = random.Random(seed)
    rows = []
    for edit in EDITS:
        for i in range(per_edit):
            prefs, hotel, cur, ops = make_scenario(rng, ds, edit)
            rows.append((edit, i + 1, prefs.days, hotel, len(cur.days and [s for d in cur.days for s in d.stops]),
                         run_one(prefs, cur, ops, ds, "disruption_aware", max_seconds), run_one(prefs, cur, ops, ds, "naive", max_seconds)))
    return rows


def summarise(rows):
    """Raw numbers (no formatting) for the evaluation report. N is explicit everywhere."""
    A, N = [r[5] for r in rows], [r[6] for r in rows]
    both = [(a, n) for a, n in zip(A, N) if a["status"] == "applied" and n["status"] == "applied"]

    def one(rs):
        ap = [r for r in rs if r["status"] == "applied"]
        return {"n": len(rs), "applied": len(ap), "moved": [r["moved"] for r in ap], "cost_change_jpy": [r["delta"] for r in ap],
                "infeasible": sum(r["status"] == "infeasible" for r in rs), "rejected": sum(r["status"] == "rejected" for r in rs),
                "runtime_seconds": [r["runtime"] for r in rs if "runtime" in r]}
    return {"n_scenarios": len(rows), "aware": one(A), "naive": one(N), "n_both_applied": len(both),
            "aware_fewer_moves": sum(a["moved"] < n["moved"] for a, n in both), "same_moves": sum(a["moved"] == n["moved"] for a, n in both),
            "aware_more_moves": sum(a["moved"] > n["moved"] for a, n in both),
            "extra_cost_of_stability_jpy": [a["after"] - n["after"] for a, n in both],
            "solver_status": [r["solver_status"] for r in A + N if "solver_status" in r]}


def main():
    ds = load_dataset()
    rows = collect(ds)
    A = [r[5] for r in rows]
    N = [r[6] for r in rows]
    app_a = [a for a in A if a["status"] == "applied"]
    app_n = [n for n in N if n["status"] == "applied"]
    both = [(a, n) for a, n in zip(A, N) if a["status"] == "applied" and n["status"] == "applied"]
    out = [
        "# Replanning evaluation (SAMPLE data)", "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `backend/scripts/run_replan_evaluation.py` (seed {SEED}). "
        "Hotels fictional; attraction data approximate; travel times and fares estimated.", "",
        f"Scenarios: {len(rows)} ({PER_EDIT} each of remove / lock / move / switch_hotel), 2-4 days, random 5-8 sight subsets with 2 must-visits, "
        f"true-cost objective (VoT 1,000 JPY/h, missed penalty {config.MISSED_PREFERENCE_PENALTY_JPY}). "
        f"Disruption weight {config.W_DISRUPTION} JPY per moved activity; moved = day change or start shift > {config.MOVE_THRESHOLD_MINUTES} min; "
        f"per-replan time limit {config.REPLAN_TIME_LIMIT_SECONDS:.0f} s.", "",
        "## Summary", "",
        "| Metric | (a) Disruption-aware | (b) Naive full re-solve |", "|---|---|---|",
        f"| Activities unnecessarily moved (per applied replan) | {stat([a['moved'] for a in app_a])} | {stat([n['moved'] for n in app_n])} |",
        f"| True-cost change, JPY (after - before; negative = cheaper) | {stat([a['delta'] for a in app_a])} | {stat([n['delta'] for n in app_n])} |",
        f"| Solve time, s | {stat([round(r['runtime'], 3) for r in A if 'runtime' in r])} | {stat([round(r['runtime'], 3) for r in N if 'runtime' in r])} |",
        f"| Infeasible replans | {sum(a['status'] == 'infeasible' for a in A)} of {len(A)} | {sum(n['status'] == 'infeasible' for n in N)} of {len(N)} |",
        f"| Rejected before solving (conflicting operations) | {sum(a['status'] == 'rejected' for a in A)} of {len(A)} | {sum(n['status'] == 'rejected' for n in N)} of {len(N)} |",
        f"| Solves not proven OPTIMAL | {sum(a.get('solver_status') == 'FEASIBLE' for a in A)} | {sum(n.get('solver_status') == 'FEASIBLE' for n in N)} |", "",
    ]
    if both:
        extra = [a["after"] - n["after"] for a, n in both]
        fewer = sum(a["moved"] < n["moved"] for a, n in both)
        same = sum(a["moved"] == n["moved"] for a, n in both)
        worse = sum(a["moved"] > n["moved"] for a, n in both)
        out += ["## Cost of stability", "",
                f"Over the {len(both)} scenarios where both strategies produced a plan: disruption-aware moved fewer activities in {fewer}, the same number in {same}, more in {worse}. "
                f"Its final true cost minus the naive plan's final true cost (JPY, always >= 0 when both are optimal): {stat(extra)}.", ""]
    out += ["## Every scenario", "", "| # | Edit | Days | Hotel | Stops | Aware: status / moved / cost change / s | Naive: status / moved / cost change / s | Notes |", "|---|---|---|---|---|---|---|---|"]
    for n, (edit, i, days, hotel, nstops, a, b) in enumerate(rows, 1):
        def cell(x):
            if x["status"] != "applied":
                return x["status"] + (f" ({x['why']})" if "why" in x else "")
            return f"applied / {x['moved']} / {x['delta']:+,} / {x['runtime']}"
        notes = []
        if a["status"] == "applied" and a["like"]:
            notes.append("not like-for-like")
        if a["status"] == "applied" and b["status"] == "applied":
            if a["moved"] > b["moved"]:
                notes.append("aware moved MORE")
            elif a["moved"] == b["moved"] and a["moved"] > 0:
                notes.append("tie on moves")
            if a["after"] > b["after"]:
                notes.append(f"aware costs {a['after'] - b['after']:,} JPY more than naive")
        if a["status"] == "applied" and a.get("solver_status") != "OPTIMAL":
            notes.append("aware not proven optimal")
        out.append(f"| {n} | {edit} | {days} | {hotel[6:]} | {nstops} | {cell(a)} | {cell(b)} | {'; '.join(notes)} |")
    out += ["", "Notes: a `lock` edit here locks an activity at its CURRENT slot, so it changes nothing by itself (cost change 0) and mainly tests that other activities stay put; "
            "`move` edits that conflict with opening hours, travel time or other constraints are rejected before solving (counted separately, not as infeasible). "
            "Cost changes are not like-for-like when optional sights change (flagged per scenario). A shift of 30 minutes or less does not count as moved."]
    (DOCS / "replan-results.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
