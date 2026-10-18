"""Explanations of computed results.

build_facts() precomputes EVERY figure the explanation may use as display-ready text; the LLM does no arithmetic.
explain() asks the model (at most one call) to describe the facts, then runs the grounding check. On any rejection,
outage or odd output the template text is used instead. Warnings are appended by code, verbatim, never by the model.
"""
import logging
import re
from dataclasses import dataclass, field

from app import config
from app.config import get_settings
from app.data.loader import Dataset
from app.llm.client import LLMClient, LLMUnavailable
from app.llm.claims import unsupported_claims
from app.llm.destination import _generic_tokens
from app.llm.grounding import check_grounding
from app.llm.leakguard import forbidden
from app.llm.names import normalise
from app.llm.prompts import explain_system
from app.llm.runner import _json_object
from app.llm.schemas import CitedSentence, Explanation, FactRef, GroundingReport
from app.money import display_amount, money, signed
from app.optimiser.hotel_compare import HotelComparison
from app.optimiser.replan import ReplanResult

log = logging.getLogger("app.llm")


def _fmt(ds: Dataset):
    """Amount formatters bound to the selected city: its own currency code, never a hardcoded one."""
    return (lambda n: money(n, ds)), (lambda n, unit=None: signed(n, ds, unit)), (lambda n: display_amount(n, ds))


