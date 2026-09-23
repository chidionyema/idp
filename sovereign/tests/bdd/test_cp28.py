"""cp28 acceptance: Auto-distillation -- every frontier success is a training row

Owner: W5 (sovereign/shadow/distill.py).

Two true external boundaries are stubbed, nothing else: the LoRA job is
a subprocess (the recorded argv is asserted, the process is not run), and
the local model's completions come from a stub completer instead of
LiteLLM. The queue, the dataset mirror, the grader, the routes file and
the signed receipt are all real. Langfuse is not configured in the
scenario's estate, so "a Langfuse dataset item exists" is proved on the
local mirror, which is the same item the Langfuse client is handed when
the host is configured (distill._push_to_langfuse).
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sovereign import cli as sb_cli
from sovereign.engine import receipts as receipts_mod
from sovereign.shadow import config_keys as ck
from sovereign.shadow import distill

scenarios("features/sovereign-bus/cp28_distillation.feature")

_TASK_CLASS = "git_rebase"
_PROMPT = "rebase feature/{n} onto main and resolve the conflict in README.md"
_COMPLETION = "git fetch origin && git rebase origin/main && git add README.md && git rebase --continue #{n}"


@pytest.fixture(autouse=True)
def _software_trust(estate_home: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")


def _frontier_step(n: int, status: str = "done") -> dict[str, Any]:
    return {
        "session_id": f"sb-{n:04d}",
        "task_class": _TASK_CLASS,
        "model": "claude",
        "status": status,
        "prompt": _PROMPT.format(n=n),
        "completion": _COMPLETION.format(n=n),
        "tool_calls": [{"name": "bash", "args": {"cmd": "git rebase origin/main"}}],
    }


# ---- scenario 1 --------------------------------------------------------------


@given(parsers.parse('a session step ran on a frontier model and finished "{status}"'))
def _one_step(status: str, context: dict[str, Any]) -> None:
    context["step"] = _frontier_step(1, status)
    context["item"] = distill.capture(context["step"])


@then("a Langfuse dataset item exists with prompt, completion and tool calls, tagged with the task class")
def _item_exists(context: dict[str, Any]) -> None:
    step = context["step"]
    rows = distill.items(_TASK_CLASS)
    assert len(rows) == 1
    item = rows[0]
    assert item["dataset"] == distill.dataset_name(_TASK_CLASS)
    assert item["input"] == step["prompt"]
    assert item["expected_output"] == step["completion"]
    assert item["metadata"]["tool_calls"] == step["tool_calls"]
    assert _TASK_CLASS in item["metadata"]["tags"]
    assert distill.queue_path().exists()
    # A step that did not finish "done", or ran on the local model, is not a training row.
    assert distill.capture(_frontier_step(2, "failed")) is None
    assert distill.capture({**_frontier_step(3), "model": str(ck.get("distill.local_model"))}) is None
    assert len(distill.items(_TASK_CLASS)) == 1


# ---- scenario 2 --------------------------------------------------------------


@when(parsers.parse('I run "bin/sb distill --task-class {task_class} --json"'))
def _run_distill(task_class: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], context: dict[str, Any]) -> None:
    minimum = int(ck.get("distill.min_items"))
    expected: dict[str, str] = {}
    for n in range(minimum):
        step = _frontier_step(n)
        assert distill.capture(step) is not None
        expected[step["prompt"]] = step["completion"]

    # The LoRA job: a subprocess whose argv is recorded, never run.
    calls: list[list[str]] = []

    def _fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(distill.subprocess, "run", _fake_run)

    # The local model: right on every prompt but one, so the measured
    # number (0.95 at 20 items) sits above the 0.9 threshold by evidence
    # and not by construction of a perfect stub.
    wrong_prompt = next(iter(expected))

    def _stub_completer(prompt: str) -> str:
        if prompt == wrong_prompt:
            return "git merge main"
        return expected[prompt].upper()  # normalization makes case irrelevant

    monkeypatch.setattr(distill, "local_completer", lambda model=None: _stub_completer)

    rc = sb_cli.main(["distill", "--task-class", task_class, "--json"])  # the real entry point, plug-in loop included
    assert rc == 0
    context["out"] = json.loads(capsys.readouterr().out)
    context["train_calls"] = calls
    context["task_class"] = task_class


@then(parsers.parse('the output has "{field}" measured over at least {minimum:d} dataset items'))
def _measured(context: dict[str, Any], field: str, minimum: int) -> None:
    out = context["out"]
    assert out["measured"] is True
    assert out[field] is not None
    assert out["items"] >= minimum
    assert 0.0 <= float(out[field]) <= 1.0
    assert len(context["train_calls"]) == 1, "the LoRA job ran exactly once"
    argv = context["train_calls"][0]
    assert argv[0] == str(ck.get("distill.trainer")), argv
    assert context["task_class"] in " ".join(argv)


@then(parsers.re(r"if local_accuracy (?:≥|>=) (?P<threshold>[0-9.]+) the LiteLLM route for that class is set to the local model"))
def _route_flips(context: dict[str, Any], threshold: str) -> None:
    out = context["out"]
    assert float(out["threshold"]) == float(threshold)
    routes = distill.routes()
    local = str(ck.get("distill.local_model"))
    if float(out["local_accuracy"]) >= float(threshold):
        assert routes.get(context["task_class"]) == local
        assert out["routing"] == local and out["flipped"] is True
    else:
        assert context["task_class"] not in routes
        assert out["flipped"] is False


@then(parsers.parse('a receipt "{line}" is written'))
def _receipt_written(context: dict[str, Any], line: str) -> None:
    rows = [r for r in receipts_mod.read_all() if r.get("kind") == str(ck.get("distill.receipt_kind"))]
    assert len(rows) == 1
    text = rows[0]["text"]
    pattern = re.escape(line).replace(re.escape("<n>"), r"[0-9.]+").replace(re.escape("<model>"), r"\S+")
    assert re.fullmatch(pattern, text), (text, pattern)
    assert text == context["out"]["text"]
    assert rows[0]["local_accuracy"] == context["out"]["local_accuracy"]
