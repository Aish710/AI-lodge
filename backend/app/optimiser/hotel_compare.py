"""Hotel comparison: for each hotel, the itinerary that minimises TRUE COST for that hotel.

true_cost = rooms + admissions + transport + (travel_hours x value_of_time) + missed_preference_penalty
  rooms          = nightly_rate x nights            (constant per hotel: moves the ranking, not the itinerary)
  admissions     = known admission prices           (unknown prices excluded and listed)
  transport      = ESTIMATED fares, hotel legs included
  time_cost      = round(travel_minutes x value_of_time / 60)
  missed penalty = MISSED_PREFERENCE_PENALTY_JPY x visitable nice-to-have attractions not scheduled
All figures are integer JPY or minutes. SGD is added only at the API presentation layer.

Sensitivity cache rule (see docs/SOLVER_DESIGN.md): a hotel's best cost is  K + T*v/60  for a plan with
non-time cost K and travel minutes T. If the same (K, T) is optimal at two value-of-time values a and b, it
is optimal for every v in [a, b] (a difference of linear functions cannot change sign inside an interval
whose ends agree), so no further solves are needed there. Intervals whose plans differ are halved.
"""
import hashlib
import json
import time
from dataclasses import dataclass

from pydantic import BaseModel

from app import config
from app.money import code, missed_preference_penalty, money, per_hour
from app.data.loader import Dataset, unknown_price_placeholder
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import Conflict, Preferences, SolveResult, nights_for
from app.optimiser.baselines import Baselines, build_baselines
from app.validator.feasibility_report import build_report


class ComparisonInputError(ValueError):
    """Bad hotel list (count, unknown id, duplicate)."""


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------
class MissedPreferences(BaseModel):
    count: int
    attraction_ids: list[str]
    names: list[str]
    penalty_per_item_jpy: int
    penalty_jpy: int


class CostBreakdown(BaseModel):
    nights: int
    nightly_rate_jpy: int
    rooms_jpy: int
    admissions_jpy: int
    transport_jpy: int
    travel_minutes: int
    travel_hours: float
    value_of_time_per_hour: int
    time_cost_jpy: int
    missed_preferences: MissedPreferences
    unknown_price_items: list[str]  # excluded from totals
    optimisation_placeholder_jpy: int = 0  # NOT in totals: value the optimiser assumed per unknown-price sight
    optimisation_placeholder_total_jpy: int = 0
    true_cost_jpy: int


class HotelResult(BaseModel):
    hotel_id: str
    hotel_name: str  # FICTIONAL
    area: str
    nightly_rate_jpy: int
    status: str  # feasible | infeasible | timeout | skipped
    feasible: bool
    solver_status: str
    proven_optimal: bool | None  # None when no solve ran
    runtime_seconds: float
    conflicts: list[Conflict] = []
    itinerary: SolveResult | None = None
    breakdown: CostBreakdown | None = None
    validator_overall: str | None = None
    note: str | None = None


class RankEntry(BaseModel):
    rank: int
    hotel_id: str
    true_cost_jpy: int
    gap_to_winner_jpy: int
    gap_to_winner_travel_hours: float


class Flip(BaseModel):
    from_winner: str
    to_winner: str
    value_of_time_per_hour: float
    method: str  # exact_crossing | bisection_estimate


class GridPoint(BaseModel):
    value_of_time_per_hour: int
    winner: str
    true_cost_jpy: dict[str, int]
    exact: bool


class Sensitivity(BaseModel):
    vot_min: int
    vot_max: int
    grid: list[GridPoint]
    flips: list[Flip]
    flip_summary: str
    approximate: bool
    solves: int
    cache_hits: int
    warnings: list[str] = []


