"""Destination check, in CODE (never by the model): which city is the user talking about?

An index of ALL cities (names, countries and aliases in English and native script) plus every attraction and hotel name or alias is scanned
against the user's text, and against the model's optional `destination_mentioned`. A request that points at a DIFFERENT city than the
selected one is never planned: the result offers a "switch to <city>" choice and the client decides. An unknown place (e.g. "Bangkok")
gets a plain "not available yet" answer listing the available cities. Nothing here ever switches the city or schedules another city's place."""
import re
from dataclasses import dataclass, field

from app.data.loader import Dataset
from app.llm.names import normalise

_MAX_ECHO = 60


@dataclass(frozen=True)
class Entry:
    form: str        # normalised
    kind: str        # city | country | attraction | hotel | area
    city_id: str
    label: str       # display text for messages


@dataclass
class Mentions:
    cities: dict = field(default_factory=dict)  # city_id -> list of evidence labels

    def add(self, e: Entry):
        self.cities.setdefault(e.city_id, [])
        if e.label not in self.cities[e.city_id]:
            self.cities[e.city_id].append(e.label)


def _generic_tokens(all_datasets: dict[str, Dataset]) -> set[str]:
    """Single words shared by two or more different places' names across all cities ('gardens', 'museum', 'tower', 'market', 'lantern')."""
    owners: dict[str, set] = {}
    for cid, ds in all_datasets.items():
        for a in ds.attractions.values():
            for n in [a.name, *a.aliases]:
                for t in set(normalise(n).split()):
                    owners.setdefault(t, set()).add((cid, a.id))
        for h in ds.hotels.values():
            for t in set(normalise(h.name).split()):
                owners.setdefault(t, set()).add((cid, h.id))
    return {t for t, o in owners.items() if len(o) >= 2}


def build_index(all_datasets: dict[str, Dataset]) -> list[Entry]:
    generic = _generic_tokens(all_datasets)
    out: list[Entry] = []

    def add(form_raw: str, kind: str, cid: str, label: str, single_ok: bool = True):
        f = normalise(form_raw)
        if not f:
            return
        toks = f.split()
        cjk = bool(re.search(r"[぀-ヿ一-鿿가-힣]", f))
        if len(toks) == 1 and not cjk and not single_ok:
            return
        out.append(Entry(f, kind, cid, label))

    for cid, ds in all_datasets.items():
        c = ds.city
        for n in [c.display_name, *c.aliases]:
            add(n, "city", cid, c.display_name)
        for n in [c.country, *c.country_aliases]:
            add(n, "country", cid, c.country)
        for a in ds.attractions.values():
            for i, n in enumerate([a.name, *a.aliases]):
                f = normalise(n)
                specific = len(f.split()) > 1 or (len(f) >= 6 and f not in generic)
                add(n, "attraction", cid, a.name, single_ok=specific)
            add(a.area, "area", cid, a.area, single_ok=normalise(a.area) not in generic and len(normalise(a.area)) >= 5)
        for h in ds.hotels.values():
            add(h.name, "hotel", cid, h.name)
            add(h.area, "area", cid, h.area, single_ok=normalise(h.area) not in generic and len(normalise(h.area)) >= 5)
    return out


def _present(form: str, ntext: str) -> bool:
    return re.search(r"(?<![0-9a-z])" + re.escape(form) + r"(?![0-9a-z])", ntext) is not None


def scan_text(text: str, index: list[Entry], kinds=("city", "country", "attraction", "hotel")) -> Mentions:
    """Which cities does this text point at? An entry also present for the selected city is the selected city's, handled by the caller."""
    ntext = normalise(text)
    m = Mentions()
    for e in index:
        if e.kind in kinds and _present(e.form, ntext):
            m.add(e)
    return m


def resolve_destination(label: str, index: list[Entry]) -> Mentions:
    """Resolve the model's free-text `destination_mentioned` to cities. Areas count here (a model may say 'Shibuya')."""
    return scan_text(label, index, kinds=("city", "country", "attraction", "hotel", "area"))


def _short(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:_MAX_ECHO] + ("..." if len(s) > _MAX_ECHO else "")


def available_cities(all_datasets: dict[str, Dataset]) -> str:
    return ", ".join(f"{d.city.display_name} ({d.city.country})" for d in all_datasets.values())


