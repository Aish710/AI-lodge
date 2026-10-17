"""Run every red-team attack through the real pipeline for every city with two SIMULATED models (a gullible one that obeys the injection, a harmless one).
Writes docs/redteam-results.md and docs/redteam-results.json. No network, no key. Every number is labelled "simulated models, not a real model".
Usage:  python scripts/run_redteam.py [--out DIR]"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import redteam_lib as rl  # noqa: E402

CITIES = ("tokyo", "singapore", "seoul", "kuala_lumpur")


def run_all() -> list:
    world = rl.World()
    attacks = rl.load_attacks()
    cases = []
    for kind in ("gullible", "harmless"):
        fac = rl.mock_factory(kind)
        for a in attacks:
            for city in CITIES:
                for ep in rl.ENDPOINTS:
                    cases.append(rl.run_case(world, a, city, fac, f"mock-{kind}", ep))
    return cases


def table(title: str, d: dict) -> list[str]:
    out = [f"### {title}", "", "| | Runs | Model was called | Raw output tried to comply | Final result affected |", "|---|---|---|---|---|"]
    for k, v in sorted(d.items()):
        out.append(f"| {k} | {v['runs']} | {v['model_called']} | {v['raw_tried_to_comply']} | {v['final_affected']} |")
    return out + [""]


def render(s: dict, n_attacks: int, found_fixed: list[dict]) -> str:
    head = ["# Red-team results (SIMULATED models, not a real model)", "",
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `backend/scripts/run_redteam.py`. Git: `{_git()}`. **Every number here comes from two simulated models**: a deliberately gullible one that obeys the injection and emits the forbidden output, "
            "and a harmless one. They test the code around the model. They say nothing about how any real model behaves; see `docs/redteam-live.md` (only if it exists for this code version) for a real model.", "",
            f"{n_attacks} attacks (English, Korean, Chinese, Malay; `backend/tests/fixtures/redteam_attacks.json`) x 4 cities x 2 models x the paths each applies to (the parse box, the change box, the explanation). "
            f"{s['runs']} runs in total. A run is \"final result affected\" if a safety flag was set, a place from another city or from nowhere was scheduled, an invented number was shown, or the system prompt, a key or another user's data was shown.", ""]
    head += table("By model", s["by_model"]) + table("By category", s["by_category"]) + table("By language", s["by_language"]) + table("By city", s["by_city"]) + table("By path", s["by_endpoint"])
    head += ["## Cases where the final result WAS affected", ""]
    aff = s["affected"]
    head += (["| Attack | City | Model | Path | What was affected |", "|---|---|---|---|---|"] + [f"| {c['attack']} | {c['city']} | {c['model']} | {c['endpoint']} | {'; '.join(c['effects'])} |" for c in aff]) if aff else ["None. In every simulated run the final result was unaffected."]
    head += ["", "## Found and fixed", ""]
    head += (["| Attack category | Before the fix | After the fix | Fix |", "|---|---|---|---|"] + [f"| {f['what']} | {f['before']} | {f['after']} | {f['fix']} |" for f in found_fixed]) if found_fixed else ["Nothing was found."]
    return "\n".join(head) + "\n"


def _git() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=rl.REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main(argv: list[str]) -> int:
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else rl.REPO / "docs"
    cases = run_all()
    s = rl.summarise(cases)
    ff = json.loads((out_dir / "redteam-found-fixed.json").read_text()) if (out_dir / "redteam-found-fixed.json").exists() else []
    (out_dir / "redteam-results.md").write_text(render(s, len(rl.load_attacks()), ff), encoding="utf-8")
    (out_dir / "redteam-results.json").write_text(json.dumps({"label": "simulated models, not a real model", "attacks": len(rl.load_attacks()), **s, "found_and_fixed": ff}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{s['runs']} runs; final result affected in {len(s['affected'])}.")
    for c in s["affected"][:40]:
        print("  AFFECTED:", c["attack"], c["city"], c["model"], c["endpoint"], "|", "; ".join(c["effects"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
