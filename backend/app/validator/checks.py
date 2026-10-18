"""Independent re-check of a schedule.

WHY THIS FILE DUPLICATES LOGIC: the validator exists to catch bugs in the optimiser, so it must not
share code with it. It imports only plain data (schemas, loader) and recomputes every time, travel
and cost figure itself from the raw dataset, ignoring the cost/travel numbers the schedule reports
(except to flag mismatches). Nothing from app.optimiser may be imported here; a test enforces it.
"""
from dataclasses import dataclass, field

from app.money import money
from app.data.loader import Dataset
from app.schemas import Preferences, SolveResult

WD = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
PACE_CAPS = {"relaxed": 2, "balanced": 3, "packed": 4}  # kept separate from the optimiser's config on purpose


@dataclass
class Check:
    id: str
    name: str
    status: str  # pass | fail | warning
    message: str
    stop_ids: list[str] = field(default_factory=list)


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _verdict(cid, name, bad, ok_msg, bad_msg, level="fail") -> Check:
    return Check(cid, name, "pass", ok_msg) if not bad else Check(cid, name, level, bad_msg, sorted(set(bad)))


def run_checks(schedule: SolveResult, ds: Dataset, prefs: Preferences, hotel_id: str) -> list[Check]:
    day_start, day_end = _mins(prefs.day_start), _mins(prefs.day_end)
    cap = prefs.max_activities_per_day or PACE_CAPS[prefs.pace]   # the user's own limit replaces the preset's cap
    must = set(prefs.must_visit)
    locked = {l.attraction_id: (l.day, _mins(l.start_time)) for l in prefs.locked}
    skip = set(prefs.skip) | {a.id for a in ds.attractions.values() if a.priority == "skip"}
    skip -= must

    # Normalise the schedule into (day, id, start, end) with our own parsing.
    rows = []  # (day_no, weekday_idx, aid, start, end, stop)
    for dp in schedule.days:
        for s in dp.stops:
            rows.append((dp.day, (prefs.start_weekday + dp.day - 1) % 7, s.attraction_id, _mins(s.start), _mins(s.end), s))
    known = [r for r in rows if r[2] in ds.attractions]
    by_day: dict[int, list] = {}
    for r in known:
        by_day.setdefault(r[0], []).append(r)
    for lst in by_day.values():
        lst.sort(key=lambda r: r[3])

    checks: list[Check] = []

    bad = [r[2] for r in rows if r[2] not in ds.attractions]
    bad += [str(dp.day) for dp in schedule.days if dp.day < 1 or dp.day > prefs.days]
    checks.append(_verdict("known_items", "Known attractions and trip length", bad,
                           "All stops are known attractions within the trip length.",
                           "Unknown attraction id(s) or day number outside the trip."))

    dups = [a for a in {r[2] for r in rows} if sum(r[2] == a for r in rows) > 1]
    checks.append(_verdict("duplicates", "No duplicate attractions", dups, "Each attraction appears at most once.",
                           "Attraction scheduled more than once."))

    # Overlaps and durations (own arithmetic from dataset durations).
    bad = []
    for lst in by_day.values():
        for r in lst:
            if r[4] - r[3] != ds.attractions[r[2]].duration_minutes:
                bad.append(r[2])
        for a, b in zip(lst, lst[1:]):
            if b[3] < a[4]:
                bad += [a[2], b[2]]
    checks.append(_verdict("overlaps", "No overlapping stops and correct durations", bad,
                           "No stops overlap and each stop lasts the dataset duration.",
                           "Stops overlap or a stop's length differs from the attraction's duration."))

    # Travel gaps: matrix time between consecutive stops, including hotel legs.
    bad, msg_extra = [], ""
    for lst in by_day.values():
        prev_id, prev_end = hotel_id, None
        for r in lst:
            need = ds.minutes[prev_id][r[2]]
            if prev_end is not None and r[3] - prev_end < need:
                bad.append(r[2])
            if prev_end is None and r[3] - need < day_start:
                bad.append(r[2])  # cannot leave the hotel before day start
            if r[5].travel_minutes_from_previous != need:
                bad.append(r[2])  # reported travel time disagrees with the matrix
            prev_id, prev_end = r[2], r[4]
    checks.append(_verdict("travel_gaps", "Enough time to travel between stops", bad,
                           "Every gap covers the estimated travel time (hotel legs included).",
                           "A stop starts before the estimated travel time has elapsed, or its reported travel time is wrong."))

    # Opening hours for the specific weekday.
    bad = []
    for r in known:
        h = ds.attractions[r[2]].opening_hours[WD[r[1]]]
        if h is None:
            bad.append(r[2])
        elif h == "unknown":
            if not prefs.allow_unknown_hours:
                bad.append(r[2])
        elif not any(_mins(o) <= r[3] and r[4] <= _mins(c) for o, c in h):
            bad.append(r[2])
    checks.append(_verdict("opening_hours", "Open when visited", bad,
                           "Every stop lies inside its opening hours for that weekday.",
                           "Stop is on a closing day, outside opening hours, or has unknown hours that are not allowed."))

    # Day window: hotel departure and return.
    bad = []
    for lst in by_day.values():
        if lst[0][3] - ds.minutes[hotel_id][lst[0][2]] < day_start:
            bad.append(lst[0][2])
        if lst[-1][4] + ds.minutes[lst[-1][2]][hotel_id] > day_end:
            bad.append(lst[-1][2])
        bad += [r[2] for r in lst if r[3] < day_start or r[4] > day_end]
    checks.append(_verdict("day_window", "Within the day window", bad,
                           f"Each day starts and ends at the hotel within {prefs.day_start}-{prefs.day_end}.",
                           f"A day starts before {prefs.day_start} or the return to the hotel is after {prefs.day_end}."))

    present = {r[2] for r in rows}
    missing = [a for a in must if a not in present]
    checks.append(_verdict("must_visits", "All must-visits present", missing, "Every must-visit is scheduled.",
                           "Must-visit(s) missing from the schedule."))

    bad = []
    for a, (day, start) in locked.items():
        match = [r for r in rows if r[2] == a]
        if not match or match[0][0] != day or match[0][3] != start:
            bad.append(a)
    checks.append(_verdict("locked", "Locked activities unmoved", bad,
                           "Every locked activity is on its day at its time." if locked else "No locked activities.",
                           "Locked activity moved or missing."))

    bad = [str(d) for d, lst in by_day.items() if len(lst) > cap]
    own = prefs.max_activities_per_day is not None
    checks.append(_verdict("pace_cap", "Daily activity limit respected" if own else "Pace cap respected", bad,
                           f"At most {cap} attractions per day ({'your limit' if own else repr(prefs.pace)}).",
                           f"A day exceeds {'your limit' if own else 'the ' + repr(prefs.pace) + ' cap'} of {cap}."))

    if prefs.min_active_days is not None:     # counted from the schedule itself: days that have at least one stop
        active = sum(1 for d in by_day if by_day[d])
        checks.append(_verdict("active_days", "Minimum active days respected", [] if active >= prefs.min_active_days else [str(d) for d in range(1, prefs.days + 1) if not by_day.get(d)],
                               f"{active} of {prefs.days} days have activities (at least {prefs.min_active_days} requested).",
                               f"Only {active} of {prefs.days} days have activities; at least {prefs.min_active_days} were requested."))
    if prefs.max_daily_travel_minutes is not None:   # recomputed from the matrix: first leg from the hotel, legs between stops, the leg back
        limit, bad = prefs.max_daily_travel_minutes, []
        for d, lst in by_day.items():
            prev, total = hotel_id, 0
            for r in lst:
                total += ds.minutes[prev][r[2]]
                prev = r[2]
            total += ds.minutes[prev][hotel_id]
            if total > limit:
                bad.append(str(d))
        checks.append(_verdict("daily_travel", "Daily estimated travel limit respected", bad, f"Each day needs at most {limit} min of estimated travel (hotel legs included).",
                               f"A day needs more than {limit} min of estimated travel (hotel legs included)."))

    bad = [r[2] for r in rows if r[2] in skip and r[2] not in locked]
    checks.append(_verdict("skip_respected", "Skipped attractions not scheduled", bad,
                           "No skipped attraction is scheduled.", "A skipped attraction was scheduled."))

    # Budget: recompute admissions + fares from the dataset.
    adm = sum(ds.attractions[r[2]].admission_cost or 0 for r in known)
    fare = 0
    for lst in by_day.values():
        prev = hotel_id
        for r in lst:
            fare += ds.fare_jpy[prev][r[2]]
            prev = r[2]
        fare += ds.fare_jpy[prev][hotel_id]
    total = adm + fare
    if prefs.budget is None:
        checks.append(Check("budget", "Budget", "pass", f"No budget set (recomputed total {money(total, ds)})."))
    elif total <= prefs.budget:
        checks.append(Check("budget", "Budget", "pass", f"Total {money(total, ds)} (admissions {adm:,} + transport {fare:,}) is within the budget of {money(prefs.budget, ds)}."))
    else:
        level = "fail" if prefs.strict_budget else "warning"
        kind = "strict" if prefs.strict_budget else "soft"
        checks.append(Check("budget", "Budget", level, f"Total {money(total, ds)} exceeds the {kind} budget of {money(prefs.budget, ds)} by {money(total - prefs.budget, ds)}."))

    # Data-quality warnings (never a plain pass).
    unk_h = [r[2] for r in known if ds.attractions[r[2]].opening_hours[WD[r[1]]] == "unknown"]
    checks.append(_verdict("unknown_hours_used", "Unknown opening hours", unk_h, "No stop relies on unknown opening hours.",
                           "Opening hours unverified (unknown in the data): the plan holds only if this is open at the scheduled time.", "warning"))
    unk_p = [r[2] for r in known if ds.attractions[r[2]].admission_cost is None]
    checks.append(_verdict("unknown_prices", "Unknown prices", unk_p, "All scheduled prices are known.",
                           "Price unknown: excluded from total (unknown).", "warning"))
    legs = sum(len(l) for l in by_day.values())
    checks.append(Check("transport_estimated", "Transport estimates",
                        "warning" if legs else "pass",
                        "Travel times and fares are ESTIMATES from straight-line distance, not real transit data." if legs else "No transport legs.",
                        []))
    adv = [r[2] for r in known if ds.attractions[r[2]].advance_booking_required]
    checks.append(_verdict("advance_booking", "Advance booking", adv, "No stop needs advance booking.",
                           "Advance booking required; availability not checked.", "warning"))
    return checks
