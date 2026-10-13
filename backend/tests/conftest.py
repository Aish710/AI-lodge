"""Writes PASS/FAIL results with timestamps to tests/results/latest.md after every run."""
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

RESULTS = Path(__file__).parent / "results" / "latest.md"
_rows: list[tuple[str, str, str]] = []


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        status = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}[report.outcome]
        _rows.append((datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), status, report.nodeid))


def pytest_sessionfinish(session, exitstatus):
    passed = sum(r[1] == "PASS" for r in _rows)
    failed = sum(r[1] == "FAIL" for r in _rows)
    lines = [
        "# Latest test results",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} by pytest "
        f"(auto-written by tests/conftest.py). Passed: {passed}, failed: {failed}, total: {len(_rows)}.",
        "",
        "| Time | Result | Test |",
        "|---|---|---|",
    ]
    lines += [f"| {t} | {s} | `{n}` |" for t, s, n in _rows]
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text("\n".join(lines) + "\n")


@pytest.fixture(autouse=True)
def _no_network_no_keys(monkeypatch):
    """Tests must never reach the network or depend on an API key: block outbound sockets, clear LLM env vars."""
    def blocked(*a, **k):
        raise RuntimeError("network access is blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    for var in ("LLM_API_KEY", "LLM_MODEL", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _reset_shared_app_state():
    """The module-level app keeps in-memory rate-limit and LLM-budget state; reset it so tests are independent."""
    from app.main import app
    app.state.limiter.reset()
    app.state.llm_budget.reset()
    yield
    app.dependency_overrides.clear()