class HotelComparison(BaseModel):
    nights_used: int
    nights_source: str
    value_of_time_per_hour: int
    missed_preference_penalty_jpy: int
    results: list[HotelResult]
    cheapest_by_rate: str
    best_by_true_cost: str | None
    ranking: list[RankEntry]
    rate_winner_differs_from_true_winner: bool
    insight: str
    warnings: list[str]
    approximate: bool
    partial: bool
    elapsed_seconds: float
    time_limit_seconds: float
    sensitivity: Sensitivity | None = None
    baselines: Baselines | None = None


# ---------------------------------------------------------------------------
# Solve cache
# ---------------------------------------------------------------------------
def _prefs_key(prefs: Preferences) -> str:
    """Hash of everything that can change an itinerary except value-of-time and nights."""
    d = prefs.model_dump(exclude={"nights", "value_of_time_per_hour"})
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


class SolveCache:
    def __init__(self):
        self._store: dict[tuple, SolveResult] = {}
        self.solves = 0
        self.hits = 0

    def solve(self, prefs, hotel_id, ds, spec: ObjectiveSpec, max_seconds: float) -> SolveResult:
        key = (hotel_id, _prefs_key(prefs), spec.mode, spec.value_of_time_per_hour, spec.missed_penalty_jpy)
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.solves += 1
        res = solve(prefs, hotel_id, ds, with_alternatives=False, max_seconds=max_seconds, objective=spec)
        self._store[key] = res
        return res


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _validate_input(hotel_ids: list[str], ds: Dataset) -> None:
    if not 2 <= len(hotel_ids) <= 3:
        raise ComparisonInputError(f"Compare 2 or 3 hotels (got {len(hotel_ids)}).")
    if len(set(hotel_ids)) != len(hotel_ids):
        raise ComparisonInputError("Duplicate hotel ids in the request.")
    unknown = [h for h in hotel_ids if h not in ds.hotels]
    if unknown:
        raise ComparisonInputError(f"Unknown hotel id(s): {unknown}")


def _status_of(res: SolveResult) -> str:
    if res.status == "feasible":
        return "feasible"
    return "timeout" if any(c.code == "solver_timeout" for c in res.conflicts) else "infeasible"


def _breakdown(ds: Dataset, prefs: Preferences, hotel_id: str, res: SolveResult, nights: int, vot: int) -> CostBreakdown:
    rate = ds.hotels[hotel_id].nightly_rate
    t = res.totals
    time_cost = (t.travel_minutes * vot + 30) // 60
    pen = missed_preference_penalty(ds)
    missed = res.missed_preferences
    rooms = rate * nights
    return CostBreakdown(
        nights=nights, nightly_rate_jpy=rate, rooms_jpy=rooms, admissions_jpy=t.admissions_jpy,
        transport_jpy=t.transport_jpy, travel_minutes=t.travel_minutes,
        travel_hours=round(t.travel_minutes / 60, 2), value_of_time_per_hour=vot, time_cost_jpy=time_cost,
        missed_preferences=MissedPreferences(
            count=len(missed), attraction_ids=missed, names=[ds.attractions[a].name for a in missed],
            penalty_per_item_jpy=pen, penalty_jpy=pen * len(missed)),
        unknown_price_items=list(t.unknown_cost_items),
        optimisation_placeholder_jpy=unknown_price_placeholder(ds),
        optimisation_placeholder_total_jpy=unknown_price_placeholder(ds) * len(t.unknown_cost_items),
        true_cost_jpy=rooms + t.admissions_jpy + t.transport_jpy + time_cost + pen * len(missed),
    )


def _more_less(x: int, unit: str, more="more", less="less") -> str:
    return f"{abs(x):,} {unit} {more if x >= 0 else less}"


