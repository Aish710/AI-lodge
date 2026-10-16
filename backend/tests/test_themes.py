"""Every attraction maps to exactly one known theme; the committed inventory is the generator's output; counts match."""
import importlib.util
import json
from collections import Counter
from pathlib import Path

from app.data.loader import load_all_city_datasets

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "frontend" / "src" / "lib" / "themes.json").read_text(encoding="utf-8"))
ALL = load_all_city_datasets()
IDS = {t["id"] for t in CFG["themes"]}
spec = importlib.util.spec_from_file_location("make_theme_inventory", ROOT / "backend" / "scripts" / "make_theme_inventory.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_every_category_in_every_city_is_mapped_to_a_known_theme():
    cats = {a.category for ds in ALL.values() for a in ds.attractions.values()}
    assert cats <= set(CFG["category"]), cats - set(CFG["category"])
    assert set(CFG["category"].values()) <= IDS


def test_every_attraction_maps_to_exactly_one_theme_and_overrides_are_real():
    all_ids = {a.id for ds in ALL.values() for a in ds.attractions.values()}
    assert set(CFG["overrides"]) <= all_ids
    for o in CFG["overrides"].values():
        assert o["theme"] in IDS and o["why"]
    for ds in ALL.values():
        for a in ds.attractions.values():
            assert gen.theme_of(a, CFG) in IDS


def test_counts_per_theme_per_city_match_the_documented_inventory():
    expected = {"tokyo": {"sightseeing": 10, "shopping": 1, "food": 1}, "singapore": {"sightseeing": 8, "shopping": 1, "food": 1},
                "seoul": {"sightseeing": 7, "shopping": 2, "food": 1}, "kuala_lumpur": {"sightseeing": 8, "shopping": 1, "food": 1}}
    for cid, ds in ALL.items():
        got = Counter(gen.theme_of(a, CFG) for a in ds.attractions.values())
        assert dict(got) == expected[cid], cid
        assert sum(got.values()) == len(ds.attractions)


def test_the_committed_inventory_is_what_the_generator_produces():
    committed = (ROOT / "docs" / "design" / "themes-inventory.md").read_text(encoding="utf-8")
    assert committed == gen.render()
    assert "Limited" in committed or "limited" in committed
