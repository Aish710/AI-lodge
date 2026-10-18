"""CP-SAT itinerary solver. See docs/SOLVER_DESIGN.md for the full model description.

solve(preferences, hotel_id, dataset) -> SolveResult

Model (per trip day d, hotel = depot):
  * one optional node per (attraction, opening-range) that could be visited on that day
  * AddCircuit over [depot + nodes]: chooses visiting order; absent nodes take a self-loop
  * arc i->j  =>  start_j >= start_i + duration_i + travel(i, j)         (travel time respected)
  * arc depot->j => start_j >= day_start + travel(hotel, j); arc i->depot => end_i + travel(i, hotel) <= day_end
  * start domain is inside the opening range (closed days have no nodes; unknown hours only if allowed)
  * each attraction at most once overall; must-visits and locked items exactly once
  * locked items: single node on the locked day with the start fixed
  * per-day count <= pace cap; strict budget: admissions + fares <= budget

Objective (all integer; see config.py for weights, SOLVER_DESIGN.md for the normalisation):
  W_TRAVEL  * travel_min / (days * window)
+ W_COST    * cost_jpy / (COST_REF_JPY_PER_DAY * days)
+ W_MISSED  * missed_nice_to_have / n_nice
+ W_PACE    * (busiest_day - quietest_day) / pace_cap
+ W_OVER    * over_budget_jpy / cost_ref            (only for a non-strict budget)
"""
import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app import config
from app.money import money
from app.data.loader import Dataset, travel_fare, travel_minutes, unknown_price_placeholder
from app.optimiser.cancel import Cancelled, current_token
from app.optimiser.schedule import assemble, fmt, fmt_duration, required_ids, weekday_of
from app.schemas import (
    Alternative, Conflict, Preferences, SolveResult, SolverMeta, to_minutes,
)

SOLVER_NAME = "ortools-cp-sat"


@dataclass(frozen=True)
class ObjectiveSpec:
    """Which objective to minimise. Default = the Phase 2 weighted objective (unchanged).

    mode="true_cost" (hotel comparison): minimise, in JPY,
        admissions + fares + travel_hours * value_of_time + missed_penalty_jpy * missed_nice_to_have
    Solved as integers in units of 1/60 JPY:  60*(adm+fares) + VoT_per_hour*travel_min + 60*penalty*missed
    (+ 60*disruption_jpy*moved + 1 per minute of start-time drift as a tie-break when replanning).
    Unknown admission prices are valued at a median placeholder inside the objective only.
    """
    mode: str = "default"
    value_of_time_per_hour: int = 0
    missed_penalty_jpy: int = 0
    # Replanning (true_cost mode only): charge disruption_jpy per activity that was in `reference`
    # (aid, day_index, start_minute) and now changes day or shifts by more than move_threshold_min.
    disruption_jpy: int = 0
    move_threshold_min: int = 30
    reference: tuple = ()


@dataclass
class _Ctx:
    prefs: Preferences
    hotel_id: str
    ds: Dataset
    D: int = 0
    ds_min: int = 0
    de_min: int = 0
    window: int = 0
    cap: int = 0
    must: list[str] = field(default_factory=list)
    skip: set[str] = field(default_factory=set)
    locked: dict[str, tuple[int, int]] = field(default_factory=dict)  # id -> (day index, start minute)
    candidates: list[str] = field(default_factory=list)

    @property
    def required(self) -> list[str]:
        return list(dict.fromkeys(self.must + list(self.locked)))


