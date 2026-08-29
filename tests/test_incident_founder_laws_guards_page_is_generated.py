"""Founder, 2026-08-28: the laws and guard report is a generated TechDocs page, never typed.

The generator reads the laws table and the harness settings file; this proves it against a small
tree. It read `policy/adapters.rego` until 2026-08-29, and this fixture wrote one -- so the test
was green for eleven months of estate-time while the real generator could not run at all, because
no branch of the guards repo carries that file. A fixture that supplies the input the real world
does not have is a proxy, not a proof, which is why the missing-source case below is now graded.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "bin" / "idp-laws-guards-report"


def _tree(tmp):
    g = tmp / "guards"
    g.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(g)], check=True)
    (g / "a-guard.py").write_text('"""Refuse a session that starts stale (LAW 7).\n\nmore."""\n')
    (g / "b-guard.py").write_text('"""Refuse git add -A."""\n')
    settings = tmp / "settings.json"
    settings.write_text(json.dumps({"hooks": {
        "SessionStart": [{"hooks": [{"command": f"python3 {g}/hook-run.py {g}/a-guard.py"}]}],
        "UserPromptSubmit": [],
        "PreToolUse": [{"matcher": "Bash",
                        "hooks": [{"command": f"python3 {g}/hook-run.py {g}/b-guard.py"}]}],
        "Stop": [],
    }}))
    laws = tmp / "AGENTS.md"
    laws.write_text("| # | Law | Fires |\n|---|-----|-------|\n"
                    "| 1 | Put the fire out first | while anything is broken |\n")
    return g, laws, settings


def _env(g, laws, settings):
    return {**os.environ, "CLAUDE_GUARDS_DIR": str(g), "LAWS_FILE": str(laws),
            "CLAUDE_SETTINGS_FILE": str(settings)}


def test_page_is_rendered_from_the_tree_and_check_sees_staleness(tmp_path):
    g, laws, settings = _tree(tmp_path)
    env = _env(g, laws, settings)
    out = ROOT / "docs" / "reference" / "laws-and-guards.md"
    before = out.read_text()
    try:
        subprocess.run([sys.executable, str(GEN)], env=env, capture_output=True, text=True, check=True)
        text = out.read_text()
        assert "| 1 | Put the fire out first |" in text
        assert "| 1 | `a-guard.py` | Refuse a session that starts stale (LAW 7) | 7 | every tool |" in text, text
        assert "| 1 | `b-guard.py` | Refuse git add -A | — | Bash |" in text, text
        assert "## UserPromptSubmit" not in text, "an event with no guards is not a section"
        assert subprocess.run([sys.executable, str(GEN), "--check"], env=env).returncode == 0
        out.write_text(text + "typed by hand\n")
        assert subprocess.run([sys.executable, str(GEN), "--check"], env=env).returncode == 1
    finally:
        out.write_text(before)


def test_the_runner_is_not_listed_as_a_guard(tmp_path):
    """Every command is `hook-run.py <guard>.py`. Listing the runner would put a row in the page
    for something that decides nothing, once per guard."""
    g, laws, settings = _tree(tmp_path)
    out = ROOT / "docs" / "reference" / "laws-and-guards.md"
    before = out.read_text()
    try:
        subprocess.run([sys.executable, str(GEN)], env=_env(g, laws, settings),
                       capture_output=True, text=True, check=True)
        rows = [ln for ln in out.read_text().splitlines() if ln.startswith("| ")]
        assert not [ln for ln in rows if "`hook-run.py`" in ln], rows
    finally:
        out.write_text(before)


def test_a_missing_settings_file_is_a_named_refusal_not_a_traceback(tmp_path):
    """The case that was live on 2026-08-29: the source the generator reads was not there, and it
    answered with a FileNotFoundError traceback from inside pathlib. A generator that cannot find
    its input says which file, and exits."""
    g, laws, settings = _tree(tmp_path)
    settings.unlink()
    run = subprocess.run([sys.executable, str(GEN), "--check"], env=_env(g, laws, settings),
                         capture_output=True, text=True)
    assert run.returncode != 0
    assert str(settings) in run.stderr, run.stderr
    assert "Traceback" not in run.stderr, run.stderr
