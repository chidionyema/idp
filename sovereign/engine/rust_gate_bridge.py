"""Thin Temporal-side subprocess bridge to the compiled Rust `meridian-gate` binary.

Holds ZERO invariant logic in Python. If the compiled Rust binary is missing,
unexecutable, or returns invalid JSON, this bridge fails closed (`RustGateBlindError`).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class RustGateError(RuntimeError):
    def __init__(self, verdict: Dict[str, Any], returncode: int) -> None:
        self.verdict = verdict
        self.returncode = returncode
        super().__init__(f"MERIDIAN_GATE_REJECTED rc={returncode} verdict={json.dumps(verdict, sort_keys=True)}")


class RustGateBlindError(RustGateError):
    """Fail-closed error when the compiled Rust binary is absent or unreadable."""


def resolve_binary(explicit: Optional[str] = None) -> Path:
    candidates = [
        explicit,
        os.environ.get("MERIDIAN_GATE_BIN"),
        "target/release/meridian-gate",
        "target/debug/meridian-gate",
        shutil.which("meridian-gate"),
    ]
    for c in candidates:
        if c:
            p = Path(c)
            if p.is_file() and os.access(p, os.X_OK):
                return p
    raise RustGateBlindError(
        {
            "verdict": "BLIND",
            "error": {"code": "BLIND_OBSERVATION", "detail": "compiled rust meridian-gate binary missing"},
            "violated_predicate": "B10_COMPILED_ENFORCEMENT_REQUIRED",
        },
        returncode=127,
    )


def call_rust_gate(subcommand: str, payload: Any, binary: Optional[str] = None, timeout_s: int = 10) -> Dict[str, Any]:
    bin_path = resolve_binary(binary)
    stdin_text = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run(
        [str(bin_path), subcommand, "-"],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    raw = proc.stdout.strip()
    try:
        verdict = json.loads(raw)
    except Exception as exc:
        raise RustGateBlindError(
            {
                "verdict": "BLIND",
                "error": {"code": "BLIND_OBSERVATION", "detail": f"non-json output: {exc}"},
            },
            returncode=proc.returncode or 2,
        ) from exc

    if proc.returncode != 0 or verdict.get("verdict") != "ALLOW":
        raise RustGateError(verdict, returncode=proc.returncode)
    return verdict