def _make_ctx(prefs: Preferences, hotel_id: str, ds: Dataset) -> _Ctx:
    if hotel_id not in ds.hotels:
        raise ValueError(f"unknown hotel id '{hotel_id}'")
    c = _Ctx(prefs, hotel_id, ds)
    c.D = prefs.days
    c.ds_min, c.de_min = to_minutes(prefs.day_start), to_minutes(prefs.day_end)
    c.window = c.de_min - c.ds_min
    c.cap = prefs.max_activities_per_day or config.PACE_MAX_PER_DAY[prefs.pace]   # the user's own limit replaces the pace preset's cap
    c.must = required_ids(prefs)
    c.skip = set(prefs.skip) | {a.id for a in ds.attractions.values() if a.priority == "skip"}
    c.skip -= set(c.must)  # an explicit must-visit overrides a dataset-level "skip"
    c.locked = {l.attraction_id: (l.day - 1, to_minutes(l.start_time)) for l in prefs.locked}
    c.candidates = [a for a in ds.attractions if a not in c.skip or a in c.locked]
    return c


def _cap_text(c: _Ctx) -> str:
    return f"your limit of {c.cap} a day" if c.prefs.max_activities_per_day else f"the '{c.prefs.pace}' pace"


def _name(c: _Ctx, aid: str) -> str:
    return c.ds.attractions[aid].name


def _ranges(c: _Ctx, aid: str, d: int) -> list[tuple[int, int]]:
    """Usable [lo, hi] windows (minutes) for attraction aid on day index d; empty = not visitable."""
    att = c.ds.attractions[aid]
    dur = att.duration_minutes
    hours = att.opening_hours[weekday_of(c.prefs, d)]
    if hours is None:
        return []  # closed
    if hours == "unknown":
        raw = [(c.ds_min, c.de_min)] if c.prefs.allow_unknown_hours else []
    else:
        raw = [(max(to_minutes(o), c.ds_min), min(to_minutes(cl), c.de_min)) for o, cl in hours]
    out = [(lo, hi) for lo, hi in raw if hi - lo >= dur]
    if aid in c.locked:
        ld, ls = c.locked[aid]
        if d != ld:
            return []
        out = [(lo, hi) for lo, hi in out if lo <= ls <= hi - dur]
    return out


