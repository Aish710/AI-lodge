#!/usr/bin/env python3
"""Find stale or contradictory statements in the documentation and the frontend copy, by comparing them with FACTS READ FROM GENERATED FILES.
Prints every conflict as  file:line | the stale text | the generated fact it contradicts, and exits 1 if there is any.

Scanned: README.md, docs/**/*.md, and the user-facing copy in frontend/src (How it works, Proof, footer). Not scanned: dated history logs (docs/BUILD_NOTES.md,
docs/SAFETY_LOG.md, docs/UI-COPY-CHANGES.md, docs/STATUS-AUDIT.md, docs/design/test-edits.md) because they record what was true on a past date, and the generated result
files themselves. In .vue files, lines that sit behind a v-if / v-else (copy shown only while a result is missing) are not statements about the present.

Checks
  1. "not run / not measured" next to a topic whose result file exists (live AI self-check, gold set, red team live, user test)
  2. "0 verified" (or any count) against the verification counts / the data's source_status
  3. test counts against the generated full-suite result and the frontend test summary
  4. city counts against the city packs on disk
  5. the model name and gateway host against the live reports

Usage:  python scripts/check_doc_consistency.py [--root DIR]      (--root is for the tests' fixture trees)"""
import json
import re
import sys
from pathlib import Path

HISTORY = {"docs/BUILD_NOTES.md", "docs/SAFETY_LOG.md", "docs/UI-COPY-CHANGES.md", "docs/STATUS-AUDIT.md", "docs/design/test-edits.md"}
NOT_RUN = re.compile(r"(has|have|had|is|are|was|were)? ?not (yet )?(been )?(measured|run|ran|collected)|never been (run|measured)|not run( yet| on this version)?|\bnot measured\b", re.I)


class Facts:
    def __init__(self, root: Path):
        self.root = root
        self.notes: list[str] = []
        self.cities = sorted(p.name for p in (root / "backend/app/data/cities").glob("*") if p.is_dir()) if (root / "backend/app/data/cities").exists() else []
        self.reports = {k: root / v for k, v in {"selfcheck": "docs/ai-selfcheck.md", "redteam_live": "docs/redteam-live.md"}.items()}
        self.gold = sorted((root / "docs/eval").glob("gold-results-live*.md")) if (root / "docs/eval").exists() else []
        self.prompt_version = self._prompt_version()
        self.user_rows = self._user_rows()
        self.verified = self._verified()
        self.backend_total = self._backend_total()
        self.frontend = self._frontend()
        self.models, self.hosts = self._live_stamp()

    def _prompt_version(self):
        f = self.root / "backend/app/llm/prompts.py"
        m = re.search(r'PROMPT_VERSION\s*=\s*"([^"]+)"', f.read_text()) if f.exists() else None
        return m.group(1) if m else None

    def _user_rows(self):
        f = self.root / "docs/user-test/results.csv"
        return max(0, len([l for l in f.read_text().splitlines() if l.strip() and any(c.strip() for c in l.split(","))]) - 1) if f.exists() else 0

    def _verified(self):
        """(human_verified_rows, source) from the generated verification counts if present, else records whose source_status is 'verified'."""
        f = self.root / "docs/data-verification/counts.json"
        if f.exists():
            d = json.loads(f.read_text())
            return int(d.get("human_verified", 0)), "docs/data-verification/counts.json"
        n = 0
        for p in (self.root / "backend/app/data/cities").glob("*/*.json") if (self.root / "backend/app/data/cities").exists() else []:
            n += len(re.findall(r'"source_status"\s*:\s*"verified"', p.read_text()))
        return n, "backend/app/data/cities/*/ (records with source_status \"verified\")"

    def _backend_total(self):
        j = self.root / "backend/tests/results/full-suite.json"
        if j.exists():
            return int(json.loads(j.read_text())["total"]), "backend/tests/results/full-suite.json"
        m = self.root / "backend/tests/results/latest-full.md"
        if m.exists():
            g = re.search(r"total: (\d+)\.", m.read_text())
            if g:
                return int(g.group(1)), "backend/tests/results/latest-full.md"
        return None, None

    def _frontend(self):
        f = self.root / "docs/test-summary-frontend.json"
        if not f.exists():
            return {}
        return {s["suite"].lower(): int(s["total"]) for s in json.loads(f.read_text()).get("suites", [])}

    def _live_stamp(self):
        models, hosts = set(), set()
        for f in [self.reports["selfcheck"], *self.gold]:
            if f.exists():
                t = f.read_text()
                models |= set(re.findall(r"[Mm]odel:?\s*`([^`]+)`", t))
                hosts |= set(re.findall(r"[Ee]ndpoint(?: host)?:?\s*`([^`]+)`", t))
                hosts |= set(re.findall(r"[Ee]ndpoint(?: host)?:\s*([a-z0-9-]+(?:\.[a-z0-9-]+)+)", t))
        return models, hosts


def _is_conditional_vue(line: str) -> bool:
    return bool(re.search(r'\bv-(if|else-if|else|show)\b', line))


def scan_files(root: Path):
    out = []
    if (root / "README.md").exists():
        out.append(root / "README.md")
    out += sorted((root / "docs").glob("**/*.md")) if (root / "docs").exists() else []
    for f in ("HowItWorks.vue", "Proof.vue"):
        p = root / "frontend/src/views" / f
        if p.exists():
            out.append(p)
    app = root / "frontend/src/App.vue"
    if app.exists():
        out.append(app)
    keep = []
    for p in out:
        rel = p.relative_to(root).as_posix()
        if rel in HISTORY or rel.startswith("docs/eval/gold-results") or rel in ("docs/ai-selfcheck.md", "docs/redteam-results.md", "docs/redteam-live.md", "docs/test-summary-frontend.md"):
            continue
        keep.append(p)
    return keep


