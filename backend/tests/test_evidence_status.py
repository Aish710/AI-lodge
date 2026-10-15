import importlib.util
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evidence_status.py"
spec = importlib.util.spec_from_file_location("evidence_status", SCRIPT)
es = importlib.util.module_from_spec(spec)
spec.loader.exec_module(es)

HEAD = "a7d5be1d8e9161bef0dfca4baa0ff7895caef7cd"
BASE = {"name": "x", "label": "x", "exists": True, "generated": datetime(2026, 10, 14, tzinfo=timezone.utc), "version": None, "dirty": False, "code_commits_since": 0}


def test_matching_clean_version_is_current():
    assert es.status({**BASE, "version": "a7d5be1"}, HEAD) == "CURRENT"


def test_old_version_or_uncommitted_code_is_stale():
    assert es.status({**BASE, "version": "859c357", "code_commits_since": 7}, HEAD) == "STALE"
    assert es.status({**BASE, "version": "a7d5be1", "dirty": True}, HEAD) == "STALE"


def test_file_without_hash_is_stale_only_if_code_changed_after_it():
    assert es.status({**BASE, "code_commits_since": 0}, HEAD) == "CURRENT"
    assert es.status({**BASE, "code_commits_since": 3}, HEAD) == "STALE"


def test_missing_or_unstamped_files_are_not_called_current():
    assert es.status({**BASE, "exists": False}, HEAD) == "MISSING"
    assert es.status({**BASE, "generated": None}, HEAD).startswith("UNKNOWN")


def test_render_lists_every_evidence_file_from_the_repository():
    out = es.render()
    for name, _ in es.EVIDENCE:
        assert f"docs/{name}" in out
