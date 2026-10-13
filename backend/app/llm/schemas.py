"""Models for LLM output (strict: extra fields forbidden) and for the API results of the LLM layer."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.optimiser.replan import Operation
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


class GroundingReport(_R):
    checked: int = 0  # numeric/time/name tokens checked
    rejected_tokens: list[str] = []


class Explanation(_R):
    text: str
    source: Literal["llm", "template"]
    grounding: GroundingReport = GroundingReport()
    warnings: list[str] = []
    call_count: int = 0
    reason: str | None = None  # why the template was used, if it was
