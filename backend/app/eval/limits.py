"""Deterministic solver limits for evaluation runs.

The shipped limits include wall-clock safety nets (20 s per solve, 5 s per probe/replan, 10 s per hotel comparison). On a slower
machine those could stop a solve earlier than on a fast one and change the plan. For evaluation they are lifted to one hour, so only
the DETERMINISTIC limit (config.SOLVER_MAX_DETERMINISTIC_TIME), a fixed seed and one worker decide when a solve stops.
Wall-clock runtimes are still measured and reported, but separately and labelled machine-dependent.
"""
from contextlib import contextmanager

from app import config

WALL_CLOCK_LIMIT_KEYS = ("SOLVER_MAX_SECONDS", "SOLVER_PROBE_SECONDS", "HOTEL_COMPARE_TIME_LIMIT_SECONDS", "REPLAN_TIME_LIMIT_SECONDS")
LIFTED_SECONDS = 3600.0


def effective_limits() -> dict:
    return {"solver_seed": config.SOLVER_SEED, "solver_workers": 1, "max_deterministic_time": config.SOLVER_MAX_DETERMINISTIC_TIME,
            **{k.lower(): getattr(config, k) for k in WALL_CLOCK_LIMIT_KEYS}}


@contextmanager
def deterministic_limits():
    saved = {k: getattr(config, k) for k in WALL_CLOCK_LIMIT_KEYS}
    try:
        for k in WALL_CLOCK_LIMIT_KEYS:
            setattr(config, k, LIFTED_SECONDS)
        yield effective_limits()
    finally:
        for k, v in saved.items():
            setattr(config, k, v)


@contextmanager
def pace_balance_off():
    """DIAGNOSTIC ONLY (evaluation section A2): switch off the solver's pace-balance term (config.W_PACE = 0) to see how much of the
    travel gap against the baselines it explains. Never used for the headline numbers; restored on exit."""
    saved = config.W_PACE
    try:
        config.W_PACE = 0
        yield
    finally:
        config.W_PACE = saved
