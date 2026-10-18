"""Structured evidence for copilot answers, and a fail-closed check of it. No model is involved.

Every number a copilot answer shows is evidence: a labelled item with a kind and a reference. Before an answer is returned, `verify_evidence` re-derives the checkable ones from the dataset and the
schedule's own order (sharing no code with the cost summary or the solver) and compares. One mismatch, an unknown kind or reference, or a number in the message that no evidence explains rejects the whole
answer: the person sees that the evidence could not be verified, never a plausible but unchecked figure.
"""
import re

from app.data.loader import Dataset
from app.schemas import Preferences, SolveResult
from app.validator.feasibility_report import FeasibilityReport

KINDS = {"dataset", "calculated", "preference", "unknown"}
SMALL = {"0", "1", "2", "3"}


def structured_evidence(result: SolveResult, rep: FeasibilityReport) -> list[dict]:
    """Facts about feasibility and the solver that messages quote: counted from the report and result, never typed."""
    counts = {s: sum(1 for c in rep.checks if c.status == s) for s in ("pass", "warning", "fail")}
    items = [("feasibility_report.overall", "Validator verdict", rep.overall), ("feasibility_report.checks", "Validator checks run", len(rep.checks)),
             ("feasibility_report.counts", "Checks passed / with warnings / failed", f"{counts['pass']} / {counts['warning']} / {counts['fail']}")]
    if result.solver_meta is not None:
        items.append(("result.solver_meta.solver_status", "Solver status", result.solver_meta.solver_status))
    return [{"kind": "calculated", "reference": r, "label": l, "value": v} for r, l, v in items]


def _recompute(ds: Dataset, result: SolveResult, nights: int) -> dict:
    hotel = result.hotel_id
    adm = sum((ds.attractions[s.attraction_id].admission_cost or 0) for d in result.days for s in d.stops)
    minutes = fare = 0
    for d in result.days:
        prev = hotel
        for s in d.stops:
            a = s.attraction_id
            minutes += ds.minutes[prev][a]
            fare += ds.fare_jpy[prev][a]
            prev = a
        if d.stops:
            minutes += ds.minutes[prev][hotel]
            fare += ds.fare_jpy[prev][hotel]
    rooms = ds.hotels[hotel].nightly_rate * nights
    return {"admissions": adm, "transport": fare, "rooms": rooms, "cash_total_with_rooms": adm + fare + rooms, "travel_minutes": minutes,
            "attractions_scheduled": sum(len(d.stops) for d in result.days)}


def verify_evidence(out: dict, result: SolveResult, rep: FeasibilityReport, prefs: Preferences, ds: Dataset, nights: int) -> list[str]:
    """Problems found (empty = verified). Pure; raises nothing."""
    problems: list[str] = []
    feasible = result.status == "feasible"
    truth = _recompute(ds, result, nights) if feasible else None
    names = {a.name for a in ds.attractions.values()}
    shown: set[str] = set()
    for e in out.get("evidence", []):
        if e.get("kind") not in KINDS or not isinstance(e.get("reference"), str):
            problems.append("malformed evidence item")
            continue
        ref, val = e["reference"], e.get("value")
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            shown.add(str(val))
        elif isinstance(val, str) and e["kind"] == "calculated":
            shown.update(re.findall(r"\d[\d,]*", val))       # "13 / 1 / 0" explains the numbers 13, 1 and 0
        if feasible and ref.startswith("cost_summary.trip."):
            key = ref.rsplit(".", 1)[1]
            if key in truth and val != truth[key]:
                problems.append(f"{ref} does not match the schedule")
        if feasible and ref == "result.totals.travel_minutes" and val != truth["travel_minutes"]:
            problems.append("travel minutes do not match the schedule")
        if feasible and ref == "result.totals.attractions_scheduled" and val != truth["attractions_scheduled"]:
            problems.append("scheduled count does not match the schedule")
        if ref == "feasibility_report.overall" and val != rep.overall:
            problems.append("validator verdict mismatch")
        if ref == "feasibility_report.checks" and val != len(rep.checks):
            problems.append("validator check count mismatch")
        if ref == "feasibility_report.verification" and val != rep.verification:
            problems.append("verification label mismatch")
        if ref == "preferences.must_visit" and sorted(val) != sorted(ds.attractions[a].name for a in prefs.must_visit if a in ds.attractions):
            problems.append("must-visit names do not match the request")
        if e["kind"] == "dataset" and ref.startswith("attractions.") and val not in names:
            problems.append("a dataset value is not in the data")
    explained = {s.replace(",", "") for s in shown}
    for n in re.findall(r"\d[\d,]*", out.get("message", "")):
        if n.replace(",", "") not in explained and n not in SMALL:
            problems.append(f"the message contains the number {n}, which no evidence item explains")
    return problems


FAIL_CLOSED = "The evidence for this answer could not be verified, so no answer is shown. Your plan is unchanged. Use the controls below."
