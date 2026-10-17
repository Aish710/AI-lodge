"""OPTIONAL official coordinates check for SINGAPORE against OneMap (Singapore Land Authority). OFFLINE script: it is never imported by the app, the map provider is
unchanged, and it is NOT run by the tests (they use canned responses only).

  ONEMAP_TOKEN=... python scripts/onemap_check.py            report only (writes docs/data-verification/singapore-onemap-check.{md,csv})
  ONEMAP_TOKEN=... python scripts/onemap_check.py --apply    ALSO marks `coordinates` source_checked for clearly matching places (coordinates themselves are never changed)

The token is read from the environment only. It is never printed, logged, written to a file or committed. At most ONEMAP_MAX_CALLS requests are made (one per attraction,
a short pause between them). Each report is stamped with the run date and "token valid at run time" (the calls succeeded). A place counts as a CLEAR MATCH only when
the OneMap result's name or address contains every significant word of our name or of an alias, AND the result is within MATCH_METRES of our coordinates. Everything
else is listed for you to look at; nothing is changed for it.

Terms (read 2026-10-17): the Singapore Open Data Licence page (onemap.gov.sg/legal/opendatalicence.html) requires a conspicuous notice acknowledging the source, e.g.
"Contains information from {dataset} accessed on {date} from {source}, which is made available under the terms of the Singapore Open Data Licence version 1.0
{licence URL}", and states no logo requirement and no rate limit on that page. The OneMap API documentation page is a JavaScript site that could not be read by the
tool used to prepare this script, so the endpoint, header and limits below are from general knowledge: if a call fails, check https://www.onemap.gov.sg/apidocs/ first."""
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "https://www.onemap.gov.sg/api/common/elastic/search"
ONEMAP_MAX_CALLS = 30
MATCH_METRES = 300
ATTRIBUTION = ("Contains information from OneMap search results accessed on {d} from the Singapore Land Authority (OneMap), which is made available under the terms of "
               "the Singapore Open Data Licence version 1.0 (https://www.onemap.gov.sg/legal/opendatalicence.html).")
STOP = {"the", "of", "and", "at", "by", "in", "a", "an"}


def metres(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def words(s: str) -> set[str]:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return {w for w in re.split(r"[^a-z0-9]+", s) if w and w not in STOP}


def best_match(name: str, aliases: list[str], lat: float, lon: float, results: list[dict]) -> dict | None:
    """The nearest result whose text contains every significant word of our name or of one of our (ASCII) aliases; else None."""
    wanted = [w for w in (words(name), *(words(a) for a in aliases)) if w]
    ok = []
    for r in results:
        text = words(f"{r.get('SEARCHVAL', '')} {r.get('BUILDING', '')} {r.get('ADDRESS', '')}")
        if any(w <= text for w in wanted):
            ok.append((metres(lat, lon, float(r["LATITUDE"]), float(r["LONGITUDE"])), r))
    return min(ok, key=lambda t: t[0])[1] if ok else None


def decide(a: dict, results: list[dict]) -> dict:
    m = best_match(a["name"], a["aliases"], a["lat"], a["lon"], results)
    if not m:
        return {"id": a["id"], "our_name": a["name"], "status": "no_match", "matched_name": "", "address": "", "lat": "", "lon": "", "metres": ""}
    d = metres(a["lat"], a["lon"], float(m["LATITUDE"]), float(m["LONGITUDE"]))
    return {"id": a["id"], "our_name": a["name"], "status": "match" if d <= MATCH_METRES else "too_far", "matched_name": m.get("SEARCHVAL", ""),
            "address": m.get("ADDRESS", ""), "lat": m["LATITUDE"], "lon": m["LONGITUDE"], "metres": round(d)}


def render(rows: list[dict], today: str) -> str:
    n = sum(r["status"] == "match" for r in rows)
    out = [f"# Singapore coordinates vs OneMap (generated {today})", "",
           f"Run on {today}; the token was valid at run time (every call succeeded). Produced by `backend/scripts/onemap_check.py`. A place is a clear match only if the OneMap result "
           f"contains every significant word of our name (or an alias) and lies within {MATCH_METRES} m of our coordinates. **{n} of {len(rows)} clear matches.** Our coordinates were not changed.", "",
           ATTRIBUTION.format(d=today), "", "| Place | Status | OneMap name | Address | Distance (m) |", "|---|---|---|---|---|"]
    out += [f"| {r['our_name']} | {r['status']} | {r['matched_name']} | {r['address']} | {r['metres']} |" for r in rows]
    out += ["", "Rows that are not clear matches need a human look (a street such as Haji Lane, a wide area such as Sentosa or the Botanic Gardens, or a renamed place).", ""]
    return "\n".join(out)


def search(token: str, query: str) -> list[dict]:
    import urllib.parse
    import urllib.request
    url = f"{ENDPOINT}?{urllib.parse.urlencode({'searchVal': query, 'returnGeom': 'Y', 'getAddrDetails': 'Y', 'pageNum': 1})}"
    req = urllib.request.Request(url, headers={"Authorization": token, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:           # noqa: S310 (fixed https endpoint)
        return json.loads(resp.read().decode("utf-8")).get("results", [])


def main(argv: list[str], fetch=search, root: Path = ROOT, sleep=time.sleep) -> int:
    token = os.environ.get("ONEMAP_TOKEN", "")
    if not token:
        print("ONEMAP_TOKEN is not set, so nothing was called. Export your OneMap token in this shell (it is never printed or stored) and run again.")
        return 0
    d = root / "backend" / "app" / "data" / "cities" / "singapore"
    atts = json.loads((d / "attractions.json").read_text(encoding="utf-8"))
    if len(atts) > ONEMAP_MAX_CALLS:
        print(f"Refusing: {len(atts)} attractions would exceed the cap of {ONEMAP_MAX_CALLS} calls.")
        return 0
    rows, calls = [], 0
    for a in atts:
        try:
            calls += 1
            results = fetch(token, a["name"])
        except Exception as e:                                       # never echo the token or the request headers
            print(f"Stopped after {calls - 1} call(s): the request failed ({type(e).__name__}). The token may have expired, or the endpoint changed. Nothing was written.")
            return 2
        rows.append(decide(a, results))
        sleep(1.0)
    today = date.today().isoformat()
    out = root / "docs" / "data-verification"
    out.mkdir(parents=True, exist_ok=True)
    (out / "singapore-onemap-check.md").write_text(render(rows, today), encoding="utf-8")
    with open(out / "singapore-onemap-check.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["run_date", "token", *rows[0]])
        w.writeheader()
        w.writerows({"run_date": today, "token": "valid at run time", **r} for r in rows)
    if "--apply" in argv:
        clear = {r["id"] for r in rows if r["status"] == "match"}
        for a in atts:
            if a["id"] in clear:
                a.setdefault("verification", {})["coordinates"] = {"state": "source_checked", "source_url": "https://www.onemap.gov.sg/", "checked_on": today, "checked_by": "web-assisted",
                    "note": f"A OneMap search for the place name returned a result within {MATCH_METRES} m of these coordinates (docs/data-verification/singapore-onemap-check.md)."}
        (d / "attractions.json").write_text(json.dumps(atts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{calls} call(s) made. {sum(r['status'] == 'match' for r in rows)} of {len(rows)} clear matches. Reports written to {out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
