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
import shutil
import subprocess
import sys
import tempfile
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
        if any(
            not isinstance(c, dict) or type(c.get("admitted")) is not bool
            for c in decisions
        ):
            return Verdict("UNKNOWN", "malformed proof")
        ok = result.get("ok")
        if type(ok) is not bool:
            return Verdict("UNKNOWN", "missing gate verdict")
        if returncode == 0 and ok and all(c["admitted"] for c in decisions):
            return Verdict(
                "ADMIT", "trusted DoF accepted; full required CI remains mandatory"
            )
        refusals = [c for c in decisions if c["admitted"] is False]
        # A denied API read is the gate's synthetic dof-probe, not an actual
        # healthy-authorized incident. We must NOT park otherwise valid work
        # based on a credential/observer failure in this cost-only pass.
        incidents = result.get("open_incidents")
        if (
            not isinstance(incidents, list)
            or not incidents
            or any(
                not isinstance(i, dict)
                or i.get("id") == "dof-probe"
                or not isinstance(i.get("issue"), int)
                for i in incidents
            )
        ):
            return Verdict("UNKNOWN", "incident observation unproved; run trusted CI")
        if returncode != 1 or ok or not refusals:
            return Verdict("UNKNOWN", "gate exit/result disagreement")
        reasons = sorted(
            {str(c.get("reason", "")).strip() for c in refusals if c.get("reason")}
        )
        if not reasons:
            return Verdict("UNKNOWN", "DoF refused without diagnosis")
        incident_ids = sorted(
            str(i.get("id"))
            for i in result.get("open_incidents", [])
            if isinstance(i, dict) and i.get("id")
        )
        canonical = json.dumps(
            ["dof", base, incident_ids, reasons], separators=(",", ":")
        )
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()[:20]
        return Verdict(
            "REFUSE",
            f"trusted DoF [{fingerprint}]: {'; '.join(reasons)[:300]}",
            fingerprint,
        )
    except (TypeError, ValueError, AttributeError):
        return Verdict("UNKNOWN", "unparseable trusted gate result")


def assess(base: str, candidate: str, repo: str, runner=None) -> Verdict:
    if not TRUSTED_DOF.is_file():
        return Verdict("UNKNOWN", "trusted main DoF gate missing")
    execute = runner or subprocess.run
    try:
        p = execute(
            [sys.executable, str(TRUSTED_DOF), base, candidate],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            env={
                **os.environ,
                "GITHUB_REPOSITORY": repo,
                "GH_TOKEN": os.environ.get("GREENLANE_STATUS_TOKEN")
                or os.environ.get("GITHUB_TOKEN")
                or os.environ.get("GH_TOKEN", ""),
            },
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Verdict("UNKNOWN", f"trusted gate unavailable: {type(exc).__name__}")
    return interpret(base, p.returncode, p.stdout)

# Fast CI runs MUST NOT be the first observer of deterministic source defects.
# This is a cost-only admission pass: it reads Git objects, never executes
# candidate code, and does not replace protected required checks.
TRUSTED_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_LANGUAGE_GATE = TRUSTED_ROOT / "bin" / "language-gate"
TRUSTED_RUFF_VERSION = "0.15.18"


def source_assess(
    base: str,
    candidate: str,
    repo: str,
    runner=None,
    checkout: Path | None = None,
    ruff_binary: str | bool | None = None,
) -> Verdict:
    """Reject provable language/format failures before any queue CI starts."""
    execute = runner or subprocess.run
    cwd = checkout or TRUSTED_ROOT
    try:
        lang = execute(
            [sys.executable, str(TRUSTED_LANGUAGE_GATE), base, candidate],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        if lang.returncode == 1 and "FAIL  language-gate:" in lang.stderr:
            return Verdict(
                "REFUSE", "pre-CI language-gate: " + lang.stderr.strip()[:220]
            )
        if lang.returncode != 0:
            return Verdict("UNKNOWN", "trusted language preflight unavailable")
        changed = execute(
            [
                "git",
                "diff",
                "--name-only",
                "-z",
                "--diff-filter=ACMR",
                f"{base}...{candidate}",
                "--",
                "*.py",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if changed.returncode:
            return Verdict("UNKNOWN", "candidate Python paths unavailable")
        python_paths = [p for p in changed.stdout.split("\0") if p]
        if not python_paths:
            return Verdict(
                "ADMIT", "trusted language gate passed; no Python format delta"
            )
        for name in python_paths:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or name.startswith(".git/"):
                return Verdict("REFUSE", "unsafe candidate Python path")
        # The exact Ruff version installed by fast-gate and the agent worker.
        # Missing format authority holds the Python lane rather than launching
        # expensive CI that can only discover the same unformatted files.
        binary = ruff_binary if ruff_binary is not None else shutil.which("ruff")
        if not binary and ruff_binary is None:
            installer = execute(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--disable-pip-version-check",
                    "--no-input",
                    "--only-binary=:all:",
                    f"ruff=={TRUSTED_RUFF_VERSION}",
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                env={
                    k: v
                    for k, v in os.environ.items()
                    if not any(
                        s in k.upper() for s in ("TOKEN", "SECRET", "PASSWORD", "KEY")
                    )
                },
            )
            if installer.returncode:
                return Verdict("REFUSE", "pre-CI hold: trusted pinned Ruff unavailable")
            binary = shutil.which("ruff")
        if not binary:
            return Verdict("REFUSE", "pre-CI hold: trusted pinned Ruff unavailable")
        with tempfile.TemporaryDirectory(prefix="greenlane-pre-ci-") as folder:
            names = []
            for name in python_paths:
                blob = execute(
                    ["git", "show", f"{candidate}:{name}"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if blob.returncode:
                    return Verdict("UNKNOWN", "candidate Python blob unavailable")
                target = Path(folder) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(blob.stdout, encoding="utf-8")
                names.append(str(target))
            check = execute(
                [
                    str(binary),
                    "format",
                    "--check",
                    "--config",
                    str(TRUSTED_ROOT / "pyproject.toml"),
                    *names,
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=35,
                check=False,
            )
            if check.returncode == 1:
                return Verdict(
                    "REFUSE",
                    "pre-CI Ruff format failure: " + ", ".join(python_paths)[:220],
                )
            if check.returncode != 0:
                return Verdict("REFUSE", "pre-CI hold: pinned Ruff could not verify")
        return Verdict("ADMIT", "trusted language and exact-source Ruff format passed")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return Verdict("UNKNOWN", "trusted source preflight unavailable")
