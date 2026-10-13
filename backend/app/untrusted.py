"""Client-supplied schedules are UNTRUSTED.

(a) structure is validated by Pydantic at the route; (b) here we rebuild every stop from the raw ids and start times only,
recomputing travel, fares, admissions, flags, totals and missed sights from the dataset (client-supplied cost or total
fields are ignored); (c) the independent validator runs on the rebuilt schedule. A schedule whose structure or times are
altered (negative or changed durations, unknown ids, bad days) or that fails the validator is rejected with HTTP 422
and the findings. Explanations are always built from server-computed results, never from client-supplied figures."""
from app.data.loader import Dataset
from app.hardening.errors import ApiError
from app.optimiser.schedule import assemble
from app.optimiser.solver import missed_preferences_for
from app.schemas import Preferences, SolverMeta, SolveResult, to_minutes
from app.validator.feasibility_report import build_report


def _t(hhmm: str):
    try:
        h, m = hhmm.split(":")
        if len(m) != 2 or not (0 <= int(h) < 24 and 0 <= int(m) < 60):
            return None
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def rebuild_client_schedule(prefs: Preferences, current: SolveResult, ds: Dataset) -> SolveResult:
    findings: list[dict] = []
    if current.status != "feasible":
        raise ApiError(422, "invalid_schedule", "The supplied schedule must be a feasible plan.")
    if current.hotel_id not in ds.hotels:
        raise ApiError(422, "invalid_schedule", "The supplied schedule names an unknown hotel.", [{"check": "hotel", "message": "unknown hotel id"}])
    plan: list[list[tuple[str, int]]] = [[] for _ in range(prefs.days)]
    seen_days: set[int] = set()
    for dp in current.days:
        if dp.day > prefs.days or dp.day in seen_days:
            findings.append({"check": "days", "message": f"day {dp.day} is outside the trip length ({prefs.days}) or repeated"})
            continue
        seen_days.add(dp.day)
        for s in dp.stops:
            att = ds.attractions.get(s.attraction_id)
            start, end = _t(s.start), _t(s.end)
            if att is None:
                findings.append({"check": "known_items", "message": "unknown attraction id", "stop_ids": [s.attraction_id[:64]]})
            elif start is None or end is None:
                findings.append({"check": "times", "message": f"{att.name}: start/end must be HH:MM", "stop_ids": [s.attraction_id]})
            elif end - start != att.duration_minutes:
                findings.append({"check": "durations", "message": f"{att.name}: end time does not match its duration of {att.duration_minutes} min (negative or altered)",
                                 "stop_ids": [s.attraction_id]})
            else:
                plan[dp.day - 1].append((s.attraction_id, start))
    if findings:
        raise ApiError(422, "invalid_schedule", "The supplied schedule is structurally invalid.", findings)
    for lst in plan:
        lst.sort(key=lambda v: v[1])
    days, totals = assemble(ds, prefs, current.hotel_id, plan)
    scheduled = {a for lst in plan for a, _ in lst}
    rebuilt = SolveResult(
        status="feasible", hotel_id=current.hotel_id, days=days, totals=totals,
        missed_preferences=missed_preferences_for(prefs, current.hotel_id, ds, scheduled),
        notes=["Schedule rebuilt server-side from stop ids and start times; client-supplied costs, totals and flags were ignored."],
        solver_meta=SolverMeta(solver="client-supplied (rebuilt)", solver_status="N/A", runtime_seconds=0.0, seed=0))
    rep = build_report(rebuilt, ds, prefs, current.hotel_id)
    if rep.overall == "fail":
        raise ApiError(422, "invalid_schedule", "The supplied schedule fails the independent validator.",
                       [{"check": c.id, "message": c.message, "stop_ids": c.stop_ids} for c in rep.checks if c.status == "fail"])
    return rebuilt
