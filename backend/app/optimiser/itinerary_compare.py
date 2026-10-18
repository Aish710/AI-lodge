"""Your itinerary versus the optimiser, on identical data.

Three arms, all for ONE hotel and the user's own set of sights, scored by the same breakdown (`hotel_compare._breakdown`) and checked by the same independent validator:

  your plan      the user's own day assignment and order. Each stop is placed at the earliest time that respects its opening hours and the day window (waiting for opening if early);
                 nothing else about it is changed. A stop that cannot be placed is reported with the reason and the plan is NOT presented as feasible.
  same sights    the optimiser, required to visit exactly the user's sights (every one a must-visit). It can only change order, day and timing, so any difference isolates scheduling.
  full plan      the optimiser with the user's must-visit flags: it may leave optional sights out when including them costs more than they are worth.

The score is the optimisation score (true cost), never money spent; monetary spending is reported separately. A travel-time saving is only called a saving when the two plans visit the
same sights. No optimisation or arithmetic about plans happens in the browser.
"""
import time

from app import config
from app.data.loader import Dataset, travel_fare, travel_minutes
from app.money import missed_preference_penalty
from app.optimiser.hotel_compare import _breakdown
from app.optimiser.schedule import assemble, weekday_of
from app.optimiser.solver import ObjectiveSpec, missed_preferences_for, solve
from app.schemas import Conflict, Preferences, SolveResult, SolverMeta, nights_for, to_minutes
from app.validator.feasibility_report import build_report


class ItineraryInputError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _earliest_start(ds: Dataset, prefs: Preferences, hotel_id: str, d: int, pos: str, free: int, aid: str) -> tuple[int | None, str]:
    """Earliest start at day d after leaving `pos` at `free`, or (None, plain reason)."""
    att = ds.attractions[aid]
    hours = att.opening_hours[weekday_of(prefs, d)]
    if hours is None:
        return None, f"{att.name} is closed on day {d + 1}."
    if hours == "unknown" and not prefs.allow_unknown_hours:
        return None, f"{att.name} has unknown opening hours on day {d + 1}, and unknown hours are never assumed open."
    ds_min, de_min = to_minutes(prefs.day_start), to_minutes(prefs.day_end)
    arrive = free + travel_minutes(ds, pos, aid)
    windows = [(ds_min, de_min)] if hours == "unknown" else [(to_minutes(o), to_minutes(c)) for o, c in hours]
    for lo, hi in windows:
        start = max(arrive, lo)
        end = start + att.duration_minutes
        if end <= min(hi, de_min) and end + travel_minutes(ds, aid, hotel_id) <= de_min:
            return start, ""
    return None, f"{att.name} does not fit on day {d + 1} after the stops before it (opening hours, the day window and the trip back to the hotel)."


def place_user_plan(prefs: Preferences, hotel_id: str, ds: Dataset, days: list[list[str]]) -> SolveResult:
    t0 = time.perf_counter()
    plan: list[list[tuple[str, int]]] = [[] for _ in range(prefs.days)]
    conflicts: list[Conflict] = []
    for d, ids in enumerate(days[: prefs.days]):
        pos, free = hotel_id, to_minutes(prefs.day_start)
        for aid in ids:
            start, why = _earliest_start(ds, prefs, hotel_id, d, pos, free, aid)
            if start is None:
                conflicts.append(Conflict(code="user_stop_not_placeable", message=why, attraction_ids=[aid]))
                continue
            plan[d].append((aid, start))
            pos, free = aid, start + ds.attractions[aid].duration_minutes
    out_days, totals = assemble(ds, prefs, hotel_id, plan)
    placed = {a for day in plan for a, _ in day}
    asked = {a for ids in days for a in ids}
    res = SolveResult(status="feasible" if not conflicts else "infeasible", hotel_id=hotel_id, days=out_days, totals=totals, conflicts=conflicts,
                      notes=["Your itinerary: your days and order; each stop at the earliest time it can happen."],
                      solver_meta=SolverMeta(solver="user-itinerary", solver_status="N/A", seed=0, runtime_seconds=round(time.perf_counter() - t0, 4)))
    res.missed_preferences = []     # filled by the caller (needs the target set)
    res.notes.append(f"{len(placed)} of {len(asked)} requested stops placed.")
    return res


def _arm(ds, prefs, hotel_id, res: SolveResult, target: list[str], nights: int, vot: int, name: str, label: str) -> dict:
    feasible = res.status == "feasible"
    scheduled = {s.attraction_id for dp in res.days for s in dp.stops}
    if feasible:
        optional_visitable = set(missed_preferences_for(prefs, hotel_id, ds, scheduled))
        res = res.model_copy(update={"missed_preferences": [a for a in target if a in optional_visitable and a not in prefs.must_visit]})
    rep = build_report(res, ds, prefs, hotel_id) if feasible else None
    passed = bool(rep) and rep.overall != "fail"
    out = {"key": name, "label": label, "feasible": bool(feasible and passed), "status": res.status,
           "conflicts": [c.message for c in res.conflicts], "failed_checks": [c.name for c in (rep.checks if rep else []) if c.status == "fail"],
           "schedule": res.model_dump() if feasible else None, "sights": sorted(scheduled), "omitted": [], "breakdown": None}
    if feasible:
        b = _breakdown(ds, prefs, hotel_id, res, nights, vot)
        out["breakdown"] = b.model_dump()
        out["omitted"] = list(b.missed_preferences.attraction_ids)
        out["known_spend_jpy"] = b.rooms_jpy + b.admissions_jpy + b.transport_jpy
        out["travel_minutes"] = b.travel_minutes
        out["score_jpy"] = b.true_cost_jpy
    return out