def analyse(text: str, destination_mentioned: str | None, ds: Dataset, all_datasets: dict[str, Dataset], index: list[Entry] | None = None) -> dict:
    """Returns a plain dict that becomes `ParseResult.destination`:
       {status: ok|other_city|mixed|unsupported, mentioned: [...], offer: {city_id, display_name, country}|None, message}"""
    index = index or build_index(all_datasets)
    sel = ds.city.id
    found = scan_text(text, index)
    # a form that exists for the selected city is the selected city's (e.g. "Seoul Tower" never means leaving Seoul)
    sel_forms = {e.form for e in index if e.city_id == sel}
    ntext = normalise(text)
    sel_hit = any(_present(f, ntext) for f in sel_forms if f)
    others = {cid: ev for cid, ev in found.cities.items() if cid != sel}
    # drop other-city evidence that is only a form shared with the selected city
    others = {cid: [lab for lab in ev if not any(e.label == lab and e.form in sel_forms for e in index)] or [] for cid, ev in others.items()}
    others = {cid: ev for cid, ev in others.items() if ev}
    dest_cities: dict = {}
    dest_unknown = None
    if destination_mentioned:
        d = resolve_destination(destination_mentioned, index)
        dest_cities = d.cities
        if not d.cities:
            dest_unknown = _short(destination_mentioned)
        for cid, ev in d.cities.items():
            if cid != sel:
                others.setdefault(cid, ev)
    if dest_unknown and not sel_hit and not found.cities:
        return {"status": "unsupported", "mentioned": [], "offer": None, "unsupported_place": dest_unknown,
                "message": f"'{dest_unknown}' is not available yet. Available cities: {available_cities(all_datasets)}."}
    if others:
        names = [all_datasets[cid].city.display_name for cid in others]
        first = next(iter(others))
        offer = {"city_id": first, "display_name": all_datasets[first].city.display_name, "country": all_datasets[first].city.country}
        mixed = sel_hit or (sel in found.cities) or (sel in dest_cities)
        evidence = "; ".join(f"you mentioned {', '.join(ev[:3])}" if len(others) == 1 else f"{all_datasets[cid].city.display_name}: {', '.join(ev[:3])}"
                             for cid, ev in others.items())
        if mixed:
            msg = (f"Your request mentions {ds.city.display_name} and also {', '.join(names)} ({evidence}). One trip covers one city. "
                   f"Plan {ds.city.display_name} here, or switch city to plan {names[0]}.")
            status = "mixed"
        else:
            msg = (f"This looks like a request for {', '.join(names)} ({evidence}), but {ds.city.display_name} is selected. "
                   f"Nothing was planned. Switch city to plan {names[0]}.")
            status = "other_city"
        return {"status": status, "mentioned": sorted(others), "offer": offer, "message": msg}
    return {"status": "ok", "mentioned": [sel] if (sel_hit or sel in found.cities) else [], "offer": None, "message": ""}


def cross_city_hint(raw_name: str, ds: Dataset, all_datasets: dict[str, Dataset]) -> dict | None:
    """For a name the selected city could not resolve: which OTHER cities have a place that matches it exactly or by shared words?
    One city -> a switch offer; several -> 'exists in N cities' (ask, never guess)."""
    n = normalise(raw_name)
    if not n:
        return None
    toks = set(n.split())
    hits: dict[str, list[str]] = {}
    for cid, other in all_datasets.items():
        if cid == ds.city.id:
            continue
        for a in other.attractions.values():
            forms = [normalise(x) for x in [a.name, *a.aliases]]
            if any(f == n or (toks and toks <= set(f.split())) for f in forms):
                hits.setdefault(cid, []).append(a.name)
        for h in other.hotels.values():
            f = normalise(h.name)
            if f == n or (toks and toks <= set(f.split())):
                hits.setdefault(cid, []).append(h.name)
    if not hits:
        return None
    cities = [all_datasets[c].city.display_name for c in hits]
    sample = "; ".join(f"{all_datasets[c].city.display_name}: {', '.join(v[:2])}" for c, v in hits.items())
    if len(hits) == 1:
        cid = next(iter(hits))
        return {"cities": [cid], "message": f"'{_short(raw_name)}' is not in the {ds.city.display_name} data. It matches {sample}. Switch city to plan it.",
                "offer": {"city_id": cid, "display_name": all_datasets[cid].city.display_name, "country": all_datasets[cid].city.country}}
    return {"cities": list(hits), "offer": None,
            "message": f"'{_short(raw_name)}' is not in the {ds.city.display_name} data, and it matches places in several other cities ({sample}). Tell me which city you mean."}