def _hm(minutes: int) -> str:
    h, m = divmod(abs(int(minutes)), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


@dataclass
class ExplainFacts:
    kind: str
    lines: list[str]
    attraction_ids: set[str]
    hotel_ids: set[str]
    warnings: list[str]
    template: str
    values: list = field(default_factory=list)
    roles: list = field(default_factory=list)       # (Decimal amount, frozenset of words one of which a sentence must use with it, what it is)

    def numbered(self) -> list[tuple[str, str]]:
        """Stable ids F1, F2, ... in the order of the facts."""
        return [(f"F{i}", line) for i, line in enumerate(self.lines, start=1)]

    def prompt_block(self) -> str:
        return "<facts>\n" + "\n".join(f"{fid}: {line}" for fid, line in self.numbered()) + "\n</facts>"

    def allowed_text(self) -> str:
        return "\n".join(self.lines + [self.template] + self.warnings)


@dataclass
class OptimiseView:
    """A computed /optimise outcome (plan + validator report) to be explained."""
    result: object        # SolveResult
    report: object        # FeasibilityReport
    hotel_id: str
    approximate: bool
    nights: int


ROOM_WORDS = frozenset({"room", "rooms", "accommodation", "lodging", "hotel", "stay"})
CASH_WORDS = frozenset({"spending", "cash", "modelled", "modeled", "altogether", "overall"})
SIGHT_WORDS = frozenset({"sights", "admissions", "attractions", "transport", "fares", "tickets"})


def _cash_facts(v: "OptimiseView", ds: Dataset, _jpy) -> tuple[list[str], list]:
    """Rooms and the modelled cash total as FACTS (computed by code from the schedule and the hotel's sample rate), each with the words that make a sentence about it meaningful.
    A correct number used for the wrong thing (the cash total called the room cost) is then rejected, not just a number that is absent."""
    from decimal import Decimal

    from app.optimiser.cost_summary import summarise_costs
    cs = summarise_costs(v.result, ds, v.hotel_id, v.nights)
    if cs is None:
        return [], []
    t = cs["trip"]
    unknown = t["unknown_price_count"]
    lines = [f"Rooms: {_jpy(t['rooms'])} ({_jpy(t['nightly_rate'])} x {t['nights']} nights; demo hotel at its sample rate, not a quote)",
             f"Modelled cash total including rooms: {_jpy(t['cash_total_with_rooms'])} (sights and transport {_jpy(t['cash_total'])} + rooms {_jpy(t['rooms'])}); "
             + (f"{unknown} admission price(s) are unknown and are excluded, not free" if unknown else "every admission price is known")]
    roles = [(Decimal(t["rooms"]), ROOM_WORDS, "the rooms cost"), (Decimal(t["cash_total_with_rooms"]), CASH_WORDS, "the modelled total spending including rooms"),
             (Decimal(t["cash_total"]), SIGHT_WORDS, "the cost of sights and transport")]
    return lines, roles


def _optimise_facts(v: OptimiseView, ds: Dataset) -> ExplainFacts:
    _jpy, _signed, _sgd = _fmt(ds)
    r, rep = v.result, v.report
    h = ds.hotels[v.hotel_id]
    lines = ["Kind: single-hotel itinerary", f"Hotel: {h.name}, rate {_jpy(h.nightly_rate)} per night, nights used {v.nights}",
             f"Outcome: {r.status}", f"Validator verdict: {rep.overall.replace('_', ' ')}" + (" (approximate: solver not proven optimal)" if v.approximate else "")]
    ids: set[str] = set()
    roles: list = []
    if r.status == "feasible":
        t = r.totals
        lines += [f"Totals: admissions {_jpy(t.admissions_jpy)}, estimated transport {_jpy(t.transport_jpy)}, total {_jpy(t.total_jpy)} ({_sgd(t.total_jpy)}), travel {t.travel_minutes} min ({_hm(t.travel_minutes)})",
                  f"Activities scheduled: {t.attractions_scheduled} over {len(r.days)} days"]
        for d in r.days:
            if d.stops:
                lines.append(f"Day {d.day}: " + ", ".join(f"{ds.attractions[s.attraction_id].name} at {s.start}" for s in d.stops))
                ids |= {s.attraction_id for s in d.stops}
        cash_lines, roles = _cash_facts(v, ds, _jpy)
        lines += cash_lines
        template = (f"Plan for {h.name}: {t.attractions_scheduled} activities over {len(r.days)} days; admissions {_jpy(t.admissions_jpy)} plus estimated transport "
                    f"{_jpy(t.transport_jpy)} (total {_jpy(t.total_jpy)}); travel {t.travel_minutes} min. Validator verdict: {rep.overall.replace('_', ' ')}.")
    else:
        lines += [f"Conflict: {c.message}" for c in r.conflicts] + [f"Alternative: {a.message}" for a in r.alternatives]
        ids |= {a for c in r.conflicts for a in c.attraction_ids}
        template = "No feasible plan: " + " ".join(c.message for c in r.conflicts)
    warnings = list(rep.data_quality_warnings) if r.status == "feasible" else [c.message for c in r.conflicts]
    return ExplainFacts("optimise", lines, ids, {v.hotel_id}, warnings, template, roles=roles if r.status == "feasible" else [])


def build_facts(result, ds: Dataset) -> ExplainFacts:
    if isinstance(result, OptimiseView):
        return _optimise_facts(result, ds)
    if isinstance(result, ReplanResult):
        return _replan_facts(result, ds)
    if isinstance(result, HotelComparison):
        return _compare_facts(result, ds)
    raise TypeError("unsupported result type")


def _replan_facts(r: ReplanResult, ds: Dataset) -> ExplainFacts:
    _jpy, _signed, _sgd = _fmt(ds)
    lines = ["Kind: replanning result", "Operations requested: " + ("; ".join(r.operations_applied) or "none"),
             f"Outcome: {r.status}", f"Solver status: {r.solver_status}" + (" (approximate)" if r.approximate else "")]
    ids: set[str] = set()
    hotels = {r.previous_hotel_id, r.hotel_id}
    warnings: list[str] = []
    if r.status == "applied" and r.diff:
        d = r.diff
        lines += [
            f"True cost: {_jpy(d.true_cost_jpy.before)} before, {_jpy(d.true_cost_jpy.after)} after, change {_signed(d.true_cost_jpy.delta)} ({_sgd(d.true_cost_jpy.after)})",
            f"Travel time: {d.travel_minutes.before} min ({_hm(d.travel_minutes.before)}) before, {d.travel_minutes.after} min ({_hm(d.travel_minutes.after)}) after, change {_signed(d.travel_minutes.delta, 'min')}",
            f"Admissions: {_jpy(d.admissions_jpy.before)} before, {_jpy(d.admissions_jpy.after)} after",
            f"Transport: {_jpy(d.transport_jpy.before)} before, {_jpy(d.transport_jpy.after)} after",
        ]
        if r.previous_hotel_id != r.hotel_id:
            lines.append(f"Rooms: {_jpy(d.rooms_jpy.before)} before, {_jpy(d.rooms_jpy.after)} after, change {_signed(d.rooms_jpy.delta)}; hotel changed from "
                         f"{ds.hotels[r.previous_hotel_id].name} to {ds.hotels[r.hotel_id].name}; nights used {r.nights_used}")
        lines.append(f"Activities: {len(d.kept)} kept, {len(d.moved)} moved, {len(d.removed)} removed, {len(d.added)} added")
        for m in d.moved:
            ids.add(m.attraction_id)
            lines.append(f"Moved: {m.name} from day {m.from_day} {m.from_start} to day {m.to_day} {m.to_start} ({m.reason})")
        for x in d.removed:
            ids.add(x.attraction_id)
            lines.append(f"Removed: {x.name} ({x.reason.replace('_', ' ')})")
        for a in d.added:
            ids.add(a.attraction_id)
            lines.append(f"Added: {a.name} on day {a.day} at {a.start}")
        lines.append(f"Unnecessarily moved activities: {d.disruption_count}, weighted at {_jpy(d.disruption_jpy_per_move)} each")
        if d.newly_missed:
            lines.append("Newly missed: " + ", ".join(d.newly_missed))
        if d.no_longer_missed:
            lines.append("No longer missed: " + ", ".join(d.no_longer_missed))
        ids |= {k.attraction_id for k in d.kept}
        warnings = list(d.warnings)
    else:
        lines += ["The original plan is unchanged."] + [f"Conflict: {c.message}" for c in r.conflicts]
        ids |= {a for c in r.conflicts for a in c.attraction_ids}
        warnings = [c.message for c in r.conflicts]
    if r.feasibility_report:
        warnings += [w for w in r.feasibility_report.data_quality_warnings if w not in warnings]
    template = r.summary.split(" Warnings: ")[0]  # warnings are appended once, by code, in _finish()
    return ExplainFacts("replan", lines, ids, hotels, warnings, template)


def _compare_facts(c: HotelComparison, ds: Dataset) -> ExplainFacts:
    _jpy, _signed, _sgd = _fmt(ds)
    lines = ["Kind: hotel comparison", f"Nights used for rooms: {c.nights_used} ({c.nights_source})",
             f"Value of time: {_jpy(c.value_of_time_per_hour)} per hour"]
    ids: set[str] = set()
    hotels = {r.hotel_id for r in c.results}
    for r in c.results:
        if r.breakdown:
            b = r.breakdown
            lines.append(f"{r.hotel_name}: rate {_jpy(b.nightly_rate_jpy)} per night; rooms {_jpy(b.rooms_jpy)}; admissions {_jpy(b.admissions_jpy)}; "
                         f"transport {_jpy(b.transport_jpy)}; travel {b.travel_minutes} min ({_hm(b.travel_minutes)}); time cost {_jpy(b.time_cost_jpy)}; "
                         f"missed preferences {b.missed_preferences.count}; true cost {_jpy(b.true_cost_jpy)} ({_sgd(b.true_cost_jpy)})")
        else:
            lines.append(f"{r.hotel_name}: no plan ({r.status})")
    for rk in c.ranking:
        lines.append(f"Rank {rk.rank}: {ds.hotels[rk.hotel_id].name}, gap to winner {_jpy(rk.gap_to_winner_jpy)} and {rk.gap_to_winner_travel_hours:+.2f} hours of travel")
    lines.append(f"Cheapest by nightly rate: {ds.hotels[c.cheapest_by_rate].name}")
    lines.append("Best by true cost: " + (ds.hotels[c.best_by_true_cost].name if c.best_by_true_cost else "none"))
    lines.append("Rate winner differs from true-cost winner: " + ("yes" if c.rate_winner_differs_from_true_winner else "no"))
    if c.sensitivity:
        lines.append("Value-of-time sensitivity: " + c.sensitivity.flip_summary + (" (approximate)" if c.sensitivity.approximate else ""))
    warnings = list(c.warnings)
    for r in c.results:
        if r.itinerary:
            ids |= {s.attraction_id for d in r.itinerary.days for s in d.stops}
        if r.breakdown:
            ids |= set(r.breakdown.missed_preferences.attraction_ids)
    tmpl = c.insight + " Ranking by true cost: " + "; ".join(f"{rk.rank}. {ds.hotels[rk.hotel_id].name} {_jpy(rk.true_cost_jpy)}" for rk in c.ranking) + "."
    return ExplainFacts("compare", lines, ids, hotels, warnings, tmpl)


def _forms(ds: Dataset, facts_text: str, all_datasets: dict[str, Dataset] | None = None):
    """allowed = every name/alias of each place whose name or alias already appears in the facts text.
    every = all place forms of the selected city AND of every other city (so a Seoul sight in a Tokyo explanation is rejected).
    Single words that name several different places across cities ('gardens', 'museum', 'tower') are not treated as names of another
    city: they are ordinary words, and the full names (which are what an invented place would use) are still rejected."""
    ntext = normalise(facts_text)

    def present(form: str) -> bool:
        return bool(form) and re.search(r"(?<![0-9a-z])" + re.escape(form) + r"(?![0-9a-z])", ntext) is not None

    allowed: set[str] = set()
    every: dict[str, str] = {}
    for a in ds.attractions.values():
        forms = [normalise(n) for n in [a.name] + list(a.aliases)]
        for f in forms:
            if f:
                every[f] = a.name
        if any(present(f) for f in forms):
            allowed |= {f for f in forms if f}
    for h in ds.hotels.values():
        f = normalise(h.name)
        every[f] = h.name
        if present(f):
            allowed.add(f)
    if all_datasets:
        generic = _generic_tokens(all_datasets)
        for cid, other in all_datasets.items():
            if other is ds or cid == ds.city.id:
                continue
            for a in other.attractions.values():
                for n in [a.name] + list(a.aliases):
                    f = normalise(n)
                    if f and f not in every and (len(f.split()) > 1 or (len(f) >= 6 and f not in generic) or re.search(r"[぀-ヿ一-鿿가-힣]", f)):
                        every[f] = a.name
            for h in other.hotels.values():
                f = normalise(h.name)
                if f and f not in every:
                    every[f] = h.name
    return allowed, every


def _finish(body: str, warnings: list[str], ds: Dataset | None = None) -> str:
    """The city is always stated, by code (not by the model): 'Destination: Seoul, South Korea.', after the body and before the warnings.
    Warnings are appended once, by code, last."""
    city = f"\n\nDestination: {ds.city.display_name}, {ds.city.country}." if ds is not None else ""
    return body + city + ("\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings) if warnings else "")


def _cited_json(text: str):
    """The model's sentences as a list of dicts, or None if the reply is not the cited format ({"sentences": [{"text", "fact_ids"}]})."""
    try:
        obj = _json_object(text)
    except (ValueError, TypeError):
        return None
    s = obj.get("sentences") if isinstance(obj, dict) else None
    if not isinstance(s, list) or not s or not all(isinstance(x, dict) for x in s):
        return None
    return s


def role_mismatch(text: str, facts: ExplainFacts) -> str | None:
    """A number that equals one of the money facts must be used with a word that says what it is. Returns the first offending amount, or None. Pure and deterministic.
    "Rooms cost 495" is wrong even though 495 is a real figure: it is the modelled TOTAL including rooms."""
    from decimal import Decimal

    from app.llm.grounding import extract_tokens
    if not facts.roles:
        return None
    words = set(re.findall(r"[a-z]+", text.lower()))
    present = {v for _, k, v in extract_tokens(text).raw if k == "num"}
    for amount, need, what in facts.roles:
        if Decimal(amount) in present and not (words & need):
            # the same figure may legitimately be another fact's amount (equal values): accept if ANY role that owns it is satisfied
            if not any(Decimal(a) == Decimal(amount) and (words & n) for a, n, _ in facts.roles):
                return f"{amount} is {what}"
    return None


def _cited_explanation(raw: list, facts: ExplainFacts, ds: Dataset, all_datasets, tmpl: Explanation) -> Explanation:
    """Validate each sentence on its own. A sentence is dropped unless: it cites at least one fact id, every id exists, every number and time in it is in the CITED facts,
    every place and hotel name in it is in the facts, it holds no leak and no claim the data cannot support. Fewer than 2 surviving sentences -> the template.
    Warnings are appended by code, verbatim, as for every explanation."""
    ids = dict(facts.numbered())
    allowed_forms, every = _forms(ds, facts.allowed_text(), all_datasets)
    secret = get_settings().llm_api_key
    system = explain_system(ds)
    kept: list[CitedSentence] = []
    rejected: list[str] = []
    checked = 0
    for n, s in enumerate(raw[:10], start=1):
        text = str(s.get("text", "")).strip()
        fids = s.get("fact_ids")
        why = None
        if not text:
            why = "empty"
        elif not isinstance(fids, list) or not fids:
            why = "uncited"
        elif any(not isinstance(f, str) or f not in ids for f in fids):
            why = "unknown fact id"
        else:
            g = check_grounding(text, "\n".join(ids[f] for f in dict.fromkeys(fids)), facts.values, allowed_forms, every)
            checked += g.checked
            if not g.ok:
                why = "not supported by the cited facts (" + ", ".join(g.rejected_tokens[:3]) + ")"
            elif (wrong := role_mismatch(text, facts)):
                why = f"a number used for the wrong item ({wrong})"
            elif forbidden(text, system, secret, phones=False):
                why = "internal text"
            elif unsupported_claims(text, facts.allowed_text()):
                why = "claim the data cannot support"
        if why:
            rejected.append(f"S{n}: {why}")
        else:
            kept.append(CitedSentence(text=text, fact_ids=list(dict.fromkeys(fids))))
    dropped = len(raw[:10]) - len(kept)
    body = " ".join(k.text for k in kept)
    if len(kept) < 2 or len(body.split()) > config.EXPLAIN_MAX_WORDS:
        tmpl.reason = f"fewer than 2 cited sentences passed the checks ({dropped} dropped); template used" if len(kept) < 2 else "model output too long; template used"
        tmpl.grounding = GroundingReport(checked=checked, rejected_tokens=rejected[:8])
        tmpl.dropped = dropped
        return tmpl
    used = list(dict.fromkeys(f for k in kept for f in k.fact_ids))
    return Explanation(text=_finish(body, facts.warnings, ds), source="llm", cited=True, sentences=kept, facts=[FactRef(id=f, text=ids[f]) for f in used],
                       dropped=dropped, grounding=GroundingReport(checked=checked, rejected_tokens=rejected[:8]), warnings=facts.warnings, call_count=1)


def explain(result, ds: Dataset, client: LLMClient | None, sample_reason: str | None = None,
            all_datasets: dict[str, Dataset] | None = None) -> Explanation:
    facts = build_facts(result, ds)
    tmpl = Explanation(text=_finish(facts.template, facts.warnings, ds), source="template", warnings=facts.warnings)
    if client is None:
        tmpl.reason = sample_reason or "sample mode: no language model configured"
        return tmpl
    try:
        resp = client.complete(explain_system(ds), [{"role": "user", "content": facts.prompt_block()}], config.LLM_MAX_TOKENS_EXPLAIN)
    except LLMUnavailable as e:
        tmpl.call_count = 0
        tmpl.reason = f"language model unavailable ({e.category})"
        log.info("llm_call", extra={"op": "explain", "outcome": f"unavailable:{e.category}", "calls": 0})
        return tmpl
    tmpl.call_count = 1
    text = resp.text.strip()
    parsed = _cited_json(text)
    if parsed is not None:        # the model followed the cited format: every sentence is validated on its own
        log.info("llm_call", extra={"op": "explain", "outcome": "cited", "calls": 1, "in_tokens": resp.input_tokens, "out_tokens": resp.output_tokens, "latency": resp.latency_seconds})
        return _cited_explanation(parsed, facts, ds, all_datasets, tmpl)
    if text.lstrip().startswith(("{", "```")):
        tmpl.reason = "model reply was JSON but not in the cited format; template used"
        tmpl.grounding = GroundingReport(checked=0, rejected_tokens=["format"])
        log.info("llm_call", extra={"op": "explain", "outcome": "rejected_format", "calls": 1})
        return tmpl
    if not text or len(text.split()) > config.EXPLAIN_MAX_WORDS:
        tmpl.reason = "model output empty or too long"
        tmpl.grounding = GroundingReport(checked=0, rejected_tokens=["length"])
        log.info("llm_call", extra={"op": "explain", "outcome": "rejected_length", "calls": 1})
        return tmpl
    allowed, every = _forms(ds, facts.allowed_text(), all_datasets)
    g = check_grounding(text, facts.allowed_text(), facts.values, allowed, every)
    log.info("llm_call", extra={"op": "explain", "outcome": "grounded" if g.ok else "rejected_grounding", "calls": 1,
                                "in_tokens": resp.input_tokens, "out_tokens": resp.output_tokens, "latency": resp.latency_seconds})
    if not g.ok:
        tmpl.grounding = GroundingReport(checked=g.checked, rejected_tokens=g.rejected_tokens)
        tmpl.reason = "grounding check failed; template used"
        return tmpl
    if forbidden(text, explain_system(ds), get_settings().llm_api_key, phones=False):   # grounding checks numbers and names only; this stops a quoted prompt or a secret
        tmpl.reason = "model text contained internal instructions or a secret; template used"
        tmpl.grounding = GroundingReport(checked=g.checked, rejected_tokens=["internal text"])
        log.info("llm_call", extra={"op": "explain", "outcome": "rejected_leak", "calls": 1})
        return tmpl
    claims = unsupported_claims(text, facts.allowed_text())     # words about access, quiet, safety, children, diet, weather or queues: the app has no data for them
    if claims:
        tmpl.reason = "model text made a claim the data cannot support (" + ", ".join(sorted({g for g, _ in claims})) + "); template used"
        tmpl.grounding = GroundingReport(checked=g.checked, rejected_tokens=[f"claim:{t}" for _, t in claims][:8])
        log.info("llm_call", extra={"op": "explain", "outcome": "rejected_unsupported_claim", "calls": 1})
        return tmpl
    return Explanation(text=_finish(text, facts.warnings, ds), source="llm", grounding=GroundingReport(checked=g.checked),
                       warnings=facts.warnings, call_count=1)
