"""The Turn-1 rule budget gate, proven against the real script and the real AGENTS.md.

Hold #1 of the context-governance kit: its compiler replaced AGENTS.md wholesale (58,150 bytes
-> 800, measured 2026-11-27). These tests fail on that behaviour and pass on composition.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "estate_context_fleet_sync.py"
POLICY = ROOT / "policy" / "context-policy.v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("estate_context_fleet_sync", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--policy", str(POLICY), *args],
        capture_output=True,
        text=True,
    )


def test_self_test_refuses_every_bad_input_and_admits_every_good_one():
    rc = _run("--self-test")
    report = json.loads(rc.stdout)
    assert rc.returncode == 0, report
    assert report["self_test"] == "pass"
    assert len(report["results"]) >= 14


def test_compose_on_the_real_agents_md_deletes_nothing_and_is_idempotent():
    mod = _load()
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    original = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    block = mod.contract_block(policy)
    once = mod.compose(original, block)
    assert len(once) > len(original)
    assert once.count(mod.BLOCK_START) == 1
    # every original line survives, in order
    lines = iter(once.splitlines())
    assert all(any(line == x for x in lines) for line in original.splitlines())
    assert mod.compose(once, block) == once
    assert once.splitlines()[0] == original.splitlines()[0]


def test_a_2000_token_rule_file_is_refused_with_exit_43(tmp_path):
    (tmp_path / "AGENTS.md").write_text("x" * 8000, encoding="utf-8")
    rc = _run("--audit", "--repo-root", str(tmp_path))
    assert rc.returncode == 43, rc.stdout
    assert any(
        v.startswith("FC_TURN1_BLOATED_RULES")
        for v in json.loads(rc.stdout)["violations"]
    )


def test_an_unreadable_base_is_refused_not_passed(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "AGENTS.md").write_text("x" * 8000, encoding="utf-8")
    rc = _run("--audit", "--repo-root", str(tmp_path), "--base", "no-such-ref")
    assert rc.returncode == 2, rc.stdout


def test_this_repo_does_not_grow_its_turn_one_rules_against_its_parent():
    base = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", "HEAD~1"],
        capture_output=True,
        text=True,
    )
    if base.returncode != 0:
        import pytest

        pytest.skip("no parent commit in this checkout (shallow clone)")
    rc = _run("--audit", "--repo-root", str(ROOT), "--base", "HEAD~1")
    assert rc.returncode == 0, rc.stdout


def test_the_registered_optimus_measure_prints_its_line_on_this_tree():
    """DBG-039: a measure that cannot print `optimus.<name>=<n>` on main can never gate."""
    import re

    metrics = json.loads((ROOT / "catalog" / "optimus-metrics.json").read_text())[
        "metrics"
    ]
    entry = next(m for m in metrics if m["name"] == "context.turn1_rule_tokens")
    rc = subprocess.run(entry["measure"], cwd=str(ROOT), capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert re.fullmatch(r"optimus\.context\.turn1_rule_tokens=\d+\n", rc.stdout), (
        rc.stdout
    )
    assert int(rc.stdout.split("=")[1]) > 0


def test_optimus_on_a_tree_with_no_rule_files_is_unknown_not_zero(tmp_path):
    rc = _run("--optimus", "--repo-root", str(tmp_path))
    assert rc.returncode == 2, rc.stdout
    assert "optimus." not in rc.stdout
