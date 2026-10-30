"""One workflow for every harness: the renderer writes it and the check can FAIL.

WHY THESE TESTS. 2026-10-29: the workflow existed as three different AGENTS.md files and a pi
session never saw it. A check that only passes proves nothing, so most tests here break a copy
on purpose: a hand-edited harness file, a deleted one, and a canonical change that leaves every
installed copy stale must each make `check` exit 1 and name the harness.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "platform"
    / "estate"
    / "harness"
    / "render.py"
)
HARNESSES = ["claude-code", "pi", "codex", "kimi", "opencode"]


def run(action: str, source: Path, home: Path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            action,
            "--source",
            str(source),
            "--home",
            str(home),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def setup(tmp_path: Path):
    source = tmp_path / "AGENTS.md"
    source.write_text("# Workflow\nseven gates\n")
    home = tmp_path / "home"
    home.mkdir()
    return source, home


def test_all_five_harnesses_are_rendered_and_check_passes(tmp_path):
    source, home = setup(tmp_path)
    assert run("render", source, home).returncode == 0
    r = run("check", source, home)
    assert r.returncode == 0, r.stdout
    for h in HARNESSES:
        assert f"OK       {h}" in r.stdout


def test_every_copy_carries_the_canonical_text(tmp_path):
    source, home = setup(tmp_path)
    run("render", source, home)
    for p in home.rglob("*.md"):
        assert "seven gates" in p.read_text()


def test_a_hand_edited_copy_is_drift_and_names_the_harness(tmp_path):
    source, home = setup(tmp_path)
    run("render", source, home)
    target = home / ".codex" / "AGENTS.md"
    target.write_text(target.read_text() + "\nlocal override\n")
    r = run("check", source, home)
    assert r.returncode == 1
    assert "DRIFT    codex" in r.stdout


def test_a_missing_copy_fails_the_check(tmp_path):
    source, home = setup(tmp_path)
    run("render", source, home)
    (home / ".pi" / "AGENTS.md").unlink()
    r = run("check", source, home)
    assert r.returncode == 1
    assert "MISSING  pi" in r.stdout


def test_a_canonical_change_makes_every_installed_copy_stale(tmp_path):
    source, home = setup(tmp_path)
    run("render", source, home)
    source.write_text("# Workflow\nseven gates\nnew rule\n")
    r = run("check", source, home)
    assert r.returncode == 1
    assert r.stdout.count("DRIFT") == len(HARNESSES)


def test_check_on_an_empty_home_fails_all_five(tmp_path):
    source, home = setup(tmp_path)
    r = run("check", source, home)
    assert r.returncode == 1
    assert r.stdout.count("MISSING") == len(HARNESSES)
