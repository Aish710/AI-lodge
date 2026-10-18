"""Stable identities for plans and scenarios.

A fingerprint is a short sha256 over the canonical JSON of everything that determines a plan: the city data version, the (sorted) hotel(s), the full preferences and the solver
configuration. Two results with the same fingerprint came from identical inputs; the interface refuses to compare results whose fingerprints differ in anything but what a feature
deliberately varied. Nothing here optimises or stores anything.
"""
import hashlib
import json
from functools import lru_cache

from app import config
from app.data.loader import CITIES_DIR, Dataset
from app.schemas import Preferences

SOLVER_VERSION = "cpsat-1"          # bump when the objective or constraint semantics change


@lru_cache(maxsize=16)
def dataset_version(city_id: str) -> str:
    """12 hex chars over the bytes of every JSON file of the city, in name order."""
    h = hashlib.sha256()
    for p in sorted((CITIES_DIR / city_id).glob("*.json")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def plan_fingerprint(prefs: Preferences, hotel_ids: str | list[str], ds: Dataset) -> str:
    ids = [hotel_ids] if isinstance(hotel_ids, str) else sorted(hotel_ids)
    payload = {"city": ds.city.id, "data": dataset_version(ds.city.id), "hotels": ids, "prefs": prefs.model_dump(mode="json"),
               "solver": SOLVER_VERSION, "seed": getattr(config, "SOLVER_SEED", None)}
    return hashlib.sha256(_canon(payload).encode()).hexdigest()[:16]


def stamp(out: dict, prefs: Preferences, hotel_ids, ds: Dataset) -> dict:
    out["fingerprint"] = plan_fingerprint(prefs, hotel_ids, ds)
    out["dataset_version"] = dataset_version(ds.city.id)
    out["solver_version"] = SOLVER_VERSION
    return out