def _insight(ds: Dataset, results: list[HotelResult], cheapest: str, best: str | None) -> str:
    byid = {r.hotel_id: r for r in results}
    if best is None:
        cs = [c for r in results for c in r.conflicts]
        if cs and all(c.category == "missing_information" for c in cs):
            return ("Every hotel is blocked by the same missing information: the data does not say whether a required sight is open, so no plan can be confirmed. "
                    "This is a gap in the sample data, not a finding that the visit is impossible.")
        return "No hotel can host a feasible plan for these requirements; see each hotel's conflicts."
    A, B = byid[cheapest], byid[best]
    ranked = sorted([r for r in results if r.breakdown and r.status == "feasible"], key=lambda r: r.breakdown.true_cost_jpy)
    if A.hotel_id == B.hotel_id:
        if len(ranked) > 1:
            nxt = ranked[1]
            return (f"{A.hotel_name} is both the cheapest per night and the best by true cost; it is "
                    f"{money(nxt.breakdown.true_cost_jpy - A.breakdown.true_cost_jpy, ds)} cheaper in total than {nxt.hotel_name}.")
        return f"{A.hotel_name} is the only hotel with a feasible plan."
    if A.breakdown is None:
        why = A.conflicts[0].message if A.conflicts else A.note or A.status
        return (f"{A.hotel_name} has the lowest nightly rate but has no feasible plan ({why}). "
                f"{B.hotel_name} is the best by true cost.")
    a, b = A.breakdown, B.breakdown
    return (f"{B.hotel_name} costs {money(b.nightly_rate_jpy - a.nightly_rate_jpy, ds)} more per night than {A.hotel_name} "
            f"(the cheapest by rate) but {money(a.true_cost_jpy - b.true_cost_jpy, ds)} less in total once transport and "
            f"travel time are counted: {A.hotel_name} needs {_more_less(a.transport_jpy - b.transport_jpy, code(ds), 'more', 'less')} "
            f"in fares and {abs(a.travel_hours - b.travel_hours):.1f} h {'more' if a.travel_hours >= b.travel_hours else 'less'} travel "
            f"({_more_less(a.time_cost_jpy - b.time_cost_jpy, code(ds), 'more', 'less')} of time at {per_hour(a.value_of_time_per_hour, ds)}).")


# ---------------------------------------------------------------------------
# Sensitivity to value-of-time
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Line:
    K: int  # rooms + admissions + fares + missed penalty (everything except time cost)
    T: int  # travel minutes
    optimal: bool

    def cost(self, v: float) -> float:
        return self.K + self.T * v / 60.0


def _line(ds, prefs, hotel_id, res: SolveResult, nights: int) -> _Line:
    t = res.totals
    K = ds.hotels[hotel_id].nightly_rate * nights + t.admissions_jpy + t.transport_jpy \
        + missed_preference_penalty(ds) * len(res.missed_preferences)
    return _Line(K, t.travel_minutes, res.solver_meta.solver_status == "OPTIMAL")