def _delta(a: dict, b: dict, key: str):
    return None if a.get(key) is None or b.get(key) is None else b[key] - a[key]


def evaluate_itinerary(prefs: Preferences, hotel_id: str, ds: Dataset, days: list[list[str]], *, max_seconds: float) -> dict:
    if hotel_id not in ds.hotels:
        raise ItineraryInputError("unknown_hotel", f"Unknown hotel id '{hotel_id[:64]}'.")
    if len(days) > prefs.days:
        raise ItineraryInputError("too_many_days", f"The itinerary has {len(days)} day(s) but the trip has {prefs.days}.")
    target = list(dict.fromkeys(a for ids in days for a in ids))
    if not target:
        raise ItineraryInputError("empty_itinerary", "Add at least one attraction to your itinerary.")
    unknown = [a for a in target if a not in ds.attractions]
    if unknown:
        raise ItineraryInputError("unknown_attraction", f"Unknown attraction id '{unknown[0][:64]}'.")
    if len(target) != sum(len(i) for i in days):
        raise ItineraryInputError("duplicate_stop", "An attraction appears more than once in your itinerary.")
    must_missing = [a for a in prefs.must_visit if a not in target]
    if must_missing:
        raise ItineraryInputError("must_visit_not_in_itinerary", f"{ds.attractions[must_missing[0]].name} is marked must-visit but is not in your itinerary.")

    skip = [a for a in sorted(ds.attractions) if a not in target]
    base = prefs.model_copy(update={"skip": skip, "locked": [l for l in prefs.locked if l.attraction_id in target]})
    nights, _ = nights_for(base)
    vot = base.value_of_time_per_hour
    spec = ObjectiveSpec("true_cost", vot, missed_preference_penalty(ds))
    t0 = time.perf_counter()

    mine = place_user_plan(base, hotel_id, ds, days)
    arm_user = _arm(ds, base, hotel_id, mine if mine.status == "feasible" else mine.model_copy(update={"status": "infeasible"}), target, nights, vot, "yours", "Your itinerary")
    if mine.status != "feasible":
        # still show what the placed part costs, clearly marked as incomplete
        arm_user["incomplete"] = True
    same_prefs = base.model_copy(update={"must_visit": target})
    same = solve(same_prefs, hotel_id, ds, objective=spec, max_seconds=max_seconds, with_alternatives=False)
    arm_same = _arm(ds, same_prefs, hotel_id, same, target, nights, vot, "same_sights", "Optimised, same sights")
    full = solve(base, hotel_id, ds, objective=spec, max_seconds=max_seconds, with_alternatives=False)
    arm_full = _arm(ds, base, hotel_id, full, target, nights, vot, "full_plan", "Optimised, may leave optional sights out")

    cmp_same = {"valid": bool(arm_user["feasible"] and arm_same["feasible"]),
                "why_not": None if arm_user["feasible"] and arm_same["feasible"] else
                ("Your itinerary is not feasible as arranged, so there is no like-for-like saving to report." if not arm_user["feasible"] else
                 "The optimiser found no feasible plan that visits all of your sights."),
                "travel_minutes_saved": None, "known_spend_saved": None, "score_gain": None}
    if cmp_same["valid"]:
        cmp_same.update(travel_minutes_saved=arm_user["travel_minutes"] - arm_same["travel_minutes"],
                        known_spend_saved=arm_user["known_spend_jpy"] - arm_same["known_spend_jpy"],
                        score_gain=arm_user["score_jpy"] - arm_same["score_jpy"])
    cmp_full = {"valid": bool(arm_full["feasible"]), "different_sights": bool(arm_full["feasible"] and set(arm_full["sights"]) != set(arm_user["sights"])),
                "sights_left_out": arm_full["omitted"], "score_gain": None, "travel_minutes_difference": None}
    if arm_full["feasible"] and arm_user["feasible"]:
        cmp_full.update(score_gain=arm_user["score_jpy"] - arm_full["score_jpy"], travel_minutes_difference=arm_user["travel_minutes"] - arm_full["travel_minutes"])
    verdict = _verdict(ds, arm_user, arm_same, arm_full, cmp_same, cmp_full)
    return {"hotel_id": hotel_id, "target_sights": target, "arms": [arm_user, arm_same, arm_full], "same_sights": cmp_same, "full_plan": cmp_full, "verdict": verdict,
            "runtime_seconds": round(time.perf_counter() - t0, 3),
            "note": "Estimated straight-line travel times on sample data. The score is the optimisation score, not money spent."}


def _verdict(ds, user, same, full, cs, cf) -> dict:
    """One plain sentence from numbers already computed above. No claim without its condition."""
    if not user["feasible"]:
        why = user["conflicts"][0] if user["conflicts"] else ("it fails: " + ", ".join(user["failed_checks"]))
        return {"kind": "yours_infeasible", "text": f"Your itinerary does not work as arranged ({why})" + (" The optimiser found a plan that visits all of your sights." if same["feasible"] else " The optimiser could not visit all of your sights either.")}
    if cs["valid"]:
        m, s = cs["travel_minutes_saved"], cs["known_spend_saved"]
        if m == 0 and s == 0:
            return {"kind": "tie", "text": "Your itinerary is as good as the optimiser's for the same sights: same estimated travel time and the same sight spending."}
        if m > 0 or s > 0:
            return {"kind": "better_same_sights", "text": f"For exactly the same sights, the optimised order saves {max(m, 0)} min of estimated travel and {max(s, 0):,} of sight and transport spending."}
        return {"kind": "yours_cheaper_on_time_or_money", "text": "For the same sights the optimiser's plan is not shorter or cheaper than yours; it can still differ in score because of how the score weighs them."}
    return {"kind": "no_like_for_like", "text": cs["why_not"] or "No like-for-like comparison is available."}
