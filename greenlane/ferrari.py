"""Read-only, exact-candidate DoF preflight for the existing Greenlane.

This is a CI *cost* gate, never a release authorization. Only an explicit,
well-formed refusal by the trusted main-branch DoF code can suppress an
expensive candidate test. UNKNOWN always continues to ordinary required CI.
No candidate source is executed by this module.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TRUSTED_DOF = Path(__file__).resolve().parents[1] / "bin" / "dof-gate"


@dataclass(frozen=True)
class Verdict:
    state: str  # ADMIT / REFUSE / UNKNOWN
    reason: str
    fingerprint: str = ""

    @property
    def admissible(self) -> bool:
        return self.state != "REFUSE"


def interpret(base: str, returncode: int, stdout: str) -> Verdict:
    try:
        result = json.loads(stdout)
        if not isinstance(result, dict) or result.get("gate") != "dof":
            return Verdict("UNKNOWN", "unrecognised trusted gate output")
        decisions = result.get("commits")
        if not isinstance(decisions, list) or not decisions:
            return Verdict("UNKNOWN", "no per-commit proof")
        if any(not isinstance(c, dict) or type(c.get("admitted")) is not bool
               for c in decisions):
            return Verdict("UNKNOWN", "malformed proof")
        ok = result.get("ok")
        if type(ok) is not bool:
            return Verdict("UNKNOWN", "missing gate verdict")
        if returncode == 0 and ok and all(c["admitted"] for c in decisions):
            return Verdict("ADMIT", "trusted DoF accepted; full required CI remains mandatory")
        refusals = [c for c in decisions if c["admitted"] is False]
        if returncode != 1 or ok or not refusals:
            return Verdict("UNKNOWN", "gate exit/result disagreement")
        reasons = sorted({str(c.get("reason", "")).strip() for c in refusals
                          if c.get("reason")})
        if not reasons:
            return Verdict("UNKNOWN", "DoF refused without diagnosis")
        incident_ids = sorted(str(i.get("id")) for i in result.get("open_incidents", [])
                              if isinstance(i, dict) and i.get("id"))
        canonical = json.dumps(["dof", base, incident_ids, reasons], separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()[:20]
        return Verdict("REFUSE", f"trusted DoF [{fingerprint}]: {'; '.join(reasons)[:300]}", fingerprint)
    except (TypeError, ValueError, AttributeError):
        return Verdict("UNKNOWN", "unparseable trusted gate result")


def assess(base: str, candidate: str, repo: str, runner=None) -> Verdict:
    if not TRUSTED_DOF.is_file():
        return Verdict("UNKNOWN", "trusted main DoF gate missing")
    execute = runner or subprocess.run
    try:
        p = execute(
            [sys.executable, str(TRUSTED_DOF), base, candidate],
            capture_output=True, text=True, timeout=45, check=False,
            env={**os.environ, "GITHUB_REPOSITORY": repo},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Verdict("UNKNOWN", f"trusted gate unavailable: {type(exc).__name__}")
    return interpret(base, p.returncode, p.stdout)
