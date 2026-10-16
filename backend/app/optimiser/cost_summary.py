"""Per-day and whole-trip cash totals for a feasible plan, computed on the SERVER from the same stop fields the validator re-checks
(`Stop.cost`, `Stop.transport_jpy_from_previous`, the day's return leg), so the client never sums or invents a cost.

Additive: it is a separate block on the /optimise and /replan responses and is NOT part of `SolveResult`, which clients send back unchanged
to /replan under a strict schema. Field names are neutral (`admissions`, `transport`); amounts are in the selected city's local currency
(`currency`). "Cash" is money spent (admissions + estimated transport + rooms). It is deliberately NOT the hotel comparison's "true cost",
which also prices the traveller's time. Unknown prices are listed by attraction id and are never counted as zero in any total."""
from app.data.loader import Dataset
from app.schemas import SolveResult, to_minutes


def _minutes(hhmm: str) -> int:
    return to_minutes(hhmm)


def summarise_costs(result: SolveResult, ds: Dataset, hotel_id: str, nights: int) -> dict | None:
    if result.status != "feasible":
        return None
    days = []
    for d in result.days:
        admissions = sum(s.cost for s in d.stops)  # unknown prices carry cost 0 AND cost_status "unknown": they are listed, not summed as free
        transport = sum(s.transport_jpy_from_previous for s in d.stops) + d.return_transport_jpy
        travel = sum(s.travel_minutes_from_previous for s in d.stops) + d.return_travel_minutes
        at_sights = sum(_minutes(s.end) - _minutes(s.start) for s in d.stops)
        days.append({"day": d.day, "weekday": d.weekday, "stops": len(d.stops), "admissions": admissions, "transport": transport,
                     "day_total": admissions + transport, "travel_minutes": travel, "minutes_at_sights": at_sights,
                     "unknown_price_ids": [s.attraction_id for s in d.stops if s.cost_status == "unknown"]})
    admissions = sum(x["admissions"] for x in days)
    transport = sum(x["transport"] for x in days)
    rate = ds.hotels[hotel_id].nightly_rate
    unknown = [a for x in days for a in x["unknown_price_ids"]]
    n = max(len(days), 1)
    travel_total = sum(x["travel_minutes"] for x in days)
    return {
        "currency": ds.city.currency_code,
        "days": days,
        "trip": {"admissions": admissions, "transport": transport, "cash_total": admissions + transport,
                 "rooms": rate * nights, "nightly_rate": rate, "nights": nights, "cash_total_with_rooms": admissions + transport + rate * nights,
                 "unknown_price_count": len(unknown), "unknown_price_ids": unknown,
                 "travel_minutes": travel_total, "avg_travel_minutes_per_day": round(travel_total / n),
                 "hotel_area": ds.hotels[hotel_id].area},
    }
