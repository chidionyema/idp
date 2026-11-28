"""Optimus measure: kernel.rust_invariant_gate_enforced (MERIDIAN-CTRL-001 B06/B08/B10, section 11).

Runs the compiled Rust `meridian-gate --optimus` and relays its reading. The gate itself drives
the real kernel both ways (a valid admission and settlement are allowed; cross-class billing, a
proxy-green contract, an expired deadline and a self-certified receipt are refused). Stdlib
only: the Greenlane judge runs this under a bare python3 inside a 60 second bound.

Binary lookup: $MERIDIAN_GATE_BIN, then target/release/meridian-gate. With neither, it builds
the release binary when cargo is on PATH. If no binary can be produced, it prints 0: a gate
that is not there enforces nothing.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = "kernel.rust_invariant_gate_enforced"
LINE = re.compile(rf"^optimus\.{re.escape(NAME)}=(\d+)\s*$", re.MULTILINE)


def _binary() -> pathlib.Path | None:
    for cand in (
        os.environ.get("MERIDIAN_GATE_BIN"),
        str(ROOT / "target/release/meridian-gate"),
    ):
        if cand and pathlib.Path(cand).is_file() and os.access(cand, os.X_OK):
            return pathlib.Path(cand)
    cargo = shutil.which("cargo")
    if cargo is None:
        return None
    try:
        built = subprocess.run(  # noqa: S603 - fixed argv
            [cargo, "build", "--release", "--locked", "-q", "-p", "meridian-gate"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=52,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    path = ROOT / "target/release/meridian-gate"
    return path if built.returncode == 0 and path.is_file() else None


def measure() -> int:
    binary = _binary()
    if binary is None:
        return 0
    try:
        run = subprocess.run(  # noqa: S603 - fixed argv
            [str(binary), "--optimus"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    found = LINE.search(run.stdout or "")
    return 1 if run.returncode == 0 and found and found.group(1) == "1" else 0


if __name__ == "__main__":
    print(f"optimus.{NAME}={measure()}")
    sys.exit(0)
