"""The user-test kit (Addendum A): the script computes counts and medians from a CSV and nothing else; the shipped template is empty; personal data is refused;
quotes appear only where quote_ok is yes; add_user_test_row.py validates the same way."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load("summarise_user_test")
adder = _load("add_user_test_row")


def row(**over):
    base = dict(participant_id="P1", city="tokyo", winner_changed_in_comparison="yes", time_to_first_plan_seconds="180", hotel_before="Hotel A", confidence_before="3",
                hotel_after="Hotel B", confidence_after="4", changed_choice="yes", why_changed="Travel time was shorter", self_estimated_manual_minutes="60",
                rating_clear="5", rating_trust="4", rating_use="4", rating_ai_helped="3", rating_ai_findable="2", confused_most="Where the AI box was", quote_ok="yes")
    base.update(over)
    return base


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mod.COLUMNS)
        w.writeheader()
        w.writerows(rows)


# made-up rows used ONLY to test the arithmetic (they are not results and never leave this test)
ROWS = [row(), row(participant_id="P2", city="seoul", winner_changed_in_comparison="no", time_to_first_plan_seconds="240", confidence_before="4", confidence_after="4",
              changed_choice="no", why_changed="", self_estimated_manual_minutes="90", quote_ok="no", confused_most="Private words"),
        row(participant_id="P3", winner_changed_in_comparison="yes", time_to_first_plan_seconds="300", confidence_before="2", confidence_after="5", changed_choice="yes",
            self_estimated_manual_minutes="45", rating_clear="3", rating_ai_findable="4", confused_most="")]


def test_the_shipped_template_has_a_header_and_no_rows_and_no_pre_filled_summary():
    template = ROOT / "docs" / "user-test" / "results.csv"
    assert [l for l in template.read_text().splitlines() if l.strip()] == [",".join(mod.COLUMNS)]
    assert mod.load_rows(template) == []
    summary = (ROOT / "docs" / "user-test" / "summary.md").read_text()
    assert "No results yet (N = 0)" in summary and "|" not in summary


def test_the_columns_are_exactly_the_agreed_ones():
    assert mod.COLUMNS == ["participant_id", "city", "winner_changed_in_comparison", "time_to_first_plan_seconds", "hotel_before", "confidence_before", "hotel_after",
                           "confidence_after", "changed_choice", "why_changed", "self_estimated_manual_minutes", "rating_clear", "rating_trust", "rating_use",
                           "rating_ai_helped", "rating_ai_findable", "confused_most", "quote_ok"]


def test_counts_and_medians_are_computed_exactly(tmp_path):
    p = tmp_path / "r.csv"
    write(p, ROWS)
    text = mod.summarise(mod.load_rows(p))
    assert "N = 3 participants. Informal, small sample" in text and "nothing here is statistically significant" in text
    assert "| Landing to first plan, with the app, timed by the observer (minutes) | 4 | 3 |" in text            # median 240 s
    assert "(self-reported, minutes) | 60 | 3 |" in text                                                          # median of 60, 90, 45
    assert "| Median confidence (1 to 5) before seeing the comparison, nightly rates only | 3 | 3 |" in text      # 3, 4, 2
    assert "| Median confidence (1 to 5) after seeing the comparison | 4 | 3 |" in text                          # 4, 4, 5
    assert "| Changed their hotel choice after the comparison | 2 of 3 | 3 |" in text
    assert "where the app's best-value hotel differed from the cheapest-rate hotel | 2 of 2 | 2 |" in text
    assert "where the best-value hotel was also the cheapest-rate hotel | 0 of 1 | 1 |" in text
    assert "| The AI part helped | 3 | 3 | 3 | 3 |" in text and "| It was easy to find the AI | 2 | 2 | 4 | 3 |" in text
    assert "not a controlled comparison" in text and "%" not in text.replace("Informal", "")


def test_quotes_only_where_quote_ok_is_yes(tmp_path):
    p = tmp_path / "r.csv"
    write(p, ROWS)
    text = mod.summarise(mod.load_rows(p))
    assert '- "Travel time was shorter" (P1)' in text and '- "Where the AI box was" (P1)' in text
    assert "Private words" not in text
    write(p, [row(quote_ok="no")])
    assert "No quotes are shown" in mod.summarise(mod.load_rows(p))


@pytest.mark.parametrize("over", [
    dict(participant_id="Jane"), dict(participant_id="P11"), dict(city="paris"), dict(changed_choice="maybe"), dict(confidence_before="6"), dict(rating_trust="0"),
    dict(time_to_first_plan_seconds="abc"), dict(why_changed="mail me at jane.doe@example.com"), dict(confused_most="call +65 9123 4567 please"),
    dict(hotel_before="x@y.org"),
])
def test_invalid_rows_and_personal_data_are_refused(tmp_path, over):
    p = tmp_path / "r.csv"
    write(p, [row(**over)])
    with pytest.raises(mod.UserTestError):
        mod.load_rows(p)


def test_duplicate_ids_and_extra_columns_are_refused(tmp_path):
    p = tmp_path / "dup.csv"
    write(p, [row(), row()])
    with pytest.raises(mod.UserTestError, match="unique"):
        mod.load_rows(p)
    q = tmp_path / "extra.csv"
    q.write_text(",".join(mod.COLUMNS + ["email"]) + "\n")
    with pytest.raises(mod.UserTestError, match="Extra columns"):
        mod.load_rows(q)


def test_main_writes_the_summary_and_reports_errors_with_a_nonzero_exit(tmp_path):
    p, out = tmp_path / "r.csv", tmp_path / "s.md"
    write(p, ROWS)
    assert mod.main(["--csv", str(p), "--out", str(out)]) == 0 and "N = 3 participants" in out.read_text()
    p.write_text("not,the,right,header\n")
    assert mod.main(["--csv", str(p), "--out", str(out)]) == 1


def test_add_row_appends_one_validated_row_and_refuses_an_email(tmp_path, capsys):
    csv_path = tmp_path / "r.csv"
    ans = tmp_path / "a.json"
    ans.write_text(json.dumps(row()))
    assert adder.main(["--csv", str(csv_path), "--answers", str(ans)]) == 0
    assert len(mod.load_rows(csv_path)) == 1
    assert adder.main(["--csv", str(csv_path), "--answers", str(ans)]) == 1                      # the same id twice
    ans.write_text(json.dumps(row(participant_id="P2", why_changed="write to me at a.b@example.com")))
    assert adder.main(["--csv", str(csv_path), "--answers", str(ans)]) == 1
    assert "email address or phone number" in capsys.readouterr().err
    assert len(mod.load_rows(csv_path)) == 1                                                       # nothing was appended


def test_prompts_cover_every_column_exactly_once():
    assert list(adder.PROMPTS) == mod.COLUMNS


def test_study_v2_with_no_rows_says_not_conducted_and_invents_nothing(tmp_path):
    import subprocess, sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    (tmp_path / "docs/user-test").mkdir(parents=True)
    (tmp_path / "docs/user-test/study-v2-results.csv").write_text((repo / "docs/user-test/study-v2-results.csv").read_text())
    subprocess.run([sys.executable, str(repo / "scripts/summarise_study_v2.py"), "--root", str(tmp_path)], check=True, capture_output=True)
    text = (tmp_path / "docs/user-test/study-v2-summary.md").read_text()
    assert "No results yet (N = 0)" in text and "not been conducted" in text
    assert "NOT CONDUCTED" in (repo / "docs/user-test/STUDY-PLAN-v2.md").read_text()


def test_study_v2_summary_reports_the_new_measures_from_synthetic_test_rows_only(tmp_path):
    """Synthetic rows in a temp dir exercise the arithmetic. They are test fixtures, not participants, and are never written to the repository."""
    import subprocess, sys
    repo = Path(__file__).resolve().parents[2]
    (tmp_path / "docs/user-test").mkdir(parents=True)
    head = (repo / "docs/user-test/study-v2-results.csv").read_text().strip().split(",")
    rows = [{"participant_id": "T1", "workflow": "x", "task": "12", "completed": "yes", "seconds": "30", "errors": "0", "edit_seconds": "20", "ai_edit_condition": "manual", "error_recovered": "yes", "cash_total_correct": "right"},
            {"participant_id": "T1", "workflow": "x", "task": "12", "completed": "yes", "seconds": "20", "errors": "1", "edit_seconds": "10", "ai_edit_condition": "assistant", "ai_edit_helpful_1to5": "4"}]
    with open(tmp_path / "docs/user-test/study-v2-results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head); w.writeheader(); [w.writerow(r) for r in rows]
    subprocess.run([sys.executable, str(repo / "scripts/summarise_study_v2.py"), "--root", str(tmp_path)], check=True, capture_output=True)
    text = (tmp_path / "docs/user-test/study-v2-summary.md").read_text()
    assert "Median edit seconds, manual | 1 | 20.0" in text and "Median edit seconds, assistant | 1 | 10.0" in text and "Recovered from a bad change unaided | 1 of 1" in text
