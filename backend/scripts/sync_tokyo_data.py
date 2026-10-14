"""Tokyo's data exists in two places: the pack the API serves (app/data/cities/tokyo/, the SOURCE OF TRUTH) and a mirror at app/data/ that
`load_dataset()` reads by default (used by many tests and by the Tokyo prompt constants). This script keeps the mirror identical.
  python scripts/sync_tokyo_data.py          copy the pack's files over the mirror
  python scripts/sync_tokyo_data.py --check  exit 1 if they differ (the test suite runs the same check)"""
import shutil
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "app" / "data"
SRC = DATA / "cities" / "tokyo"
FILES = ("attractions.json", "hotels.json", "travel_times.json")


def differing() -> list[str]:
    return [f for f in FILES if (SRC / f).read_bytes() != (DATA / f).read_bytes()]


if __name__ == "__main__":
    bad = differing()
    if "--check" in sys.argv:
        print("identical" if not bad else f"DIFFERENT: {', '.join(bad)} (source of truth: app/data/cities/tokyo/; run without --check to sync)")
        sys.exit(1 if bad else 0)
    for f in bad:
        shutil.copyfile(SRC / f, DATA / f)
    print("synced: " + (", ".join(bad) if bad else "nothing to do"))
