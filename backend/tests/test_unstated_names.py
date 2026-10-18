"""A place the model names but the user never wrote must not become a must-visit, skip, removal or repair target.

Reproduces the live gold miss `kuala_lumpur_ambiguous_1` ("2 days in KL, I want to see the temple."): the model answers with a specific temple from its own knowledge. The name resolves,
so without this guard the plan would silently require a place the user did not choose.
"""
from app.data.loader import load_all_city_datasets
from app.llm.extract import extract_preferences
from app.llm.names import stated_in_text
from llm_mock import MockLLM, extraction

KL = load_all_city_datasets()["kuala_lumpur"]
TEXT = "2 days in KL, I want to see the temple."


def test_a_guessed_place_is_not_added_and_the_ambiguity_is_reported():
    r = extract_preferences(TEXT, KL, MockLLM([extraction(days=2, must_visit_names=["Batu Caves"], interests=["temple"])]), all_datasets={"kuala_lumpur": KL})
    assert r.draft is not None and r.draft.must_visit == []                      # nothing was guessed for the user
    assert any(a.input.lower().strip("the ").strip() in ("temple", "temples") for a in r.ambiguities) or r.unresolved_names
    assert any("did not name" in (u.message or "") for u in r.unresolved_names)


def test_a_place_the_user_really_wrote_still_resolves_including_by_alias_and_script():
    ok = extract_preferences("2 days in KL, I want to see Batu Caves.", KL, MockLLM([extraction(days=2, must_visit_names=["Batu Caves"])]), all_datasets={"kuala_lumpur": KL})
    assert ok.draft.must_visit == ["batu_caves"]
    zh = extract_preferences("2 days in KL, 我想去黑风洞", KL, MockLLM([extraction(days=2, must_visit_names=["Batu Caves"])]), all_datasets={"kuala_lumpur": KL})
    assert zh.draft.must_visit == ["batu_caves"]                                # the dataset alias is in the user's own text: stated


def test_stated_in_text_is_a_pure_code_check():
    assert stated_in_text("batu_caves", "Batu Caves", KL, "i want batu caves")
    assert not stated_in_text("batu_caves", "Batu Caves", KL, "i want to see the temple")
    assert stated_in_text("thean_hou_temple", "temple of heaven", KL, "visit thean hou")      # any of the place's own names counts
