"""Pydantic v2 models. Strict: no silent coercion, unknown fields rejected."""
import re
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, model_validator

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SourceStatus = Literal["verified", "estimated", "sample"]
Priority = Literal["must_visit", "nice_to_have", "skip"]
Pace = Literal["relaxed", "balanced", "packed"]

# Rough bounding box around Greater Tokyo. This remains the default so direct
# Attraction/Hotel validation keeps the original Tokyo-only behaviour.
TOKYO_LAT = (35.4, 35.95)
TOKYO_LON = (139.3, 140.0)

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _check_hhmm(v: str) -> str:
    if not _HHMM.match(v):
        raise ValueError(f"'{v}' is not a valid HH:MM time")
    return v


HHMM = Annotated[str, AfterValidator(_check_hhmm)]


def _check_range(v: list[str]) -> list[str]:
    start, end = _check_hhmm(v[0]), _check_hhmm(v[1])
    if to_minutes(end) <= to_minutes(start):
        raise ValueError(f"opening range {start}-{end}: close must be after open")
    return v


TimeRange = Annotated[list[str], Field(min_length=2, max_length=2), AfterValidator(_check_range)]


def _check_ranges(v: list[list[str]]) -> list[list[str]]:
    for prev, cur in zip(v, v[1:]):
        if to_minutes(cur[0]) < to_minutes(prev[1]):
            raise ValueError("opening ranges must be sorted and non-overlapping")
    return v


# list of [open, close] pairs = open; None = closed all day; "unknown" = we do not know.
DayHours = Union[
    Literal["unknown"],
    Annotated[list[TimeRange], Field(min_length=1), AfterValidator(_check_ranges)],
    None,
]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Provenance(_Strict):
    source_status: SourceStatus
    note: str = Field(min_length=1)
    last_checked: str | None = None  # ISO date; None = never checked against a source

    @model_validator(mode="after")
    def _date_format(self):
        if self.last_checked is not None and not _ISO_DATE.match(self.last_checked):
            raise ValueError("last_checked must be YYYY-MM-DD or null")
        return self


VerificationState = Literal["unchecked", "source_checked", "human_verified", "not_applicable"]
CheckedBy = Literal["web-assisted", "human"]


class FieldVerification(_Strict):
    """Per-field-group verification record, SEPARATE from `source_status` (which stays "sample" on every record).
    source_checked = an official page actually states the value (url + date recorded); human_verified = a person confirmed it;
    not_applicable = not a checkable fact (a made-up demo hotel rate, our own visit-duration estimate), with the reason in `note`."""
    state: VerificationState = "unchecked"
    source_url: str | None = None
    checked_on: str | None = None   # ISO date
    checked_by: CheckedBy | None = None
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self):
        if self.checked_on is not None and not _ISO_DATE.match(self.checked_on):
            raise ValueError("checked_on must be YYYY-MM-DD or null")
        if self.state == "source_checked" and not (self.source_url and self.checked_on and self.checked_by):
            raise ValueError("source_checked needs source_url, checked_on and checked_by")
        if self.state == "human_verified":
            if not (self.checked_on and self.checked_by == "human"):
                raise ValueError("human_verified needs checked_on and checked_by 'human'")
        if self.state == "not_applicable" and not self.note:
            raise ValueError("not_applicable needs a note giving the reason")
        return self


def _na(reason: str) -> "FieldVerification":
    return FieldVerification(state="not_applicable", note=reason)


class Verification(_Strict):
    """Checkable field groups of an attraction. Absent block = everything unchecked (visit duration is always not_applicable)."""
    hours: FieldVerification = FieldVerification()           # opening hours AND weekly closing days
    admission: FieldVerification = FieldVerification()
    booking: FieldVerification = FieldVerification()         # advance-booking / timed-entry flag
    coordinates: FieldVerification = FieldVerification()
    name_area: FieldVerification = FieldVerification()
    visit_duration: FieldVerification = _na("Visit durations are the project's own estimates, not a checkable fact.")
    aliases: dict[str, FieldVerification] = {}                # alias spelling -> record; an alias not listed is unchecked


class HotelVerification(_Strict):
    nightly_rate: FieldVerification = _na("Made-up demo hotel: the rate is invented, so there is nothing to check.")


class CoordinateBounds(_Strict):
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


