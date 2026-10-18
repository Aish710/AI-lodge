"""AI-assisted repair: text -> PROPOSED, validated, solver-verified changes. Nothing is applied here.

The model chooses from a closed list of actions and copies names as the user wrote them. Code resolves the names, computes every number and id, derives the confirmation flags
(app/repair.py), refuses what the allowlist or the person's locks forbid, tries the allowed changes on a COPY with the normal optimiser and the independent validator, and writes the
"what changes / what stays" text itself. A model failure, an invalid reply or a refused action leaves the current plan exactly as it was.
"""
import re
from contextlib import nullcontext

from app import config
from app.config import get_settings
from app.data.loader import Dataset
from app.llm.client import LLMClient
from app.llm.names import resolve_attraction, resolve_hotel
from app.llm.prompts import PROMPT_VERSION, repair_system
from app.llm.runner import call_json
from app.llm.sanitize import sanitise_user_text
from app.llm.schemas import Ambiguity, Candidate, RepairOut, RepairProposal, ResolvedName, SuggestionOut, UnresolvedName
from app.optimiser.solver import precheck
from app.repair import RepairAction, RepairError, apply_actions, base_fingerprint, build_action, later_end, unchanged_summary, verify, VOT_FACTOR
from app.schemas import Preferences


def _settings_block(prefs: Preferences, hotel_id: str, keep_hotel: bool, ds: Dataset, codes: list[str]) -> str:
    musts = ", ".join(ds.attractions[a].name for a in prefs.must_visit if a in ds.attractions) or "none"
    lines = [f"must-visits: {musts}", f"hotel: {ds.hotels[hotel_id].name} ({'kept by the traveller' if keep_hotel else 'not locked'})", f"days: {prefs.days}", f"day: {prefs.day_start}-{prefs.day_end}",
             f"pace: {prefs.pace}", f"max activities per day: {prefs.max_activities_per_day or 'pace decides'}", f"max estimated travel per day: {prefs.max_daily_travel_minutes or 'none'}",
             f"budget: {'strict' if prefs.strict_budget else 'soft or none'}", f"unknown opening hours allowed: {'yes' if prefs.allow_unknown_hours else 'no'}",
             "problems found (kinds only): " + (", ".join(codes) or "none established")]
    return "<current_settings>\n" + "\n".join(lines) + "\n</current_settings>"


_MONEY_OR_NUMBER = re.compile(r"\d|[¥$₩€£]|\b(yen|won|ringgit|dollars?|rm|sgd|jpy|krw|myr|save[sd]?|saving|savings|cheaper|cost[s]?|price[sd]?|free)\b", re.I)


def _clean_reason(reason: str) -> str:
    """The model's reason is only ever DISPLAYED, and only if it makes no claim about money or numbers (a fabricated saving would otherwise sit next to a computed result). Numbers come from code."""
    r = (reason or "").strip()
    return "" if _MONEY_OR_NUMBER.search(r) else r


def _shown(parsed: RepairOut) -> dict:
    d = parsed.model_dump()
    for a in d["actions"]:
        a["reason"] = _clean_reason(a["reason"])          # the echo of what the model returned carries no money or number claims either
    return d


def _words(a: RepairAction, ds: Dataset) -> str:
    n, p = a.target_label, a.proposed
    return {"extend_day": f"Let the day end at {p} (now {a.expected_previous})", "set_max_activities": f"At most {p} activities a day (now {a.expected_previous or 'set by pace'})",
            "set_max_daily_travel": f"Estimated travel per day: {'no limit' if p is None else f'{p} min'} (now {a.expected_previous or 'no limit'})", "set_pace": f"Pace {a.expected_previous} → {p}",
            "change_value_of_time": f"Value of an hour {a.expected_previous} → {p}", "remove_optional": f"Leave out {n} (it is optional)",
            "promote_to_must": f"Make {n} a must-visit", "demote_must_visit": f"Stop requiring {n} as a must-visit",
            "allow_unknown_hours": "Allow sights with unknown opening hours (provisional: labelled \"Opening hours unverified\")", "soften_budget": "Treat the budget as soft instead of strict",
            "switch_hotel": f"Use {n} instead of {ds.hotels[a.expected_previous].name if a.expected_previous in ds.hotels else 'the current hotel'}", "unlock_hotel": "Stop keeping the current hotel (allows a hotel switch)"}[a.action]


