#!/usr/bin/env python3
"""Recompute the manifest against the bytes on disk. Exit 1 on any disagreement."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def main() -> int:
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    bad, n = [], 0
    for repo, entry in sorted(manifest.items()):
        for rel, want in sorted(entry["files"].items()):
            f = HERE / repo / rel
            n += 1
            if not f.is_file():
                bad.append(f"{repo}/{rel}: missing")
                continue
            got = hashlib.sha256(f.read_bytes()).hexdigest()
            if got != want:
                bad.append(f"{repo}/{rel}: {got[:12]} != {want[:12]}")

    declared = {f"{r}/{p}" for r, e in manifest.items() for p in e["files"]}
    skip = {"MANIFEST.json", "verify.py", "README.md"}
    on_disk = {
        str(p.relative_to(HERE))
        for p in HERE.rglob("*")
        if p.is_file() and p.name not in skip
    }
    bad += [f"{p}: present but not declared" for p in sorted(on_disk - declared)]
    if bad:
        print("\n".join(bad[:20]))
        print(f"FAIL {len(bad)} disagreement(s) over {n} declared file(s)")
        return 1
    print(f"OK {n} files match the manifest across {len(manifest)} repositories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
