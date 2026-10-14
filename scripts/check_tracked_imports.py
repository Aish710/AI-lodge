#!/usr/bin/env python3
"""Fail if source code depends on a file git does not carry (the `frontend/src/lib/` incident: a Python-template `lib/` ignore rule hid a
folder every import needed, so a clean clone could not build).

Checks, using only the standard library:
  1. every relative import in frontend/src, frontend/scripts, frontend/tests (JS/Vue) and every `app.*` import in backend/app, backend/scripts,
     backend/tests (Python) resolves to a file that is NOT git-ignored (and, with --untracked, is tracked);
  2. no git-ignored file sits inside a source folder, except the allowlisted generated ones.
Usage:  python scripts/check_tracked_imports.py [--untracked] [--list FILE]
Exit code 1 and a plain list of offenders when anything is wrong."""
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_DIRS = ["frontend/src", "frontend/scripts", "frontend/tests", "frontend/playwright.config.js", "frontend/vite.config.js"]
PY_DIRS = ["backend/app", "backend/scripts", "backend/tests"]
SOURCE_FOLDERS = ["frontend/src", "frontend/scripts", "frontend/tests", "frontend/public", "backend/app", "backend/scripts", "backend/tests", "scripts", "docs"]
# generated on purpose, never imported by source (fetched at runtime or rebuilt by a script): allowed to be git-ignored
ALLOWED_IGNORED = ("frontend/public/evidence-data", "__pycache__", ".pytest_cache", "node_modules", ".DS_Store", "frontend/tests/e2e/pw-artifacts")
JS_EXT = ["", ".js", ".mjs", ".vue", ".json", ".css", "/index.js"]
JS_IMPORT = re.compile(r"""(?:import\s+(?:[^'"]*?\s+from\s+)?|import\(\s*|require\(\s*|export\s+[^'"]*?\s+from\s+)['"]([^'"]+)['"]""")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def tracked() -> set[str]:
    return set(git("ls-files").splitlines())


def is_ignored(rel: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT).returncode == 0


def files_under(spec: str, suffixes: tuple[str, ...]):
    p = ROOT / spec
    if p.is_file():
        yield p
    elif p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix in suffixes and not any(part in ("node_modules", "__pycache__", "dist", "dist-e2e", "pw-artifacts", "test-results") for part in f.parts):
                yield f


def resolve_js(src: Path, spec: str) -> Path | None:
    base = (src.parent / spec).resolve()
    for ext in JS_EXT:
        cand = Path(str(base) + ext)
        if cand.is_file():
            return cand
    return None


def resolve_py(spec: str) -> Path | None:
    """app.x.y -> backend/app/x/y.py or backend/app/x/y/__init__.py"""
    rel = Path("backend") / Path(*spec.split("."))
    for cand in (ROOT / (str(rel) + ".py"), ROOT / rel / "__init__.py"):
        if cand.is_file():
            return cand
    return None


def py_imports(path: Path):
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "app":
                    yield a.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.split(".")[0] == "app":
            yield node.module
            for a in node.names:  # `from app import config` imports the submodule app/config.py
                yield f"{node.module}.{a.name}"


def collect() -> list[tuple[str, str]]:
    """(importing file, imported file), both repo-relative."""
    pairs: list[tuple[str, str]] = []
    for spec in JS_DIRS:
        for f in files_under(spec, (".js", ".mjs", ".vue")):
            for m in JS_IMPORT.finditer(f.read_text(errors="ignore")):
                s = m.group(1)
                if s.startswith("."):
                    target = resolve_js(f, s)
                    if target:
                        pairs.append((str(f.relative_to(ROOT)), str(target.relative_to(ROOT))))
    for spec in PY_DIRS:
        for f in files_under(spec, (".py",)):
            for mod in py_imports(f):
                target = resolve_py(mod)
                if target:
                    pairs.append((str(f.relative_to(ROOT)), str(target.relative_to(ROOT))))
    return pairs


def main(argv: list[str]) -> int:
    check_untracked = "--untracked" in argv
    in_git = tracked()
    pairs = collect()
    imported = sorted({t for _, t in pairs})
    problems: list[str] = []
    for t in imported:
        if is_ignored(t):
            who = sorted({s for s, tt in pairs if tt == t})[:3]
            problems.append(f"IGNORED but imported: {t} (imported by {', '.join(who)})")
        elif check_untracked and t not in in_git:
            problems.append(f"NOT TRACKED but imported: {t} (run `git add`)")
    hidden = []
    for folder in SOURCE_FOLDERS:
        base = ROOT / folder
        if not base.is_dir():
            continue
        out = git("ls-files", "--others", "--ignored", "--exclude-standard", "--", folder)
        for rel in out.splitlines():
            if not any(a in rel for a in ALLOWED_IGNORED):
                hidden.append(rel)
    for rel in sorted(set(hidden)):
        problems.append(f"IGNORED file inside a source folder: {rel}")
    if "--list" in argv:
        out_path = ROOT / argv[argv.index("--list") + 1]
        lines = [f"# Files checked by scripts/check_tracked_imports.py ({len(imported)} imported files from {len({s for s, _ in pairs})} source files)",
                 *[f"{t}" for t in imported]]
        out_path.write_text("\n".join(lines) + "\n")
    print(f"checked {len({s for s, _ in pairs})} source files, {len(imported)} imported local files")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
