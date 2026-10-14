"""Natural-language replanning: text -> PROPOSED operations (nothing is executed).

The model names attractions as the user said them and uses a day-part word instead of clock times. Code resolves
names (current schedule first, then the dataset), maps day parts to times from config, and builds the same typed
operations as POST /replan. The model's schema has no confirm_remove_must_visit field; removing a must-visit is
only ever FLAGGED (requires_confirmation) and the human must confirm it.
"""
from app import config
from app.config import get_settings
from app.data.loader import Dataset
from app.llm.client import LLMClient
from app.llm.destination import analyse, build_index, cross_city_hint
from app.llm.extract import resolve_money
from app.llm.names import resolve_attraction, resolve_hotel
from app.llm.prompts import PROMPT_VERSION, parse_replan_system
from app.llm.runner import call_json
from app.llm.sanitize import sanitise_user_text
from app.llm.schemas import (
    Ambiguity, Candidate, ProposedOperations, ReplanOut, ResolvedName, SuggestionOut, UnresolvedName,
)
from app.optimiser.replan import ChangeBudgetOp, LockOp, MoveOp, RemoveOp, SwitchHotelOp, UnlockOp
from app.schemas import Preferences, SolveResult


def _positions(res: SolveResult) -> dict[str, tuple[int, str]]:
    return {s.attraction_id: (d.day, s.start) for d in res.days for s in d.stops}


def _itinerary_block(res: SolveResult, ds: Dataset) -> str:
    """Names only (no descriptions): day by day, then wrapped as data."""
    lines = [f"Day {d.day}: " + ", ".join(ds.attractions[s.attraction_id].name for s in d.stops) for d in res.days if d.stops]
    return "<current_itinerary>\n" + "\n".join(lines) + "\n</current_itinerary>"


