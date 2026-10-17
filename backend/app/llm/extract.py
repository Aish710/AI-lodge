"""Natural language -> Preferences DRAFT.

sanitise -> LLM (strict JSON schema, one retry) -> validate -> resolve names against the dataset -> convert currency
in code -> disclosed defaults for low-stakes fields -> Preferences draft. The model can propose; this code decides.
`days` is never defaulted. The model's output schema has no field for allow_unknown_hours, confirm flags, ids,
hotel prices or nights.
"""
import re

from pydantic import ValidationError

from app import config
from app.data.loader import Dataset
from app.llm.client import LLMClient
from app.llm.currency import resolve_currency, to_local
from app.llm.destination import analyse, build_index, cross_city_hint
from app.llm.names import resolve_attraction
from app.llm.prompts import PROMPT_VERSION, extract_system
from app.llm.runner import call_json
from app.llm.sanitize import sanitise_user_text
from app.llm.schemas import (
    Ambiguity, Candidate, ExtractionOut, ParseResult, ResolvedName, SuggestionOut, UnresolvedName,
)
from app.schemas import Preferences

from app.llm.currency import SUPPORTED_CODES as SUPPORTED_CURRENCIES  # noqa: E402,F401  (SGD, JPY, KRW, MYR, CNY; plus the city's display currency)


def to_jpy(amount: float, currency: str) -> int | None:
    """Convert in CODE with the labelled SAMPLE FX rate. None = unsupported currency."""
    cur = currency.strip().upper()
    if cur == "JPY":
        return int(round(amount))
    if cur == "SGD":
        return int(round(amount * config.SAMPLE_FX_JPY_PER_SGD))
    return None


def to_city_money(amount: float, currency: str, ds: Dataset) -> int | None:
    """Convert in CODE using the city's labelled SAMPLE FX rate. Returns local integer currency units, or None when the currency is
    ambiguous, unsupported for this city, or has no sample rate (see app/llm/currency.py for the messages)."""
    res = resolve_currency(currency, ds)
    return to_local(amount, res.code, ds) if res.status == "ok" else None


def resolve_money(amount: float, currency: str, ds: Dataset, what: str, assumptions: dict, clar: list, confirmations: list) -> int | None:
    """Like to_city_money, but records WHY it could not convert: an ambiguous symbol becomes a confirmation, anything else a clarification."""
    res = resolve_currency(currency, ds)
    if res.status == "ok":
        if res.assumption:
            assumptions[f"{what}_currency_note"] = res.assumption
        return to_local(amount, res.code, ds)
    if res.status == "confirm":
        confirmations.append({"field": what, "symbol": currency.strip()[:8], "could_mean": list(res.candidates), "city_currency": ds.city.currency_code,
                              "display_currency": ds.city.display_currency_code, "amount": amount, "message": res.message})
    clar.append(res.message)
    return None


def _other_city_message(raw: str, ds: Dataset, all_datasets: dict[str, Dataset] | None) -> str | None:
    if not all_datasets:
        return None
    hint = cross_city_hint(raw, ds, all_datasets)
    return hint["message"] if hint else None


def _singular(word: str) -> str:
    w = word.strip().lower()
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def ambiguous_interests(interests: list[str], ds: Dataset, existing: list[Ambiguity]) -> list[Ambiguity]:
    """A real model often files "I want to see the museum" under `interests` (["museums"]) instead of `must_visit_names`, so no name reaches the
    resolver and the wish is silently lost. Any interest that IS an ambiguous place word (as written or singularised) is reported as an ambiguity
    with choose-one candidates. Nothing is guessed or added to the plan; a unique match or a general interest ("food") is left alone."""
    out: list[Ambiguity] = []
    asked = {frozenset(c.id for c in a.candidates) for a in existing}   # the same question is never asked twice ("the museum" and "museum")
    for raw in interests:
        words = [w for w in re.split(r"[^\w]+", raw.lower()) if len(w) >= 3]     # "bay views" -> "bay"; "history museums" -> "museum"
        for form in dict.fromkeys([raw, _singular(raw), *words, *(_singular(w) for w in words)]):
            m = resolve_attraction(form, ds)
            if m.status == "ambiguous":
                key = frozenset(c["id"] for c in m.candidates)
                if key not in asked:
                    asked.add(key)
                    out.append(Ambiguity(input=raw, candidates=[Candidate(**c) for c in m.candidates]))
                break
    return out


