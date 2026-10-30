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
    (tool_dir / "bin").mkdir(parents=True, exist_ok=True)
    (tool_dir / "bin" / "founder-decision").write_text("#!/bin/sh\nexit 0\n")

    record = tmp_path / "recorded.txt"
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir(exist_ok=True)
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


def test_the_global_options_come_before_the_verb(tmp_path):
    """argparse accepts `--repo`/`--state` only BEFORE the verb.

    Found 2026-10-30: the repaired intent passed `--state` AFTER the verb, and the door died
    with `unrecognized arguments: --state ...` before it asked anything. The recorded argv is
    the proof that the global options lead and the verb follows.
    """
    args = defaults()
    args["question"] = "Authorise the guarded-path change?"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert recorded, f"the door called nothing:\n{out}"
    verbs = {"ask", "show", "answer", "poll", "reply", "wait", "list"}
    verb_positions = [i for i, token in enumerate(recorded) if token in verbs]
    assert verb_positions, f"no verb in the recorded argv:\n{recorded}"
    verb_at = verb_positions[0]
    for option in ("--repo", "--state"):
        assert option in recorded, f"{option} was not passed:\n{recorded}"
        assert recorded.index(option) < verb_at, (
            f"{option} comes after the verb {recorded[verb_at]!r}; argparse rejects that:\n{recorded}"
        )


def test_an_empty_option_reaches_the_door_as_an_empty_argument(tmp_path):
    """`--options` defaults to empty. It must arrive EMPTY, not as the two characters ''.

    interpolate() already shell-quotes, so `"{{options}}"` in the template is a literal pair
    of quote characters INSIDE the value. The door would store `options: "''"` and the founder
    would read a stray quote pair.
    """
    args = defaults()
    args["question"] = "Authorise the guarded-path change?"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert "--options" in recorded, f"no options were passed:\n{recorded}"
    value = recorded[recorded.index("--options") + 1]
    assert value == "", (
        f"the empty option arrived as {value!r}, not as an empty argument"
    )
    assert "--context" in recorded
    assert recorded[recorded.index("--context") + 1] == ""


def test_a_question_with_spaces_stays_one_argument(tmp_path):
    args = defaults()
    args["question"] = "Authorise the guarded-path change on lane/prepush-gherkin?"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert "--question" in recorded, f"no question was passed:\n{recorded}"
    value = recorded[recorded.index("--question") + 1]
    assert value == args["question"], f"the question was mangled into {value!r}"


def test_the_absent_sentinel_is_compared_as_a_string_not_a_bash_error(tmp_path):
    """`[ - != "-" ]` is a bash error, so the read-back branch never fires.

    The template must read the sentinel through a VARIABLE. The proof is that the read-back
    branch is actually TAKEN for a decision_id and NOT taken for the absent sentinel.
    """
    args = defaults()
    args["decision_id"] = "dec-1a2b3c4d"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert "show" in recorded, f"the read-back branch was not taken:\n{recorded}"
    assert "ask" not in recorded

    args = defaults()
    args["question"] = "Authorise the guarded-path change?"
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc == 0, out
    assert "ask" in recorded, f"the ask branch was not taken:\n{recorded}"


def test_an_absent_question_refuses_and_asks_nothing(tmp_path):
    args = defaults()  # question defaults to the absent sentinel
    rc, out, recorded = run_rendered(step_cmd(), args, tmp_path)
    assert rc != 0, "an absent question must be refused, not asked"
    assert "question" in out.lower(), f"the refusal does not say why:\n{out}"
    assert not recorded, f"the door asked something with no question:\n{recorded}"


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
