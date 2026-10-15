"""Cooperative cancellation of a running CP-SAT solve.

A route that notices its client has gone calls CancelToken.cancel(): the solve in progress is told to stop (CpSolver.StopSearch) and any
solve that has not started yet is refused, so the solver slot is released within moments instead of when the time limit ends.
If the stop signal is missed (it races the very start of a solve), the slot still frees when that solve's own time limit ends.
The token travels in a ContextVar so the optimiser functions do not need a new parameter."""
import threading
from contextvars import ContextVar


class Cancelled(Exception):
    """The caller went away; the solve was stopped on purpose. Never shown to a user (nobody is listening)."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._solver = None

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            if self._solver is not None:
                self._solver.StopSearch()

    def check(self) -> None:
        if self._event.is_set():
            raise Cancelled()

    def attach(self, solver) -> None:
        with self._lock:
            self._solver = solver

    def detach(self) -> None:
        with self._lock:
            self._solver = None


_current: ContextVar[CancelToken | None] = ContextVar("solver_cancel_token", default=None)


def current_token() -> CancelToken | None:
    return _current.get()


def bind(token: CancelToken):
    """Make `token` the current one for work started from here on (threads started by anyio inherit the context). Returns the reset handle."""
    return _current.set(token)


def unbind(handle) -> None:
    _current.reset(handle)
