"""AI-interpreted travel style: text -> PROPOSED settings, each labelled explicit or inferred. Nothing is applied and nothing is solved here.

The model only TAGS which supported preferences the text expresses (a closed list) and copies numbers/names the user wrote. Code decides everything else:
  * explicit  = a number that really appears in the user's text (checked in code); a number the model made up is dropped, never used;
  * inferred  = the program's documented mapping of a tag (for example slow_pace -> relaxed pace); it is labelled inferred and needs confirmation, like every setting;
  * "limited budget" with no amount is a QUESTION, not an invented amount;
  * a setting the user already set themselves is shown as "kept yours" unless this text explicitly asks for a different value;
  * preferences the planner cannot enforce are listed as unsupported and never turned into a setting.
The person previews and confirms; the plan is re-optimised only when they press Plan.
"""
import re

from app import config
from app.config import get_settings
from app.data.loader import Dataset
from app.llm.client import LLMClient
from app.llm.extract import resolve_money
from app.llm.names import resolve_attraction
from app.llm.prompts import PROMPT_VERSION, profile_system
from app.llm.runner import call_json
from app.llm.sanitize import sanitise_user_text
from app.llm.schemas import Ambiguity, Candidate, ProfileOut, ProfileProposal, ProfileSetting, ResolvedName, SuggestionOut, UnresolvedName

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
# documented tag -> setting mappings (the only place numbers come from when the user wrote none)
TAG_MAP = {"slow_pace": [("pace", "relaxed"), ("maxActivities", 2)], "few_activities": [("maxActivities", 2)], "many_sights": [("pace", "packed")],
           "short_travel": [("maxDailyTravel", 120)]}
VOT_TAG = {"pay_more_to_save_time": 4, "save_money": 0.5}
LABEL = {"pace": "Pace", "maxActivities": "Activities per day", "maxDailyTravel": "Estimated travel per day (min)", "valueOfTime": "Value of an hour", "budget": "Budget", "must_visit": "Must-visit"}


