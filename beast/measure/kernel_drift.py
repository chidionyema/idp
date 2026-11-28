#!/usr/bin/env python3
"""Optimus measure: Beast kernel files that differ from the committed sha256 manifest.

Target 0. A file that is missing, altered or unlisted counts once. This reads the tree it is run
in, so it measures the Beast that landed, byte for byte. It does not measure that the Beast is
running; that is the SHIP-CONTRACT probe's job.
Prints exactly one line: optimus.beast.kernel_manifest_drift_files=<n>
"""

import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
MANIFEST = ROOT / "beast" / "measure" / "kernel.sha256"
TREE = ROOT / "beast" / "meridian-beast-v1"

want = {}
for line in MANIFEST.read_text().splitlines():
    digest, _, path = line.partition("  ")
    if digest and path:
        want[path] = digest

have = {}
for p in TREE.rglob("*"):
    if p.is_file():
        have[p.relative_to(ROOT).as_posix()] = hashlib.sha256(
            p.read_bytes()
        ).hexdigest()

drift = sum(1 for k in set(want) | set(have) if want.get(k) != have.get(k))
print(f"optimus.{'beast.kernel_manifest_drift_files'}={drift}")