# ---------------------------------------------------------------------------
# Pre-check: human-readable conflicts computed from data, before any solving.
# ---------------------------------------------------------------------------
def _precheck(c: _Ctx) -> list[Conflict]:
    ds, p, out = c.ds, c.prefs, []
    unknown = [a for a in c.must + list(c.locked) + p.skip if a not in ds.attractions]
    for a in dict.fromkeys(unknown):
        out.append(Conflict(code="unknown_attraction", message=f"Attraction id '{a}' is not in the dataset.", attraction_ids=[a]))
    if out:
        return out
    for a in c.must:
        if a in p.skip:
            out.append(Conflict(code="must_and_skip", message=f"{_name(c, a)} is both a must-visit and skipped.", attraction_ids=[a]))
    for a, (ld, ls) in c.locked.items():
        if a in p.skip:
            out.append(Conflict(code="locked_and_skip", message=f"{_name(c, a)} is locked but also marked skip.", attraction_ids=[a]))
        if ld >= c.D:
            out.append(Conflict(code="lock_outside_trip", message=f"{_name(c, a)} is locked on day {ld + 1} but the trip has {c.D} day(s).", attraction_ids=[a]))
    if out:
        return out

    for a in c.required:
        att = ds.attractions[a]
        days = [d for d in range(c.D) if _ranges(c, a, d)]
        if a in c.locked:
            ld, ls = c.locked[a]
            if not days:
                wd = weekday_of(p, ld).upper()
                hours = att.opening_hours[weekday_of(p, ld)]
                why = ("it is closed that day" if hours is None else
                       "its opening hours are unknown and unknown hours are not allowed" if hours == "unknown" and not p.allow_unknown_hours else
                       f"{fmt(ls)}-{fmt(ls + att.duration_minutes)} is outside its opening hours or the day window")
                out.append(Conflict(code="locked_not_possible", message=f"{att.name} is locked on day {ld + 1} ({wd}) at {fmt(ls)} but {why}.", attraction_ids=[a]))
            else:
                tin, tout = travel_minutes(ds, c.hotel_id, a), travel_minutes(ds, a, c.hotel_id)
                if ls < c.ds_min + tin or ls + att.duration_minutes + tout > c.de_min:
                    out.append(Conflict(code="locked_no_travel_time", message=f"{att.name} locked at {fmt(ls)} leaves no room for the {tin} min trip from the hotel or the {tout} min trip back within {p.day_start}-{p.day_end}.", attraction_ids=[a]))
            continue
        tin, tout = travel_minutes(ds, c.hotel_id, a), travel_minutes(ds, a, c.hotel_id)
        need = att.duration_minutes + tin + tout
        if need > c.window:
            out.append(Conflict(code="does_not_fit_day", message=f"Must-visit {att.name} needs {fmt_duration(need)} ({att.duration_minutes} min visit + {tin + tout} min round trip from the hotel) but a day only has {fmt_duration(c.window)} ({p.day_start}-{p.day_end}).", attraction_ids=[a]))
            continue
        if p.max_daily_travel_minutes and tin + tout > p.max_daily_travel_minutes:
            out.append(Conflict(code="daily_travel_limit", message=f"Must-visit {att.name} needs {tin + tout} min of estimated travel for the round trip from the hotel but the daily limit is {p.max_daily_travel_minutes} min.", attraction_ids=[a]))
            continue
        if not days:
            all_closed = all(att.opening_hours[weekday_of(p, d)] is None for d in range(c.D))
            has_unknown = any(att.opening_hours[weekday_of(p, d)] == "unknown" for d in range(c.D))
            if has_unknown and not p.allow_unknown_hours:
                out.append(Conflict(code="unknown_hours_not_allowed", message=f"Must-visit {att.name} has unknown opening hours, and unknown hours are not allowed (it is never assumed open).", attraction_ids=[a]))
            elif all_closed:
                out.append(Conflict(code="closed_all_days", message=f"Must-visit {att.name} is closed on all {c.D} trip day(s).", attraction_ids=[a]))
            else:
                out.append(Conflict(code="no_open_slot", message=f"Must-visit {att.name} has no usable time slot on any trip day given its opening hours and the day window.", attraction_ids=[a]))
    if out:
        return out

    req = c.required
    if len(req) > c.D * c.cap:
        out.append(Conflict(code="pace_cap", message=f"{len(req)} required attractions but {_cap_text(c)} allows {c.cap}/day x {c.D} day(s) = {c.D * c.cap}.", attraction_ids=req))
    # Lower bound on time: visits + the cheapest possible inbound leg for each + one return leg.
    others = c.candidates

    def min_in(a, table):
        return min([table(ds, c.hotel_id, a)] + [table(ds, o, a) for o in others if o != a])

    if req:
        need = sum(ds.attractions[a].duration_minutes + min_in(a, travel_minutes) for a in req)
        need += min(travel_minutes(ds, a, c.hotel_id) for a in others)
        if need > c.D * c.window:
            out.append(Conflict(code="not_enough_time", message=f"Must-visits need at least {fmt_duration(need)} including travel but only {fmt_duration(c.D * c.window)} are available ({c.D} day(s) x {fmt_duration(c.window)}).", attraction_ids=req))
        if p.strict_budget and p.budget is not None:
            adm = sum(ds.attractions[a].admission_cost or 0 for a in req)
            fare = sum(min_in(a, travel_fare) for a in req) + min(travel_fare(ds, a, c.hotel_id) for a in others)
            if adm + fare > p.budget:
                out.append(Conflict(code="budget_too_low", message=f"Cost of must-visits exceeds the strict budget by at least {money(adm + fare - p.budget, ds)} (admissions {adm:,} + minimum estimated transport {fare:,} vs budget {p.budget:,}).", attraction_ids=req))
    # Locked activities on the same day must be reachable from each other.
    by_day: dict[int, list[tuple[int, str]]] = {}
    for a, (ld, ls) in c.locked.items():
        by_day.setdefault(ld, []).append((ls, a))
    for ld, items in by_day.items():
        items.sort()
        for (s1, a1), (s2, a2) in zip(items, items[1:]):
            need = s1 + ds.attractions[a1].duration_minutes + travel_minutes(ds, a1, a2)
            if need > s2:
                out.append(Conflict(code="locked_overlap", message=f"Locked {_name(c, a1)} ({fmt(s1)}) and {_name(c, a2)} ({fmt(s2)}) on day {ld + 1} cannot both happen: travel between them ends at {fmt(need)}.", attraction_ids=[a1, a2]))
        if len(items) > c.cap:
            out.append(Conflict(code="pace_cap", message=f"Day {ld + 1} has {len(items)} locked activities but {_cap_text(c)} allows {c.cap}.", attraction_ids=[a for _, a in items]))
    return out


