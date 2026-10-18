"""AI-assisted repair, the DETERMINISTIC half. Nothing in this module calls a model.

A repair is a short list of allowlisted actions. Each names its target, the value it expects the plan to have NOW (`expected_previous`), the value it proposes, whether it touches a hard
constraint and whether it needs the person's explicit confirmation. The language model (app/llm/repair.py) only chooses actions and words; everything that matters is decided here:

  * the action set is closed; a proposal outside it cannot be built;
  * numbers and ids are computed or resolved in code, ranges are checked in code;
  * a hotel the person has kept cannot be switched (the lock is a request field the client sets, never the model);
  * `requires_confirmation` is derived from the action, never read from the model;
  * applying a repair RE-CHECKS everything against the CURRENT plan (fingerprint, expected values, allowlist, lock, confirmation) so a stale or tampered proposal is refused;
  * the result is produced by the normal optimiser and checked by the independent validator, exactly like a plan made from the form.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app import config
from app.data.loader import Dataset
from app.fingerprint import plan_fingerprint
from app.money import missed_preference_penalty
from app.optimiser.solver import ObjectiveSpec, solve
from app.optimiser.schedule import fmt as fmt_hhmm
from app.schemas import Preferences, to_minutes
from app.validator.feasibility_report import build_report

ActionName = Literal["extend_day", "set_max_activities", "set_max_daily_travel", "set_pace", "change_value_of_time", "remove_optional", "promote_to_must",
                     "demote_must_visit", "allow_unknown_hours", "soften_budget", "switch_hotel", "unlock_hotel"]
ACTIONS: tuple[str, ...] = ActionName.__args__
# Actions that give something up or change a hard constraint: the person must tick an explicit confirmation for each before they can be applied.
CONFIRMED = frozenset({"demote_must_visit", "allow_unknown_hours", "soften_budget", "unlock_hotel", "promote_to_must"})
HARD = frozenset({"demote_must_visit", "allow_unknown_hours", "soften_budget", "unlock_hotel", "promote_to_must", "set_max_activities", "set_max_daily_travel", "extend_day"})
VOT_FACTOR = {"lower": 0.5, "higher": 2.0}       # documented, applied to the CURRENT value of time


class _P(BaseModel):
    model_config = ConfigDict(extra="forbid")


Scalar = str | int | bool | None


class RepairAction(_P):
    id: str = Field(max_length=8)
    action: ActionName
    target: str = Field(max_length=64)               # a field name, an attraction id or a hotel id
    target_label: str = Field(max_length=120)
    expected_previous: Scalar = None
    proposed: Scalar = None
    reason: str = Field(default="", max_length=200)  # the model's words (scrubbed); never used for anything but display
    hard_constraint: bool = False
    requires_confirmation: bool = False


class RepairError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ---- reading the CURRENT value an action is about ---------------------------------------------------------------------------------------------
def current_value(action: str, target: str, prefs: Preferences, hotel_id: str, keep_hotel: bool) -> Scalar:
    if action == "extend_day":
        return prefs.day_end
    if action == "set_max_activities":
        return prefs.max_activities_per_day
    if action == "set_max_daily_travel":
        return prefs.max_daily_travel_minutes
    if action == "set_pace":
        return prefs.pace
    if action == "change_value_of_time":
        return prefs.value_of_time_per_hour
    if action in ("remove_optional", "promote_to_must", "demote_must_visit"):
        return "must" if target in prefs.must_visit else "skip" if target in prefs.skip else "optional"
    if action == "allow_unknown_hours":
        return prefs.allow_unknown_hours
    if action == "soften_budget":
        return prefs.strict_budget
    if action == "switch_hotel":
        return hotel_id
    if action == "unlock_hotel":
        return keep_hotel
    raise RepairError("unknown_action", f"Unknown repair action '{action[:40]}'.")


def _check(a: RepairAction, prefs: Preferences, hotel_id: str, keep_hotel: bool, ds: Dataset) -> None:
    """Refuse anything the allowlist, the ranges or the person's own locks do not permit. Raises RepairError."""
    if a.action not in ACTIONS:
        raise RepairError("unknown_action", f"Unknown repair action '{a.action[:40]}'.")
    if a.action in ("remove_optional", "promote_to_must", "demote_must_visit"):
        if a.target not in ds.attractions:
            raise RepairError("unknown_attraction", "That attraction is not in this city's data.")
        if any(l.attraction_id == a.target for l in prefs.locked):
            raise RepairError("locked_attraction", f"{ds.attractions[a.target].name} is locked at a fixed time. Unlock it yourself first: a repair never moves or removes a lock.")
    if a.action == "switch_hotel":
        if a.proposed not in ds.hotels:
            raise RepairError("unknown_hotel", "That hotel is not in this city's data.")
        if keep_hotel:
            raise RepairError("hotel_locked", "You asked to keep your hotel, so a repair cannot switch it. Unlock the hotel first if you want that.")
    if a.requires_confirmation != (a.action in CONFIRMED) or a.hard_constraint != (a.action in HARD):
        raise RepairError("flags_mismatch", "The confirmation or hard-constraint flags do not match the action.")
    now = current_value(a.action, a.target, prefs, hotel_id, keep_hotel)
    if now != a.expected_previous:
        raise RepairError("stale_proposal", "The plan changed since this proposal was made. Ask again for a fresh proposal.", 409)
    p = a.proposed
    if a.action == "extend_day":
        if not (isinstance(p, str) and len(p) == 5 and p[2] == ":") or not to_minutes(prefs.day_end) < to_minutes(p) <= 23 * 60 + 59:
            raise RepairError("out_of_range", "The new end of day must be later than the current one and before midnight.")
    elif a.action == "set_max_activities":
        if not (isinstance(p, int) and not isinstance(p, bool) and 1 <= p <= 8):
            raise RepairError("out_of_range", "Activities per day must be 1 to 8.")
    elif a.action == "set_max_daily_travel":
        if p is not None and not (isinstance(p, int) and not isinstance(p, bool) and 20 <= p <= 720):
            raise RepairError("out_of_range", "Estimated travel per day must be 20 to 720 minutes (or no limit).")
    elif a.action == "set_pace":
        if p not in ("relaxed", "balanced", "packed"):
            raise RepairError("out_of_range", "Pace must be relaxed, balanced or packed.")
    elif a.action == "change_value_of_time":
        if not (isinstance(p, int) and not isinstance(p, bool) and 0 <= p <= 100_000):
            raise RepairError("out_of_range", "Value of time is out of range.")
    elif a.action == "remove_optional":
        if now != "optional":
            raise RepairError("not_optional", f"{ds.attractions[a.target].name} is a must-visit or already left out; use the must-visit action, which needs your confirmation.")
    elif a.action == "promote_to_must":
        if now != "optional" or p != "must":
            raise RepairError("not_optional", "Only an optional attraction can be made a must-visit.")
    elif a.action == "demote_must_visit":
        if now != "must" or p != "optional":
            raise RepairError("not_must", "That attraction is not a must-visit.")
    elif a.action == "allow_unknown_hours":
        if p is not True or now is not False:
            raise RepairError("out_of_range", "Unknown hours are already allowed or the value is invalid.")
    elif a.action == "soften_budget":
        if p is not False or now is not True:
            raise RepairError("out_of_range", "There is no strict budget to soften.")
    elif a.action == "unlock_hotel":
        if p is not False or now is not True:
            raise RepairError("out_of_range", "The hotel is not locked.")


