"""Shared helpers for turning (attraction, start-minute) plans into a SolveResult body.

Used by the solver and the baseline so both report travel, cost and flags the same way.
The validator deliberately does NOT use this module.
"""
from app.data.loader import Dataset, travel_fare, travel_minutes
from app.schemas import WEEKDAYS, DayPlan, Preferences, Stop, Totals, to_minutes


def fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_duration(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h}h{m:02d}"
    return f"{h}h" if h else f"{m}min"


def weekday_of(prefs: Preferences, day_index: int) -> str:
    return WEEKDAYS[(prefs.start_weekday + day_index) % 7]


def required_ids(prefs: Preferences) -> list[str]:
    """Must-visit ids, de-duplicated, order preserved."""
    return list(dict.fromkeys(prefs.must_visit))


def assemble(
    ds: Dataset, prefs: Preferences, hotel_id: str, plan: list[list[tuple[str, int]]]
) -> tuple[list[DayPlan], Totals]:
    """plan[d] = [(attraction_id, start_minute), ...] in visiting order."""
    must = set(prefs.must_visit)
    days: list[DayPlan] = []
    totals = Totals()
    for d, visits in enumerate(plan):
        wd = weekday_of(prefs, d)
        stops: list[Stop] = []
        prev = hotel_id
        prev_end = None
        for aid, start in visits:
            att = ds.attractions[aid]
            tmin, fare = travel_minutes(ds, prev, aid), travel_fare(ds, prev, aid)
            known = att.admission_cost is not None
            flags = []
            if att.opening_hours[wd] == "unknown":
                flags.append("opening_hours_unknown")
            if not known:
                flags.append("price_unknown")
                totals.unknown_cost_items.append(aid)
            if att.advance_booking_required:
                flags.append("advance_booking_required")
            stops.append(Stop(
                attraction_id=aid, start=fmt(start), end=fmt(start + att.duration_minutes),
                travel_minutes_from_previous=tmin, transport_jpy_from_previous=fare,
                cost=att.admission_cost or 0, cost_status="known" if known else "unknown",
                is_must_visit=aid in must, uncertainty_flags=flags,
            ))
            totals.travel_minutes += tmin
            totals.transport_jpy += fare
            totals.admissions_jpy += att.admission_cost or 0
            prev, prev_end = aid, start + att.duration_minutes
        day = DayPlan(day=d + 1, weekday=wd, stops=stops)
        if stops:
            first_start = to_minutes(stops[0].start)
            day.hotel_departure = fmt(first_start - stops[0].travel_minutes_from_previous)
            day.return_travel_minutes = travel_minutes(ds, prev, hotel_id)
            day.return_transport_jpy = travel_fare(ds, prev, hotel_id)
            day.hotel_return = fmt(prev_end + day.return_travel_minutes)
            totals.travel_minutes += day.return_travel_minutes
            totals.transport_jpy += day.return_transport_jpy
        totals.attractions_scheduled += len(stops)
        days.append(day)
    totals.total_jpy = totals.admissions_jpy + totals.transport_jpy
    return days, totals
