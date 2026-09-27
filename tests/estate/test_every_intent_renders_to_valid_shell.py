"""Every intent step, rendered the way estate-execute renders it, is valid shell.

2026-09-26: six intents used a `{{if(...)}}` form the executor's interpolate() never renders, so
it reached sh verbatim and every call was a syntax error -- for days, silently, because nothing
ran them. This renders each step with its declared defaults (a placeholder for required args)
and asks `bash -n`, so a template the executor cannot render is a red test, not a dead door.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

INTENTS = sorted(
    (Path(__file__).resolve().parents[2] / "platform/estate/intents").glob("*.yaml")
)


def _render(cmd: str, args: dict) -> str:
    # the same substitution as platform/estate/bin/estate-execute interpolate()
    for name, val in args.items():
        cmd = cmd.replace("{{" + name + "}}", shlex.quote(str(val)))
        cmd = cmd.replace("<<" + name + ">>", str(val))
    return cmd


@pytest.mark.parametrize("path", INTENTS, ids=lambda p: p.stem)
def test_intent_steps_render_to_valid_shell(path):
    intent = yaml.safe_load(path.read_text())
    args = {
        k: (v or {}).get("default", "x") if isinstance(v, dict) else v
        for k, v in (intent.get("args") or {}).items()
    }
    for step in intent.get("steps") or []:
        if "cmd" not in step:
            continue  # a composite step names another intent; that intent is tested itself
        cmd = _render(step["cmd"], args)
        left = re.findall(r"\{\{\s*[A-Za-z_]\w*\s*[(}]", cmd)
        assert not left, (
            f"{path.name}: unrendered template {left} -- interpolate() only does {{{{var}}}}"
        )
        r = subprocess.run(["bash", "-n", "-c", cmd], capture_output=True, text=True)
        assert r.returncode == 0, (
            f"{path.name} step {step.get('name')}: {r.stderr}\n{cmd}"
        )
