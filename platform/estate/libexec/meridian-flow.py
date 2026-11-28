#!/usr/bin/env python3
"""meridian-flow: ask the compiled FLOW engine what to do with a task, against the real registry.

Outcome: one JSON decision line (event meridian.flow.decision) saying REUSE_OPERATING,
DECLARED_NOT_VERIFIED or IMPLEMENT_NEW for the task, read from catalog/estate-capability-registry.json.
It never runs a capability. DECLARED_NOT_VERIFIED means the registry only claims the route; it is
reported with its path and is not a service. Refusals print meridian.flow.refused and exit 2.

Each decision is also appended to ~/.estate/results/flow-decide.jsonl so there is a durable log line.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "crates" / "meridian-estate-engine"
REGISTRY = ROOT / "catalog" / "estate-capability-registry.json"
CARGO = Path.home() / ".cargo" / "bin" / "cargo"
TARGET = Path(
    os.environ.get(
        "ESTATE_FLOW_TARGET",
        str(Path.home() / ".estate" / "cache" / "meridian-engine-target"),
    )
)
INDEX = Path(
    os.environ.get("ESTATE_CAPABILITY_INDEX") or ROOT / "bin" / "capability-index"
)
# The door is granted 100s at most (the budget gate refuses a larger declaration), so the two
# bounded waits below must sum under it: 30s for the live registry read, 55s for the engine.
LIVE_TIMEOUT_S = int(os.environ.get("ESTATE_FLOW_LIVE_TIMEOUT", "30"))
ENGINE_TIMEOUT_S = int(os.environ.get("ESTATE_FLOW_ENGINE_TIMEOUT", "55"))
LOG = Path.home() / ".estate" / "results" / "flow-decide.jsonl"


def refuse(why: str) -> int:
    print(json.dumps({"event": "meridian.flow.refused", "reason": why}))
    return 2


def live_registry(tmp: Path) -> tuple[Path | None, str]:
    """The registry as the estate's own writer reads it NOW, not as the committed snapshot froze it.

    Why: a receipt is HMAC-signed with a per-machine key and expires, so the committed snapshot can
    never say `operating` to another reader (measured 2026-11-28: snapshot 0 operating, the live store
    on the same machine 52). Reading the snapshot made REUSE unreachable, a defect of the source and
    not of the engine. Returns (file, "") or (None, why) so the caller can fall back, loudly.
    """
    try:
        done = subprocess.run(
            [sys.executable, str(INDEX), "query", "--json", "--limit", "1000000"],
            capture_output=True,
            text=True,
            timeout=LIVE_TIMEOUT_S,
            check=False,
        )
        rows = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return None, f"live read failed: {type(exc).__name__}: {exc}"[:300]
    if not isinstance(rows, list) or not rows:
        return (
            None,
            f"live read exit {done.returncode}, no records: {(done.stderr or '').strip()[-200:]}",
        )
    rows = [r for r in rows if isinstance(r, dict) and not r.get("tombstoned")]
    if not rows:
        return None, "live read returned only tombstoned records"
    path = tmp / "live-registry.json"
    path.write_text(json.dumps({"records": rows}), encoding="utf-8")
    return path, ""


def main(argv: list[str]) -> int:
    intent = " ".join(argv).strip()
    if not intent:
        return refuse("no task text: pass the task as the argument")
    if not ENGINE.joinpath("Cargo.toml").exists():
        return refuse(f"engine workspace missing at {ENGINE}")
    cargo = os.environ.get("CARGO") or (str(CARGO) if CARGO.exists() else "cargo")
    env = {**os.environ, "CARGO_TARGET_DIR": str(TARGET)}
    with tempfile.TemporaryDirectory(prefix="meridian-flow-") as tmpdir:
        live, why = live_registry(Path(tmpdir))
        source = "live" if live else "snapshot"
        if not live:
            print(
                f"meridian-flow: {why}; falling back to the committed snapshot, which is "
                "declared-only (no receipt can verify there)",
                file=sys.stderr,
            )
        try:
            done = subprocess.run(
                [cargo, "run", "-q", "--locked", "-p", "meridian-army", "--"]
                + ["--registry", str(live or REGISTRY), "--intent", intent],
                cwd=ENGINE,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=ENGINE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return refuse(
                f"engine did not answer in {ENGINE_TIMEOUT_S}s (a cold build does not fit the "
                "door): build it first, detached: cd crates/meridian-estate-engine && "
                "cargo build --locked -p meridian-army"
            )
    lines = done.stdout.strip().splitlines()
    if done.returncode not in (0, 2) or not lines:
        return refuse(
            f"engine exit {done.returncode}: {(done.stderr or '').strip()[-300:]}"
        )
    try:
        record = json.loads(lines[-1])
    except ValueError:
        return refuse(f"engine printed a line that is not JSON: {lines[-1][:200]}")
    record["registry_source"] = source
    if why:
        record["live_error"] = why
    print(json.dumps(record, sort_keys=True))
    try:
        record["at"] = int(time.time())
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        print(
            f"meridian-flow: decision printed, log append failed: {exc}",
            file=sys.stderr,
        )
    return done.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
