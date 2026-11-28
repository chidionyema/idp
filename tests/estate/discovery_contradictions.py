#!/usr/bin/env python3
"""Reading for optimus.estate.discovery_contradictions (idp#8746).

WHY. `bin/estate-discovery` is the receipt an agent holds before it reports a block, and the
whole point of it is that a declared status is judged against a probe instead of trusted. The
number that says whether it is doing that job is how often the ledger's own verdict is
CONTRADICTED -- a resource declared up that did not answer, or declared down that did.

WHAT IS COUNTED. Every resource in catalog/estate-resources.json is probed by the shipped
`bin/estate-discovery` itself (never by a copy of its logic here), and the reading is the
number of rows whose verdict is CONTRADICTED *and* whose probe actually produced an answer.
A probe that could not run on this host (a timeout, a missing binary) is a fact about the
host's reach, not about the estate's declaration: the receipt records it as CONTRADICTED for
an OPERATIONAL resource, and this measure prints that count separately on stderr so it is never
silently dropped. That distinction is what makes the reading the same on a laptop and in CI.

    0  every observed resource matched its declared status
    n  n observed resources were declared one way and answered another
    exit 2, nothing on stdout
       the ledger or the tool cannot be run here, so nothing was judged: a broken measurement
       is BLIND, never a 0 that reads as a verdict

    python3 tests/estate/discovery_contradictions.py
        -> optimus.estate.discovery_contradictions=0
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "bin" / "estate-discovery"
NAME = "optimus.estate.discovery_contradictions"


def reading() -> int:
    """CONTRADICTED rows whose probe answered, from the shipped tool's own output."""
    if not TOOL.is_file():
        print(f"BLIND {NAME}: {TOOL} is missing", file=sys.stderr)
        raise SystemExit(2)
    with tempfile.TemporaryDirectory(prefix="discovery-measure-") as tmp:
        # Never clobber the host's real receipt: this run is a measurement, not a discovery.
        env = {**os.environ, "ESTATE_DISCOVERY_RECEIPT": str(Path(tmp) / "latest.json")}
        run = subprocess.run(
            [sys.executable, str(TOOL)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    rows = [ln for ln in (run.stdout or "").splitlines() if "\t" in ln]
    receipt = [
        ln for ln in (run.stdout or "").splitlines() if ln.startswith("receipt ")
    ]
    if not rows or not receipt:
        detail = (run.stderr or "").strip().splitlines()
        print(
            f"BLIND {NAME}: {TOOL} printed no receipt: "
            + (detail[-1] if detail else f"exit {run.returncode}")[:200],
            file=sys.stderr,
        )
        raise SystemExit(2)
    observed = 0
    unrun = 0
    for line in rows:
        field = line.split("\t")
        if len(field) < 4 or field[-1] != "CONTRADICTED":
            continue
        if "probe-error=" in field[2]:
            unrun += 1
        else:
            observed += 1
    if unrun:
        print(
            f"  {unrun} row(s) contradicted only because a probe could not run on this host",
            file=sys.stderr,
        )
    return observed


def main() -> int:
    print(f"{NAME}={reading()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
