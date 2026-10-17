"""Addendum C: per-field verification records, counts computed from the data, the web-assisted findings, the sheet and import scripts, and the data sanity checks.
No network. Singapore only is checked; every other city stays unchecked."""
import csv
import importlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.data.loader import load_all_city_datasets
from app.main import app
from app.schemas import FieldVerification
from app.verification import count_dataset

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND / "scripts"))
counts_mod = importlib.import_module("make_verification_counts")
sheets = importlib.import_module("make_verification_sheets")
imp = importlib.import_module("import_human_verification")
apply_mod = importlib.import_module("apply_verification_findings")
sanity = importlib.import_module("check_data_sanity")
ALL = load_all_city_datasets()


# ---- the record ----
def test_the_record_rules():
    ok = dict(source_url="https://example.gov.sg/x", checked_on="2026-10-17", checked_by="web-assisted")
    assert FieldVerification(state="source_checked", **ok).state == "source_checked"
    for bad in (dict(state="source_checked"), dict(state="source_checked", source_url="u", checked_on="2026-10-17"),
                dict(state="human_verified", checked_on="2026-10-17", checked_by="web-assisted"), dict(state="human_verified"),
                dict(state="not_applicable"), dict(state="source_checked", **{**ok, "checked_on": "17/10/2026"})):
        with pytest.raises(ValidationError):
            FieldVerification(**bad)
    assert FieldVerification(state="human_verified", checked_on="2026-10-17", checked_by="human").state == "human_verified"


def test_every_record_is_still_sample_and_nothing_is_human_verified_by_default():
    for ds in ALL.values():
        for a in ds.attractions.values():
            assert a.provenance.source_status == "sample"
            for r in (a.verification.__dict__.values() if a.verification else []):
                assert getattr(r, "state", None) != "human_verified"
        assert count_dataset(ds)["human_verified"] == 0


def test_singapore_findings_are_official_dated_and_web_assisted_and_other_cities_are_unchecked():
    sg = ALL["singapore"]
    n = 0
    for a in sg.attractions.values():
        for g in ("hours", "admission", "booking", "coordinates", "name_area"):
            r = getattr(a.verification, g)
            if r.state == "source_checked":
                n += 1
                assert r.checked_by == "web-assisted" and r.checked_on == "2026-10-17" and r.source_url.startswith("https://")
        assert a.verification.visit_duration.state == "not_applicable" and a.verification.visit_duration.note
    assert n == count_dataset(sg)["source_checked"] > 0
    assert all(h.verification.nightly_rate.state == "not_applicable" for h in sg.hotels.values())
    for cid, ds in ALL.items():
        if cid != "singapore":
            assert count_dataset(ds)["source_checked"] == 0


def test_counts_json_is_fresh_and_the_api_summary_matches():
    saved = json.loads((ROOT / "docs" / "data-verification" / "counts.json").read_text())
    assert saved == counts_mod.build("singapore"), "run backend/scripts/make_verification_counts.py"
    with TestClient(app) as c:
        v = c.get("/data/summary", params={"city_id": "singapore"}).json()["verification"]
    assert v == count_dataset(ALL["singapore"]) and v["total_fields"] == sum(v[s] for s in counts_mod.STATES)
    assert saved["readme_sentence"].startswith("Singapore: ") and "other cities unchecked; all data is still sample data" in saved["readme_sentence"]


