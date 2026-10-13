"""Naive baseline for fair comparison with the solver.

Takes attractions in the order the user listed them (preferences.must_visit unless `order` is given)
and fills days sequentially. Uses the same travel matrix, hotel, opening hours, day window, pace cap
and strict budget as the solver, so the only difference is *no route optimisation*:
  * each attraction goes after the previous one, in input order
  * if it does not fit on the current day (closed, outside the window, pace cap, budget), move to the next day
  * if it fits on no remaining day it is reported as not placed (never silently dropped)
Locked activities are ignored (the baseline has no notion of them); it waits for opening time if it arrives early.
"""
import time

from app import config
from app.data.loader import Dataset, travel_fare, travel_minutes
from app.optimiser.schedule import assemble, fmt, weekday_of
from app.schemas import Conflict, Preferences, SolveResult, SolverMeta, to_minutes


def baseline(prefs: Preferences, hotel_id: str, ds: Dataset, order: list[str] | None = None) -> SolveResult:
    t0 = time.perf_counter()
    order = list(dict.fromkeys(order if order is not None else prefs.must_visit))
    ds_min, de_min = to_minutes(prefs.day_start), to_minutes(prefs.day_end)
    cap = config.PACE_MAX_PER_DAY[prefs.pace]
    strict = prefs.strict_budget and prefs.budget is not None

    plan: list[list[tuple[str, int]]] = [[] for _ in range(prefs.days)]
    conflicts: list[Conflict] = []
    day = 0
    spent = 0  # admissions + fares committed so far, including the return leg of each non-empty day

    def try_place(aid: str, d: int) -> int | None:
        """Return start minute if aid fits at the end of day d's current route, else None."""
        nonlocal spent
        att = ds.attractions[aid]
        hours = att.opening_hours[weekday_of(prefs, d)]
        if hours is None or len(plan[d]) >= cap:
            return None
        if hours == "unknown" and not prefs.allow_unknown_hours:
            return None
        prev = plan[d][-1][0] if plan[d] else hotel_id
        free = (plan[d][-1][1] + ds.attractions[prev].duration_minutes) if plan[d] else ds_min
        arrive = free + travel_minutes(ds, prev, aid)
        windows = [(ds_min, de_min)] if hours == "unknown" else [(to_minutes(o), to_minutes(c)) for o, c in hours]
        for lo, hi in windows:
            start = max(arrive, lo)
            if start + att.duration_minutes <= min(hi, de_min) and start + att.duration_minutes + travel_minutes(ds, aid, hotel_id) <= de_min:
                if strict:
                    extra = (att.admission_cost or 0) + travel_fare(ds, prev, aid)
                    if plan[d]:
                        extra += travel_fare(ds, aid, hotel_id) - travel_fare(ds, prev, hotel_id)
                    else:
                        extra += travel_fare(ds, aid, hotel_id)
                    if spent + extra > prefs.budget:
                        return None
                    spent += extra
                return start
        return None

    for aid in order:
        if aid not in ds.attractions:
            conflicts.append(Conflict(code="unknown_attraction", message=f"Unknown attraction id '{aid}'.", attraction_ids=[aid]))
            continue
        placed = False
        for d in range(day, prefs.days):
            start = try_place(aid, d)
            if start is not None:
                plan[d].append((aid, start))
                day, placed = d, True
                break
        if not placed:
            conflicts.append(Conflict(code="baseline_not_placed", message=f"Baseline could not fit {ds.attractions[aid].name} on any remaining day.", attraction_ids=[aid]))

    days, totals = assemble(ds, prefs, hotel_id, plan)
    status = "infeasible" if any(a in {x for c in conflicts for x in c.attraction_ids} for a in prefs.must_visit) or any(c.code == "unknown_attraction" for c in conflicts) else "feasible"
    return SolveResult(
        status=status, hotel_id=hotel_id, days=days, totals=totals, conflicts=conflicts,
        notes=["Naive baseline: input order, sequential fill, no route optimisation."],
        solver_meta=SolverMeta(solver="baseline-sequential", solver_status="N/A", seed=0,
                               runtime_seconds=round(time.perf_counter() - t0, 4)),
    )


