"""Trip Feasibility Report: turns validator checks into one verdict a person can read."""
from pydantic import BaseModel

from app.data.loader import Dataset
from app.schemas import Preferences, SolveResult
from app.validator.checks import Check, run_checks


class CheckOut(BaseModel):
    id: str
    name: str
    status: str
    message: str
    stop_ids: list[str] = []


class FeasibilityReport(BaseModel):
    overall: str  # pass | pass_with_warnings | fail
    checks: list[CheckOut]
    data_quality_warnings: list[str]
    summary: str
    # Additive. "verified": every stop is open at its scheduled time according to the data. "conditional": the plan holds only if the listed stops are open
    # (their opening hours are unknown in the data, so they are labelled "Opening hours unverified"). "none": there is no plan to describe.
    verification: str = "verified"
    conditional_stop_ids: list[str] = []
    blocked_by: str | None = None       # "missing_information" when every conflict is about something the data does not say


def build_report(schedule: SolveResult, ds: Dataset, prefs: Preferences, hotel_id: str,
                 user_removed_must_visits: list[str] | None = None) -> FeasibilityReport:
    if schedule.status != "feasible":
        # No schedule to validate: the report is a fail that carries the specific conflicts.
        # ONE short statement; the specific conflicts are returned once, in `conflicts`, and are not repeated here.
        missing = bool(schedule.conflicts) and all(c.category == "missing_information" for c in schedule.conflicts)
        what = ("Blocked by missing information: the data does not say whether a required sight is open, so the planner cannot confirm a plan."
                if missing else "No feasible plan under the known constraints.")
        checks = [CheckOut(id="plan_exists", name="A valid plan exists", status="fail", message=what,
                           stop_ids=sorted({a for c in schedule.conflicts for a in c.attraction_ids}))]
        return FeasibilityReport(overall="fail", checks=checks, data_quality_warnings=[], summary="FAIL: " + what[0].lower() + what[1:],
                                 verification="none", blocked_by="missing_information" if missing else None)
    checks: list[Check] = run_checks(schedule, ds, prefs, hotel_id)
    out = [CheckOut(**c.__dict__) for c in checks]
    if user_removed_must_visits:
        names = [ds.attractions[a].name if a in ds.attractions else a for a in user_removed_must_visits]
        out.append(CheckOut(id="must_visit_removed_by_user", name="Must-visit removed by user", status="warning",
                            message="Must-visit removed by user (explicitly confirmed): " + ", ".join(names),
                            stop_ids=list(user_removed_must_visits)))
    fails = [c for c in out if c.status == "fail"]
    warns = [c for c in out if c.status == "warning"]
    overall = "fail" if fails else ("pass_with_warnings" if warns else "pass")
    if fails:
        summary = f"FAIL: {len(fails)} check(s) failed: " + "; ".join(f"{c.name} ({c.message})" for c in fails)
    elif warns:
        summary = f"All {len(out) - len(warns)} hard checks passed, with {len(warns)} data-quality warning(s): " + "; ".join(c.name for c in warns) + "."
    else:
        summary = f"All {len(out)} checks passed."
    cond = next((c.stop_ids for c in out if c.id == "unknown_hours_used" and c.status == "warning"), [])
    if cond and not fails:
        names = ", ".join(ds.attractions[a].name for a in cond if a in ds.attractions)
        summary += f" Conditional: feasible only if {names} {'is' if len(cond) == 1 else 'are'} open at the scheduled time (opening hours unverified). Check before you travel."
    return FeasibilityReport(overall=overall, checks=out, data_quality_warnings=[f"{c.name}: {c.message}" for c in warns], summary=summary,
                             verification="none" if fails else ("conditional" if cond else "verified"), conditional_stop_ids=list(cond) if not fails else [])