def parse_replan(text: str, current: SolveResult, prefs: Preferences, ds: Dataset, client: LLMClient | None,
                 *, max_input_chars: int | None = None, unavailable_note: str | None = None,
                 all_datasets: dict[str, Dataset] | None = None) -> ProposedOperations:
    san = sanitise_user_text(text, max_input_chars or get_settings().max_input_chars)
    base = dict(raw_input_echo=san.text, prompt_version=PROMPT_VERSION, city_id=ds.city.id, city_name=ds.city.display_name)
    all_datasets = all_datasets or {ds.city.id: ds}
    if client is None:
        return ProposedOperations(status="llm_unavailable", mode="sample", **base,
                                  clarifications=[f"{unavailable_note or 'The language model is not available (sample mode).'} Use the re-optimise controls instead."])
    # Destination check in CODE before the model is asked anything: a request about another city is never turned into operations.
    pre = analyse(san.text, None, ds, all_datasets, build_index(all_datasets))
    if pre["status"] in ("other_city", "mixed"):
        return ProposedOperations(status="needs_clarification", mode="llm", call_count=0, **base, destination=pre, switch_offer=pre["offer"],
                                  clarifications=[pre["message"] + " Switching city starts a new trip: the current plan is not carried over."])
    out = call_json(client, parse_replan_system(ds), _itinerary_block(current, ds) + "\n" + san.wrapped, ReplanOut,
                    config.LLM_MAX_TOKENS_EXTRACT, config.LLM_MAX_CALLS_PARSE, "parse_replan")
    if out.unavailable:
        return ProposedOperations(status="llm_unavailable", mode="sample", call_count=out.call_count, **base,
                                  clarifications=["The language model could not be reached. Use the re-optimise controls instead."])
    base.update(call_count=out.call_count, mode="llm")
    if out.parsed is None:
        return ProposedOperations(status="needs_clarification", **base,
                                  clarifications=["I could not reliably read that request. Please rephrase it or use the re-optimise controls."])
    parsed: ReplanOut = out.parsed
    pos = _positions(current)
    scope = list(pos)
    ops, desc, clar, defaults = [], [], [], []
    resolved: list[ResolvedName] = []
    unresolved: list[UnresolvedName] = []
    ambiguities: list[Ambiguity] = []
    confirm_reasons: list[str] = []
    assumptions: dict = {}
    confirmations: list[dict] = []
    hints: list[dict] = []

    for o in parsed.operations:
        if o.op == "change_budget":
            if o.budget is None:
                clar.append("Budget change: no amount was given.")
                continue
            jpy = resolve_money(o.budget.amount, o.budget.currency, ds, "budget", assumptions, clar, confirmations)
            if jpy is None:
                continue
            ops.append(ChangeBudgetOp(op="change_budget", budget=jpy, strict=o.budget.strict))
            desc.append(f"change budget to {jpy:,} {ds.city.currency_code} ({'strict' if o.budget.strict else 'soft'})")
            assumptions.update(fx=ds.city.sample_fx_label, budget_scope=config.BUDGET_SCOPE_TEXT,
                               budget_interpreted=f"{o.budget.amount:g} {o.budget.currency.upper()} = {jpy:,} {ds.city.currency_code}")
            continue
        if o.op == "switch_hotel":
            if not o.hotel_name:
                clar.append("Hotel change: no hotel was named.")
                continue
            m = resolve_hotel(o.hotel_name, ds)
            if m.status == "resolved":
                ops.append(SwitchHotelOp(op="switch_hotel", hotel_id=m.id))
                desc.append(f"switch hotel to {m.name}")
            elif m.status == "ambiguous":
                ambiguities.append(Ambiguity(input=o.hotel_name, candidates=[Candidate(**c) for c in m.candidates]))
            else:
                hint = cross_city_hint(o.hotel_name, ds, all_datasets)
                if hint:
                    hints.append(hint)
                unresolved.append(UnresolvedName(input=o.hotel_name, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions],
                                                 message=hint["message"] if hint else "Not a hotel in this dataset."))
            continue
        if not o.attraction_name:
            clar.append(f"'{o.op}': no place was named.")
            continue
        m = resolve_attraction(o.attraction_name, ds, scope)
        if m.status == "ambiguous":
            ambiguities.append(Ambiguity(input=o.attraction_name, candidates=[Candidate(**c) for c in m.candidates]))
            continue
        if m.status != "resolved":
            hint = cross_city_hint(o.attraction_name, ds, all_datasets)
            if hint:
                hints.append(hint)
            unresolved.append(UnresolvedName(input=o.attraction_name, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions],
                                             **({"message": hint["message"]} if hint else {})))
            continue
        aid, name = m.id, m.name
        resolved.append(ResolvedName(input=o.attraction_name, id=aid, name=name, matched_as=m.matched_as, from_schedule=m.from_schedule))
        cur = pos.get(aid)
        if o.op == "unlock":
            ops.append(UnlockOp(op="unlock", attraction_id=aid))
            desc.append(f"unlock {name}")
        elif o.op == "remove":
            ops.append(RemoveOp(op="remove", attraction_id=aid))
            desc.append(f"remove {name}")
            if aid in prefs.must_visit:
                confirm_reasons.append(f"{name} is a must-visit; removing it needs your explicit confirmation.")
        else:  # lock | move
            day = o.day or (cur[0] if cur else None)
            if o.day is None and cur:
                defaults.append(f"{name}: day not stated, kept day {cur[0]}")
            if day is None:
                clar.append(f"{name} is not in the current plan: which day?")
                continue
            if o.day_part != "none":
                start = config.DAY_PART_START_TIMES[o.day_part]
                defaults.append(f"{name}: '{o.day_part}' interpreted as {start}")
            elif o.op == "lock" and cur and day == cur[0]:
                start = cur[1]
                defaults.append(f"{name}: no time stated, locked at its current time {start}")
            else:
                clar.append(f"{name}: what time of day (morning, midday, afternoon or evening)?")
                continue
            cls = LockOp if o.op == "lock" else MoveOp
            ops.append(cls(op=o.op, attraction_id=aid, day=day, start_time=start))
            desc.append(f"{o.op} {name} to day {day} {start}")

    if unresolved:
        clar.append("Not in this dataset: " + ", ".join(f"'{u.input}'" for u in unresolved) + ".")
    if ambiguities:
        clar.append("Please pick one: " + "; ".join(f"'{a.input}' could be " + " or ".join(c.name for c in a.candidates) for a in ambiguities) + ".")
    if not ops and not clar:
        clar.append("I did not find any change to make in that request.")
    status = "ok" if ops and not clar else "needs_clarification"
    return ProposedOperations(status=status, operations=ops, descriptions=desc, requires_confirmation=bool(confirm_reasons),
                              confirmation_reasons=confirm_reasons, extracted_json=parsed.model_dump(), resolved_names=resolved,
                              unresolved_names=unresolved, ambiguities=ambiguities, defaults_applied=defaults, clarifications=clar,
                              unclear=parsed.unclear, assumptions=assumptions, currency_confirmations=confirmations, cross_city_hints=hints,
                              switch_offer=(lambda offers: offers[0] if offers and len(offers) == len(hints) and len({o["city_id"] for o in offers}) == 1 else None)([h["offer"] for h in hints if h.get("offer")]), **base)