def nearest_neighbour(prefs: Preferences, hotel_id: str, ds: Dataset, order: list[str] | None = None) -> SolveResult:
    """Nearest-neighbour greedy baseline: the heuristic a careful person with a map could follow.

    Day by day, starting at the hotel at day_start: go to the nearest (fewest travel minutes) unvisited attraction that is
    open when you arrive (waiting for opening if early), fits before day_end including the trip back to the hotel, is within
    the pace cap and keeps a strict budget. Ties: earliest start, then id. Same matrix, hours and rules as the solver; no
    lookahead and no must-visit priority, so a must-visit it cannot reach is reported as not placed (never silently dropped).
    `order` is the pool of requested attractions (default: must_visit); its order does not influence the result except through
    the tie-break rules above.
    """
    t0 = time.perf_counter()
    pool = list(dict.fromkeys(order if order is not None else prefs.must_visit))
    ds_min, de_min = to_minutes(prefs.day_start), to_minutes(prefs.day_end)
    cap = config.PACE_MAX_PER_DAY[prefs.pace]
    strict = prefs.strict_budget and prefs.budget is not None
    conflicts = [Conflict(code="unknown_attraction", message=f"Unknown attraction id '{a}'.", attraction_ids=[a]) for a in pool if a not in ds.attractions]
    remaining = [a for a in pool if a in ds.attractions]
    plan: list[list[tuple[str, int]]] = [[] for _ in range(prefs.days)]
    spent = 0

    def earliest_start(d: int, pos: str, free: int, aid: str) -> int | None:
        att = ds.attractions[aid]
        hours = att.opening_hours[weekday_of(prefs, d)]
        if hours is None or (hours == "unknown" and not prefs.allow_unknown_hours):
            return None
        arrive = free + travel_minutes(ds, pos, aid)
        windows = [(ds_min, de_min)] if hours == "unknown" else [(to_minutes(o), to_minutes(c)) for o, c in hours]
        for lo, hi in windows:
            start = max(arrive, lo)
            end = start + att.duration_minutes
            if end <= min(hi, de_min) and end + travel_minutes(ds, aid, hotel_id) <= de_min:
                return start
        return None

    def extra_cost(pos: str, aid: str, first_of_day: bool) -> int:
        extra = (ds.attractions[aid].admission_cost or 0) + travel_fare(ds, pos, aid) + travel_fare(ds, aid, hotel_id)
        return extra if first_of_day else extra - travel_fare(ds, pos, hotel_id)

    for d in range(prefs.days):
        pos, free = hotel_id, ds_min
        while len(plan[d]) < cap and remaining:
            best = None  # (key, aid, start, extra)
            for aid in remaining:
                start = earliest_start(d, pos, free, aid)
                if start is None:
                    continue
                extra = extra_cost(pos, aid, not plan[d])
                if strict and spent + extra > prefs.budget:
                    continue
                key = (travel_minutes(ds, pos, aid), start, aid)
                if best is None or key < best[0]:
                    best = (key, aid, start, extra)
            if best is None:
                break
            _, aid, start, extra = best
            plan[d].append((aid, start))
            remaining.remove(aid)
            spent += extra
            pos, free = aid, start + ds.attractions[aid].duration_minutes

    for aid in remaining:
        conflicts.append(Conflict(code="nn_not_placed", message=f"Nearest-neighbour baseline could not place {ds.attractions[aid].name}.", attraction_ids=[aid]))
    days, totals = assemble(ds, prefs, hotel_id, plan)
    unplaced_must = [c for c in conflicts if c.code == "unknown_attraction" or set(c.attraction_ids) & set(prefs.must_visit)]
    return SolveResult(
        status="infeasible" if unplaced_must else "feasible", hotel_id=hotel_id, days=days, totals=totals, conflicts=conflicts,
        notes=["Nearest-neighbour baseline: always go to the nearest feasible attraction; no route optimisation."],
        solver_meta=SolverMeta(solver="baseline-nearest-neighbour", solver_status="N/A", seed=0,
                               runtime_seconds=round(time.perf_counter() - t0, 4)),
    )