# ---------------------------------------------------------------------------
# CP-SAT model
# ---------------------------------------------------------------------------
def _solve_core(c: _Ctx, max_seconds: float, spec: ObjectiveSpec = ObjectiveSpec()) -> tuple[str, list[list[tuple[str, int]]] | None, float | None]:
    ds, p = c.ds, c.prefs
    m = cp_model.CpModel()
    S = config.OBJECTIVE_SCALE
    presence: dict[str, list] = {a: [] for a in c.candidates}  # literals per attraction
    day_count = []
    travel_terms, fare_terms, adm_terms, ph_terms = [], [], [], []
    placeholder = unknown_price_placeholder(ds)
    ref = {a: (d, st) for a, d, st in spec.reference}
    moved_terms, drift_terms = [], []
    node_info: list[list[tuple]] = []  # per day: (aid, pres, start)
    arc_lits: list[list[tuple]] = []  # per day: (i_aid|None, j_aid|None, lit, start_i, start_j)

    for d in range(c.D):
        t_first = len(travel_terms)   # this day's travel terms start here (for the daily travel limit)
        nodes = []  # (aid, lo, hi)
        for a in c.candidates:
            for lo, hi in _ranges(c, a, d):
                nodes.append((a, lo, hi - ds.attractions[a].duration_minutes))
        pres, starts = [], []
        for k, (a, lo, hi) in enumerate(nodes):
            pr = m.NewBoolVar(f"p_{d}_{k}")
            st = m.NewIntVar(lo, hi, f"s_{d}_{k}")
            if a in c.locked:
                m.Add(st == c.locked[a][1])
            pres.append(pr)
            starts.append(st)
            presence[a].append(pr)
            if ds.attractions[a].admission_cost:
                adm_terms.append((ds.attractions[a].admission_cost, pr))
            elif ds.attractions[a].admission_cost is None and placeholder:
                ph_terms.append((placeholder, pr))  # objective only, never in constraints or displayed totals
            if spec.mode == "true_cost" and spec.disruption_jpy and a in ref and a not in c.locked:
                pd_, ps_ = ref[a]
                if d != pd_:
                    moved_terms.append(pr)
                else:
                    ok = m.NewBoolVar(f"ok_{d}_{k}")
                    m.Add(st >= ps_ - spec.move_threshold_min).OnlyEnforceIf(ok)
                    m.Add(st <= ps_ + spec.move_threshold_min).OnlyEnforceIf(ok)
                    mv = m.NewBoolVar(f"mv_{d}_{k}")
                    m.AddBoolOr([pr.Not(), ok, mv])
                    moved_terms.append(mv)
                    dev = m.NewIntVar(0, 24 * 60, f"dev_{d}_{k}")
                    m.Add(dev >= st - ps_)
                    m.Add(dev >= ps_ - st)
                    drift_terms.append(dev)
            if ref:  # warm start from the previous plan
                m.AddHint(pr, 1 if (a in ref and ref[a][0] == d and lo <= ref[a][1] <= hi) else 0)
                if a in ref and ref[a][0] == d:
                    m.AddHint(st, min(max(ref[a][1], lo), hi))
        node_info.append([(nodes[k][0], pres[k], starts[k]) for k in range(len(nodes))])
        empty = m.NewBoolVar(f"empty_{d}")
        arcs = [(0, 0, empty)]
        for k, pr in enumerate(pres):
            m.AddImplication(pr, empty.Not())
            arcs.append((k + 1, k + 1, pr.Not()))
        day_arcs = []
        for k, (a, lo, hi) in enumerate(nodes):
            dur = ds.attractions[a].duration_minutes
            lit = m.NewBoolVar(f"in_{d}_{k}")  # hotel -> k
            m.Add(starts[k] >= c.ds_min + travel_minutes(ds, c.hotel_id, a)).OnlyEnforceIf(lit)
            arcs.append((0, k + 1, lit))
            travel_terms.append((travel_minutes(ds, c.hotel_id, a), lit))
            fare_terms.append((travel_fare(ds, c.hotel_id, a), lit))
            lit2 = m.NewBoolVar(f"out_{d}_{k}")  # k -> hotel
            m.Add(starts[k] + dur + travel_minutes(ds, a, c.hotel_id) <= c.de_min).OnlyEnforceIf(lit2)
            arcs.append((k + 1, 0, lit2))
            travel_terms.append((travel_minutes(ds, a, c.hotel_id), lit2))
            fare_terms.append((travel_fare(ds, a, c.hotel_id), lit2))
            for j, (b, _, _) in enumerate(nodes):
                if j == k or b == a:
                    continue
                lit3 = m.NewBoolVar(f"a_{d}_{k}_{j}")
                m.Add(starts[j] >= starts[k] + dur + travel_minutes(ds, a, b)).OnlyEnforceIf(lit3)
                arcs.append((k + 1, j + 1, lit3))
                travel_terms.append((travel_minutes(ds, a, b), lit3))
                fare_terms.append((travel_fare(ds, a, b), lit3))
        m.AddCircuit(arcs)
        if p.max_daily_travel_minutes:      # hard: ESTIMATED minutes of the day, both hotel legs included, from the same table the validator re-reads
            m.Add(sum(w * l for w, l in travel_terms[t_first:]) <= p.max_daily_travel_minutes)
        cnt = m.NewIntVar(0, c.cap, f"cnt_{d}")
        m.Add(cnt == sum(pres)) if pres else m.Add(cnt == 0)
        day_count.append(cnt)

    for a in c.candidates:
        lits = presence[a]
        if a in c.required:
            m.Add(sum(lits) == 1) if lits else m.AddBoolOr([])  # empty -> infeasible
        elif lits:
            m.Add(sum(lits) <= 1)

    cost_expr = sum(w * l for w, l in adm_terms) + sum(w * l for w, l in fare_terms)
    cost_obj_expr = cost_expr + sum(w * l for w, l in ph_terms)  # objective only
    travel_expr = sum(w * l for w, l in travel_terms)
    if p.strict_budget and p.budget is not None:
        m.Add(cost_expr <= p.budget)

    ref_cost = config.COST_REF_JPY_PER_DAY * c.D
    nice = [a for a in c.candidates if a not in c.required]
    const = 0
    if spec.mode == "true_cost":
        elig = [a for a in nice if presence[a]]
        pen = 60 * spec.missed_penalty_jpy
        obj = [60 * cost_obj_expr, spec.value_of_time_per_hour * travel_expr]
        if moved_terms:
            obj += [60 * spec.disruption_jpy * sum(moved_terms), sum(drift_terms)]
        const = pen * len(elig)
        obj += [-pen * sum(presence[a]) for a in elig]
    else:
        obj = [round(config.W_TRAVEL * S / (c.D * c.window)) * travel_expr,
               round(config.W_COST * S / ref_cost) * cost_obj_expr]
        if nice:
            unit = round(config.W_MISSED * S / len(nice))
            const += unit * len(nice)
            obj += [-unit * sum(presence[a]) for a in nice if presence[a]]
        if c.D > 1:
            hi, lo = m.NewIntVar(0, c.cap, "maxc"), m.NewIntVar(0, c.cap, "minc")
            m.AddMaxEquality(hi, day_count)
            m.AddMinEquality(lo, day_count)
            obj.append(round(config.W_PACE * S / c.cap) * (hi - lo))
        if p.budget is not None and not p.strict_budget:
            over = m.NewIntVar(0, 10_000_000, "over")
            m.Add(over >= cost_expr - p.budget)
            obj.append(round(config.W_OVER_BUDGET * S / ref_cost) * over)
    m.Minimize(sum(obj) + const)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = config.SOLVER_SEED
    solver.parameters.num_workers = 1
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.max_deterministic_time = config.SOLVER_MAX_DETERMINISTIC_TIME
    token = current_token()
    if token is not None:
        token.check()  # the caller already left: do not start
        token.attach(solver)
    try:
        if token is not None:
            token.check()
        status = solver.Solve(m)
    finally:
        if token is not None:
            token.detach()
    if token is not None:
        token.check()  # stopped early on purpose: whatever the solver holds is not a result
    name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return name, None, None
    plan = []
    for d in range(c.D):
        visits = [(a, solver.Value(st)) for a, pr, st in node_info[d] if solver.Value(pr)]
        visits.sort(key=lambda v: v[1])
        plan.append(visits)
    return name, plan, solver.ObjectiveValue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def solve(prefs: Preferences, hotel_id: str, ds: Dataset, *, with_alternatives: bool = True,
          max_seconds: float | None = None, objective: ObjectiveSpec | None = None,
          alternatives_budget: float | None = None) -> SolveResult:
    t0 = time.perf_counter()
    spec = objective or ObjectiveSpec()  # keep: `objective` is reassigned below
    c = _make_ctx(prefs, hotel_id, ds)
    conflicts = _precheck(c)
    status_name, plan, objective = "NOT_RUN", None, None
    if not conflicts:
        status_name, plan, objective = _solve_core(c, max_seconds or config.SOLVER_MAX_SECONDS, spec)
        if plan is None:
            if status_name == "INFEASIBLE":
                conflicts = [Conflict(code="no_feasible_schedule", message="Each requirement is individually possible, but no schedule satisfies all of them together (opening hours, travel time, the daily activity and travel limits, budget and locks).", attraction_ids=c.required)]
            else:
                conflicts = [Conflict(code="solver_timeout", message=f"No schedule found within the time limit (solver status {status_name}); this is not a proof of infeasibility.", attraction_ids=[])]
    meta = SolverMeta(solver=SOLVER_NAME, solver_status=status_name, runtime_seconds=0.0,
                      seed=config.SOLVER_SEED, objective=objective)
    if plan is None:
        res = SolveResult(status="infeasible", hotel_id=hotel_id, conflicts=conflicts, solver_meta=meta)
        if with_alternatives:
            res.alternatives = _alternatives(prefs, hotel_id, ds, alternatives_budget)
    else:
        days, totals = assemble(ds, prefs, hotel_id, plan)
        notes = []
        if totals.unknown_cost_items:
            notes.append("Prices unknown for " + ", ".join(totals.unknown_cost_items) + ": excluded from total (unknown).")
        if prefs.budget is not None and not prefs.strict_budget and totals.total_jpy > prefs.budget:
            notes.append(f"Budget (soft) exceeded by {money(totals.total_jpy - prefs.budget, ds)}.")
        notes.append("max_walking_minutes_per_day is not enforced in this version.")
        scheduled = {s.attraction_id for dp in days for s in dp.stops}
        eligible = [a for a in c.candidates if a not in c.required and any(_ranges(c, a, d) for d in range(c.D))]
        res = SolveResult(status="feasible", hotel_id=hotel_id, days=days, totals=totals, notes=notes,
                          missed_preferences=[a for a in eligible if a not in scheduled], solver_meta=meta)
    meta.runtime_seconds = round(time.perf_counter() - t0, 4)
    return res


