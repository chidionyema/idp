"""Founder, 2026-08-28: the laws and guard report is a generated TechDocs page, never typed.
The generator reads the laws table and policy/adapters.rego; this proves it against a small tree."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "bin" / "idp-laws-guards-report"


def _tree(tmp):
    g = tmp / "guards"; (g / "policy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(g)], check=True)
    (g / "policy" / "adapters.rego").write_text(
        'package adapters\n\nsession_start := [\n\t["a-guard.py"],\n]\n\nuser_prompt_submit := []\n\n'
        'pre_tool_use := [\n\t{"run": ["b-guard.py"], "tools": ["Bash"]},\n]\n\nstop := []\n')
    (g / "a-guard.py").write_text('"""Refuse a session that starts stale (LAW 7).\n\nmore."""\n')
    (g / "b-guard.py").write_text('"""Refuse git add -A."""\n')
    laws = tmp / "AGENTS.md"
    laws.write_text("| # | Law | Fires |\n|---|-----|-------|\n| 1 | Put the fire out first | while anything is broken |\n")
    return g, laws


def test_page_is_rendered_from_the_tree_and_check_sees_staleness(tmp_path):
    g, laws = _tree(tmp_path)
    env = {**os.environ, "CLAUDE_GUARDS_DIR": str(g), "LAWS_FILE": str(laws)}
    out = ROOT / "docs" / "reference" / "laws-and-guards.md"
    before = out.read_text()
    try:
        subprocess.run([sys.executable, str(GEN)], env=env, capture_output=True, text=True, check=True)
        text = out.read_text()
        assert "| 1 | Put the fire out first |" in text
        assert "| 1 | `a-guard.py` | Refuse a session that starts stale (LAW 7) | 7 | every tool |" in text, text
        assert "| 1 | `b-guard.py` | Refuse git add -A | — | Bash |" in text, text
        assert subprocess.run([sys.executable, str(GEN), "--check"], env=env).returncode == 0
        out.write_text(text + "typed by hand\n")
        assert subprocess.run([sys.executable, str(GEN), "--check"], env=env).returncode == 1
    finally:
        out.write_text(before)
