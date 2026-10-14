"""The user-test kit: the script computes medians from a CSV and nothing else; the shipped template is empty; personal data is refused."""
import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("summarise_user_test", ROOT / "scripts" / "summarise_user_test.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(mod.COLUMNS)
        w.writerows(rows)


# three made-up rows used ONLY to test the arithmetic (they are not results and never leave this test)
ROWS = [
    ["P1", "2026-01-01", "tokyo", "yes", "180", "30", "5", "4", "4", "5", "5", "The hotel table was clear"],
    ["P2", "2026-01-01", "tokyo", "yes", "240", "45", "4", "3", "4", "4", "3", ""],
    ["P3", "2026-01-01", "tokyo", "no", "", "20", "2", "3", "2", "3", "2", "I got lost on the sights page"],
]


def test_the_shipped_template_has_a_header_and_no_rows_and_no_pre_filled_summary():
    template = ROOT / "docs" / "user-test" / "results.csv"
    lines = [l for l in template.read_text().splitlines() if l.strip()]
    assert lines == [",".join(mod.COLUMNS)]
    assert mod.load_rows(template) == []
    summary = (ROOT / "docs" / "user-test" / "summary.md").read_text()
    assert "No results yet (N = 0)" in summary and "|" not in summary


def test_medians_are_computed_exactly_and_quotes_are_verbatim(tmp_path):
    p = tmp_path / "r.csv"
    write(p, ROWS)
    text = mod.summarise(mod.load_rows(p))
    assert "N = 3 participants. Completed the 5-minute task: 2 of 3." in text
    # measured minutes of the two completers: 3.0 and 4.0 -> median 3.5 ; estimates 30 and 45 -> 37.5 ; differences 27 and 41 -> 34
    assert "| Time to an itinerary, measured (minutes) | 3.5 | 2 |" in text
    assert "| Same task without the app, participants' own estimate (minutes) | 37.5 | 2 |" in text
    assert "| Estimate minus measured time (minutes) | 34 | 2 |" in text
    # questions over all three: q1 [5,4,2] -> 4 ; q2 [4,3,3] -> 3 ; q5 [5,3,2] -> 3
    assert "| It was clear what to do at each step | 4 | 2 | 5 | 3 |" in text
    assert "| I trust the costs shown | 3 | 3 | 4 | 3 |" in text
    assert "| I would use something like this for a real trip | 3 | 2 | 5 | 3 |" in text
    assert '- "The hotel table was clear" (P1)' in text and '- "I got lost on the sights page" (P3)' in text
    assert "not a controlled comparison" in text and "Small sample" in text


def test_everyone_failing_the_task_is_reported_as_it_is(tmp_path):
    p = tmp_path / "r.csv"
    write(p, [["P1", "d", "tokyo", "no", "", "20", "1", "1", "1", "1", "1", ""]])
    text = mod.summarise(mod.load_rows(p))
    assert "Completed the 5-minute task: 0 of 1" in text and "## Time" not in text and "No quotes were recorded." in text


@pytest.mark.parametrize("bad_row,why", [
    (["P1", "d", "tokyo", "maybe", "10", "5", "3", "3", "3", "3", "3", ""], "completed_task"),
    (["P1", "d", "tokyo", "yes", "10", "5", "6", "3", "3", "3", "3", ""], "q1..q5"),
    (["P1", "d", "tokyo", "yes", "abc", "5", "3", "3", "3", "3", "3", ""], "task_seconds"),
    (["P1", "d", "tokyo", "yes", "10", "5", "3", "3", "3", "3", "3", "mail me at jane.doe@example.com"], "email"),
    (["P1", "d", "tokyo", "yes", "10", "5", "3", "3", "3", "3", "3", "call +65 9123 4567 please"], "phone"),
])
def test_invalid_rows_and_personal_data_are_refused(tmp_path, bad_row, why):
    p = tmp_path / "r.csv"
    write(p, [bad_row])
    with pytest.raises(mod.UserTestError):
        mod.load_rows(p)


def test_duplicate_ids_and_extra_columns_are_refused(tmp_path):
    p = tmp_path / "dup.csv"
    write(p, [ROWS[0], ROWS[0]])
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
