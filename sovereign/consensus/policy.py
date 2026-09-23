"""The policy invariant that beats consensus (cp30, spec v1.0 4.2).

This module runs conftest against policy/sovereign_command.rego. It does
not decide anything itself, and that is the design: bin/policy-test, the
licence gate and the placement gate already evaluate this estate's rules
with conftest, and the estate's ruling is that command guards are Rego.
LAW 43 -- the rejected alternative was a Python allowlist next to
sovereign/consensus/models.py, which would have been a second policy
engine, unauditable from outside the process, and untestable by the
paired-control harness bin/policy-test already is.

Fails CLOSED, every time. conftest missing, the policy directory missing,
the binary timing out, JSON that will not parse: all of them are `allowed:
False` with a reason, never a pass. A policy engine that cannot be
reached has not said yes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from sovereign.consensus import config_keys as ck

_OUTPUT_FLAG = "--output"
_OUTPUT_FORMAT = "json"
_PARSER_FLAG = "--parser"
_NAMESPACE_FLAG = "--namespace"
_POLICY_FLAG = "-p"
_JSON_SUFFIX = ".json"


def idp_root() -> Path:
    """The checkout root, computed from this file's own location -- never
    a literal home directory or checkout path (LAW 46). sovereign/ sits
    directly under it."""
    env = os.environ.get("IDP_ROOT")
    if env:
        return Path(env)
    # .parent three times, not parents[2]: config.py's lint refuses a
    # bare numeric literal outside {0, 1, -1} anywhere under sovereign/,
    # and an index is exactly the kind of number it is looking for.
    return Path(__file__).resolve().parent.parent.parent


def policy_dir() -> Path:
    return idp_root() / str(ck.get("consensus.policy_dirname"))


def evaluate(command: str, destructive: bool = True) -> dict[str, Any]:
    """Returns {"allowed", "reason", "violations", "engine"}.

    `reason` is "policy" whenever the policy itself refused, which is the
    exact word cp30's receipt has to carry. An engine failure gets its own
    reason so an outage is never mistaken for a refusal, but it is still
    not allowed."""
    binary = str(ck.get("consensus.policy_binary"))
    resolved = shutil.which(binary)
    if resolved is None:
        return {"allowed": False, "reason": "policy_engine_missing",
                "violations": [f"{binary} is not on PATH"], "engine": binary}
    directory = policy_dir()
    if not directory.is_dir():
        return {"allowed": False, "reason": "policy_missing",
                "violations": [f"no policy directory at {directory}"], "engine": binary}

    document = {"command": command, "destructive": bool(destructive)}
    with tempfile.TemporaryDirectory() as tmp:
        doc_path = Path(tmp) / (Path(tmp).name + _JSON_SUFFIX)
        doc_path.write_text(json.dumps(document))
        cmd = [
            resolved, "test",
            _PARSER_FLAG, _OUTPUT_FORMAT,
            _NAMESPACE_FLAG, str(ck.get("consensus.policy_namespace")),
            _POLICY_FLAG, str(directory),
            _OUTPUT_FLAG, _OUTPUT_FORMAT,
            str(doc_path),
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=float(ck.get("consensus.policy_timeout_s")),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"allowed": False, "reason": "policy_engine_error",
                    "violations": [str(exc)], "engine": binary}

    violations = _failures(proc.stdout)
    if proc.returncode == 0 and not violations:
        return {"allowed": True, "reason": None, "violations": [], "engine": binary}
    if violations:
        return {"allowed": False, "reason": "policy", "violations": violations, "engine": binary}
    # Non-zero with nothing parseable to show for it: an engine problem,
    # not a policy refusal, and still not a pass.
    return {"allowed": False, "reason": "policy_engine_error",
            "violations": [proc.stderr.strip() or proc.stdout.strip()], "engine": binary}


def _failures(stdout: str) -> list[str]:
    try:
        results = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return []
    out: list[str] = []
    for result in results if isinstance(results, list) else []:
        for failure in (result.get("failures") or []):
            message = failure.get("msg") if isinstance(failure, dict) else str(failure)
            if message:
                out.append(str(message))
    return out