def resolve_list(names: list[str], ds: Dataset, scope_ids: list[str] | None = None, all_datasets: dict[str, Dataset] | None = None):
    resolved, unresolved, ambiguities = [], [], []
    for n in names:
        m = resolve_attraction(n, ds, scope_ids)
        if m.status == "resolved":
            resolved.append(ResolvedName(input=n, id=m.id, name=m.name, matched_as=m.matched_as, from_schedule=m.from_schedule))
        elif m.status == "ambiguous":
            ambiguities.append(Ambiguity(input=n, candidates=[Candidate(**c) for c in m.candidates]))
        else:
            unresolved.append(UnresolvedName(input=n, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions],
                                             message=_other_city_message(n, ds, all_datasets) or "Not a place in this dataset, so it cannot be scheduled."))
    return resolved, unresolved, ambiguities


def _unavailable(echo: str, calls: int, msg: str) -> ParseResult:  # msg: instruction shown to the user
    return ParseResult(status="llm_unavailable", raw_input_echo=echo, call_count=calls, mode="sample", prompt_version=PROMPT_VERSION,
                       clarifications=[msg])


def extract_preferences(text: str, ds: Dataset, client: LLMClient | None, *, start_weekday: int | None = None,
                        max_input_chars: int | None = None, unavailable_note: str | None = None,
                        all_datasets: dict[str, Dataset] | None = None) -> ParseResult:
    from app.config import get_settings

    limit = max_input_chars or get_settings().max_input_chars
    san = sanitise_user_text(text, limit)  # raises InputTooLong / EmptyInput: rejected, never truncated
    if client is None:
        note = unavailable_note or "The language model is not available (sample mode)."
        return _unavailable(san.text, 0, f"{note} Please fill in the trip form instead.")
    all_datasets = all_datasets or {ds.city.id: ds}
    index = build_index(all_datasets)
    city = dict(city_id=ds.city.id, city_name=ds.city.display_name)
    # Destination check in CODE, before the model is asked anything: a request about another city is never planned (and costs no call).
    pre = analyse(san.text, None, ds, all_datasets, index)
    if pre and pre["status"] in ("other_city", "mixed"):
        return ParseResult(status="needs_clarification", raw_input_echo=san.text, call_count=0, mode="llm", prompt_version=PROMPT_VERSION,
                           destination=pre, switch_offer=pre["offer"], clarifications=[pre["message"]], **city)
    out = call_json(client, extract_system(ds), san.wrapped, ExtractionOut, config.LLM_MAX_TOKENS_EXTRACT,
                    config.LLM_MAX_CALLS_PARSE, "parse")
    if out.unavailable:
        return _unavailable(san.text, out.call_count, "The language model could not be reached. Please fill in the trip form instead.")
    base = dict(raw_input_echo=san.text, call_count=out.call_count, mode="llm", prompt_version=PROMPT_VERSION, **city)
    if out.parsed is None:
        return ParseResult(status="needs_clarification", **base,
                           clarifications=["I could not reliably read that request. Please rephrase it or use the form. "
                                           "The number of days is required."])
    ex: ExtractionOut = out.parsed
    # The model's own report of the destination is checked in code too (free text: Bangkok, Gyeongju, an injected string...).
    post = analyse(san.text, ex.destination_mentioned, ds, all_datasets, index)
    if post and post["status"] != "ok":
        return ParseResult(status="needs_clarification", extracted_json=ex.model_dump(), destination=post, switch_offer=post["offer"],
                           clarifications=[post["message"], *(["Some text written by the AI was removed because it looked like internal instructions or a secret. It was not shown."] if out.removed else [])], unclear=ex.unclear, **base)
    clar: list[str] = ["Some text written by the AI was removed because it looked like internal instructions or a secret. It was not shown."] if out.removed else []
    confirmations: list[dict] = []
    defaults: list[str] = []
    assumptions: dict = {"fx": ds.city.sample_fx_label, "currency": ds.city.currency_code,
                         "display_currency": ds.city.display_currency_code,
                         "sample_fx_to_display_currency": ds.city.sample_fx_to_display_currency}

    must, must_unres, must_amb = resolve_list(ex.must_visit_names[:config.LLM_MAX_NAMES], ds, all_datasets=all_datasets)
    skip, skip_unres, skip_amb = resolve_list(ex.skip_names[:config.LLM_MAX_NAMES], ds, all_datasets=all_datasets)
    interest_amb = ambiguous_interests(ex.interests[:config.LLM_MAX_NAMES], ds, must_amb + skip_amb)
    both = {r.id for r in must} & {r.id for r in skip}
    for aid in sorted(both):
        clar.append(f"{ds.attractions[aid].name} is listed as both must-visit and skip. Which do you want?")
    if must_unres or skip_unres:
        clar.append("Some places are not in this dataset and cannot be scheduled: "
                    + ", ".join(f"'{u.input}'" for u in must_unres + skip_unres) + ".")
    if must_amb or skip_amb or interest_amb:
        clar.append("Some names match more than one place; please pick one: "
                    + "; ".join(f"'{a.input}' could be " + " or ".join(c.name for c in a.candidates) for a in must_amb + skip_amb + interest_amb) + ".")

    budget_jpy = None
    strict = False
    if ex.budget is not None:
        budget_jpy = resolve_money(ex.budget.amount, ex.budget.currency, ds, "budget", assumptions, clar, confirmations)
        if budget_jpy is not None:
            strict = ex.budget.strict
            assumptions["budget_scope"] = config.BUDGET_SCOPE_TEXT
            assumptions["budget_interpreted"] = (f"{ex.budget.amount:g} {ex.budget.currency.upper()} = {budget_jpy:,} {ds.city.currency_code} "
                                                 f"({'strict limit' if strict else 'soft target'})")
    else:
        defaults.append("budget: none (no amount was stated)")
    vot = None
    if ex.value_of_time is not None:
        vot = resolve_money(ex.value_of_time.amount, ex.value_of_time.currency, ds, "value_of_time", assumptions, clar, confirmations)
        if vot is not None:
            assumptions["value_of_time_interpreted"] = f"{ex.value_of_time.amount:g} {ex.value_of_time.currency.upper()} per hour = {vot:,} {ds.city.currency_code} per hour"
    if vot is None and ex.value_of_time is None:
        vot = ds.city.default_value_of_time_per_hour
        defaults.append(f"value of time: {vot:,} {ds.city.currency_code}/hour (not stated)")
    pace = ex.pace
    if pace is None:
        pace = config.DEFAULT_PACE
        defaults.append(f"pace: {pace} (not stated)")
    day_start, day_end = ex.day_start, ex.day_end
    if day_start is None:
        day_start = ds.city.default_day_start
        defaults.append(f"day start: {day_start} (not stated)")
    if day_end is None:
        day_end = ds.city.default_day_end
        defaults.append(f"day end: {day_end} (not stated)")
    walking = ex.max_walking_minutes
    if walking is None:
        walking = config.DEFAULT_MAX_WALKING_MINUTES
        defaults.append(f"max walking: {walking} min/day (not stated; not enforced by the optimiser yet)")

    draft = None
    if ex.days is None:
        clar.insert(0, "How many days is the trip? (1-7) This is required and is never assumed.")
    else:
        try:
            kwargs = dict(days=ex.days, budget=budget_jpy, strict_budget=strict and budget_jpy is not None, pace=pace,
                          interests=ex.interests, must_visit=list(dict.fromkeys(r.id for r in must)),
                          skip=list(dict.fromkeys(r.id for r in skip if r.id not in both)),
                          day_start=day_start, day_end=day_end, value_of_time_per_hour=vot if vot is not None else config.DEFAULT_VALUE_OF_TIME_JPY_PER_HOUR,
                          max_walking_minutes_per_day=walking)
            if start_weekday is not None:
                kwargs["start_weekday"] = start_weekday
            kwargs["must_visit"] = [m for m in kwargs["must_visit"] if m not in both]
            draft = Preferences(**kwargs)
        except ValidationError as e:
            clar.append("Some values are out of range: " + "; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()[:6]))
    status = "ok" if (draft is not None and not clar) else "needs_clarification"
    hints = [h for h in (cross_city_hint(u.input, ds, all_datasets) for u in must_unres + skip_unres) if h]
    offers = [h["offer"] for h in hints if h.get("offer")]
    return ParseResult(status=status, draft=draft, extracted_json=ex.model_dump(), resolved_names=must + skip,
                       unresolved_names=must_unres + skip_unres, ambiguities=must_amb + skip_amb + interest_amb,
                       defaults_applied=defaults, clarifications=clar, unclear=ex.unclear, assumptions=assumptions,
                       destination=post, switch_offer=offers[0] if offers and len(offers) == len(hints) and len({o["city_id"] for o in offers}) == 1 else None, currency_confirmations=confirmations,
                       cross_city_hints=hints, **base)
