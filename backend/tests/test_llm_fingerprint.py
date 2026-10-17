"""The LLM-code fingerprint: the live scripts stamp it, the Proof page compares it with the current one, so a live report made before a change to backend/app/llm reads
"not run on this version" without any prompt change. Python and Node must compute the same value."""
import importlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND / "scripts"))
lc = importlib.import_module("live_common")


def test_python_and_node_compute_the_same_fingerprint():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    out = subprocess.run([node, "-e", "import('./frontend/scripts/llm-fingerprint.mjs').then(m=>console.log(m.llmFingerprint('.')))"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    assert out == lc.llm_fingerprint() and len(out) == 12


def _tree(tmp_path):
    t = tmp_path / "backend"
    shutil.copytree(BACKEND / "app" / "llm", t / "app" / "llm", ignore=shutil.ignore_patterns("__pycache__"))
    return t


def test_the_fingerprint_changes_with_any_byte_of_the_llm_code_and_ignores_caches_and_line_endings(tmp_path, monkeypatch):
    t = _tree(tmp_path)
    monkeypatch.setattr(lc, "ROOT", t)
    base = lc.llm_fingerprint()
    (t / "app" / "llm" / "__pycache__").mkdir()
    (t / "app" / "llm" / "__pycache__" / "x.py").write_text("junk")
    assert lc.llm_fingerprint() == base
    f = t / "app" / "llm" / "claims.py"
    f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
    assert lc.llm_fingerprint() == base
    f.write_bytes(f.read_bytes() + b"# a change\n")
    assert lc.llm_fingerprint() != base
    g = t / "app" / "llm" / "unsupported_terms.json"
    before = lc.llm_fingerprint()
    g.write_bytes(g.read_bytes().replace(b"wheelchair", b"wheelchairs"))
    assert lc.llm_fingerprint() != before


def test_every_live_report_header_carries_the_fingerprint():
    fp = lc.llm_fingerprint()
    import score_gold as sg
    from app.data.loader import load_all_city_datasets
    all_ds = load_all_city_datasets()
    res = {c: {"prompts": 0, "fields": 0, "fields_ok": 0, "exact": 0, "kinds": {k: [0, 0] for k in sg.KINDS}, "failed": [], "calls": 0} for c in sg.CITIES}
    assert f"LLM code fingerprint: `{fp}`" in sg.render(res, all_ds, label="x", model="m", calls=1, endpoint_note="")
    import redteam_live as rt
    assert f"LLM code fingerprint: `{fp}`" in rt.render([], model="m", stamp="", calls=0, plan_n=0)
    spec = importlib.util.spec_from_file_location("score_holdout", ROOT / "scripts" / "score_holdout.py")
    sh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sh)
    assert f"LLM code fingerprint: `{fp}`" in sh.render({c: {"n": 0, "code": [0, 0], "model": [0, 0], "fields": [0, 0], "failed": []} for c in sh.CITIES}, [], all_ds, label="x", model="m", calls=1)
    import ai_selfcheck as sc
    assert "LLM code fingerprint" in Path(sc.__file__).read_text()          # the self-check writes its report from a live client; its header line is pinned here by text


def test_the_shipped_live_reports_predate_the_stamp_so_the_proof_page_will_say_not_run_on_this_version():
    for rel in ("docs/ai-selfcheck.md", "docs/redteam-live.md"):
        text = (ROOT / rel).read_text()
        assert "LLM code fingerprint" not in text or lc.llm_fingerprint() in text, f"{rel} carries an old fingerprint"
