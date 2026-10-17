"""scripts/check_claims.py: every number in the drafts must exist in a generated evidence file; the README keeps its seven headings in order; placeholders are listed."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts" / "check_claims.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

HEADS = "\n\n".join(f"## {i}. {h}\n\ntext" for i, h in enumerate(cc.HEADINGS, start=1))


def tree(tmp_path, readme_body="", dev="", evidence="Passed: 642. 14.1% less travel. 20 of 20 checks passed. 1,000 JPY."):
    (tmp_path / "docs/submission").mkdir(parents=True)
    (tmp_path / "docs/SUBMISSION-FACTS.md").write_text(evidence)
    (tmp_path / "README.md").write_text("# T\n\n" + readme_body + "\n\n" + HEADS + "\n")
    (tmp_path / "docs/submission/devpost.md").write_text(dev)
    (tmp_path / "docs/submission/linkedin.md").write_text("")
    return tmp_path


def test_numbers_that_are_in_the_evidence_pass_including_commas_and_percentages(tmp_path):
    t = tree(tmp_path, "642 backend tests pass, 14.1% less travel, 20 of 20 checks, 1,000 yen.")
    r = cc.check(t, t)
    assert r["unmatched"] == [] and r["heading_ok"] and cc.main(["--root", str(t)]) == 0


def test_an_invented_number_is_listed_with_its_line_and_fails(tmp_path):
    t = tree(tmp_path, "We saved 87% of the time.")
    r = cc.check(t, t)
    assert [(u[0], u[2]) for u in r["unmatched"]] == [("README.md", "87")] and cc.main(["--root", str(t)]) == 1


def test_a_pair_must_exist_as_a_pair_not_just_as_digits(tmp_path):
    t = tree(tmp_path, "It passed 20 of 642 checks.")             # 20 and 642 both exist in the evidence, but not as "20 of 642"
    assert [u[2] for u in cc.check(t, t)["unmatched"]] == ["20 of 642"]


def test_structure_is_not_a_claim_dates_urls_code_versions_list_numbers_and_model_ids(tmp_path):
    body = ("1. first item\n\nSee https://example.com/a/123 and `run 999 times`. Python 3.13 and Node 22 on 2026-10-18, model claude-haiku-4-5-20251001.\n\n```\nnumber 4242\n```\n")
    t = tree(tmp_path, body)
    assert cc.check(t, t)["unmatched"] == []


def test_placeholders_are_listed_and_do_not_count_as_numbers(tmp_path):
    t = tree(tmp_path, "[PLACEHOLDER: video link 12345]", dev="Live: [PLACEHOLDER: live app URL]")
    r = cc.check(t, t)
    assert [p[2] for p in r["placeholders"]] == ["[PLACEHOLDER: video link 12345]", "[PLACEHOLDER: live app URL]"] and r["unmatched"] == []


def test_a_missing_or_reordered_heading_fails(tmp_path):
    t = tree(tmp_path)
    (t / "README.md").write_text("# T\n\n## 2. Solution Overview\n\n## 1. Problem Statement\n")
    assert not cc.check(t, t)["heading_ok"] and cc.main(["--root", str(t)]) == 1


def test_drafts_can_be_checked_against_evidence_in_another_tree(tmp_path):
    ev = tree(tmp_path / "ev")
    dr = tree(tmp_path / "dr", "642 tests")
    assert cc.check(ev, dr)["unmatched"] == []


def test_the_real_drafts_have_no_unmatched_numbers_and_the_required_headings():
    if not (ROOT / "docs/submission/devpost.md").exists():
        return
    r = cc.check(ROOT, ROOT)
    assert r["heading_ok"] and r["unmatched"] == [], r["unmatched"][:5]


# ---- result slots: user-test and human red-team numbers only from their own summary files ----
def test_a_result_slot_accepts_numbers_only_from_its_own_summary(tmp_path):
    t = tree(tmp_path, "**User test (informal, small N):** 5 of 8 people changed their choice.\n\n**Human red team (informal, small N):** Not run yet.")
    (t / "docs/user-test").mkdir(parents=True)
    (t / "docs/user-test/summary.md").write_text("No results yet (N = 0).")
    (t / "docs/SUBMISSION-FACTS.md").write_text("5 of 8 people. 642 tests.")        # the numbers exist elsewhere, but a slot may not use them
    r = cc.check(t, t)
    assert sorted(u[2] for u in r["unmatched"]) == ["5", "8"] and all("slot number not in docs/user-test/summary.md" in u[3] for u in r["unmatched"])
    (t / "docs/user-test/summary.md").write_text("N = 8 participants. 5 of 8 changed their choice.")
    assert cc.check(t, t)["unmatched"] == []


def test_a_slot_that_says_not_run_yet_needs_no_numbers_and_the_human_slot_reads_its_own_file(tmp_path):
    t = tree(tmp_path, "**User test (informal, small N):** Not run yet.\n\n**Human red team (informal, small N):** Human attempts: 4, final result wrong in 1.")
    (t / "docs/user-test").mkdir(parents=True)
    (t / "docs/user-test/redteam-human-summary.md").write_text("Human attempts: 4, final result wrong in 1.")
    assert cc.check(t, t)["unmatched"] == []
    (t / "docs/user-test/redteam-human-summary.md").write_text("Human attempts: 4, final result wrong in 0.")
    assert [u[2] for u in cc.check(t, t)["unmatched"]] == ["1"]
