"""scripts/make_value_claims.py: per-city value statements computed from the evaluation files, never pooled, rounded down, with small-N and unlike-currency caveats."""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_value_claims", ROOT / "scripts" / "make_value_claims.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)
BLOCK = vc.block(ROOT)


def test_there_are_four_statements_per_city_and_no_pooled_figure():
    keys = re.findall(r"^- \*\*(value_[a-z_]+)\*\*", BLOCK, re.M)
    assert len(keys) == 16 and all(any(k.startswith(f"value_{c}_") for c in vc.ORDER) for k in keys)
    assert "pooled" not in BLOCK.lower().replace("never pooled", "")


def test_the_numbers_are_the_evaluation_numbers_and_the_caveats_are_there():
    ev = json.loads((ROOT / "docs/eval-results.json").read_text())["metrics"]
    h = ev["hotel_value"]["vots"]["1000"]
    assert f"in {h['cheapest_by_rate_not_best']} of {h['n_eligible']} eligible trips at the default value of time (1,000 JPY an hour)" in BLOCK
    v = ev["validation"]["solver"]
    assert f"passed {v['pass'] + v['pass_with_warnings']} of {v['n_trips'] - v['no_plan']} plans" in BLOCK
    seoul = [l for l in BLOCK.splitlines() if "value_seoul_travel" in l][0]
    assert seoul.count("N is too small to conclude anything") == 2 and "not a claim about real trips" in seoul
    assert "far from this city's own default of 15,000 KRW" in [l for l in BLOCK.splitlines() if "value_seoul_frequency" in l][0]
    assert "far from" not in [l for l in BLOCK.splitlines() if "value_tokyo_frequency" in l][0]


def test_percentages_are_rounded_down_never_up():
    assert vc.n1(14.157) == "14.1" and vc.n1(7.686) == "7.6" and vc.n1(0.0) == "0.0"


def test_the_committed_claims_file_holds_the_current_block():
    text = (ROOT / "docs/README-claims.md").read_text()
    assert BLOCK.strip() in text, "run scripts/make_value_claims.py after every evaluation run"
    claims = re.findall(r"^- \*\*([^*]+)\*\*: (.*)$", text, re.M)
    assert len(claims) >= 28 and len({k for k, _ in claims}) == len(claims)


def test_apply_replaces_the_block_instead_of_duplicating_it(tmp_path):
    for rel in ("docs/eval-results.json", "docs/city-eval-results.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text((ROOT / rel).read_text())
    for c in vc.ORDER:
        d = tmp_path / "backend/app/data/cities" / c
        d.mkdir(parents=True)
        (d / "city.json").write_text((ROOT / "backend/app/data/cities" / c / "city.json").read_text())
    (tmp_path / "docs/README-claims.md").write_text("# Claims\n\n- **a**: text\n")
    vc.apply(tmp_path)
    vc.apply(tmp_path)
    t = (tmp_path / "docs/README-claims.md").read_text()
    assert t.count(vc.START) == 1 and t.count(vc.END) == 1 and "- **a**: text" in t