def _digits(text: str) -> set[int]:
    return {int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", text) if x.replace(",", "").isdigit()} | {NUMBER_WORDS[w] for w in re.findall(r"[a-z]+", text.lower()) if w in NUMBER_WORDS}


def parse_profile(text: str, current: dict, user_overrides: list[str], ds: Dataset, client: LLMClient | None, *, max_input_chars: int | None = None,
                  unavailable_note: str | None = None) -> ProfileProposal:
    san = sanitise_user_text(text, max_input_chars or get_settings().max_input_chars)
    base = dict(raw_input_echo=san.text, prompt_version=PROMPT_VERSION, city_id=ds.city.id)
    if client is None:
        return ProfileProposal(status="llm_unavailable", mode="sample", **base, clarifications=[f"{unavailable_note or 'The language model is not available (sample mode).'} Choose a travel style or set the values yourself."])
    out = call_json(client, profile_system(ds), san.wrapped, ProfileOut, config.LLM_MAX_TOKENS_EXTRACT, config.LLM_MAX_CALLS_PARSE, "parse_profile")
    if out.unavailable:
        return ProfileProposal(status="llm_unavailable", mode="sample", call_count=out.call_count, **base, clarifications=["The language model could not be reached. Choose a travel style or set the values yourself."])
    base.update(call_count=out.call_count, mode="llm")
    if out.parsed is None:
        return ProfileProposal(status="needs_clarification", **base, clarifications=["I could not reliably read that. Please rephrase, or choose a travel style."])
    o: ProfileOut = out.parsed
    written = _digits(san.text)
    clar = ["Some text written by the AI was removed because it looked like internal instructions or a secret. It was not shown."] if out.removed else []
    settings: list[ProfileSetting] = []
    questions: list[str] = []
    resolved, unresolved, ambiguities, confirmations = [], [], [], []
    mine = set(user_overrides)

    def add(field, proposed, source, reason, **kw):
        cur = current.get(field)
        if cur == proposed:
            return
        settings.append(ProfileSetting(field=field, label=LABEL[field], current=cur, proposed=proposed, source=source, reason=reason, kept_yours=(field in mine and source != "explicit"), **kw))

    # explicit numbers: only if the number is in the user's own words
    if o.max_activities is not None:
        if o.max_activities in written:
            add("maxActivities", o.max_activities, "explicit", f"You asked for at most {o.max_activities} activities a day.")
        else:
            clar.append("I did not use an activities-per-day number because it was not written in your text. Tell me the number you want.")
    if o.max_daily_travel_minutes is not None:
        m = o.max_daily_travel_minutes
        if m in written or (m % 60 == 0 and m // 60 in written):
            add("maxDailyTravel", m, "explicit", f"You asked to keep estimated travel to {m} minutes a day.")
        else:
            clar.append("I did not use a travel-time number because it was not written in your text. Tell me how many minutes or hours.")
    if o.budget is not None:
        if int(round(o.budget.amount)) in written or int(o.budget.amount) in written:
            local = resolve_money(o.budget.amount, o.budget.currency, ds, "budget", {}, clar, confirmations)
            if local is not None:
                add("budget", local, "explicit", f"You gave a budget of {o.budget.amount:g} {o.budget.currency.upper()} (about {local:,} {ds.city.currency_code}).", requires_confirmation=True)
        else:
            clar.append("I did not use a budget amount because it was not written in your text.")
    # tags: documented, labelled inferred; never an invented number beyond the documented mapping
    have = {s.field for s in settings}
    blocked_tags = set()
    if "many_sights" in o.tags and ({"slow_pace", "few_activities"} & set(o.tags)):
        questions.append("Would you prefer fewer activities with breaks, or more sights each day? Your explicit limits stay unchanged; no conflicting pace is inferred.")
        blocked_tags.update({"many_sights", "slow_pace", "few_activities"})
    if "save_money" in o.tags and ({"pay_more_to_save_time", "short_travel"} & set(o.tags)):
        questions.append("When lower spending means more estimated travel, which matters more: spending less or travelling less? No time valuation or travel limit is inferred until you choose.")
        blocked_tags.update({"save_money", "pay_more_to_save_time", "short_travel"})
    for tag in o.tags:
        if tag in blocked_tags:
            continue
        for field, val in TAG_MAP.get(tag, []):
            if field not in have:
                add(field, val, "inferred", {"slow_pace": "A slow trip with breaks: relaxed pace and at most 2 activities a day is a suggested starting point.", "few_activities": "Fewer things each day: 2 a day is a suggested starting point.",
                                              "many_sights": "As many sights as possible: the packed pace is a suggested starting point.", "short_travel": "Avoiding long travel: 120 estimated minutes a day is a suggested starting point."}[tag])
                have.add(field)
        if tag in VOT_TAG and "valueOfTime" not in have:
            base_v = ds.city.default_value_of_time_per_hour
            add("valueOfTime", int(round(base_v * VOT_TAG[tag])), "inferred", ("Willing to pay for less travel time: weigh an hour of travel at 4 times this city's default." if tag == "pay_more_to_save_time"
                                                                                else "Cheapest wins: weigh an hour of travel at half this city's default."))
            have.add("valueOfTime")
        if tag == "limited_budget" and not any(s.field == "budget" for s in settings):
            questions.append("You mentioned a limited budget. How much is it (an amount and currency)? I will not guess a number.")
    for nm in o.must_visit_names:
        m = resolve_attraction(nm, ds)
        if m.status == "ambiguous":
            ambiguities.append(Ambiguity(input=nm, candidates=[Candidate(**c) for c in m.candidates]))
        elif m.status != "resolved":
            unresolved.append(UnresolvedName(input=nm, suggestions=[SuggestionOut(id=s.id, name=s.name, reason=s.reason) for s in m.suggestions]))
        else:
            resolved.append(ResolvedName(input=nm, id=m.id, name=m.name, matched_as=m.matched_as))
            settings.append(ProfileSetting(field="must_visit", label=f"Must-visit: {m.name}", current=None, proposed=True, source="explicit", reason=f"You said {m.name} is essential.", target=m.id))
    if unresolved:
        clar.append("Not in this dataset: " + ", ".join(f"'{u.input}'" for u in unresolved) + ".")
    if ambiguities:
        clar.append("Please pick one: " + "; ".join(f"'{a.input}' could be " + " or ".join(c.name for c in a.candidates) for a in ambiguities) + ".")
    status = "ok" if settings and not (unresolved or ambiguities or questions) else "needs_clarification"
    if not settings and not questions and not clar and not o.unsupported:
        clar.append("I did not find a supported preference in that.")
    return ProfileProposal(status=status, settings=settings, questions=questions, unsupported=o.unsupported, extracted_json=o.model_dump(), resolved_names=resolved, unresolved_names=unresolved,
                           ambiguities=ambiguities, clarifications=clar, currency_confirmations=confirmations, **base)
