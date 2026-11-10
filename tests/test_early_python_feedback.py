"""Editor and build feedback run before the commit boundary can be reached."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vscode_fixes_and_formats_python_on_save():
    settings = json.loads((ROOT / ".vscode/settings.json").read_text())["[python]"]
    assert settings["editor.defaultFormatter"] == "charliermarsh.ruff"
    assert settings["editor.formatOnSave"] is True
    assert settings["editor.codeActionsOnSave"] == {
        "source.fixAll.ruff": "explicit",
        "source.organizeImports.ruff": "explicit",
    }


def test_vscode_default_build_runs_the_full_staged_preflight():
    tasks = json.loads((ROOT / ".vscode/tasks.json").read_text())["tasks"]
    build = next(t for t in tasks if t["group"]["isDefault"])
    assert build["group"]["kind"] == "build"
    assert build["command"].endswith("/.githooks/pre-commit")


def test_commit_message_hook_refuses_an_unjustified_python_file(tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".git/idp-hook-secret").write_text("test-secret\n")
    (repo / ".githooks").mkdir()
    (repo / "bin").mkdir()
    shutil.copy(ROOT / ".githooks/commit-msg", repo / ".githooks/commit-msg")
    shutil.copy(ROOT / "bin/language-gate", repo / "bin/language-gate")
    (repo / "new.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "new.py"], cwd=repo, check=True)
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("add new Python file\n")
    result = subprocess.run(
        ["bash", ".githooks/commit-msg", str(message)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "new.py" in result.stderr
