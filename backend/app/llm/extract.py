"""Natural language -> Preferences DRAFT.

sanitise -> LLM (strict JSON schema, one retry) -> validate -> resolve names against the dataset -> convert currency
in code -> disclosed defaults for low-stakes fields -> Preferences draft. The model can propose; this code decides.
`days` is never defaulted. The model's output schema has no field for allow_unknown_hours, confirm flags, ids,
hotel prices or nights.
"""
from pydantic import ValidationError

from app import config
from app.data.loader import Dataset
from app.llm.client import LLMClient
from app.llm.names import resolve_attraction
from app.llm.prompts import EXTRACT_SYSTEM, PROMPT_VERSION
from app.llm.runner import call_json
from app.llm.sanitize import sanitise_user_text
from app.llm.schemas import (
    Ambiguity, Candidate, ExtractionOut, ParseResult, ResolvedName, SuggestionOut, UnresolvedName,
)
from app.schemas import Preferences

SUPPORTED_CURRENCIES = ("SGD", "JPY")


def to_jpy(amount: float, currency: str) -> int | None:
    """Convert in CODE with the labelled SAMPLE FX rate. None = unsupported currency."""
    cur = currency.strip().upper()
    if cur == "JPY":
        return int(round(amount))
    if cur == "SGD":
        return int(round(amount * config.SAMPLE_FX_JPY_PER_SGD))
    return None


def resolve_list(names: list[str], ds: Dataset, scope_ids: list[str] | None = None):
    resolved, unresolved, ambiguities = [], [], []
    for n in names:
        m = resolve_attraction(n, ds, scope_ids)
        if m.status == "resolved":
            resolved.append(ResolvedName(input=n, id=m.id, name=m.name, matched_as=m.matched_as, from_schedule=m.from_schedule))
        elif m.status == "ambiguous":
            ambiguities.append(Ambiguity(input=n, candidates=[Candidate(**c) for c in m.candidates]))
        else:
            unresolved.append(UnresolvedName(input=n, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions]))
    return resolved, unresolved, ambiguities


def _unavailable(echo: str, calls: int, msg: str) -> ParseResult:  # msg: instruction shown to the user
    return ParseResult(status="llm_unavailable", raw_input_echo=echo, call_count=calls, mode="sample", prompt_version=PROMPT_VERSION,
                       clarifications=[msg])


def extract_preferences(text: str, ds: Dataset, client: LLMClient | None, *, start_weekday: int | None = None,
                        max_input_chars: int | None = None, unavailable_note: str | None = None) -> ParseResult:
    from app.config import get_settings

    limit = max_input_chars or get_settings().max_input_chars
    san = sanitise_user_text(text, limit)  # raises InputTooLong / EmptyInput: rejected, never truncated
    if client is None:
        note = unavailable_note or "The language model is not available (sample mode)."
        return _unavailable(san.text, 0, f"{note} Please fill in the trip form instead.")
    out = call_json(client, EXTRACT_SYSTEM, san.wrapped, ExtractionOut, config.LLM_MAX_TOKENS_EXTRACT,
                    config.LLM_MAX_CALLS_PARSE, "parse")
    if out.unavailable:
        return _unavailable(san.text, out.call_count, "The language model could not be reached. Please fill in the trip form instead.")
    base = dict(raw_input_echo=san.text, call_count=out.call_count, mode="llm", prompt_version=PROMPT_VERSION)
    if out.parsed is None:
        return ParseResult(status="needs_clarification", **base,
                           clarifications=["I could not reliably read that request. Please rephrase it or use the form. "
                                           "The number of days is required."])
    ex: ExtractionOut = out.parsed
    clar: list[str] = []
    defaults: list[str] = []
    assumptions: dict = {"fx": config.FX_LABEL, "fx_jpy_per_sgd": config.SAMPLE_FX_JPY_PER_SGD}

    must, must_unres, must_amb = resolve_list(ex.must_visit_names[:config.LLM_MAX_NAMES], ds)
    skip, skip_unres, skip_amb = resolve_list(ex.skip_names[:config.LLM_MAX_NAMES], ds)
    both = {r.id for r in must} & {r.id for r in skip}
    for aid in sorted(both):
        clar.append(f"{ds.attractions[aid].name} is listed as both must-visit and skip. Which do you want?")
    if must_unres or skip_unres:
        clar.append("Some places are not in this dataset and cannot be scheduled: "
                    + ", ".join(f"'{u.input}'" for u in must_unres + skip_unres) + ".")
    if must_amb or skip_amb:
        clar.append("Some names match more than one place; please pick one: "
                    + "; ".join(f"'{a.input}' could be " + " or ".join(c.name for c in a.candidates) for a in must_amb + skip_amb) + ".")

    budget_jpy = None
    strict = False
    if ex.budget is not None:
        budget_jpy = to_jpy(ex.budget.amount, ex.budget.currency)
        if budget_jpy is None:
            clar.append(f"Currency '{ex.budget.currency[:8]}' is not supported; please give the budget in SGD or JPY.")
        else:
            strict = ex.budget.strict
            assumptions["budget_scope"] = config.BUDGET_SCOPE_TEXT
            assumptions["budget_interpreted"] = (f"{ex.budget.amount:g} {ex.budget.currency.upper()} = {budget_jpy:,} JPY "
                                                 f"({'strict limit' if strict else 'soft target'})")
    else:
        defaults.append("budget: none (no amount was stated)")
    vot = None
    if ex.value_of_time is not None:
        vot = to_jpy(ex.value_of_time.amount, ex.value_of_time.currency)
        if vot is None:
            clar.append(f"Currency '{ex.value_of_time.currency[:8]}' is not supported for value of time.")
        else:
            assumptions["value_of_time_interpreted"] = f"{ex.value_of_time.amount:g} {ex.value_of_time.currency.upper()} per hour = {vot:,} JPY per hour"
    if vot is None and ex.value_of_time is None:
        vot = config.DEFAULT_VALUE_OF_TIME_JPY_PER_HOUR
        defaults.append(f"value of time: {vot:,} JPY/hour (not stated)")
    pace = ex.pace
    if pace is None:
        pace = config.DEFAULT_PACE
        defaults.append(f"pace: {pace} (not stated)")
    day_start, day_end = ex.day_start, ex.day_end
    if day_start is None:
        day_start = config.DEFAULT_DAY_START
        defaults.append(f"day start: {day_start} (not stated)")
    if day_end is None:
        day_end = config.DEFAULT_DAY_END
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
    return ParseResult(status=status, draft=draft, extracted_json=ex.model_dump(), resolved_names=must + skip,
                       unresolved_names=must_unres + skip_unres, ambiguities=must_amb + skip_amb,
                       defaults_applied=defaults, clarifications=clar, unclear=ex.unclear, assumptions=assumptions, **base)
