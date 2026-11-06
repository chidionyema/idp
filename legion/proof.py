"""Legion proof runner — proof is a command, evidence is a chain.

`legion proof <manifest>` runs the manifest's proof.command under the clamped
timeout and appends a record to the legion's evidence chain:
state/legion-proof.jsonl (LEGION_STATE_DIR overrides the state dir).

Each record carries a sha256 over the previous record's hash + its own
canonical body — the same tamper-evidence pattern as pi_bridge's run log, so
"proven operational" is verifiable by anyone, and a stale or broken chain is
detectable by `legion proof --verify <chain-file>`.

Truth standard: this tool records what the proof command ACTUALLY did — its
exit code, its duration, the tail of its output. It never upgrades a failure.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifest import MAX_PROOF_SECONDS, load_manifest

OUTPUT_TAIL_CHARS = 500  # enough to diagnose, small enough to chain forever


def _state_dir() -> Path:
    import os

    override = os.environ.get("LEGION_STATE_DIR")
    return Path(override) if override else Path("state")


def _canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _chain_hash(prev: str, record: dict[str, Any]) -> str:
    """sha256 over the previous link's hash + this record's canonical body
    (the body excludes its own hash/prev so the chain is re-computable)."""
    body = {k: v for k, v in record.items() if k not in ("hash", "prev")}
    return hashlib.sha256(prev.encode() + _canonical(body)).hexdigest()


def run_proof(manifest_path: str | Path) -> dict[str, Any]:
    """Run the manifest's proof command and append the chained evidence record.
    Returns the record. Exit-code semantics live on the record, not on raised
    exceptions — a failed proof is a recorded fact, not a crash."""
    manifest = load_manifest(manifest_path)
    proof = manifest["proof"]
    timeout = min(float(proof.get("max_seconds", 300)), float(MAX_PROOF_SECONDS))
    command = proof["command"]

    started = time.time()
    started_iso = datetime.now(tz=timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(manifest_path).resolve().parent,
        )
        exit_code, timed_out = proc.returncode, False
        output_tail = (proc.stdout + proc.stderr)[-OUTPUT_TAIL_CHARS:]
    except subprocess.TimeoutExpired as exc:
        exit_code, timed_out = 124, True
        out = (exc.stdout or b"") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = (exc.stderr or b"") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        output_tail = (out + err)[-OUTPUT_TAIL_CHARS:] + "\n[proof: TIMEOUT]"
    duration_ms = round((time.time() - started) * 1000, 1)

    chain = _state_dir() / "legion-proof.jsonl"
    chain.parent.mkdir(parents=True, exist_ok=True)
    prev = "0" * 64
    if chain.exists():
        lines = [ln for ln in chain.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            prev = json.loads(lines[-1])["hash"]

    record: dict[str, Any] = {
        "legion": manifest.get("name", "?"),
        "ts": started_iso,
        "command": command,
        "exit": exit_code,
        "ok": exit_code == 0 and not timed_out,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "output_tail": output_tail,
        "prev": prev,
    }
    record["hash"] = _chain_hash(prev, record)
    with chain.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def verify_chain(chain_path: str | Path) -> list[str]:
    """Re-walk a proof chain; returns every integrity problem found."""
    problems: list[str] = []
    prev = "0" * 64
    path = Path(chain_path)
    if not path.exists():
        return [f"{path}: no such chain"]
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"line {n}: not JSON - {exc}")
            continue
        if record.get("prev") != prev:
            problems.append(f"line {n}: prev link broken")
        want = _chain_hash(record.get("prev", ""), record)
        if record.get("hash") != want:
            problems.append(f"line {n}: hash mismatch (tampered record)")
        prev = record.get("hash", prev)
    return problems