def parse_repair(text: str, prefs: Preferences, hotel_id: str, keep_hotel: bool, ds: Dataset, client: LLMClient | None, *, max_input_chars: int | None = None,
                 unavailable_note: str | None = None, solve_seconds: float = 10.0, solve_slot=None) -> RepairProposal:
    san = sanitise_user_text(text, max_input_chars or get_settings().max_input_chars)
    base = dict(raw_input_echo=san.text, prompt_version=PROMPT_VERSION, city_id=ds.city.id, keep_hotel=keep_hotel, base_fingerprint=base_fingerprint(prefs, hotel_id, keep_hotel, ds))
    if client is None:
        return RepairProposal(status="llm_unavailable", mode="sample", **base,
                              clarifications=[f"{unavailable_note or 'The language model is not available (sample mode).'} Use the repair options above instead."])
    codes = sorted({c.code for c in precheck(prefs, hotel_id, ds)})
    out = call_json(client, repair_system(ds), _settings_block(prefs, hotel_id, keep_hotel, ds, codes) + "\n" + san.wrapped, RepairOut, config.LLM_MAX_TOKENS_EXTRACT,
                    config.LLM_MAX_CALLS_PARSE, "parse_repair")
    if out.unavailable:
        return RepairProposal(status="llm_unavailable", mode="sample", call_count=out.call_count, **base, clarifications=["The language model could not be reached. Use the repair options above instead."])
    base.update(call_count=out.call_count, mode="llm")
    if out.parsed is None:
        return RepairProposal(status="needs_clarification", **base, clarifications=["I could not reliably read that request. Please rephrase it or use the repair options above."])
    parsed: RepairOut = out.parsed
    clar = ["Some text written by the AI was removed because it looked like internal instructions or a secret. It was not shown."] if out.removed else []
    keep = keep_hotel or parsed.keep_hotel_requested            # a stated wish to keep the hotel is honoured; it can only ever MAKE the request more cautious
    refused, resolved, unresolved, ambiguities, accepted = [], [], [], [], []
    p, h, k = prefs, hotel_id, keep
    n = 0
    for o in parsed.actions:
        n += 1
        extra: dict = {}
        try:
            if o.action in ("remove_optional", "promote_to_must", "demote_must_visit"):
                if not o.attraction_name:
                    clar.append(f"'{o.action}': no place was named.")
                    continue
                m = resolve_attraction(o.attraction_name, ds)
                if m.status == "ambiguous":
                    ambiguities.append(Ambiguity(input=o.attraction_name, candidates=[Candidate(**c) for c in m.candidates]))
                    continue
                if m.status != "resolved":
                    unresolved.append(UnresolvedName(input=o.attraction_name, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions]))
                    continue
                resolved.append(ResolvedName(input=o.attraction_name, id=m.id, name=m.name, matched_as=m.matched_as))
                extra = dict(target=m.id, proposed={"remove_optional": "skip", "promote_to_must": "must", "demote_must_visit": "optional"}[o.action])
            elif o.action == "switch_hotel":
                if not o.hotel_name:
                    clar.append("Hotel change: no hotel was named.")
                    continue
                m = resolve_hotel(o.hotel_name, ds)
                if m.status != "resolved":
                    unresolved.append(UnresolvedName(input=o.hotel_name, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions], message="Not a hotel in this dataset."))
                    continue
                extra = dict(proposed=m.id)
            elif o.action == "extend_day":
                new = later_end(p, o.minutes or 0)
                if new is None:
                    refused.append({"input": o.action, "why": "The day cannot end any later (it is already at the latest, or no number of minutes was given)."})
                    continue
                extra = dict(proposed=new)
            elif o.action == "set_max_activities":
                if o.count is None:
                    clar.append("Activities per day: no number was given.")
                    continue
                extra = dict(proposed=o.count)
            elif o.action == "set_max_daily_travel":
                if o.minutes is None:
                    clar.append("Estimated travel limit: no number of minutes was given.")
                    continue
                extra = dict(proposed=o.minutes)
            elif o.action == "set_pace":
                if o.pace is None:
                    clar.append("Pace: relaxed, balanced or packed?")
                    continue
                extra = dict(proposed=o.pace)
            elif o.action == "change_value_of_time":
                if o.direction is None or p.value_of_time_per_hour == 0 and o.direction == "higher":
                    clar.append("Value of an hour: lower or higher?")
                    continue
                extra = dict(proposed=int(round(p.value_of_time_per_hour * VOT_FACTOR[o.direction])))
            elif o.action == "allow_unknown_hours":
                extra = dict(proposed=True)
            elif o.action in ("soften_budget", "unlock_hotel"):
                extra = dict(proposed=False)
            if o.action == "switch_hotel" and parsed.keep_hotel_requested and not keep_hotel:
                refused.append({"input": o.action, "why": "You said to keep your hotel, so no hotel change is proposed."})
                continue
            act = build_action(len(accepted) + 1, o.action, p, h, k, ds, reason=_clean_reason(o.reason), **extra)
            if any(a.action == act.action and a.target == act.target for a in accepted):
                continue
            p, h, k = apply_actions(p, h, k, [act], ds)
            accepted.append(act)
        except RepairError as e:
            refused.append({"input": o.action, "why": e.message})
    if unresolved:
        clar.append("Not in this dataset: " + ", ".join(f"'{u.input}'" for u in unresolved) + ".")
    if ambiguities:
        clar.append("Please pick one: " + "; ".join(f"'{a.input}' could be " + " or ".join(c.name for c in a.candidates) for a in ambiguities) + ".")
    verification = None
    if accepted:
        with (solve_slot() if solve_slot else nullcontext()):
            verification = verify(p, h, ds, max_seconds=solve_seconds)
    if not accepted and not clar and not refused and not parsed.unsupported:
        clar.append("I did not find a change to propose in that request.")
    status = "ok" if accepted and not (unresolved or ambiguities) else "needs_clarification"
    return RepairProposal(status=status, actions=accepted, understood=[_words(a, ds) for a in accepted], unchanged=unchanged_summary(prefs, p, hotel_id, h, ds) if accepted else [],
                          hard_changes=[_words(a, ds) for a in accepted if a.hard_constraint], refused=refused, unsupported=parsed.unsupported, verification=verification, extracted_json=_shown(parsed),
                          resolved_names=resolved, unresolved_names=unresolved, ambiguities=ambiguities, clarifications=clar, unclear=parsed.unclear, keep_hotel_inferred=keep and not keep_hotel, **{**base, "keep_hotel": keep_hotel})