def sensitivity(prefs: Preferences, hotel_ids: list[str], ds: Dataset, vot_range: tuple[int, int] | None = None,
                *, cache: SolveCache | None = None, deadline: float | None = None) -> Sensitivity:
    _validate_input(hotel_ids, ds)
    vmin, vmax = vot_range or config.VOT_RANGE_DEFAULT
    if not 0 <= vmin < vmax:
        raise ComparisonInputError("vot_range must satisfy 0 <= min < max.")
    cache = cache or SolveCache()
    nights, _ = nights_for(prefs)
    deadline = deadline if deadline is not None else time.monotonic() + config.HOTEL_COMPARE_TIME_LIMIT_SECONDS
    warnings: list[str] = []
    s0, h0 = cache.solves, cache.hits
    solved: dict[int, dict[str, _Line]] = {}
    state = {"timed_out": False, "cap_hit": False, "unrefined": False}

    def solve_point(v: int) -> bool:
        if v in solved:
            return True
        lines = {}
        for i, h in enumerate(hotel_ids):
            left = deadline - time.monotonic()
            if left < config.MIN_SOLVE_SECONDS or cache.solves - s0 >= config.SENS_MAX_SOLVES:
                state["timed_out" if left < config.MIN_SOLVE_SECONDS else "cap_hit"] = True
                return False
            spec = ObjectiveSpec("true_cost", v, missed_preference_penalty(ds))
            res = cache.solve(prefs, h, ds, spec, min(config.SOLVER_MAX_SECONDS, left / (len(hotel_ids) - i)))
            if res.status == "feasible":
                lines[h] = _line(ds, prefs, h, res, nights)
        solved[v] = lines
        return True

    def same(a: int, b: int) -> bool:
        return {h: (l.K, l.T) for h, l in solved[a].items()} == {h: (l.K, l.T) for h, l in solved[b].items()}

    def refine(a: int, b: int, depth: int) -> None:
        if same(a, b):
            return
        mid = (a + b) // 2
        if depth >= config.SENS_MAX_REFINE_DEPTH or mid in (a, b) or not solve_point(mid):
            state["unrefined"] = True
            return
        refine(a, mid, depth + 1)
        refine(mid, b, depth + 1)

    if not (solve_point(vmin) and solve_point(vmax)):
        return Sensitivity(vot_min=vmin, vot_max=vmax, grid=[], flips=[], approximate=True, solves=cache.solves - s0,
                           cache_hits=cache.hits - h0, flip_summary="Not computed: time limit reached before the range ends were solved.",
                           warnings=["Sensitivity incomplete: time limit reached."])
    hotels = [h for h in hotel_ids if h in solved[vmin]]
    if len(hotels) < 2:
        return Sensitivity(vot_min=vmin, vot_max=vmax, grid=[], flips=[], approximate=False, solves=cache.solves - s0,
                           cache_hits=cache.hits - h0, flip_summary="Fewer than two hotels have a feasible plan, so there is nothing to rank.")
    refine(vmin, vmax, 0)
    points = sorted(solved)

    def bracket(v: float) -> tuple[int, int]:
        lo = max([p for p in points if p <= v], default=points[0])
        hi = min([p for p in points if p >= v], default=points[-1])
        return lo, hi

    def cost_fn(h: str, v: float) -> tuple[float, bool]:
        lo, hi = bracket(v)
        la, lb = solved[lo].get(h), solved[hi].get(h)
        if la is None or lb is None:
            return float("inf"), False
        if lo == hi:
            return la.cost(v), True
        if (la.K, la.T) == (lb.K, lb.T):
            return la.cost(v), True
        return min(la.cost(v), lb.cost(v)), False  # upper bound: both are real plans

    def winner(v: float) -> str:
        return min(hotels, key=lambda h: (cost_fn(h, v)[0], ds.hotels[h].nightly_rate, h))

    grid_vs = sorted(set(range(vmin, vmax + 1, config.VOT_GRID_STEP)) | {vmax})
    grid = []
    for v in grid_vs:
        costs = {h: cost_fn(h, v) for h in hotels}
        grid.append(GridPoint(value_of_time_per_hour=v, winner=winner(v),
                              true_cost_jpy={h: round(c[0]) for h, c in costs.items()}, exact=all(c[1] for c in costs.values())))

    flips: list[Flip] = []
    evals = sorted(set(grid_vs) | set(points))
    for e0, e1 in zip(evals, evals[1:]):
        w0, w1 = winner(e0), winner(e1)
        if w0 == w1:
            continue
        lo, hi = bracket((e0 + e1) / 2)
        pl, ql = solved[lo][w0], solved[lo][w1]
        exact = lo != hi and (pl.K, pl.T) == (solved[hi][w0].K, solved[hi][w0].T) and (ql.K, ql.T) == (solved[hi][w1].K, solved[hi][w1].T)
        exact = exact or lo == hi
        if exact and pl.T != ql.T:
            v_star = 60.0 * (ql.K - pl.K) / (pl.T - ql.T)  # K_p + v T_p/60 = K_q + v T_q/60
            if e0 - 1e-6 <= v_star <= e1 + 1e-6:
                flips.append(Flip(from_winner=w0, to_winner=w1, value_of_time_per_hour=round(v_star, 1), method="exact_crossing"))
                continue
        a, b = float(e0), float(e1)
        for _ in range(40):
            mid = (a + b) / 2
            if winner(mid) == w0:
                a = mid
            else:
                b = mid
        flips.append(Flip(from_winner=w0, to_winner=w1, value_of_time_per_hour=round(b, 1), method="bisection_estimate"))

    nonopt = any(not l.optimal for d in solved.values() for l in d.values())
    approximate = nonopt or any(f.method != "exact_crossing" for f in flips) or any(not g.exact for g in grid) \
        or state["unrefined"] or state["timed_out"] or state["cap_hit"]
    if nonopt:
        warnings.append("At least one solve was not proven OPTIMAL (time-limited): sensitivity results are approximate.")
    if state["unrefined"] or state["timed_out"] or state["cap_hit"]:
        warnings.append("Refinement stopped early (depth, solve cap or time limit): values between solved points are upper bounds.")
    if flips:
        flip_summary = "; ".join(f"ranking flips from {f.from_winner} to {f.to_winner} at about {per_hour(f.value_of_time_per_hour, ds)} ({f.method})" for f in flips)
    else:
        flip_summary = f"No flip within {vmin}-{vmax} {code(ds)}/h: {grid[0].winner} wins throughout."
    return Sensitivity(vot_min=vmin, vot_max=vmax, grid=grid, flips=flips, flip_summary=flip_summary, approximate=approximate,
                       solves=cache.solves - s0, cache_hits=cache.hits - h0, warnings=warnings)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compare_hotels(prefs: Preferences, hotel_ids: list[str], ds: Dataset, *, include_sensitivity: bool = False,
                   vot_range: tuple[int, int] | None = None, time_limit: float | None = None,
                   cache: SolveCache | None = None) -> HotelComparison:
    _validate_input(hotel_ids, ds)
    t0 = time.monotonic()
    limit = time_limit if time_limit is not None else config.HOTEL_COMPARE_TIME_LIMIT_SECONDS
    deadline = t0 + limit
    cache = cache or SolveCache()
    nights, nights_src = nights_for(prefs)
    vot = prefs.value_of_time_per_hour
    spec = ObjectiveSpec("true_cost", vot, missed_preference_penalty(ds))
    results: list[HotelResult] = []
    warnings: list[str] = []
    partial = False

    for i, h in enumerate(hotel_ids):
        hotel = ds.hotels[h]
        left = deadline - time.monotonic()
        if left < config.MIN_SOLVE_SECONDS:
            partial = True
            results.append(HotelResult(hotel_id=h, hotel_name=hotel.name, area=hotel.area, nightly_rate_jpy=hotel.nightly_rate,
                                       status="skipped", feasible=False, solver_status="NOT_RUN", proven_optimal=None,
                                       runtime_seconds=0.0, note="Skipped: overall time limit reached before this hotel was solved."))
            continue
        res = cache.solve(prefs, h, ds, spec, min(config.SOLVER_MAX_SECONDS, left / (len(hotel_ids) - i)))
        status = _status_of(res)
        hr = HotelResult(hotel_id=h, hotel_name=hotel.name, area=hotel.area, nightly_rate_jpy=hotel.nightly_rate,
                         status=status, feasible=status == "feasible", solver_status=res.solver_meta.solver_status,
                         proven_optimal=None if res.solver_meta.solver_status == "NOT_RUN" else res.solver_meta.solver_status == "OPTIMAL",
                         runtime_seconds=res.solver_meta.runtime_seconds, conflicts=res.conflicts)
        if status == "feasible":
            rep = build_report(res, ds, prefs, h)
            hr.validator_overall = rep.overall
            if rep.overall == "fail":  # defensive: never rank a plan the independent validator rejects
                hr.status, hr.feasible = "infeasible", False
                hr.note = "Rejected by the independent validator: " + rep.summary
                warnings.append(f"{hotel.name}: plan rejected by validator and excluded from ranking.")
            else:
                hr.itinerary = res
                hr.breakdown = _breakdown(ds, prefs, h, res, nights, vot)
        results.append(hr)

    feasible = [r for r in results if r.feasible and r.breakdown]
    cheapest = min(hotel_ids, key=lambda h: (ds.hotels[h].nightly_rate, h))
    ranked = sorted(feasible, key=lambda r: (r.breakdown.true_cost_jpy, r.nightly_rate_jpy, r.hotel_id))
    best = ranked[0].hotel_id if ranked else None
    ranking = [RankEntry(rank=n + 1, hotel_id=r.hotel_id, true_cost_jpy=r.breakdown.true_cost_jpy,
                         gap_to_winner_jpy=r.breakdown.true_cost_jpy - ranked[0].breakdown.true_cost_jpy,
                         gap_to_winner_travel_hours=round((r.breakdown.travel_minutes - ranked[0].breakdown.travel_minutes) / 60, 2))
               for n, r in enumerate(ranked)]

    for r in results:
        if r.status == "infeasible":
            warnings.append(f"{r.hotel_name} cannot host a feasible plan: " + " | ".join(c.message for c in r.conflicts) if r.conflicts else f"{r.hotel_name}: {r.note}")
        elif r.status == "timeout":
            warnings.append(f"{r.hotel_name}: no plan found within the time limit (not proven infeasible).")
        elif r.status == "skipped":
            warnings.append(f"{r.hotel_name}: {r.note}")
        if r.feasible and r.proven_optimal is False:
            warnings.append(f"{r.hotel_name}: solve ended {r.solver_status} (time-limited), not proven optimal; its true cost may be higher than the best possible plan.")
        if r.breakdown and r.breakdown.unknown_price_items:
            warnings.append(f"{r.hotel_name}: price unknown for {', '.join(r.breakdown.unknown_price_items)}; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of {money(unknown_price_placeholder(ds), ds)} each, not included in the totals shown).")
    sets = {r.hotel_id: {s.attraction_id for d in r.itinerary.days for s in d.stops} - set(prefs.must_visit) for r in feasible}
    if len({frozenset(v) for v in sets.values()}) > 1:
        detail = "; ".join(f"{ds.hotels[h].name}: misses {', '.join(r.breakdown.missed_preferences.names) or 'nothing'}" for h, r in ((r.hotel_id, r) for r in feasible))
        warnings.append("Not like-for-like: hotels schedule different nice-to-have attractions (" + detail + "). Compare missed preferences side by side.")
    if partial:
        warnings.append("PARTIAL result: the overall time limit was reached.")
    approximate = partial or any(r.proven_optimal is False for r in results)

    comp = HotelComparison(
        nights_used=nights, nights_source=nights_src, value_of_time_per_hour=vot,
        missed_preference_penalty_jpy=missed_preference_penalty(ds), results=results,
        cheapest_by_rate=cheapest, best_by_true_cost=best, ranking=ranking,
        rate_winner_differs_from_true_winner=best is not None and best != cheapest,
        insight=_insight(ds, results, cheapest, best), warnings=warnings, approximate=approximate, partial=partial,
        elapsed_seconds=0.0, time_limit_seconds=limit,
        baselines=build_baselines(results, cheapest, best, prefs, hotel_ids, ds))
    if include_sensitivity:
        comp.sensitivity = sensitivity(prefs, hotel_ids, ds, vot_range, cache=cache, deadline=deadline)
        if comp.sensitivity.approximate:
            comp.approximate = True
            comp.warnings.append("Sensitivity analysis is approximate: " + (" ".join(comp.sensitivity.warnings) or "see flip method."))
        if time.monotonic() > deadline:
            comp.partial = True
    comp.elapsed_seconds = round(time.monotonic() - t0, 3)
    return comp