# ---- the sheet and the import ----
def tree(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(BACKEND / "app/data/cities/singapore", root / "backend/app/data/cities/singapore")
    (root / "docs/data-verification").mkdir(parents=True)
    return root


def test_the_sheet_has_low_confidence_first_blank_answers_and_urls_only_where_found():
    rows = sheets.rows_for("singapore", ALL["singapore"])
    conf = [r["confidence"] for r in rows]
    assert conf == sorted(conf, key=lambda c: sheets.ORDER[c]) and conf[0] == "low" and conf[-1] == "high"
    assert all(r["verified_value"] == r["verified_by"] == r["date"] == "" for r in rows)
    with_url = [r for r in rows if r["source_url"]]
    assert with_url and all(r["confidence"] == "high" for r in with_url)
    n_fields = count_dataset(ALL["singapore"])["total_fields"] - count_dataset(ALL["singapore"])["not_applicable"]
    assert len(rows) == n_fields                               # one row per checkable field and alias; not-applicable ones are left out
    for r in rows:
        if r["field"] == "hours":
            assert sheets.parse_hours(r["value_in_app"])        # the format a person types back round-trips


def _sheet(tmp_path, root, edits):
    p = root / "docs/data-verification/singapore.csv"
    sheets.write("singapore", root, ds=ALL["singapore"])
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for key, upd in edits.items():
        for r in rows:
            if (r["id"], r["field"]) == key:
                r.update(upd)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sheets.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


def test_import_sets_human_verified_only_for_complete_rows_and_applies_corrections(tmp_path):
    root = tree(tmp_path)
    p = _sheet(tmp_path, root, {("sentosa", "admission"): dict(verified_value="4", verified_by="AB", date="2026-10-18"),
                                ("jewel_changi", "booking"): dict(verified_value="no", verified_by="AB", date="2026-10-18")})
    res = imp.import_sheet("singapore", p, root)
    assert res["accepted"] == 2 and ("sentosa", "admission", "6", "4") in res["corrections"]
    atts = {a["id"]: a for a in json.loads((root / "backend/app/data/cities/singapore/attractions.json").read_text())}
    assert atts["sentosa"]["admission_cost"] == 4
    assert atts["sentosa"]["verification"]["admission"]["state"] == "human_verified" and atts["sentosa"]["verification"]["admission"]["checked_by"] == "human"
    assert atts["jewel_changi"]["verification"]["booking"]["state"] == "human_verified"
    assert atts["sentosa"]["provenance"]["source_status"] == "sample"
    assert atts["maxwell_food_centre"]["verification"]["hours"]["state"] == "unchecked"          # untouched rows stay as they were
    from app.data.loader import load_city_dataset
    # the imported file still loads under the strict schema
    import app.data.loader as loader
    monkey = loader.CITIES_DIR
    loader.CITIES_DIR = root / "backend/app/data/cities"
    try:
        assert load_city_dataset("singapore").attractions["sentosa"].admission_cost == 4
    finally:
        loader.CITIES_DIR = monkey


@pytest.mark.parametrize("upd,why", [
    (dict(verified_value="4", verified_by="AB", date=""), "all"), (dict(verified_value="4", verified_by="", date="2026-10-18"), "all"),
    (dict(verified_value="", verified_by="AB", date="2026-10-18"), "all"), (dict(verified_value="4", verified_by="a.b@example.com", date="2026-10-18"), "email"),
    (dict(verified_value="4", verified_by="AB", date="18/10/2026"), "date"), (dict(verified_value="abc", verified_by="AB", date="2026-10-18"), "cannot read")])
def test_incomplete_or_invalid_rows_are_refused_and_nothing_is_imported(tmp_path, upd, why):
    root = tree(tmp_path)
    before = (root / "backend/app/data/cities/singapore/attractions.json").read_text()
    p = _sheet(tmp_path, root, {("sentosa", "admission"): upd, ("jewel_changi", "booking"): dict(verified_value="no", verified_by="AB", date="2026-10-18")})
    with pytest.raises(imp.ImportError_):
        imp.import_sheet("singapore", p, root)
    assert (root / "backend/app/data/cities/singapore/attractions.json").read_text() == before


def test_a_blank_sheet_imports_nothing(tmp_path):
    root = tree(tmp_path)
    p = _sheet(tmp_path, root, {})
    assert imp.import_sheet("singapore", p, root)["accepted"] == 0


# ---- applying findings ----
def test_findings_refuse_to_overwrite_a_value_that_is_not_the_recorded_old_one(tmp_path):
    root = tree(tmp_path)
    (root / "docs/data-verification/singapore-findings.json").write_text((ROOT / "docs/data-verification/singapore-findings.json").read_text())
    f = root / "backend/app/data/cities/singapore/attractions.json"
    d = json.loads(f.read_text())
    next(a for a in d if a["id"] == "sultan_mosque_haji_lane")["opening_hours"]["mon"] = [["08:00", "09:00"]]   # not the old value, not the new one
    f.write_text(json.dumps(d))
    with pytest.raises(apply_mod.FindingsError, match="refusing to overwrite"):
        apply_mod.apply("singapore", root)


def test_applying_the_findings_is_repeatable(tmp_path):
    root = tree(tmp_path)
    (root / "docs/data-verification/singapore-findings.json").write_text((ROOT / "docs/data-verification/singapore-findings.json").read_text())
    assert apply_mod.apply("singapore", root) == []                  # the repository data already holds the new values
    assert "Sultan" in (root / "docs/data-verification/CHANGELOG.md").read_text() or "sultan_mosque_haji_lane" in (root / "docs/data-verification/CHANGELOG.md").read_text()


# ---- sanity ----
def test_singapore_passes_the_data_sanity_checks():
    assert sanity.problems("singapore") == []


def test_the_sanity_checks_catch_bad_data():
    ds = ALL["singapore"]
    a = next(iter(ds.attractions.values()))
    bad = {**ds.attractions, a.id: a.model_copy(update={"lat": 50.0, "duration_minutes": 5, "aliases": ["sentosa"]})}
    from dataclasses import replace
    msgs = " ".join(sanity.problems("singapore", replace(ds, attractions=bad)))
    assert "outside the singapore bounding box" in msgs and "duration 5 min" in msgs and "clashes" in msgs
    cheap = {k: h.model_copy(update={"nightly_rate": 1}) for k, h in ds.hotels.items()}
    assert "plausible band" in " ".join(sanity.problems("singapore", replace(ds, hotels=cheap)))
    flat = {k: a2.model_copy(update={"advance_booking_required": False}) for k, a2 in ds.attractions.items()}
    assert "timed-entry" in " ".join(sanity.problems("singapore", replace(ds, attractions=flat)))


# ---- the OneMap script (canned responses; never the network, never a token) ----
onemap = importlib.import_module("onemap_check")


def test_onemap_needs_a_token_and_makes_no_call_without_one(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ONEMAP_TOKEN", raising=False)
    calls = []
    assert onemap.main([], fetch=lambda *a: calls.append(a), root=tree(tmp_path)) == 0
    assert calls == [] and "not set" in capsys.readouterr().out


def test_onemap_matches_clear_places_lists_the_rest_and_never_prints_the_token(tmp_path, monkeypatch, capsys):
    secret = "TOKEN-DO-NOT-LEAK-123"
    monkeypatch.setenv("ONEMAP_TOKEN", secret)
    root = tree(tmp_path)
    seen = []

    def fetch(token, q):
        seen.append(token)
        if q == "Gardens by the Bay":
            return [{"SEARCHVAL": "GARDENS BY THE BAY", "ADDRESS": "18 MARINA GARDENS DRIVE", "LATITUDE": "1.2816", "LONGITUDE": "103.8636"}]
        if q == "Sentosa":
            return [{"SEARCHVAL": "SENTOSA GOLF CLUB", "ADDRESS": "27 BUKIT MANIS ROAD", "LATITUDE": "1.25", "LONGITUDE": "103.82"}]   # a different, far place
        return []
    assert onemap.main(["--apply"], fetch=fetch, root=root, sleep=lambda s: None) == 0
    out = capsys.readouterr()
    assert secret not in out.out + out.err and set(seen) == {secret} and len(seen) == 10 <= onemap.ONEMAP_MAX_CALLS
    md = (root / "docs/data-verification/singapore-onemap-check.md").read_text()
    csv_text = (root / "docs/data-verification/singapore-onemap-check.csv").read_text()
    assert secret not in md + csv_text and "token was valid at run time" in md and "Singapore Open Data Licence" in md and "valid at run time" in csv_text
    assert "| Gardens by the Bay | match |" in md and "| Sentosa | too_far |" in md and "| Maxwell Food Centre | no_match |" in md
    atts = {a["id"]: a for a in json.loads((root / "backend/app/data/cities/singapore/attractions.json").read_text())}
    assert atts["gardens_by_the_bay"]["verification"]["coordinates"]["state"] == "source_checked"
    assert atts["sentosa"]["verification"]["coordinates"]["state"] == "unchecked" and atts["gardens_by_the_bay"]["lat"] == 1.2816   # coordinates never changed


def test_onemap_stops_without_writing_anything_when_a_call_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ONEMAP_TOKEN", "x")
    root = tree(tmp_path)

    def boom(token, q):
        raise OSError("HTTP 401 for header Authorization: x")
    assert onemap.main([], fetch=boom, root=root, sleep=lambda s: None) == 2
    assert "Nothing was written" in capsys.readouterr().out and not (root / "docs/data-verification/singapore-onemap-check.md").exists()
