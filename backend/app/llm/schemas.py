"""Models for LLM output (strict: extra fields forbidden) and for the API results of the LLM layer."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.optimiser.replan import Operation
from app.repair import RepairAction
from app.schemas import Preferences


class _LLMOut(BaseModel):
    """Everything the model may return. extra='forbid' means it cannot smuggle in fields such as
    confirm_remove_must_visit, allow_unknown_hours, hotel prices, nights or ids."""
    model_config = ConfigDict(extra="forbid")


Name = Annotated[str, Field(min_length=1, max_length=80)]


class BudgetOut(_LLMOut):
    amount: float = Field(ge=0, le=100_000_000)
    currency: str = Field(min_length=1, max_length=8)
    strict: bool = False


class MoneyOut(_LLMOut):
    amount: float = Field(ge=0, le=100_000_000)
    currency: str = Field(min_length=1, max_length=8)


class ExtractionOut(_LLMOut):
    days: int | None = None
    budget: BudgetOut | None = None
    pace: Literal["relaxed", "balanced", "packed"] | None = None
    interests: list[Name] = Field(default_factory=list, max_length=20)
    must_visit_names: list[Name] = Field(default_factory=list, max_length=20)
    skip_names: list[Name] = Field(default_factory=list, max_length=20)
    day_start: str | None = Field(default=None, max_length=5)
    day_end: str | None = Field(default=None, max_length=5)
    value_of_time: MoneyOut | None = None
    max_walking_minutes: int | None = None
    destination_mentioned: str | None = Field(default=None, max_length=80)  # free text; code (not the model) decides what it means
    unclear: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=10)


class OpOut(_LLMOut):
    op: Literal["lock", "unlock", "remove", "move", "change_budget", "switch_hotel"]
    attraction_name: Name | None = None
    day: int | None = Field(default=None, ge=1, le=7)
    day_part: Literal["morning", "midday", "afternoon", "evening", "none"] = "none"
    budget: BudgetOut | None = None
    hotel_name: Name | None = None


class ReplanOut(_LLMOut):
    operations: list[OpOut] = Field(max_length=10)
    unclear: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=10)


class RepairActionOut(_LLMOut):
    action: Literal["extend_day", "set_max_activities", "set_max_daily_travel", "set_pace", "change_value_of_time", "remove_optional", "promote_to_must",
                    "demote_must_visit", "allow_unknown_hours", "soften_budget", "switch_hotel", "unlock_hotel"]
    attraction_name: Name | None = None
    hotel_name: Name | None = None
    minutes: int | None = Field(default=None, ge=0, le=1440)
    count: int | None = Field(default=None, ge=1, le=8)
    pace: Literal["relaxed", "balanced", "packed"] | None = None
    direction: Literal["lower", "higher"] | None = None
    reason: str = Field(default="", max_length=160)


class RepairOut(_LLMOut):
    actions: list[RepairActionOut] = Field(max_length=6)
    keep_hotel_requested: bool = False
    unsupported: list[Annotated[str, Field(max_length=120)]] = Field(default_factory=list, max_length=8)
    unclear: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=10)


class ProfileOut(_LLMOut):
    tags: list[Literal["slow_pace", "few_activities", "many_sights", "pay_more_to_save_time", "save_money", "limited_budget", "short_travel"]] = Field(default_factory=list, max_length=7)
    max_activities: int | None = Field(default=None, ge=1, le=8)
    max_daily_travel_minutes: int | None = Field(default=None, ge=20, le=720)
    budget: BudgetOut | None = None
    must_visit_names: list[Name] = Field(default_factory=list, max_length=10)
    unsupported: list[Annotated[str, Field(max_length=120)]] = Field(default_factory=list, max_length=8)
    unclear: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=10)


# ---- API results ----------------------------------------------------------------------------------------
class _R(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Candidate(_R):
    id: str
    name: str


class ResolvedName(_R):
    input: str
    id: str
    name: str
    matched_as: str
    from_schedule: bool = False


class SuggestionOut(_R):
    id: str
    name: str
    reason: str


class UnresolvedName(_R):
    input: str
    suggestions: list[SuggestionOut] = []
    message: str = "Not a place in this dataset, so it cannot be scheduled."


class Ambiguity(_R):
    input: str
    candidates: list[Candidate]


class ParseResult(_R):
    status: Literal["ok", "needs_clarification", "llm_unavailable"]
    draft: Preferences | None = None  # a PROPOSAL: the client edits it, then submits it to the optimiser endpoints
    raw_input_echo: str = ""
    extracted_json: dict | None = None  # what the model returned (validated, before name resolution)
    resolved_names: list[ResolvedName] = []
    unresolved_names: list[UnresolvedName] = []
    ambiguities: list[Ambiguity] = []
    defaults_applied: list[str] = []
    clarifications: list[str] = []
    unclear: list[str] = []
    assumptions: dict = {}
    call_count: int = 0
    mode: Literal["llm", "sample"] = "sample"
    prompt_version: str = ""
    city_id: str = ""
    city_name: str = ""
    destination: dict | None = None            # the code-side destination check (status, mentioned cities, message)
    switch_offer: dict | None = None           # {city_id, display_name, country}: the CLIENT may offer a button; nothing is ever switched here
    currency_confirmations: list[dict] = []    # ambiguous amounts the user must confirm (never guessed)
    cross_city_hints: list[dict] = []          # names that exist only in other cities


class ProposedOperations(_R):
    status: Literal["ok", "needs_clarification", "llm_unavailable"]
    executed: Literal[False] = False  # a proposal only: nothing has been applied
    operations: list[Operation] = []
    descriptions: list[str] = []
    requires_confirmation: bool = False  # True when a must-visit removal is proposed; only the user can confirm
    confirmation_reasons: list[str] = []
    raw_input_echo: str = ""
    extracted_json: dict | None = None
    resolved_names: list[ResolvedName] = []
    unresolved_names: list[UnresolvedName] = []
    ambiguities: list[Ambiguity] = []
    defaults_applied: list[str] = []
    clarifications: list[str] = []
    unclear: list[str] = []
    assumptions: dict = {}
    call_count: int = 0
    mode: Literal["llm", "sample"] = "sample"
    prompt_version: str = ""
    city_id: str = ""
    city_name: str = ""
    destination: dict | None = None            # the code-side destination check (status, mentioned cities, message)
    switch_offer: dict | None = None           # {city_id, display_name, country}: the CLIENT may offer a button; nothing is ever switched here
    currency_confirmations: list[dict] = []    # ambiguous amounts the user must confirm (never guessed)
    cross_city_hints: list[dict] = []          # names that exist only in other cities


class GroundingReport(_R):
    checked: int = 0  # numeric/time/name tokens checked
    rejected_tokens: list[str] = []


class CitedSentence(_R):
    text: str
    fact_ids: list[str]


class FactRef(_R):
    id: str
    text: str


class Explanation(_R):
    text: str
    source: Literal["llm", "template"]
    grounding: GroundingReport = GroundingReport()
    warnings: list[str] = []
    call_count: int = 0
    reason: str | None = None  # why the template was used, if it was
    cited: bool = False        # True only when the text is made of validated sentences, each citing the facts (by id) that support it
    sentences: list[CitedSentence] = []   # the validated sentences (cited explanations only)
    facts: list[FactRef] = []             # the cited facts, by id, so the interface can show the source of each claim
    dropped: int = 0                      # sentences code dropped (cited explanations only)


class RepairProposal(_R):
    """A PROPOSAL. Nothing has been applied; `verification` says what the normal optimiser and the independent validator returned when the proposed changes were tried on a COPY."""
    status: Literal["ok", "needs_clarification", "llm_unavailable"]
    executed: Literal[False] = False
    actions: list[RepairAction] = []
    understood: list[str] = []                 # what the changes mean, in words made by code from the actions
    unchanged: list[str] = []                  # what the repair leaves alone, made by code
    hard_changes: list[str] = []               # actions that touch a hard constraint or give something up
    refused: list[dict] = []                   # {input, why}: asked for but not allowed (locked hotel/attraction, out of range, stale)
    unsupported: list[str] = []
    verification: dict | None = None
    base_fingerprint: str = ""
    keep_hotel: bool = False
    keep_hotel_inferred: bool = False
    raw_input_echo: str = ""
    extracted_json: dict | None = None
    resolved_names: list[ResolvedName] = []
    unresolved_names: list[UnresolvedName] = []
    ambiguities: list[Ambiguity] = []
    clarifications: list[str] = []
    unclear: list[str] = []
    call_count: int = 0
    mode: Literal["llm", "sample"] = "sample"
    prompt_version: str = ""
    city_id: str = ""


class ProfileSetting(_R):
    field: str                                  # pace | maxActivities | maxDailyTravel | valueOfTime | budget | must_visit
    label: str
    current: str | int | bool | None = None
    proposed: str | int | bool | None = None
    source: Literal["explicit", "inferred"]     # explicit: the user wrote it (a number that is in their text); inferred: the program's documented mapping of a tag
    reason: str
    kept_yours: bool = False                    # the user already set this themselves and did not ask for a change here: shown, not proposed
    requires_confirmation: bool = True
    target: str | None = None                   # an attraction id, for must_visit


class ProfileProposal(_R):
    status: Literal["ok", "needs_clarification", "llm_unavailable"]
    executed: Literal[False] = False
    settings: list[ProfileSetting] = []
    questions: list[str] = []                   # e.g. "limited budget": the program asks for a number instead of inventing one
    unsupported: list[str] = []
    raw_input_echo: str = ""
    extracted_json: dict | None = None
    resolved_names: list[ResolvedName] = []
    unresolved_names: list[UnresolvedName] = []
    ambiguities: list[Ambiguity] = []
    clarifications: list[str] = []
    currency_confirmations: list[dict] = []
    call_count: int = 0
    mode: Literal["llm", "sample"] = "sample"
    prompt_version: str = ""
    city_id: str = ""
