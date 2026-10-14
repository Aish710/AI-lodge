"""Replanning: apply user operations to an existing plan and return the new plan plus a precise diff.

Stateless: the caller sends preferences + current schedule + operations; nothing is stored server-side.
The LLM never edits the schedule; operations are plain constraint edits (lock, unlock, remove, move,
change_budget, switch_hotel) applied together in ONE solve.

Objective = the Phase 3 true cost for the (fixed unless switched) hotel + W_DISRUPTION JPY per
UNNECESSARILY MOVED activity. "Moved" = an unchanged activity whose day changes or whose start shifts by
more than MOVE_THRESHOLD_MINUTES. Activities the user locked/moved are intentional and never counted.
"""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app import config
from app.money import money
from app.data.loader import Dataset, unknown_price_placeholder
from app.optimiser.hotel_compare import CostBreakdown, _breakdown
from app.optimiser.schedule import fmt
from app.optimiser.solver import ObjectiveSpec, precheck, solve
from app.schemas import (
    HHMM, Conflict, LockedActivity, Preferences, SolveResult, nights_for, to_minutes,
)
from app.validator.feasibility_report import FeasibilityReport, build_report

LOCK_CONFLICT_CODES = {"locked_not_possible", "locked_no_travel_time", "locked_overlap", "lock_outside_trip", "locked_and_skip"}


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------
class _Op(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LockOp(_Op):
    op: Literal["lock"]
    attraction_id: str
    day: int = Field(ge=1, le=7)
    start_time: HHMM


class MoveOp(_Op):
    op: Literal["move"]  # implemented as a lock at the new slot
    attraction_id: str
    day: int = Field(ge=1, le=7)
    start_time: HHMM


class UnlockOp(_Op):
    op: Literal["unlock"]
    attraction_id: str


class RemoveOp(_Op):
    op: Literal["remove"]
    attraction_id: str


class ChangeBudgetOp(_Op):
    op: Literal["change_budget"]
    budget: int | None = Field(default=None, ge=0)
    strict: bool = False


class SwitchHotelOp(_Op):
    op: Literal["switch_hotel"]
    hotel_id: str


Operation = Annotated[Union[LockOp, MoveOp, UnlockOp, RemoveOp, ChangeBudgetOp, SwitchHotelOp], Field(discriminator="op")]


class ReplanError(Exception):
    """A request that is rejected before solving (HTTP 422 at the API)."""

    def __init__(self, code: str, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details or []


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------
class Delta(BaseModel):
    before: int
    after: int
    delta: int


def _delta(b: int, a: int) -> Delta:
    return Delta(before=b, after=a, delta=a - b)


class ActivityRef(BaseModel):
    attraction_id: str
    name: str
    day: int
    start: str


class MovedActivity(BaseModel):
    attraction_id: str
    name: str
    from_day: int
    from_start: str
    to_day: int
    to_start: str
    reason: str  # "user" (locked/moved by the user) | "reoptimised" (counts as disruption)


class RemovedActivity(BaseModel):
    attraction_id: str
    name: str
    day: int
    start: str
    reason: str  # "removed_by_user" | "dropped_by_optimiser"
    was_must_visit: bool = False


class Diff(BaseModel):
    admissions_jpy: Delta
    transport_jpy: Delta
    rooms_jpy: Delta
    time_cost_jpy: Delta
    missed_penalty_jpy: Delta
    true_cost_jpy: Delta
    travel_minutes: Delta
    kept: list[ActivityRef]
    moved: list[MovedActivity]
    removed: list[RemovedActivity]
    added: list[ActivityRef]
    missed_before: list[str]
    missed_after: list[str]
    newly_missed: list[str]
    no_longer_missed: list[str]
    disruption_count: int
    disruption_jpy_per_move: int
    move_threshold_minutes: int
    disruption_cost_jpy: int  # informational: count x per-move weight; NOT part of true_cost
    optimisation_placeholder_jpy: int  # value assumed per unknown-price sight in the optimiser only; not in any total
    warnings: list[str]


class ReplanResult(BaseModel):
    status: str  # applied | infeasible | rejected_by_validator
    strategy: str
    operations_applied: list[str]
    previous_hotel_id: str
    hotel_id: str
    nights_used: int
    nights_source: str
    schedule: SolveResult  # the plan in force: new if applied, otherwise the ORIGINAL, unchanged
    schedule_changed: bool
    new_preferences: Preferences | None  # so a stateless client can keep it for the next call
    conflicts: list[Conflict] = []
    diff: Diff | None = None
    feasibility_report: FeasibilityReport | None = None
    solver_status: str
    proven_optimal: bool | None
    runtime_seconds: float
    approximate: bool
    old_breakdown: CostBreakdown | None = None
    new_breakdown: CostBreakdown | None = None
    summary: str


# ---------------------------------------------------------------------------
# Applying operations (all validation happens here, before any solving)
# ---------------------------------------------------------------------------
def _name(ds: Dataset, aid: str) -> str:
    return ds.attractions[aid].name if aid in ds.attractions else aid


def _apply(prefs: Preferences, hotel_id: str, ops: list, ds: Dataset, confirm: bool):
    if len(ops) > config.MAX_REPLAN_OPERATIONS:
        raise ReplanError("too_many_operations", f"At most {config.MAX_REPLAN_OPERATIONS} operations per request.")
    for o in ops:
        aid = getattr(o, "attraction_id", None)
        if aid is not None and aid not in ds.attractions:
            raise ReplanError("unknown_attraction", f"Unknown attraction id '{aid}'. Hallucinated or misspelled ids cannot be scheduled.")
    by_item: dict[str, list[str]] = {}
    for o in ops:
        if getattr(o, "attraction_id", None):
            by_item.setdefault(o.attraction_id, []).append(o.op)
    for aid, kinds in by_item.items():
        slots = [k for k in kinds if k in ("lock", "move")]
        if len(slots) > 1:
            raise ReplanError("conflicting_operations", f"{_name(ds, aid)} has more than one lock/move operation.")
        if slots and "remove" in kinds:
            raise ReplanError("conflicting_operations", f"Cannot lock/move and remove {_name(ds, aid)} in the same request.")
        if slots and "unlock" in kinds:
            raise ReplanError("conflicting_operations", f"Cannot lock/move and unlock {_name(ds, aid)} in the same request.")
    if sum(o.op == "change_budget" for o in ops) > 1 or sum(o.op == "switch_hotel" for o in ops) > 1:
        raise ReplanError("conflicting_operations", "Only one change_budget and one switch_hotel operation per request.")

    locked = {l.attraction_id: l for l in prefs.locked}
    must = list(dict.fromkeys(prefs.must_visit))
    skip = list(prefs.skip)
    budget, strict, new_hotel = prefs.budget, prefs.strict_budget, hotel_id
    desc: list[str] = []
    user_edited: set[str] = set()
    removed_by_user: list[str] = []
    removed_must: list[str] = []
    unlocked_now: set[str] = set()

    for o in ops:  # unlock first so "unlock + remove" is allowed
        if o.op == "unlock":
            if o.attraction_id not in locked:
                raise ReplanError("invalid_operation", f"{_name(ds, o.attraction_id)} is not locked, so it cannot be unlocked.")
            del locked[o.attraction_id]
            unlocked_now.add(o.attraction_id)
            desc.append(f"unlock {_name(ds, o.attraction_id)}")
    for o in ops:
        if o.op in ("lock", "move"):
            locked[o.attraction_id] = LockedActivity(attraction_id=o.attraction_id, day=o.day, start_time=o.start_time)
            user_edited.add(o.attraction_id)
            desc.append(f"{'lock' if o.op == 'lock' else 'move'} {_name(ds, o.attraction_id)} to day {o.day} {o.start_time}")
        elif o.op == "remove":
            aid = o.attraction_id
            if aid in locked:
                raise ReplanError("conflicting_operations", f"{_name(ds, aid)} is locked; unlock it before removing it.")
            if aid in must:
                if not confirm:
                    raise ReplanError(
                        "must_visit_removal_not_confirmed",
                        f"'{_name(ds, aid)}' is a must-visit. Removing it means the new plan will no longer include something you marked as required. "
                        "Resend with confirm_remove_must_visit=true to proceed.",
                        [aid])
                must.remove(aid)
                removed_must.append(aid)
            if aid not in skip:
                skip.append(aid)
            removed_by_user.append(aid)
            desc.append(f"remove {_name(ds, aid)}" + (" (must-visit, confirmed by user)" if aid in removed_must else ""))
        elif o.op == "change_budget":
            budget, strict = o.budget, o.strict
            desc.append(f"change budget to {money(budget, ds) if budget is not None else 'none'} ({'strict' if strict else 'soft'})")
        elif o.op == "switch_hotel":
            if o.hotel_id not in ds.hotels:
                raise ReplanError("unknown_hotel", f"Unknown hotel id '{o.hotel_id}'.")
            if o.hotel_id == hotel_id:
                raise ReplanError("invalid_operation", "Already staying at that hotel.")
            new_hotel = o.hotel_id
            desc.append(f"switch hotel to {ds.hotels[new_hotel].name}")
    if strict and budget is None:
        raise ReplanError("invalid_operation", "A strict budget needs a budget amount.")
    new_prefs = prefs.model_copy(update={"locked": list(locked.values()), "must_visit": must, "skip": skip,
                                         "budget": budget, "strict_budget": strict})
    conf = [c for c in precheck(new_prefs, new_hotel, ds) if c.code in LOCK_CONFLICT_CODES]
    if conf:
        raise ReplanError("conflicting_operations", "These operations conflict with the plan's constraints: " +
                          " | ".join(c.message for c in conf), [c.message for c in conf])
    return new_prefs, new_hotel, desc, user_edited, removed_by_user, removed_must


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------
def _positions(res: SolveResult) -> dict[str, tuple[int, int, str]]:
    return {s.attraction_id: (d.day, to_minutes(s.start), s.start) for d in res.days for s in d.stops}


def _build_diff(ds, old_prefs, new_prefs, old_res, new_res, old_bd, new_bd, user_edited, removed_by_user, removed_must, solver_ok):
    old, new = _positions(old_res), _positions(new_res)
    thr = config.MOVE_THRESHOLD_MINUTES
    kept, moved, removed, added = [], [], [], []
    for aid, (d0, s0, t0) in old.items():
        if aid in new:
            d1, s1, t1 = new[aid]
            if d1 != d0 or abs(s1 - s0) > thr:
                moved.append(MovedActivity(attraction_id=aid, name=_name(ds, aid), from_day=d0, from_start=t0, to_day=d1, to_start=t1,
                                           reason="user" if aid in user_edited else "reoptimised"))
            else:
                kept.append(ActivityRef(attraction_id=aid, name=_name(ds, aid), day=d1, start=t1))
        else:
            by_user = aid in removed_by_user
            removed.append(RemovedActivity(attraction_id=aid, name=_name(ds, aid), day=d0, start=t0,
                                           reason="removed_by_user" if by_user else "dropped_by_optimiser",
                                           was_must_visit=aid in removed_must))
    for aid, (d1, s1, t1) in new.items():
        if aid not in old:
            added.append(ActivityRef(attraction_id=aid, name=_name(ds, aid), day=d1, start=t1))
    disruption = sum(m.reason == "reoptimised" for m in moved)
    mb, ma = set(old_res.missed_preferences), set(new_res.missed_preferences)

    warnings: list[str] = []
    opt_old = set(old) - set(old_prefs.must_visit)
    opt_new = set(new) - set(new_prefs.must_visit)
    if opt_old != opt_new:
        bits = []
        if opt_old - opt_new:
            bits.append("no longer scheduled: " + ", ".join(sorted(_name(ds, a) for a in opt_old - opt_new)))
        if opt_new - opt_old:
            bits.append("newly scheduled: " + ", ".join(sorted(_name(ds, a) for a in opt_new - opt_old)))
        warnings.append("Not like-for-like: the set of optional sights changed (" + "; ".join(bits) + "), so the cost delta is not a pure saving.")
    touched = {r.attraction_id for r in removed} | {a.attraction_id for a in added} | {m.attraction_id for m in moved}
    unknown = sorted(a for a in touched if ds.attractions[a].admission_cost is None)
    if unknown:
        warnings.append("Change involves unknown-price attraction(s): " + ", ".join(_name(ds, a) for a in unknown) +
                        f"; their price is excluded from totals (the optimiser assumed a placeholder of {money(unknown_price_placeholder(ds), ds)}), so the cost delta may be misstated.")
    if not solver_ok:
        warnings.append("Approximate: the solver did not prove the new plan optimal (time-limited).")
    for aid in removed_must:
        warnings.append(f"Must-visit removed by user: {_name(ds, aid)}.")
    return Diff(
        admissions_jpy=_delta(old_bd.admissions_jpy, new_bd.admissions_jpy),
        transport_jpy=_delta(old_bd.transport_jpy, new_bd.transport_jpy),
        rooms_jpy=_delta(old_bd.rooms_jpy, new_bd.rooms_jpy),
        time_cost_jpy=_delta(old_bd.time_cost_jpy, new_bd.time_cost_jpy),
        missed_penalty_jpy=_delta(old_bd.missed_preferences.penalty_jpy, new_bd.missed_preferences.penalty_jpy),
        true_cost_jpy=_delta(old_bd.true_cost_jpy, new_bd.true_cost_jpy),
        travel_minutes=_delta(old_bd.travel_minutes, new_bd.travel_minutes),
        kept=kept, moved=moved, removed=removed, added=added,
        missed_before=[_name(ds, a) for a in old_res.missed_preferences], missed_after=[_name(ds, a) for a in new_res.missed_preferences],
        newly_missed=sorted(_name(ds, a) for a in ma - mb), no_longer_missed=sorted(_name(ds, a) for a in mb - ma),
        disruption_count=disruption, disruption_jpy_per_move=config.W_DISRUPTION, move_threshold_minutes=thr,
        disruption_cost_jpy=disruption * config.W_DISRUPTION, optimisation_placeholder_jpy=unknown_price_placeholder(ds),
        warnings=warnings)


def _summary(status, desc, diff, new_res, old_hotel, new_hotel, conflicts, ds) -> str:
    ops = "; ".join(desc) if desc else "no changes requested"
    if status == "infeasible":
        return f"Replan NOT applied ({ops}). Your original plan is unchanged. Conflicts: " + " | ".join(c.message for c in conflicts)
    if status == "rejected_by_validator":
        return f"Replan NOT applied ({ops}): the independent validator rejected the new plan. Your original plan is unchanged."
    d = diff
    parts = [f"Replan applied ({ops}).",
             f"True cost {d.true_cost_jpy.before:,} -> {money(d.true_cost_jpy.after, ds)} ({d.true_cost_jpy.delta:+,}); "
             f"travel {d.travel_minutes.before} -> {d.travel_minutes.after} min ({d.travel_minutes.delta:+})."]
    if old_hotel != new_hotel:
        parts.append(f"Rooms {d.rooms_jpy.before:,} -> {money(d.rooms_jpy.after, ds)} ({d.rooms_jpy.delta:+,}).")
    parts.append(f"{len(d.kept)} activities kept, {len(d.moved)} moved, {len(d.removed)} removed, {len(d.added)} added; "
                 f"{d.disruption_count} unnecessarily moved ({money(d.disruption_cost_jpy, ds)}-equivalent at {d.disruption_jpy_per_move:,} per move).")
    if d.moved:
        parts.append("Moved: " + "; ".join(f"{m.name} day {m.from_day} {m.from_start} -> day {m.to_day} {m.to_start} ({m.reason})" for m in d.moved) + ".")
    if d.removed:
        parts.append("Removed: " + "; ".join(f"{r.name} ({r.reason.replace('_', ' ')})" for r in d.removed) + ".")
    if d.added:
        parts.append("Added: " + ", ".join(a.name for a in d.added) + ".")
    if d.warnings:
        parts.append("Warnings: " + " ".join(d.warnings))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def replan(prefs: Preferences, current: SolveResult, ops: list, ds: Dataset, *, confirm_remove_must_visit: bool = False,
           strategy: str = "disruption_aware", max_seconds: float | None = None) -> ReplanResult:
    """strategy: "disruption_aware" (default) or "naive" (full re-solve, no disruption term; for evaluation only)."""
    if current.status != "feasible" or current.hotel_id not in ds.hotels:
        raise ReplanError("invalid_current_schedule", "The current schedule must be a feasible plan for a known hotel.")
    old_hotel = current.hotel_id
    new_prefs, new_hotel, desc, user_edited, removed_by_user, removed_must = _apply(prefs, old_hotel, ops, ds, confirm_remove_must_visit)
    nights, nights_src = nights_for(new_prefs)

    reference = ()
    spec = ObjectiveSpec("true_cost", new_prefs.value_of_time_per_hour, config.MISSED_PREFERENCE_PENALTY_JPY)
    if strategy == "disruption_aware":
        reference = tuple((aid, d - 1, s) for aid, (d, s, _) in _positions(current).items() if aid not in removed_by_user)
        spec = ObjectiveSpec("true_cost", new_prefs.value_of_time_per_hour, config.MISSED_PREFERENCE_PENALTY_JPY,
                             disruption_jpy=config.W_DISRUPTION, move_threshold_min=config.MOVE_THRESHOLD_MINUTES, reference=reference)
    res = solve(new_prefs, new_hotel, ds, with_alternatives=False,
                max_seconds=max_seconds or config.REPLAN_TIME_LIMIT_SECONDS, objective=spec)
    meta = res.solver_meta
    base = dict(strategy=strategy, operations_applied=desc, previous_hotel_id=old_hotel, hotel_id=new_hotel,
                nights_used=nights, nights_source=nights_src, solver_status=meta.solver_status,
                proven_optimal=None if meta.solver_status == "NOT_RUN" else meta.solver_status == "OPTIMAL",
                runtime_seconds=meta.runtime_seconds)

    if res.status != "feasible":
        rep = build_report(res, ds, new_prefs, new_hotel)
        return ReplanResult(status="infeasible", schedule=current, schedule_changed=False, new_preferences=None,
                            conflicts=res.conflicts, feasibility_report=rep, approximate=False,
                            summary=_summary("infeasible", desc, None, None, old_hotel, new_hotel, res.conflicts, ds),
                            **{**base, "hotel_id": old_hotel})
    rep = build_report(res, ds, new_prefs, new_hotel, user_removed_must_visits=removed_must)
    if rep.overall == "fail":  # never hide a failing report, never apply a plan the validator rejects
        return ReplanResult(status="rejected_by_validator", schedule=current, schedule_changed=False, new_preferences=None,
                            feasibility_report=rep, approximate=False,
                            summary=_summary("rejected_by_validator", desc, None, None, old_hotel, new_hotel, [], ds),
                            **{**base, "hotel_id": old_hotel})
    old_bd = _breakdown(ds, prefs, old_hotel, current, nights, prefs.value_of_time_per_hour)
    new_bd = _breakdown(ds, new_prefs, new_hotel, res, nights, new_prefs.value_of_time_per_hour)
    optimal = meta.solver_status == "OPTIMAL"
    diff = _build_diff(ds, prefs, new_prefs, current, res, old_bd, new_bd, user_edited, removed_by_user, removed_must, optimal)
    return ReplanResult(status="applied", schedule=res, schedule_changed=True, new_preferences=new_prefs, diff=diff,
                        feasibility_report=rep, approximate=not optimal, old_breakdown=old_bd, new_breakdown=new_bd,
                        summary=_summary("applied", desc, diff, res, old_hotel, new_hotel, [], ds), **base)
