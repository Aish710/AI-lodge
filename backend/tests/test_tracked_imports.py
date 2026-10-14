"""CI-style guard for the `frontend/src/lib/` incident: source code must never import a file that git ignores (a clean clone would not have it)."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_tracked_imports.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_tracked_imports", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_imported_file_is_git_ignored_and_no_source_folder_hides_ignored_files(capsys):
    mod = _load()
    code = mod.main([])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "checked" in out


def test_the_checker_sees_the_frontend_lib_folder_and_the_backend_app_package():
    mod = _load()
    imported = {t for _, t in mod.collect()}
    assert "frontend/src/lib/format.js" in imported and "frontend/src/lib/replan.js" in imported
    assert "backend/app/config.py" in imported and "backend/app/optimiser/solver.py" in imported
