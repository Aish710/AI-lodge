"""Safety mutation testing. For each safeguard, run the safety-relevant tests with ONE safeguard disabled in-process (tests/safety_mutation_plugin.py) and record which tests notice.

No production file or configuration is touched and no weakened safeguard is ever committed: the mutation lives only in the child pytest process. A mutation that no test detects is a
GAP in the tests and is reported as such. Limits: a mutation is a model of one failure, not every way the control could fail; "detected" means some test failed, not that the failure
would be caught in every scenario. Writes docs/safety/mutation-results.md and .json.   Usage (from backend/):  python scripts/run_safety_mutations.py [--only NAME]"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import safety_mutation_plugin as plugin  # noqa: E402

OUT = ROOT.parent / "docs" / "safety"
TESTS = ["tests/test_safety_invariants.py", "tests/test_llm_api_safety.py", "tests/test_llm_explain.py", "tests/test_cited_explanations.py", "tests/test_redteam.py",
         "tests/test_unsupported_claims.py", "tests/test_replan.py", "tests/test_city_isolation.py", "tests/test_llm_input.py", "tests/test_solver.py", "tests/test_conflict_resolver.py",
         "tests/test_llm_per_city.py", "tests/test_ai_repair.py", "tests/test_safety_invariants_ai.py"]


def run(name: str | None):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "tests") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    if name:
        env["SAFETY_MUTATION"] = name
    t0 = time.time()
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "safety_mutation_plugin", "-rf", *TESTS], cwd=ROOT, env=env, capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^FAILED (\S+)", p.stdout, flags=re.M)))
    summary = (p.stdout.strip().splitlines() or [""])[-1]
    return failed, summary, round(time.time() - t0, 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    base_failed, base_summary, _ = run(None)
    if base_failed:
        print("baseline is not green; refusing to mutate:", base_failed)
        return 1
    rows = []
    for name, (_, why) in plugin.MUTATIONS.items():
        if a.only and name != a.only:
            continue
        failed, summary, secs = run(name)
        rows.append({"mutation": name, "disabled_safeguard": why, "detected": bool(failed), "failing_tests": failed, "pytest_summary": summary, "seconds": secs})
        print(("DETECTED " if failed else "NOT DETECTED ") + name, len(failed), flush=True)
    res = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "baseline": base_summary, "test_files": TESTS, "mutations": rows}
    if not a.only:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "mutation-results.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        L = ["# Safety mutation testing", "", f"Generated {res['date']} by `backend/scripts/run_safety_mutations.py`. Baseline (no mutation): {base_summary}.", "",
             "Each row disables ONE safeguard in a throw-away test process and runs the safety-relevant test files. Nothing in the repository or any configuration is changed, and no weakened safeguard is committed.", "",
             "| Disabled safeguard | Detected? | Tests that failed (first 4 of N) |", "|---|---|---|"]
        for r in rows:
            first = "; ".join(t.split("::", 1)[1] if "::" in t else t for t in r["failing_tests"][:4])
            L.append(f"| `{r['mutation']}`: {r['disabled_safeguard']} | {'YES' if r['detected'] else '**NO: a gap in the tests**'} | {len(r['failing_tests'])}: {first or '-'} |")
        L += ["", "## Limits", "", "- A mutation models one way a control can fail; it is not every way.", "- \"Detected\" means at least one test failed, not that every scenario is covered.",
              "- The tests were written by the developer who also built the safeguards; this is not an independent assessment.", "- The validator gate on repair suggestions cannot be removed in a way that changes any output today (the solver's own plans already pass the validator), so that row checks the gate by making it reject everything.", ""]
        (OUT / "mutation-results.md").write_text("\n".join(L), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
