"""Independent recomputation used to audit the solver's claims. Deliberately imports NOTHING from the optimiser or validator:
only the dataset, the preference model and the data-access helpers. When the solver says "infeasible because X", these functions
re-derive X from the data, and a brute-force search checks that no schedule for the must-visits exists at all.
"""
from itertools import permutations, product

from app.data.loader import Dataset, travel_fare, travel_minutes
from app.schemas import WEEKDAYS, Preferences, to_minutes

PACE_CAP = {"relaxed": 2, "balanced": 3, "packed": 4}  # restated here on purpose: independent of the solver's config use
MAX_MUSTS_FOR_BRUTE_FORCE = 5


def _hours(ds: Dataset, prefs: Preferences, aid: str, d: int):
    return ds.attractions[aid].opening_hours[WEEKDAYS[(prefs.start_weekday + d) % 7]]


def usable_ranges(ds: Dataset, prefs: Preferences, aid: str, d: int) -> list[tuple[int, int]]:
    """Opening windows on trip day d clipped to the day window and long enough for the visit. Unknown hours count only if allowed."""
    hours = _hours(ds, prefs, aid, d)
    lo_d, hi_d = to_minutes(prefs.day_start), to_minutes(prefs.day_end)
    if hours is None or (hours == "unknown" and not prefs.allow_unknown_hours):
        return []
    raw = [(lo_d, hi_d)] if hours == "unknown" else [(max(to_minutes(o), lo_d), min(to_minutes(c), hi_d)) for o, c in hours]
    return [(lo, hi) for lo, hi in raw if hi - lo >= ds.attractions[aid].duration_minutes]


def visitable(ds: Dataset, prefs: Preferences, aid: str) -> bool:
    return any(usable_ranges(ds, prefs, aid, d) for d in range(prefs.days))


def _sequence_cost(ds: Dataset, prefs: Preferences, hotel: str, d: int, seq: tuple[str, ...]) -> int | None:
    """Admissions + fares of doing `seq` on day d from the hotel with earliest possible starts, or None if it cannot be done.
    Earliest-start is optimal for a fixed order: starting later never helps."""
    day_end = to_minutes(prefs.day_end)
    t, prev, cost = to_minutes(prefs.day_start), hotel, 0
    for aid in seq:
        att = ds.attractions[aid]
        arrive = t + travel_minutes(ds, prev, aid)
        start = next((max(arrive, lo) for lo, hi in usable_ranges(ds, prefs, aid, d) if max(arrive, lo) + att.duration_minutes <= hi), None)
        if start is None:
            return None
        cost += (att.admission_cost or 0) + travel_fare(ds, prev, aid)
        t, prev = start + att.duration_minutes, aid
    if t + travel_minutes(ds, prev, hotel) > day_end:
        return None
    return cost + travel_fare(ds, prev, hotel)


def musts_schedulable(ds: Dataset, prefs: Preferences, hotel: str) -> bool | None:
    """Exhaustive search over day assignments and visiting orders for the must-visits ONLY (nice-to-haves are optional).
    True/False = a schedule does / does not exist (honouring hours, window, travel time, pace cap and a strict budget).
    None = not decided (too many must-visits to enumerate, or an unknown attraction id)."""
    musts = list(dict.fromkeys(prefs.must_visit))
    if len(musts) > MAX_MUSTS_FOR_BRUTE_FORCE or any(a not in ds.attractions for a in musts):
        return None
    if not musts:
        return True
    cap, strict = PACE_CAP[prefs.pace], prefs.strict_budget and prefs.budget is not None
    for assignment in product(range(prefs.days), repeat=len(musts)):
        groups = [[a for a, d in zip(musts, assignment) if d == day] for day in range(prefs.days)]
        if any(len(g) > cap for g in groups):
            continue
        best_per_day = []
        for day, g in enumerate(groups):
            costs = [_sequence_cost(ds, prefs, hotel, day, perm) for perm in permutations(g)] if g else [0]
            costs = [c for c in costs if c is not None]
            if not costs:
                break
            best_per_day.append(min(costs))
        else:
            if not strict or sum(best_per_day) <= prefs.budget:
                return True
    return False


def _min_in(ds: Dataset, hotel: str, aid: str, others: list[str], table) -> int:
    return min([table(ds, hotel, aid)] + [table(ds, o, aid) for o in others if o != aid])


def confirm_conflict(code: str, attraction_ids: list[str], ds: Dataset, prefs: Preferences, hotel: str, requested: list[str]) -> bool | None:
    """Does the data support the stated conflict `code`? None = this code cannot be rechecked independently (e.g. solver timeout)."""
    window = to_minutes(prefs.day_end) - to_minutes(prefs.day_start)
    musts = list(dict.fromkeys(prefs.must_visit))
    if code in {"unknown_hours_not_allowed", "closed_all_days", "no_open_slot", "does_not_fit_day"}:
        if not attraction_ids:
            return False
        a = attraction_ids[0]
        att = ds.attractions[a]
        hours = [_hours(ds, prefs, a, d) for d in range(prefs.days)]
        if code == "does_not_fit_day":
            return att.duration_minutes + travel_minutes(ds, hotel, a) + travel_minutes(ds, a, hotel) > window
        if visitable(ds, prefs, a) or att.duration_minutes + travel_minutes(ds, hotel, a) + travel_minutes(ds, a, hotel) > window:
            return False
        if code == "closed_all_days":
            return all(h is None for h in hours)
        if code == "unknown_hours_not_allowed":
            return any(h == "unknown" for h in hours) and not prefs.allow_unknown_hours
        return not all(h is None for h in hours) and not any(h == "unknown" for h in hours)  # no_open_slot
    if code == "pace_cap":
        return len(musts) > PACE_CAP[prefs.pace] * prefs.days
    if code == "not_enough_time":
        need = sum(ds.attractions[a].duration_minutes + _min_in(ds, hotel, a, requested, travel_minutes) for a in musts)
        need += min(travel_minutes(ds, a, hotel) for a in requested)
        return need > prefs.days * window
    if code == "budget_too_low":
        if not (prefs.strict_budget and prefs.budget is not None):
            return False
        adm = sum(ds.attractions[a].admission_cost or 0 for a in musts)
        fare = sum(_min_in(ds, hotel, a, requested, travel_fare) for a in musts) + min(travel_fare(ds, a, hotel) for a in requested)
        return adm + fare > prefs.budget
    if code == "no_feasible_schedule":
        found = musts_schedulable(ds, prefs, hotel)
        return None if found is None else not found
    return None
