#!/usr/bin/env python3
"""The founder.decision door must be able to ASK, not only read back.

THE DEFECT (2026-10-30, issue #7537). The executor substitutes every intent argument into the
step as a SHELL-QUOTED value, and an unset argument is substituted as the two characters `''`.
The template's read-back branch was guarded with `[ -n "{{decision_id}}" ]`, which is TRUE for the
two characters `''`. Every ask was therefore swallowed by the read-back branch: the door called
`show --decision-id ''` and answered `no decision ''`. The ask path was unreachable, so the one
door every agent is supposed to use for a founder decision had never asked anything. The default
`repo` was broken the same way: `~/Documents/code/idp` inside a quoted substitution is not a home
directory, so the tool path did not exist.

WHAT THIS PROVES. The intent is rendered exactly the way the executor renders it (every argument
quoted, an unset argument as `''`), the rendered step is executed with `python3` shadowed by a
recorder, and the recorded verb is asserted. With the pre-fix intent the recorded verb is `show`
and this file fails; with the repaired intent it is `ask`.

The test reads `IDP_INTENT_UNDER_TEST` when set, so the falsifier can be pointed at the old
intent without touching the tree.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_INTENT = REPO / "platform" / "estate" / "intents" / "founder.decision.yaml"
PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


def intent_path() -> Path:
    override = os.environ.get("IDP_INTENT_UNDER_TEST")
    return Path(override) if override else DEFAULT_INTENT


def render(cmd: str, args: dict) -> str:
    """Substitute the way the executor does: every value shell-quoted, empty becomes ''."""

    def sub(match: re.Match) -> str:
        return shlex.quote(str(args.get(match.group(1), "")))

    return PLACEHOLDER.sub(sub, cmd)


def run_rendered(cmd: str, args: dict, tmp_path: Path) -> tuple[int, str, list[str]]:
    """Run the rendered step with python3 shadowed by a recorder; return (rc, out, recorded)."""
    tool_dir = tmp_path / "tool"
    (tool_dir / "bin").mkdir(parents=True)
    (tool_dir / "bin" / "founder-decision").write_text("#!/bin/sh\nexit 0\n")

    record = tmp_path / "recorded.txt"
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    stub = stub_dir / "python3"
    stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{record}"\nexit 0\n')
    stub.chmod(0o755)

    rendered = render(cmd, {**args, "tool_repo": str(tool_dir)})
    proc = subprocess.run(
        ["bash", "-c", rendered],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{stub_dir}:{os.environ['PATH']}"},
        timeout=30,
    )
    recorded = record.read_text().splitlines() if record.exists() else []
    return proc.returncode, proc.stdout + proc.stderr, recorded


def step_cmd() -> str:
    spec = yaml.safe_load(intent_path().read_text())
    steps = spec["steps"]
    assert steps, "the intent declares no step"
    return steps[0]["cmd"]


def defaults() -> dict:
    spec = yaml.safe_load(intent_path().read_text())
    return {name: str(meta.get("default", "")) for name, meta in spec["args"].items()}


def test_the_intent_is_present_and_declares_its_step():
    assert intent_path().exists(), f"no intent at {intent_path()}"
    assert "founder-decision" in step_cmd()


def test_the_rendered_step_parses_as_shell():
    rendered = render(step_cmd(), defaults())
    proc = subprocess.run(
        ["bash", "-n"], input=rendered, capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0, f"the rendered step is not valid shell:\n{proc.stderr}"


def test_an_ask_asks_it_does_not_read_back(tmp_path):
    args = defaults()
    args["question"] = "Authorise the guarded-path change?"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, f"the ask path failed:\n{out}"
    assert recorded, f"the door called nothing:\n{out}"
    assert "ask" in recorded, f"the door did not ask:\n{recorded}"
    assert "show" not in recorded, f"the door read back instead of asking:\n{recorded}"


def test_an_ask_carries_an_absolute_state_path_not_an_empty_one(tmp_path):
    args = defaults()
    args["question"] = "Authorise the guarded-path change?"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert "--state" in recorded, f"no state path was passed:\n{recorded}"
    state = recorded[recorded.index("--state") + 1]
    assert state.startswith("/"), f"the state path is not absolute: {state!r}"
    assert state != "''", "the state path was the empty-argument rendering"


def test_a_read_back_still_reads_back(tmp_path):
    args = defaults()
    args["decision_id"] = "dec-1a2b3c4d"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert "show" in recorded, f"a read-back must not ask:\n{recorded}"
    assert "ask" not in recorded, f"a read-back must not ask:\n{recorded}"
    assert "dec-1a2b3c4d" in recorded


def test_an_absent_question_is_refused_and_asks_nothing(tmp_path):
    args = defaults()  # question defaults to the absent sentinel
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc != 0, "an absent question must be refused, not asked"
    assert "question" in out.lower(), f"the refusal does not say why:\n{out}"
    assert not recorded, f"the door asked something with no question:\n{recorded}"


def test_the_repo_default_is_absolute_so_the_tool_can_be_found():
    repo = defaults()["repo"]
    assert repo.startswith("/"), f"the repo default is not absolute: {repo!r}"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