def apply_actions(prefs: Preferences, hotel_id: str, keep_hotel: bool, actions: list[RepairAction], ds: Dataset) -> tuple[Preferences, str, bool]:
    """Validate EVERY action against the current plan, then apply them in order. All or nothing: one refusal refuses the whole repair."""
    if not actions or len(actions) > 8:
        raise RepairError("no_actions", "A repair needs between 1 and 8 actions.")
    if len({a.id for a in actions}) != len(actions):
        raise RepairError("duplicate_action", "Two actions have the same id.")
    p, h, keep = prefs, hotel_id, keep_hotel
    for a in actions:
        _check(a, p, h, keep, ds)                 # against the state AFTER the earlier actions, so a combination cannot smuggle a conflicting pair
        upd = {}
        if a.action == "extend_day":
            upd["day_end"] = a.proposed
        elif a.action == "set_max_activities":
            upd["max_activities_per_day"] = a.proposed
        elif a.action == "set_max_daily_travel":
            upd["max_daily_travel_minutes"] = a.proposed
        elif a.action == "set_pace":
            upd["pace"] = a.proposed
        elif a.action == "change_value_of_time":
            upd["value_of_time_per_hour"] = a.proposed
        elif a.action == "remove_optional":
            upd["skip"] = [*p.skip, a.target]
        elif a.action == "promote_to_must":
            upd["must_visit"] = [*p.must_visit, a.target]
        elif a.action == "demote_must_visit":
            upd["must_visit"] = [x for x in p.must_visit if x != a.target]
        elif a.action == "allow_unknown_hours":
            upd["allow_unknown_hours"] = True
        elif a.action == "soften_budget":
            upd["strict_budget"] = False
        elif a.action == "switch_hotel":
            h = a.proposed
        elif a.action == "unlock_hotel":
            keep = False
        p = Preferences.model_validate({**p.model_dump(), **upd})     # re-validated by the request schema: a bad combination fails here, not later
    return p, h, keep


