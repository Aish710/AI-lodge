"""scripts/check_doc_consistency.py: a stale "not run" next to an existing result file is flagged; a consistent pair passes. Trees are built in tmp_path."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_doc_consistency", ROOT / "scripts" / "check_doc_consistency.py")
cdc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdc)


def tree(tmp_path, *, readme, selfcheck=True, rows=0, extra=None):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/user-test").mkdir()
    for c in ("tokyo", "seoul", "singapore", "kuala_lumpur"):
        (tmp_path / f"backend/app/data/cities/{c}").mkdir(parents=True)
        (tmp_path / f"backend/app/data/cities/{c}/attractions.json").write_text('[{"source_status": "sample"}]')
    (tmp_path / "backend/app/llm").mkdir(parents=True)
    (tmp_path / "backend/app/llm/prompts.py").write_text('PROMPT_VERSION = "2"\n')
    (tmp_path / "README.md").write_text(readme)
    if selfcheck:
        (tmp_path / "docs/ai-selfcheck.md").write_text("# AI self-check (live)\n\nModel: `model-x`. Endpoint host: `gw.example.test`.\n\n**20 of 20 checks passed.**\n")
    (tmp_path / "docs/user-test/results.csv").write_text("a,b\n" + "x,y\n" * rows)
    (tmp_path / "backend/tests/results").mkdir(parents=True)
    (tmp_path / "backend/tests/results/full-suite.json").write_text(json.dumps({"total": 700}))
    (tmp_path / "docs/test-summary-frontend.json").write_text(json.dumps({"suites": [{"suite": "Vitest", "total": 300}, {"suite": "Playwright", "total": 60}]}))
    for rel, text in (extra or {}).items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    return tmp_path


def lines(c):
    return [(f, n) for f, n, _, _ in c]


def test_a_stale_not_run_next_to_an_existing_selfcheck_is_flagged(tmp_path):
    t = tree(tmp_path, readme="# X\n\nLive AI quality has not been measured.\n")
    c = cdc.check(t)
    assert lines(c) == [("README.md", 3)] and "docs/ai-selfcheck.md exists" in c[0][3] and cdc.main(["--root", str(t)]) == 1


def test_a_consistent_pair_passes(tmp_path):
    t = tree(tmp_path, readme="# X\n\nA 20-check live smoke test was run (docs/ai-selfcheck.md). The gold set has not been run.\n")
    assert cdc.check(t) == [] and cdc.main(["--root", str(t)]) == 0


def test_not_run_is_fine_when_there_is_no_result_file(tmp_path):
    t = tree(tmp_path, readme="# X\n\nLive AI quality has not been measured.\n", selfcheck=False)
    assert cdc.check(t) == []


def test_the_user_test_and_the_gold_set_follow_their_own_files(tmp_path):
    t = tree(tmp_path, readme="# X\n\nThe user test has not been run.\n\nThe gold set has not been run.\n", rows=2,
             extra={"docs/eval/gold-results-live-first-run.md": "Model: `m`\n"})
    assert [n for _, n in lines(cdc.check(t))] == [3, 5]


def test_counts_cities_and_verified_must_match_the_generated_facts(tmp_path):
    t = tree(tmp_path, readme="# X\n\n650 backend tests pass. Vitest: 250. 3 sample cities. Current coverage is Tokyo sample data. 5 verified records.\n")
    facts = [f for _, _, _, f in cdc.check(t)]
    assert any("700 backend tests" in f for f in facts) and any("300 vitest" in f for f in facts)
    assert any("4 city packs" in f for f in facts) and any("0 human-verified" in f for f in facts)
    ok = tree(tmp_path / "ok", readme="# X\n\n700 backend tests pass. Vitest: 300. 4 sample cities. 0 verified records.\n") if (tmp_path / "ok").mkdir() is None else None
    assert cdc.check(ok) == []


def test_model_and_host_must_match_the_live_report(tmp_path):
    t = tree(tmp_path, readme="# X\n\nThe live self-check used claude-opus-9 via api.other.example.\n")
    facts = " ".join(f for _, _, _, f in cdc.check(t))
    assert "model-x" in facts and "gw.example.test" in facts


def test_history_logs_and_conditional_vue_copy_are_not_scanned(tmp_path):
    t = tree(tmp_path, readme="# X\n",
             extra={"docs/BUILD_NOTES.md": "Live AI has not been measured.\n",
                    "frontend/src/views/Proof.vue": '<p v-else>Live AI not run yet.</p>\n<p>Live AI has not been measured.</p>\n'})
    c = cdc.check(t)
    assert lines(c) == [("frontend/src/views/Proof.vue", 2)]


def test_the_real_repository_passes_except_for_files_regenerated_in_the_evidence_refresh():
    conflicts = cdc.check(ROOT)
    assert {f for f, _, _, _ in conflicts} <= {"docs/eval-results.md"}, conflicts
