"""Three FAIR baselines for the hotel decision, all read off ONE comparison so they cannot differ in candidate data, constraints, routing logic or objective:

  A  cheapest hotel first   the hotel with the lowest nightly rate, then the existing itinerary optimiser
  B  convenience first      the hotel with the smallest total ESTIMATED travel time to the trip's target sights (rule below), then the same optimiser
  C  joint optimisation     the hotel whose optimised itinerary has the lowest true cost (the existing comparison)

`compare_hotels` already solves the itinerary for every candidate hotel with the same objective, so each baseline is the already-solved result for the hotel its rule picks.
The final comparison uses ONE number for all three: the optimisation score (true cost = rooms + admissions + estimated transport + monetised travel time + the missed-sight charge).
That score is NOT what the traveller spends: the known monetary spending (rooms + admissions + estimated transport) is reported next to it, separately.
"""
from pydantic import BaseModel

from app.data.loader import Dataset
from app.schemas import Preferences

CONVENIENCE_RULE = ("Convenience first: the hotel with the smallest total ESTIMATED travel time (straight-line based, from the data's travel-time table) to the trip's target sights, "
                    "where the target sights are the must-visits if there are any, otherwise every sight not marked 'not interested'. Ties: lower nightly rate, then hotel id. "
                    "It looks only at hotel-to-sight times, not at the day-by-day route.")
CHEAPEST_RULE = "Cheapest first: the hotel with the lowest nightly rate (ties: hotel id), then the existing itinerary optimiser."
JOINT_RULE = "Joint optimisation: the hotel whose optimised itinerary has the lowest optimisation score (true cost) among the hotels compared."


class BaselineEntry(BaseModel):
    key: str                      # cheapest_rate | convenience_first | joint
    label: str
    rule: str
    hotel_id: str | None
    hotel_name: str | None = None
    area: str | None = None
    feasible: bool
    status: str
    # separate components (all in the city's local currency, legacy field names end in _jpy)
    accommodation_jpy: int | None = None        # rooms for the nights
    admissions_jpy: int | None = None           # known admissions only
    transport_jpy: int | None = None            # ESTIMATED fares
    known_spend_jpy: int | None = None          # accommodation + admissions + transport: what the trip is expected to cost, excluding unknown prices
    travel_minutes: int | None = None           # ESTIMATED travel time
    travel_time_value_jpy: int | None = None    # travel time x value of time (monetised time, not money spent)
    omitted_optional: list[str] = []            # optional sights left out
    omitted_charge_jpy: int | None = None       # the missed-sight charge inside the score (not money spent)
    unknown_price_items: list[str] = []         # sights whose admission is unknown: excluded from known spend
    objective_estimate_for_unknown_jpy: int | None = None   # what the SOLVER assumed for unknown admissions: inside its objective only, never in any total shown
    score_jpy: int | None = None                # optimisation score = true cost; NOT the traveller's spending
    same_hotel_as: list[str] = []


class Baselines(BaseModel):
    entries: list[BaselineEntry]
    convenience_minutes: dict[str, int]         # hotel id -> total estimated minutes to the target sights
    target_sights: list[str]
    note: str


def target_sights(prefs: Preferences, ds: Dataset) -> list[str]:
    skip = set(prefs.skip)
    musts = [a for a in prefs.must_visit if a in ds.attractions and a not in skip]
    return sorted(musts) if musts else sorted(a for a in ds.attractions if a not in skip)


def convenience_minutes(prefs: Preferences, hotel_ids: list[str], ds: Dataset) -> dict[str, int]:
    targets = target_sights(prefs, ds)
    return {h: sum(ds.minutes[h][a] for a in targets) for h in hotel_ids}


def convenience_hotel(prefs: Preferences, hotel_ids: list[str], ds: Dataset) -> str:
    mins = convenience_minutes(prefs, hotel_ids, ds)
    return min(hotel_ids, key=lambda h: (mins[h], ds.hotels[h].nightly_rate, h))


def _entry(key: str, label: str, rule: str, hotel_id: str | None, byid: dict) -> BaselineEntry:
    if hotel_id is None:
        return BaselineEntry(key=key, label=label, rule=rule, hotel_id=None, feasible=False, status="no feasible hotel")
    r = byid[hotel_id]
    b = r.breakdown
    if not (r.feasible and b):
        return BaselineEntry(key=key, label=label, rule=rule, hotel_id=hotel_id, hotel_name=r.hotel_name, area=r.area, feasible=False, status=r.status)
    return BaselineEntry(
        key=key, label=label, rule=rule, hotel_id=hotel_id, hotel_name=r.hotel_name, area=r.area, feasible=True, status="feasible",
        accommodation_jpy=b.rooms_jpy, admissions_jpy=b.admissions_jpy, transport_jpy=b.transport_jpy, known_spend_jpy=b.rooms_jpy + b.admissions_jpy + b.transport_jpy,
        travel_minutes=b.travel_minutes, travel_time_value_jpy=b.time_cost_jpy, omitted_optional=list(b.missed_preferences.names), omitted_charge_jpy=b.missed_preferences.penalty_jpy,
        unknown_price_items=list(b.unknown_price_items), objective_estimate_for_unknown_jpy=b.optimisation_placeholder_total_jpy, score_jpy=b.true_cost_jpy)


def build_baselines(results: list, cheapest: str, best: str | None, prefs: Preferences, hotel_ids: list[str], ds: Dataset) -> Baselines:
    byid = {r.hotel_id: r for r in results}
    conv = convenience_hotel(prefs, hotel_ids, ds)
    entries = [_entry("cheapest_rate", "A. Cheapest hotel first", CHEAPEST_RULE, cheapest, byid),
               _entry("convenience_first", "B. Convenience-first hotel", CONVENIENCE_RULE, conv, byid),
               _entry("joint", "C. Joint optimisation", JOINT_RULE, best, byid)]
    for e in entries:
        e.same_hotel_as = [o.key for o in entries if o is not e and o.hotel_id is not None and o.hotel_id == e.hotel_id]
    return Baselines(entries=entries, convenience_minutes=convenience_minutes(prefs, hotel_ids, ds), target_sights=target_sights(prefs, ds),
                     note="All three use the same candidate hotels, constraints, estimated travel times and objective: each is the already-solved itinerary of the hotel its rule picks. "
                          "The optimisation score is not money spent. Sample data; made-up hotels; estimated travel times.")