# ---- building actions (used by the language-model layer; it supplies words and small numbers, never ids or flags) --------------------------------------------
def build_action(idx: int, action: str, prefs: Preferences, hotel_id: str, keep_hotel: bool, ds: Dataset, *, target: str = "", proposed: Scalar = None, reason: str = "") -> RepairAction:
    label = {"extend_day": "Day ends at", "set_max_activities": "Activities per day", "set_max_daily_travel": "Estimated travel per day (min)", "set_pace": "Pace",
             "change_value_of_time": "Value of an hour", "allow_unknown_hours": "Unknown opening hours", "soften_budget": "Strict budget", "unlock_hotel": "Hotel locked"}.get(action, "")
    t = target or {"extend_day": "day_end", "set_max_activities": "max_activities_per_day", "set_max_daily_travel": "max_daily_travel_minutes", "set_pace": "pace",
                   "change_value_of_time": "value_of_time_per_hour", "allow_unknown_hours": "allow_unknown_hours", "soften_budget": "strict_budget", "unlock_hotel": "keep_hotel"}.get(action, "")
    if action in ("remove_optional", "promote_to_must", "demote_must_visit") and target in ds.attractions:
        label = ds.attractions[target].name
    if action == "switch_hotel":
        t = hotel_id
        label = ds.hotels[proposed].name if proposed in ds.hotels else "Hotel"
    return RepairAction(id=f"a{idx}", action=action, target=t or action, target_label=label or action, expected_previous=current_value(action, t, prefs, hotel_id, keep_hotel),
                        proposed=proposed, reason=reason[:200], hard_constraint=action in HARD, requires_confirmation=action in CONFIRMED)


def later_end(prefs: Preferences, minutes: int) -> str | None:
    """The end of day `minutes` later, capped at 23:59, or None if that would not be later."""
    end = min(to_minutes(prefs.day_end) + minutes, 23 * 60 + 59)
    return fmt_hhmm(end) if end > to_minutes(prefs.day_end) else None


# ---- verification: the normal optimiser + the independent validator ----------------------------------------------------------------------------------------
def verify(prefs: Preferences, hotel_id: str, ds: Dataset, *, max_seconds: float) -> dict:
    """Solve the repaired request exactly like /optimise and report what the validator says. `verified` means solved AND validated; `conditional` means it holds only if unverified opening hours are open."""
    res = solve(prefs, hotel_id, ds, objective=ObjectiveSpec("true_cost", prefs.value_of_time_per_hour, missed_preference_penalty(ds)), max_seconds=max_seconds, with_alternatives=False)
    rep = build_report(res, ds, prefs, hotel_id)
    if res.status != "feasible" or rep.overall == "fail":
        missing = bool(res.conflicts) and all(c.category == "missing_information" for c in res.conflicts)
        return {"state": "blocked_missing_info" if missing else "infeasible", "verified": False, "conflicts": [c.message for c in res.conflicts][:3]}
    return {"state": "conditional" if rep.verification == "conditional" else "verified", "verified": rep.verification == "verified", "attractions_scheduled": res.totals.attractions_scheduled,
            "travel_minutes": res.totals.travel_minutes, "total_jpy": res.totals.total_jpy, "conflicts": []}


def base_fingerprint(prefs: Preferences, hotel_id: str, keep_hotel: bool, ds: Dataset) -> str:
    return plan_fingerprint(prefs, [hotel_id, "keep" if keep_hotel else "free"], ds)


def unchanged_summary(before: Preferences, after: Preferences, hotel_before: str, hotel_after: str, ds: Dataset) -> list[str]:
    """What the repair leaves alone, in words, computed from the two requests (not from the model)."""
    out = []
    if before.must_visit == after.must_visit and before.must_visit:
        out.append("All your must-visits stay required: " + ", ".join(ds.attractions[a].name for a in before.must_visit if a in ds.attractions))
    if hotel_before == hotel_after:
        out.append(f"Your hotel stays {ds.hotels[hotel_after].name}")
    if before.strict_budget == after.strict_budget and before.budget is not None:
        out.append("Your budget stays " + ("strict" if before.strict_budget else "as set"))
    if before.locked and [l.model_dump() for l in before.locked] == [l.model_dump() for l in after.locked]:
        out.append("Your locked stops stay locked")
    return out