def check(root: Path) -> list[tuple[str, int, str, str]]:
    facts = Facts(root)
    conflicts: list[tuple[str, int, str, str]] = []
    topics = [
        ("the live AI self-check", re.compile(r"self-?check|live (AI|model|LLM|evaluation|eval)|real model|live LLM|how well the AI|AI reads|parsing and explanation|llm-live-eval", re.I), facts.reports["selfcheck"].exists(),
         "docs/ai-selfcheck.md exists (a live run was recorded)"),
        ("the live gold-set score", re.compile(r"gold[- ]set|gold prompts|score_gold", re.I), any(f.exists() for f in facts.gold) and bool(facts.gold),
         f"{', '.join(f.name for f in facts.gold)} exist(s) in docs/eval/"),
        ("the live red-team run", re.compile(r"red[- ]?team.*live|live.*red[- ]?team|redteam_live", re.I), facts.reports["redteam_live"].exists(), "docs/redteam-live.md exists"),
        ("the user test", re.compile(r"user[- ]test|user study", re.I), facts.user_rows > 0, f"docs/user-test/results.csv has {facts.user_rows} row(s)"),
    ]
    for p in scan_files(root):
        rel = p.relative_to(root).as_posix()
        vue = p.suffix == ".vue"
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
            if vue and _is_conditional_vue(line):
                continue
            # 1. not-run statements next to a topic that has a result (judged one sentence at a time)
            for sentence in re.split(r"(?<=[.;:])\s+", line):
                if NOT_RUN.search(sentence):
                    for name, rx, exists, fact in topics:
                        if exists and rx.search(sentence):
                            conflicts.append((rel, i, sentence.strip()[:200], f"says {name} was not run or measured, but {fact}"))
            # 2. verified counts
            for m in re.finditer(r"\b(\d+)\s+(?:human[- ])?verified\b", line, re.I):
                n, src = facts.verified
                if int(m.group(1)) != n:
                    conflicts.append((rel, i, m.group(0), f"{n} human-verified per {src}"))
            m2 = re.search(r"(\d+) fields source-checked, (\d+) rows human-verified, (\d+) unchecked", line)
            vc = root / "docs/data-verification/counts.json"
            if m2 and vc.exists():
                d = json.loads(vc.read_text())
                c = d["cities"][d["first_city"]]
                want = (c["source_checked"], c["human_verified"], c["unchecked"])
                if tuple(int(x) for x in m2.groups()) != want:
                    conflicts.append((rel, i, m2.group(0), f"{want[0]} fields source-checked, {want[1]} rows human-verified, {want[2]} unchecked per docs/data-verification/counts.json"))
            # 3. test counts
            low = line.lower()
            if facts.backend_total[0] is not None:
                for m in re.finditer(r"(\d[\d,]*)\s+(?:backend\s+|pytest\s+)?tests?\b", line, re.I):
                    ctx = low[max(0, m.start() - 12): m.end() + 10]
                    if ("backend" in ctx or "pytest" in ctx) and "vitest" not in ctx and "playwright" not in ctx and int(m.group(1).replace(",", "")) != facts.backend_total[0]:
                        conflicts.append((rel, i, m.group(0), f"{facts.backend_total[0]} backend tests per {facts.backend_total[1]}"))
            for suite, total in facts.frontend.items():
                for m in re.finditer(rf"(\d[\d,]*)\s+{suite}\b|{suite}\s*[:(]?\s*(\d[\d,]*)\b", line, re.I):
                    n = int((m.group(1) or m.group(2)).replace(",", ""))
                    if n != total and n > 9:
                        conflicts.append((rel, i, m.group(0), f"{total} {suite} tests per docs/test-summary-frontend.json"))
            # 4. cities
            if facts.cities:
                for m in re.finditer(r"\b(\d+)\s+(?:sample\s+)?(?:cities|city packs)\b", line, re.I):
                    if int(m.group(1)) != len(facts.cities):
                        conflicts.append((rel, i, m.group(0), f"{len(facts.cities)} city packs on disk: {', '.join(facts.cities)}"))
                if len(facts.cities) > 1 and re.search(r"current coverage is (only )?tokyo|tokyo[- ]only|only (covers )?tokyo", line, re.I):
                    conflicts.append((rel, i, line.strip()[:200], f"{len(facts.cities)} city packs on disk: {', '.join(facts.cities)}"))
            # 5. model and host
            if facts.models and re.search(r"live|measured|self-?check|gold|ran\b", line, re.I):
                for m in re.finditer(r"\bclaude-[a-z0-9.-]+", line):
                    if m.group(0) not in facts.models:
                        conflicts.append((rel, i, m.group(0), f"the live reports say the model was {', '.join(sorted(facts.models))}"))
            if facts.hosts and re.search(r"gateway|relay|live", line, re.I):
                for m in re.finditer(r"\bapi\.[a-z0-9.-]+\.[a-z]{2,}\b", line):
                    if m.group(0) not in facts.hosts:
                        conflicts.append((rel, i, m.group(0), f"the live reports say the gateway host was {', '.join(sorted(facts.hosts))}"))
    return conflicts


def main(argv: list[str]) -> int:
    root = Path(argv[argv.index("--root") + 1]).resolve() if "--root" in argv else Path(__file__).resolve().parents[1]
    conflicts = check(root)
    for rel, line, text, fact in conflicts:
        print(f"{rel}:{line} | {text} | contradicts: {fact}")
    print(f"\n{len(conflicts)} conflict(s)." if conflicts else "0 conflicts.")
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
