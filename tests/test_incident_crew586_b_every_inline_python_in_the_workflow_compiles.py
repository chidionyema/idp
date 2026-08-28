"""crew#586: every `python3 -c '...'` in conscience.yml must compile (run 33204074988).

The first founder-line run reached the portal-page step and died there: the f-string
`f"{r[\\"green\\"]}"` is a SyntaxError (a backslash inside an f-string expression), so the
page never reached `bot/conscience-page`. Nothing in the suite ran those snippets; they
are shell strings, invisible to pytest. This test lifts every single-quoted `python3 -c`
body out of the workflow and compiles it, the way the runner would.
"""
from __future__ import annotations

import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/conscience.yml"
SNIPPET = re.compile(r"python3 -c '((?:[^'\\]|\\.)*)'", re.S)


def _snippets() -> list[tuple[str, str]]:
    wf = yaml.safe_load(WORKFLOW.read_text())
    out = []
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            for body in SNIPPET.findall(step.get("run", "") or ""):
                out.append((step.get("name", "?"), body))
    return out


def test_the_workflow_carries_inline_python():
    assert len(_snippets()) >= 3, "the grade job's steps lost their python3 -c snippets"


@pytest.mark.parametrize("step,body", _snippets(), ids=lambda v: v[:40] if isinstance(v, str) else v)
def test_every_inline_python_snippet_compiles(step, body):
    # a `\"` inside a single-quoted shell string reaches python as a backslash and is a SyntaxError
    assert "\\" not in body, f"step {step!r}: a backslash inside python3 -c '...' is what killed run 33204074988"
    compile(body, f"conscience.yml:{step}", "exec")