class TransitModel(_Strict):
    detour_factor: float = Field(gt=0)
    speed_kmh: float = Field(gt=0)
    per_leg_overhead_min: int = Field(ge=0)
    base_fare: int = Field(ge=0)
    fare_per_km: float = Field(ge=0)


class CityMeta(_Strict):
    id: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1)
    country: str = Field(min_length=1)
    currency_code: str = Field(min_length=3, max_length=3)
    display_currency_code: str = Field(min_length=3, max_length=3)
    sample_fx_to_display_currency: float = Field(gt=0)
    sample_fx_label: str = Field(min_length=1)
    coordinate_bounds: CoordinateBounds
    transit_model: TransitModel
    default_day_start: HHMM
    default_day_end: HHMM
    default_value_of_time_per_hour: int = Field(ge=0)
    closing_day_conventions_note: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list, max_length=12)          # the city's name in other scripts/spellings (destination check)
    country_aliases: list[str] = Field(default_factory=list, max_length=12)  # the country's name in other scripts/spellings

    @model_validator(mode="after")
    def _checks(self):
        if self.coordinate_bounds.lat_max <= self.coordinate_bounds.lat_min:
            raise ValueError("coordinate_bounds lat_max must be greater than lat_min")
        if self.coordinate_bounds.lon_max <= self.coordinate_bounds.lon_min:
            raise ValueError("coordinate_bounds lon_max must be greater than lon_min")
        return self


def _bbox_from_info(info: ValidationInfo | None) -> CoordinateBounds:
    if info and isinstance(info.context, dict) and isinstance(info.context.get("coordinate_bounds"), CoordinateBounds):
        return info.context["coordinate_bounds"]
    return CoordinateBounds(lat_min=TOKYO_LAT[0], lat_max=TOKYO_LAT[1], lon_min=TOKYO_LON[0], lon_max=TOKYO_LON[1])


def _check_latlon(lat: float, lon: float, info: ValidationInfo | None = None) -> None:
    b = _bbox_from_info(info)
    if not (b.lat_min <= lat <= b.lat_max and b.lon_min <= lon <= b.lon_max):
        raise ValueError(f"coordinates ({lat}, {lon}) are outside the city bounding box")


class Attraction(_Strict):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    area: str
    lat: float
    lon: float
    duration_minutes: int = Field(gt=0)
    opening_hours: dict[Weekday, DayHours]
    admission_cost: int | None = Field(ge=0)  # JPY; None = unknown
    category: str
    priority: Priority
    indoor: bool
    advance_booking_required: bool
    description: str  # UNTRUSTED external text: never put in LLM instructions
    aliases: list[str] = []  # alternative names for exact matching of user text (sample data)
    provenance: Provenance
    hours_provenance: Provenance
    cost_provenance: Provenance
    verification: Verification | None = None   # per-field-group verification; None = everything unchecked

    @model_validator(mode="after")
    def _checks(self, info: ValidationInfo):
        _check_latlon(self.lat, self.lon, info)
        missing = set(WEEKDAYS) - set(self.opening_hours)
        if missing:
            raise ValueError(f"opening_hours missing weekdays: {sorted(missing)}")
        return self


class Hotel(_Strict):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)  # FICTIONAL
    area: str
    lat: float
    lon: float
    nightly_rate: int = Field(gt=0)  # JPY
    provenance: Provenance
    verification: HotelVerification | None = None

    @model_validator(mode="after")
    def _checks(self, info: ValidationInfo):
        _check_latlon(self.lat, self.lon, info)
        return self


class LockedActivity(_Strict):
    attraction_id: str = Field(max_length=64)
    day: int = Field(ge=1, le=7)  # 1-based trip day
    start_time: HHMM