MAX_COMBINATIONS = 10        # stage C bound: at most this many two-change probes, in a fixed order


def _levers(prefs: Preferences, hotel_id: str, ds: Dataset) -> list[tuple[str, str, dict, dict]]:
    """Single changes worth trying, in a fixed order: (kind, message, preference update, structured change). A change that would not alter the request is not offered."""
    out: list[tuple[str, str, dict, dict]] = []
    if prefs.days < 7:
        out.append(("add_day", f"Add a day (trip becomes {prefs.days + 1} days)", {"days": prefs.days + 1}, {"field": "days", "from": prefs.days, "to": prefs.days + 1}))
    if prefs.strict_budget:
        out.append(("relax_budget", "Treat the budget as a soft target instead of a strict limit", {"strict_budget": False}, {"field": "strict_budget", "from": True, "to": False}))
    if not prefs.allow_unknown_hours:
        out.append(("allow_unknown_hours", "Plan provisionally: allow attractions with unknown opening hours (they will be labelled \"Opening hours unverified\")", {"allow_unknown_hours": True}, {"field": "allow_unknown_hours", "from": False, "to": True}))
    end = min(to_minutes(prefs.day_end) + 120, 23 * 60 + 59)
    if end > to_minutes(prefs.day_end):
        out.append(("extend_day", f"Extend the day end to {fmt(end)}", {"day_end": fmt(end)}, {"field": "day_end", "from": prefs.day_end, "to": fmt(end)}))
    if prefs.max_activities_per_day is not None and prefs.max_activities_per_day < 8:
        n = prefs.max_activities_per_day + 1
        out.append(("raise_activity_limit", f"Allow {n} activities a day instead of {prefs.max_activities_per_day}", {"max_activities_per_day": n}, {"field": "max_activities_per_day", "from": prefs.max_activities_per_day, "to": n}))
    elif prefs.max_activities_per_day is None and prefs.pace != "packed":
        out.append(("pace_packed", "Use the packed pace (more activities a day)", {"pace": "packed"}, {"field": "pace", "from": prefs.pace, "to": "packed"}))
    if prefs.max_daily_travel_minutes is not None:
        m = min(prefs.max_daily_travel_minutes + 60, 720)
        if m > prefs.max_daily_travel_minutes:
            out.append(("raise_travel_limit", f"Allow {m} min of estimated travel a day instead of {prefs.max_daily_travel_minutes}", {"max_daily_travel_minutes": m}, {"field": "max_daily_travel_minutes", "from": prefs.max_daily_travel_minutes, "to": m}))
        out.append(("remove_travel_limit", "Remove the daily estimated-travel limit", {"max_daily_travel_minutes": None}, {"field": "max_daily_travel_minutes", "from": prefs.max_daily_travel_minutes, "to": None}))
    for a in dict.fromkeys(prefs.must_visit):
        if a in ds.attractions and len(prefs.must_visit) > 1 or a in ds.attractions and not prefs.locked:
            out.append(("demote_must_visit", f"Treat {ds.attractions[a].name} as nice-to-have instead of must-visit", {"must_visit": [x for x in prefs.must_visit if x != a]},
                        {"field": "must_visit", "removed": a}))
    return out


