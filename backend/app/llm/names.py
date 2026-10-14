"""Resolve user-written names to dataset ids. Never guesses.

Resolution = normalised EXACT match against names and aliases only. Anything else is reported:
  * several candidates contain all the words the user wrote (e.g. "the museum") -> ambiguity, with candidates
  * exactly one partial match, or a near spelling (difflib ratio >= NAME_SUGGESTION_RATIO), or a shared first word
    -> unresolved with a "did you mean" suggestion that is NEVER auto-accepted
"""
import difflib
import re
import unicodedata
from dataclasses import dataclass, field

from app import config
from app.data.loader import Dataset


def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    s = re.sub(r"\(.*?\)", " ", s)          # drop "(fictional)" style suffixes
    s = re.sub(r"[^0-9a-z぀-ヿ一-鿿가-힣ᄀ-ᇿ㄰-㆏]+", " ", s).strip()  # Latin, kana, Han and Hangul
    s = re.sub(r"^the\s+", "", s)
    return s


@dataclass
class Suggestion:
    id: str
    name: str
    reason: str


@dataclass
class NameMatch:
    input: str
    status: str  # resolved | ambiguous | unresolved
    id: str | None = None
    name: str | None = None
    matched_as: str | None = None  # "name" | "alias"
    candidates: list[dict] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    from_schedule: bool = False


def _forms(ds: Dataset, ids: list[str]) -> list[tuple[str, str, str]]:
    """(normalised form, id, kind) for every name/alias of the given attraction ids."""
    out = []
    for aid in ids:
        a = ds.attractions[aid]
        out.append((normalise(a.name), aid, "name"))
        out += [(normalise(x), aid, "alias") for x in a.aliases]
    return [f for f in out if f[0]]


def _resolve_in(raw: str, ds: Dataset, ids: list[str]) -> NameMatch:
    norm = normalise(raw)
    m = NameMatch(input=raw, status="unresolved")
    if not norm:
        return m
    forms = _forms(ds, ids)
    exact = {}
    for f, aid, kind in forms:
        if f == norm:
            exact.setdefault(aid, kind)
    if len(exact) == 1:
        aid, kind = next(iter(exact.items()))
        return NameMatch(input=raw, status="resolved", id=aid, name=ds.attractions[aid].name, matched_as=kind)
    if len(exact) > 1:
        m.status, m.candidates = "ambiguous", [{"id": a, "name": ds.attractions[a].name} for a in exact]
        return m
    toks = set(norm.split())
    contain = {}
    for f, aid, _ in forms:
        if toks <= set(f.split()):
            contain.setdefault(aid, f)
    if len(contain) >= 2:
        m.status, m.candidates = "ambiguous", [{"id": a, "name": ds.attractions[a].name} for a in contain]
        return m
    sugg: dict[str, Suggestion] = {}
    for aid in contain:
        sugg[aid] = Suggestion(aid, ds.attractions[aid].name, "partial name match")
    for f, aid, _ in forms:
        if aid not in sugg and difflib.SequenceMatcher(None, norm, f).ratio() >= config.NAME_SUGGESTION_RATIO:
            sugg[aid] = Suggestion(aid, ds.attractions[aid].name, "similar spelling")
    first = norm.split()[0]
    if len(first) >= 4:
        for f, aid, _ in forms:
            if aid not in sugg and f.split()[0] == first:
                sugg[aid] = Suggestion(aid, ds.attractions[aid].name, f"shares the word '{first}' (different place?)")
    m.suggestions = list(sugg.values())
    return m


def resolve_attraction(raw: str, ds: Dataset, scope_ids: list[str] | None = None) -> NameMatch:
    """Resolve against `scope_ids` (e.g. the current schedule) first, then the whole dataset."""
    if scope_ids:
        m = _resolve_in(raw, ds, [a for a in scope_ids if a in ds.attractions])
        if m.status in ("resolved", "ambiguous"):
            m.from_schedule = True
            return m
    return _resolve_in(raw, ds, list(ds.attractions))


def resolve_hotel(raw: str, ds: Dataset) -> NameMatch:
    norm = normalise(raw)
    hits = [h.id for h in ds.hotels.values() if normalise(h.name) == norm]
    if not hits:
        by_area = [h.id for h in ds.hotels.values() if normalise(h.area) == norm]
        hits = by_area if len(by_area) == 1 else []
        if len(by_area) > 1:
            return NameMatch(input=raw, status="ambiguous", candidates=[{"id": h, "name": ds.hotels[h].name} for h in by_area])
    if len(hits) == 1:
        return NameMatch(input=raw, status="resolved", id=hits[0], name=ds.hotels[hits[0]].name, matched_as="name")
    sugg = [Suggestion(h.id, h.name, "similar spelling") for h in ds.hotels.values()
            if difflib.SequenceMatcher(None, norm, normalise(h.name)).ratio() >= config.NAME_SUGGESTION_RATIO]
    return NameMatch(input=raw, status="unresolved", suggestions=sugg)
