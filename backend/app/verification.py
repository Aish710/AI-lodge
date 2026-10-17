"""Verification counts, computed from the data (never typed by hand). Used by GET /data/summary and scripts/make_verification_counts.py.

A "field" is one checkable group of an attraction (hours and closing days, admission, advance-booking flag, coordinates, name and area, visit duration), one alias
spelling, or one hotel nightly rate. Absent verification blocks count as "unchecked", except visit durations and hotel rates, which are always "not_applicable"."""
from collections import Counter

from app.schemas import FieldVerification, HotelVerification, Verification

STATES = ("unchecked", "source_checked", "human_verified", "not_applicable")
ATTRACTION_GROUPS = ("hours", "admission", "booking", "coordinates", "name_area", "visit_duration")


def attraction_fields(a) -> list[tuple[str, str, FieldVerification]]:
    """[(field label, value in the app, record)] for one attraction."""
    v = a.verification or Verification()
    out = [(g, "", getattr(v, g)) for g in ATTRACTION_GROUPS]
    out += [(f"alias:{al}", al, v.aliases.get(al, FieldVerification())) for al in a.aliases]
    return out


def hotel_fields(h) -> list[tuple[str, str, FieldVerification]]:
    v = h.verification or HotelVerification()
    return [("nightly_rate", str(h.nightly_rate), v.nightly_rate)]


def count_dataset(ds) -> dict:
    c: Counter = Counter()
    for a in ds.attractions.values():
        c.update(r.state for _, _, r in attraction_fields(a))
    for h in ds.hotels.values():
        c.update(r.state for _, _, r in hotel_fields(h))
    out = {s: c.get(s, 0) for s in STATES}
    out["total_fields"] = sum(out.values())
    return out