def _rank_key(alt: Alternative) -> tuple:
    d = alt.details
    changes = d.get("changes", [])
    return (len(changes), any(c.get("removed") for c in changes), -d.get("attractions_scheduled", 0), d.get("travel_minutes", 0), d.get("total_jpy", 0))


def _alternatives(prefs: Preferences, hotel_id: str, ds: Dataset, budget: float | None = None) -> list[Alternative]:
    """Computed alternatives: each one is a relaxed problem that was actually solved, found feasible AND passed the independent validator.

    Stage B: every single change from `_levers`, plus the same request at each other hotel. Stage C: only if no single change works, at most MAX_COMBINATIONS two-change
    combinations in a fixed order. Ranked by number of changes, then whether a must-visit is given up, then coverage and travel. The ranking is a convenience, NOT a claim of minimality:
    only the probes that ran were tried, and the search stops at the time budget."""
    from app.validator.feasibility_report import build_report
    levers = _levers(prefs, hotel_id, ds)
    t_end = time.monotonic() + budget if budget is not None else None

    def probe(kind: str, msg: str, p2: Preferences, h2: str, changes: list[dict]) -> Alternative | None:
        try:
            r = solve(p2, h2, ds, with_alternatives=False, max_seconds=config.SOLVER_PROBE_SECONDS)
        except Cancelled:
            raise
        except Exception:
            return None
        if r.status != "feasible" or build_report(r, ds, p2, h2).overall == "fail":
            return None
        details = {"attractions_scheduled": r.totals.attractions_scheduled, "total_jpy": r.totals.total_jpy, "travel_minutes": r.totals.travel_minutes,
                   "changes": changes, "hotel_id": h2, "verified_by_validator": True, "combination": len(changes) > 1}
        if kind == "demote_must_visit" or any(c.get("removed") for c in changes):
            dropped = [c["removed"] for c in changes if c.get("removed")]
            scheduled = {s.attraction_id for dp in r.days for s in dp.stops}
            details["still_scheduled"] = bool(dropped) and dropped[0] in scheduled
        return Alternative(kind=kind, message=msg + ": a feasible plan exists.", details=details)

    def out_of_time() -> bool:
        return t_end is not None and time.monotonic() >= t_end

    out: list[Alternative] = []
    for kind, msg, upd, ch in levers:                                   # stage B
        if out_of_time():
            break
        a = probe(kind, msg, prefs.model_copy(update=upd), hotel_id, [ch])
        if a:
            out.append(a)
    for h2 in sorted(ds.hotels):                                        # stage B, hotel lever (same request, another hotel)
        if h2 == hotel_id or out_of_time():
            continue
        a = probe("switch_hotel", f"Stay at {ds.hotels[h2].name} instead", prefs, h2, [{"field": "hotel", "from": hotel_id, "to": h2}])
        if a:
            out.append(a)
    if not out:                                                         # stage C: bounded, deterministic pairs of the cheaper levers
        pool = [l for l in levers if l[0] != "demote_must_visit"]
        tried = 0
        for x in range(len(pool)):
            for y in range(x + 1, len(pool)):
                if tried >= MAX_COMBINATIONS or out_of_time():
                    break
                (k1, m1, u1, c1), (k2, m2, u2, c2) = pool[x], pool[y]
                if c1["field"] == c2["field"]:
                    continue
                tried += 1
                a = probe(f"{k1}+{k2}", f"{m1}, and {m2[0].lower() + m2[1:]}", prefs.model_copy(update={**u1, **u2}), hotel_id, [c1, c2])
                if a:
                    out.append(a)
    out.sort(key=_rank_key)
    for i, a in enumerate(out, 1):
        a.details["rank"] = i
    return out[:20]


def precheck(prefs: Preferences, hotel_id: str, ds: Dataset) -> list[Conflict]:
    """Conflicts computed from data alone (no solving). Used by the replanner to reject bad operations early."""
    return _precheck(_make_ctx(prefs, hotel_id, ds))


def missed_preferences_for(prefs: Preferences, hotel_id: str, ds: Dataset, scheduled: set[str]) -> list[str]:
    """Visitable nice-to-have attractions that are not scheduled (server-side recomputation for untrusted schedules)."""
    c = _make_ctx(prefs, hotel_id, ds)
    eligible = [a for a in c.candidates if a not in c.required and any(_ranges(c, a, d) for d in range(c.D))]
    return [a for a in eligible if a not in scheduled]
