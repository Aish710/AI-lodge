"""FastAPI app factory. All hardening (limits, rate tiers, deadlines, circuit breaker, leakage control) is wired here."""
import logging
import time
from collections import Counter
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app.config import FX_LABEL, SAMPLE_FX_JPY_PER_SGD, get_settings
from app.data.loader import load_dataset
from app.hardening.config import HConfig
from app.hardening.errors import ApiError, error_response
from app.hardening.limiter import SlidingWindowLimiter
from app.hardening.llm_scope import LLMBudget, llm_for_request
from app.hardening.logging_setup import configure_logging
from app.hardening.middleware import HardeningMiddleware
from app.llm.client import LLMClient
from app.llm.explain import OptimiseView, explain
from app.llm.extract import extract_preferences
from app.llm.parse_replan import parse_replan
from app.llm.sanitize import EmptyInput, InputTooLong
from app.optimiser.hotel_compare import ComparisonInputError, compare_hotels
from app.optimiser.replan import Operation, ReplanError, replan
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import Preferences, SolveResult, nights_for
from app.untrusted import rebuild_client_schedule
from app.validator.feasibility_report import build_report

log = logging.getLogger("app.startup")
router = APIRouter()


class _Req(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected on every request model


# ---- cheap routes -------------------------------------------------------------------------------------------
@router.get("/health")
def health(request: Request):
    st = get_settings()  # never echoes the key
    limit = request.app.state.llm_budget.exhausted()
    mode = "llm" if (st.llm_enabled and not limit) else "sample"
    return {"status": "ok", "mode": mode, "llm_configured": st.llm_enabled, "llm_mode": mode, "llm_limit_reached": bool(st.llm_enabled and limit)}


@router.get("/data/summary")
def data_summary(request: Request):
    ds = request.app.state.dataset
    atts = list(ds.attractions.values())
    return {
        "counts": {"attractions": len(atts), "hotels": len(ds.hotels), "matrix_nodes": len(ds.minutes)},
        "provenance": {
            "attractions": dict(Counter(a.provenance.source_status for a in atts)),
            "hotels": dict(Counter(h.provenance.source_status for h in ds.hotels.values())),
            "travel_matrix": ds.matrix_meta["source_status"],
        },
        "data_quality": {
            "attractions_with_unknown_hours": sum(any(v == "unknown" for v in a.opening_hours.values()) for a in atts),
            "attractions_with_unknown_cost": sum(a.admission_cost is None for a in atts),
            "verified_records": sum(a.provenance.source_status == "verified" for a in atts),
        },
        "disclaimer": "Sample data, not live prices. Hotels are fictional. Travel times are estimates.",
        "fx": {"jpy_per_sgd": SAMPLE_FX_JPY_PER_SGD, "label": FX_LABEL},
    }


@router.get("/data/places")
def data_places(request: Request):
    """Read-only reference data for the UI (map markers, wishlist cards). Deliberately omits `description`: it is untrusted free text
    and nothing in the interface needs it."""
    ds = request.app.state.dataset
    src = lambda p: p.source_status
    return {
        "attractions": [
            {"id": a.id, "name": a.name, "area": a.area, "lat": a.lat, "lon": a.lon, "category": a.category, "priority": a.priority,
             "duration_minutes": a.duration_minutes, "admission_cost": a.admission_cost, "indoor": a.indoor,
             "advance_booking_required": a.advance_booking_required, "opening_hours": a.opening_hours,
             "source": {"record": src(a.provenance), "hours": src(a.hours_provenance), "cost": src(a.cost_provenance)}}
            for a in ds.attractions.values()],
        "hotels": [{"id": h.id, "name": h.name, "area": h.area, "lat": h.lat, "lon": h.lon, "nightly_rate": h.nightly_rate,
                    "source": {"record": src(h.provenance)}} for h in ds.hotels.values()],
        "travel_times_source": ds.matrix_meta["source_status"],
        "fx": {"jpy_per_sgd": SAMPLE_FX_JPY_PER_SGD, "label": FX_LABEL},
        "disclaimer": "Sample data, not live prices. Hotels are fictional. Travel times are estimates.",
    }


# ---- standard routes -------------------------------------------------------------------------------------------
class CompareRequest(_Req):
    preferences: Preferences
    hotel_ids: list[str] = Field(max_length=3)
    include_sensitivity: bool = False
    vot_min: int | None = Field(default=None, ge=0, le=100_000)
    vot_max: int | None = Field(default=None, ge=0, le=100_000)
    explain: bool = False  # optional explanation, generated server-side from the result computed here


@router.post("/compare-hotels")
def compare_hotels_route(req: CompareRequest, request: Request, client: LLMClient | None = Depends(llm_for_request)):
    ds = request.app.state.dataset
    vot_range = (req.vot_min if req.vot_min is not None else config.VOT_RANGE_DEFAULT[0],
                 req.vot_max if req.vot_max is not None else config.VOT_RANGE_DEFAULT[1])
    comp = compare_hotels(req.preferences, req.hotel_ids, ds, include_sensitivity=req.include_sensitivity, vot_range=vot_range)
    out = comp.model_dump()
    # Presentation layer only: SGD display values from the labelled SAMPLE FX rate.
    out["fx_label"] = FX_LABEL
    out["display_sgd"] = {
        r.hotel_id: {"true_cost_sgd": round(r.breakdown.true_cost_jpy / SAMPLE_FX_JPY_PER_SGD, 2),
                     "rooms_sgd": round(r.breakdown.rooms_jpy / SAMPLE_FX_JPY_PER_SGD, 2)}
        for r in comp.results if r.breakdown
    }
    if req.explain:
        out["explanation"] = explain(comp, ds, client, request.state.llm_note).model_dump()
    return out


class ReplanRequest(_Req):
    preferences: Preferences
    current_result: SolveResult
    operations: list[Operation] = Field(max_length=config.MAX_REPLAN_OPERATIONS)
    confirm_remove_must_visit: bool = False  # only ever set by the client; the server never sets it
    explain: bool = False


@router.post("/replan")
def replan_route(req: ReplanRequest, request: Request, client: LLMClient | None = Depends(llm_for_request)):
    """Stateless: nothing from the request is stored. The supplied schedule is UNTRUSTED: it is rebuilt and validated first."""
    ds = request.app.state.dataset
    current = rebuild_client_schedule(req.preferences, req.current_result, ds)
    result = replan(req.preferences, current, req.operations, ds, confirm_remove_must_visit=req.confirm_remove_must_visit)
    out = result.model_dump()
    if req.explain:  # built from the result just computed here, never from client-supplied results
        out["explanation"] = explain(result, ds, client, request.state.llm_note).model_dump()
    return out


class OptimiseRequest(_Req):
    preferences: Preferences
    hotel_id: str = Field(max_length=64)
    explain: bool = False


@router.post("/optimise")
def optimise_route(req: OptimiseRequest, request: Request, client: LLMClient | None = Depends(llm_for_request)):
    """Best feasible itinerary for ONE hotel (true-cost objective, same as the hotel comparison), always validated."""
    ds, cfg = request.app.state.dataset, request.app.state.hconf
    if req.hotel_id not in ds.hotels:
        raise ApiError(422, "unknown_hotel", f"Unknown hotel id '{req.hotel_id[:64]}'.")
    p = req.preferences
    spec = ObjectiveSpec("true_cost", p.value_of_time_per_hour, config.MISSED_PREFERENCE_PENALTY_JPY)
    res = solve(p, req.hotel_id, ds, objective=spec, max_seconds=cfg.optimise_time_limit_seconds,
                alternatives_budget=cfg.alternatives_budget_seconds)
    rep = build_report(res, ds, p, req.hotel_id)  # a failing report is returned as-is, never hidden
    nights, src = nights_for(p)
    approximate = res.status == "feasible" and res.solver_meta.solver_status != "OPTIMAL"
    out = {"result": res.model_dump(), "feasibility_report": rep.model_dump(), "approximate": approximate,
           "nights_used": nights, "nights_source": src}
    if approximate:
        out["approximate_note"] = "The solver stopped at its time limit without proving optimality: this plan is good but may not be the best."
    if req.explain:
        out["explanation"] = explain(OptimiseView(res, rep, req.hotel_id, approximate, nights), ds, client, request.state.llm_note).model_dump()
    return out


# ---- expensive (LLM) routes -----------------------------------------------------------------------------------------
class ParseRequest(_Req):
    text: str = Field(max_length=10_000)
    start_weekday: int | None = Field(default=None, ge=0, le=6)  # optional trip context supplied by the client (0=Mon .. 6=Sun)


@router.post("/parse")
def parse_route(req: ParseRequest, request: Request, client: LLMClient | None = Depends(llm_for_request)):
    """Free text -> Preferences DRAFT (a proposal). In sample mode returns status llm_unavailable (HTTP 200, never a 500)."""
    r = extract_preferences(req.text, request.app.state.dataset, client, start_weekday=req.start_weekday,
                            unavailable_note=request.state.llm_note)
    return r.model_dump()


class ParseReplanRequest(_Req):
    text: str = Field(max_length=10_000)
    preferences: Preferences
    current_result: SolveResult


@router.post("/parse-replan")
def parse_replan_route(req: ParseReplanRequest, request: Request, client: LLMClient | None = Depends(llm_for_request)):
    """Free text -> PROPOSED operations. Nothing is executed; the client must confirm and call /replan."""
    ds = request.app.state.dataset
    current = rebuild_client_schedule(req.preferences, req.current_result, ds)
    return parse_replan(req.text, current, req.preferences, ds, client, unavailable_note=request.state.llm_note).model_dump()


# ---- app factory ------------------------------------------------------------------------------------------------------
def create_app(cfg: HConfig | None = None, data_loader=load_dataset) -> FastAPI:
    cfg = cfg or HConfig.from_env()  # raises ConfigError on invalid configuration: fail fast
    cfg.validate()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        t0 = time.perf_counter()
        app.state.dataset = data_loader()  # fail fast with a clear error if data is bad
        log.info("startup", extra={"startup_seconds": round(time.perf_counter() - t0, 3), **cfg.summary(get_settings().mode)})
        yield

    docs = {} if cfg.docs_enabled else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title="Tokyo trip planner (sample data)", lifespan=lifespan, **docs)
    app.state.hconf = cfg
    app.state.limiter = SlidingWindowLimiter(
        {"expensive": cfg.rate_expensive_per_min, "standard": cfg.rate_standard_per_min, "cheap": cfg.rate_cheap_per_min},
        window=cfg.rate_window_seconds)
    app.state.llm_budget = LLMBudget(cfg.llm_daily_call_cap)
    app.include_router(router)
    app.add_middleware(HardeningMiddleware, cfg=cfg, limiter=app.state.limiter)
    app.add_middleware(CORSMiddleware, allow_origins=list(cfg.allowed_origins), allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])  # added last = outermost, so error responses carry CORS headers too

    def rid(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()[:20]]
        return error_response(422, "validation_error", "Request body is invalid.", details, rid(request))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, "Not found." if exc.status_code == 404 else "Request cannot be handled.", None, rid(request))

    @app.exception_handler(ApiError)
    async def _api(request: Request, exc: ApiError):
        return error_response(exc.status, exc.code, exc.message, exc.details, rid(request), exc.headers)

    @app.exception_handler(ReplanError)
    async def _replan(request: Request, exc: ReplanError):
        return error_response(422, exc.code, exc.message, exc.details, rid(request))

    @app.exception_handler(ComparisonInputError)
    async def _cmp(request: Request, exc: ComparisonInputError):
        return error_response(400, "invalid_request", str(exc), None, rid(request))

    @app.exception_handler(InputTooLong)
    async def _long(request: Request, exc: InputTooLong):
        return error_response(422, "input_too_long", str(exc), {"limit": exc.limit}, rid(request))

    @app.exception_handler(EmptyInput)
    async def _empty(request: Request, exc: EmptyInput):
        return error_response(422, "empty_input", str(exc), None, rid(request))

    return app


app = create_app()
