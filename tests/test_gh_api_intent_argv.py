"""The gh-api door sends gh the argv the caller wrote, including no params at all.

Measured 2026-10-25, through the door: `gh-api` with params omitted ran `gh api <path> ''` and gh
answered "accepts 1 arg(s), received 2"; with `params: --jq .state` it sent ONE quoted word and gh
printed its help text. The cause was the executor's own quoting (interpolate() shell-quotes every
{{arg}}, deliberately), not the API, so the intent must build an argv instead of pasting a string.

This test renders the intent exactly as the executor does -- same YAML, same shlex.quote
substitution -- and runs the rendered step with a stub `gh` on PATH that prints each argv word on
its own line. It asserts what gh would actually receive.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INTENT = ROOT / "platform/estate/intents/gh-api.yaml"


def _render(args: dict) -> str:
    """The intent's step command, substituted the way platform/estate/bin/estate-execute does."""
    spec = yaml.safe_load(INTENT.read_text())
    values = {k: v.get("default", "") for k, v in spec["args"].items()}
    values.update(args)
    cmd = spec["steps"][0]["cmd"]
    for name, val in values.items():
        cmd = cmd.replace("{{" + name + "}}", shlex.quote(str(val)))
    return cmd


def _run(cmd: str, tmp_path: Path) -> list[str]:
    """Run the rendered command with a stub gh; return the argv words gh received."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    out = tmp_path / "argv.txt"
    gh = bin_dir / "gh"
    gh.write_text(
        '#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > ' + str(out) + "\n"
    )
    gh.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    r = subprocess.run(
        ["bash", "-c", cmd], env=env, capture_output=True, text=True, timeout=60
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.exists(), "the stub gh was never called: " + r.stdout + r.stderr
    return out.read_text().splitlines()


@pytest.mark.parametrize(
    "params,expected",
    [
        ("", ["api", "repos/chidionyema/idp/commits/abc1234/status"]),
        (
            "--jq .state",
            ["api", "repos/chidionyema/idp/commits/abc1234/status", "--jq", ".state"],
        ),
        (
            "--jq .statuses[].state",
            [
                "api",
                "repos/chidionyema/idp/commits/abc1234/status",
                "--jq",
                ".statuses[].state",
            ],
        ),
        (
            "--paginate",
            ["api", "repos/chidionyema/idp/commits/abc1234/status", "--paginate"],
        ),
    ],
)
def test_gh_receives_the_argv_the_caller_meant(tmp_path, params, expected):
    cmd = _render({"path": "commits/abc1234/status", "params": params})
    assert _run(cmd, tmp_path) == expected


def test_an_omitted_params_never_becomes_an_empty_argument(tmp_path):
    """The exact defect: a lone '' made gh report "accepts 1 arg(s), received 2"."""
    cmd = _render({"path": "commits/abc1234/status"})
    argv = _run(cmd, tmp_path)
    assert "" not in argv, argv
    assert len(argv) == 2, argv  # `api` and the path, nothing between or after


def test_the_template_does_not_paste_params_into_the_shell_bare():
    """A regression guard a reviewer can read: the bare {{params}} slot is what broke."""
    cmd = yaml.safe_load(INTENT.read_text())["steps"][0]["cmd"]
    for line in cmd.splitlines():
        if "{{params}}" in line:
            assert line.strip().startswith("p="), (
                "{{params}} may only be assigned to a variable (p={{params}}), never used as an "
                f"argument position: {line!r}"
            )
