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


def build_report(schedule: SolveResult, ds: Dataset, prefs: Preferences, hotel_id: str,
                 user_removed_must_visits: list[str] | None = None) -> FeasibilityReport:
    if schedule.status != "feasible":
        # No schedule to validate: the report is a fail that carries the specific conflicts.
        checks = [CheckOut(id="plan_exists", name="A valid plan exists", status="fail",
                           message="No feasible plan: " + " | ".join(c.message for c in schedule.conflicts),
                           stop_ids=sorted({a for c in schedule.conflicts for a in c.attraction_ids}))]
        return FeasibilityReport(overall="fail", checks=checks, data_quality_warnings=[],
                                 summary="FAIL: no feasible plan. " + " ".join(c.message for c in schedule.conflicts))
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
    return FeasibilityReport(overall=overall, checks=out, data_quality_warnings=[f"{c.name}: {c.message}" for c in warns],
                             summary=summary)