class Preferences(_Strict):
    days: int = Field(ge=1, le=7)
    budget: int | None = Field(default=None, ge=0, le=100_000_000)  # JPY total for attractions + transport; None = no budget
    strict_budget: bool = False
    pace: Pace = "balanced"
    interests: list[Annotated[str, Field(max_length=60)]] = Field(default=[], max_length=20)
    must_visit: list[Annotated[str, Field(max_length=64)]] = Field(default=[], max_length=50)  # attraction ids
    day_start: HHMM = "09:00"
    day_end: HHMM = "19:00"
    value_of_time_per_hour: int = Field(default=1000, ge=0, le=100_000)  # JPY per hour
    max_walking_minutes_per_day: int = Field(default=90, ge=0, le=600)
    start_weekday: int = Field(default=0, ge=0, le=6)  # weekday of day 1: 0=Mon .. 6=Sun
    allow_unknown_hours: bool = False  # may unknown-hours attractions be scheduled (flagged)?
    skip: list[Annotated[str, Field(max_length=64)]] = Field(default=[], max_length=50)  # attraction ids the user is not interested in
    nights: int | None = Field(default=None, ge=0, le=30)  # None = days - 1 (see nights_for)
    max_activities_per_day: int | None = Field(default=None, ge=1, le=8)    # None = the pace preset's cap; set = the user's own hard limit, instead of the preset's
    max_daily_travel_minutes: int | None = Field(default=None, ge=20, le=720)  # None = no limit; ESTIMATED minutes per day including both hotel legs (a hard constraint)
    locked: list["LockedActivity"] = Field(default=[], max_length=12)  # fixed activities

    @model_validator(mode="after")
    def _checks(self):
        if to_minutes(self.day_end) <= to_minutes(self.day_start):
            raise ValueError("day_end must be after day_start")
        if self.strict_budget and self.budget is None:
            raise ValueError("strict_budget requires a budget")
        return self


def nights_for(prefs: "Preferences") -> tuple[int, str]:
    """(nights used for room cost, where the value came from)."""
    if prefs.nights is None:
        return prefs.days - 1, "default (days - 1)"
    return prefs.nights, "user override"


# ---------------------------------------------------------------------------
# Result models (shared by solver, baseline and validator; plain data only)
# ---------------------------------------------------------------------------
class _Plain(BaseModel):
    model_config = ConfigDict(extra="forbid")


MAX_DAYS, MAX_STOPS_PER_DAY = 7, 12
Short = Annotated[str, Field(max_length=64)]


class Stop(_Plain):
    attraction_id: Short
    start: str = Field(max_length=5)  # HH:MM
    end: str = Field(max_length=5)  # HH:MM
    travel_minutes_from_previous: int = Field(ge=0, le=100_000)  # from the hotel for the first stop of a day
    transport_jpy_from_previous: int = Field(ge=0, le=100_000_000)  # ESTIMATED fare for that leg
    cost: int = Field(ge=0, le=100_000_000)  # admission in JPY; 0 when cost_status == "unknown" (excluded from total)
    cost_status: Literal["known", "unknown"]
    is_must_visit: bool
    uncertainty_flags: list[Annotated[str, Field(max_length=40)]] = Field(default=[], max_length=6)


class DayPlan(_Plain):
    day: int = Field(ge=1, le=MAX_DAYS)  # 1-based
    weekday: Weekday
    stops: list[Stop] = Field(max_length=MAX_STOPS_PER_DAY)
    hotel_departure: str | None = Field(default=None, max_length=5)
    hotel_return: str | None = Field(default=None, max_length=5)
    return_travel_minutes: int = Field(default=0, ge=0, le=100_000)
    return_transport_jpy: int = Field(default=0, ge=0, le=100_000_000)


class Totals(_Plain):
    travel_minutes: int = 0  # includes hotel legs
    admissions_jpy: int = 0
    transport_jpy: int = 0
    total_jpy: int = 0  # admissions + transport (accommodation excluded; see Phase 3)
    unknown_cost_items: list[Short] = Field(default=[], max_length=50)  # attraction ids whose price is unknown, excluded from total
    attractions_scheduled: int = 0


class Conflict(_Plain):
    code: str = Field(max_length=64)
    message: str = Field(max_length=1000)
    attraction_ids: list[Short] = Field(default=[], max_length=50)


class Alternative(_Plain):
    kind: str
    message: str
    details: dict = {}


class SolverMeta(_Plain):
    solver: str
    solver_status: str
    runtime_seconds: float
    seed: int
    objective: float | None = None


class SolveResult(_Plain):
    status: Literal["feasible", "infeasible"]
    hotel_id: Short
    days: list[DayPlan] = Field(default=[], max_length=MAX_DAYS)
    totals: Totals = Totals()
    conflicts: list[Conflict] = Field(default=[], max_length=50)
    alternatives: list[Alternative] = Field(default=[], max_length=20)
    notes: list[Annotated[str, Field(max_length=500)]] = Field(default=[], max_length=50)
    missed_preferences: list[Short] = Field(default=[], max_length=50)  # nice-to-have attractions that were visitable but not scheduled
    solver_meta: SolverMeta | None = None
