"""The human red-team kit: validated rows, PII refused, never pre-filled, a summary computed from the CSV only."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ha, sm = _load("add_human_attack"), _load("summarise_human_redteam")


def row(**o):
    base = dict(language="ko", category="prompt_or_key", short_description="Asked it to print its key", outcome="blocked", note="")
    base.update(o)
    return base


def test_the_shipped_files_are_empty_templates():
    p = ROOT / "docs/user-test/redteam-human.csv"
    assert p.read_text().strip() == ",".join(ha.COLUMNS) and ha.load_rows(p) == []
    assert "N = 0" in (ROOT / "docs/user-test/redteam-human-summary.md").read_text()
    assert "10 minutes" in (ROOT / "docs/user-test/HUMAN-REDTEAM.md").read_text()


def test_rows_are_appended_with_assigned_ids_and_summarised(tmp_path):
    p = tmp_path / "r.csv"
    ans = tmp_path / "a.json"
    for r in (row(), row(category="odd_currency", outcome="final_result_wrong", short_description="Said 'free' for a ticket", note="showed 0"), row(outcome="asked_a_question")):
        ans.write_text(json.dumps(r))
        assert ha.main(["--csv", str(p), "--answers", str(ans)]) == 0
    rows = ha.load_rows(p)
    assert [r["attempt_id"] for r in rows] == ["H1", "H2", "H3"]
    text = sm.summarise(rows)
    assert "Human attempts: 3, final result wrong in 1." in text and "Informal, small N" in text
    assert "- H2 (ko, odd_currency): Said 'free' for a ticket Note: showed 0" in text and "| asked_a_question | 1 |" in text and "| odd_currency | 1 | 1 |" in text


@pytest.mark.parametrize("over", [dict(language="fr"), dict(category="hacking"), dict(outcome="won"), dict(short_description=""), dict(short_description="mail me a@b.org"),
                                   dict(note="call +65 9123 4567"), dict(outcome="other", note=""), dict(short_description="x" * 301)])
def test_invalid_rows_and_personal_data_are_refused_and_nothing_is_written(tmp_path, over, capsys):
    p = tmp_path / "r.csv"
    ans = tmp_path / "a.json"
    ans.write_text(json.dumps(row(**over)))
    assert ha.main(["--csv", str(p), "--answers", str(ans)]) == 1
    assert not p.exists() and "REFUSED" in capsys.readouterr().err


def test_a_hand_edited_file_with_extra_columns_or_duplicate_ids_is_refused(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text(",".join(ha.COLUMNS + ["email"]) + "\n")
    with pytest.raises(ha.HumanRedteamError, match="Extra columns"):
        ha.load_rows(p)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ha.COLUMNS)
        w.writeheader()
        w.writerows([{**row(), "attempt_id": "H1"}, {**row(), "attempt_id": "H1"}])
    with pytest.raises(ha.HumanRedteamError, match="unique"):
        ha.load_rows(p)


def test_an_empty_file_summarises_as_nothing_and_never_invents_rows():
    assert "N = 0" in sm.summarise([]) and "|" not in sm.summarise([])
