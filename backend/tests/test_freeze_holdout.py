import csv
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("freeze_holdout", Path(__file__).resolve().parents[1] / "scripts" / "freeze_holdout.py")
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)

COLS = fh.REQUIRED


def write(path, n=30, author="developer"):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for i in range(n):
            w.writerow(dict(id=f"h{i}", language="en", city="tokyo", entry_point="parse", attack_type="override", trust_boundary="B1", intended_failure="x", author=author, text=f"attack {i}"))


def test_freezing_records_a_hash_and_detects_any_later_change(tmp_path):
    p = tmp_path / "a.csv"
    write(p)
    m = fh.freeze(p)
    assert fh.verify(p) and m["attacks"] == 30 and "developer-generated" in m["label"]
    p.write_text(p.read_text() + "h99,en,tokyo,parse,x,B1,x,developer,sneaky\n")
    assert not fh.verify(p)


def test_a_suite_is_labelled_independent_only_when_every_row_says_so(tmp_path):
    p = tmp_path / "i.csv"
    write(p, author="independent")
    assert fh.freeze(p)["label"] == "independent"


def test_bad_suites_are_refused(tmp_path):
    p = tmp_path / "bad.csv"
    write(p, n=5)
    with pytest.raises(SystemExit):
        fh.freeze(p)
