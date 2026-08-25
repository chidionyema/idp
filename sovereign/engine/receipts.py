"""Receipts: a signed, append-only hash chain (cp19). Every line carries a
monotonic counter, the previous line's hash, its own hash over everything
but hash/sig, and an HMAC-SHA256 signature under the estate key. The key
lives in the macOS Keychain and is never written to disk; on a non-macOS
host it falls back to a 0600 file under $ESTATE_HOME (backend
"software_file" records which happened). Writes are serialized with a file
lock so the counter/prev_hash chain is never raced (CONTRACT.md).

A hash chain only proves that what is present has not been edited -- it
cannot see entries removed from its own tail, because nothing downstream
of the tail exists to notice the missing prev_hash link. append() closes
that gap: after every write it also rewrites a small signed head anchor
(config.RECEIPTS_HEAD) recording the counter and hash of the line that
was just appended, HMAC-signed under the same key. verify() then checks
the *last line on disk* against that anchor, not just the chain among
the lines that happen to still be there -- a chain with its tail cut off
still verifies internally (every remaining prev_hash link is intact) but
now disagrees with the anchor, which is the tamper it exists to catch.

R23 (spec 4.1, "A hardware monotonic counter prevents replay attacks").
The counter was monotonic only for as long as the log file existed:
append() read the last line, added one, and a deleted or truncated log
restarted it at 1, so an old line could be replayed at a counter the
chain would accept. The counter is now the maximum of three independent
sources -- the last line on disk, the signed head anchor, and a signed
watermark file (config.RECEIPTS_COUNTER) that only ever moves up -- so
the next counter cannot go backwards even with the log removed entirely.
Secure Enclave exposes no monotonic counter to userspace on this
machine, so this is the spec's fallback shape, signed under the same
estate key and recorded as such rather than claimed as hardware.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import secrets
import subprocess
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.trust import HardwareTrustAnchor

GENESIS_HASH = "0" * config.RECEIPTS_HASH_HEX_LEN

# Fields a line's own hash does not cover. hash and sig are derived from
# the body; hw_sig and hw_backend (a `signed` record, cp20) are a hardware
# signature OVER that hash and so can only be added after it exists.
# append() and verify() both exclude exactly this tuple -- before it was
# one tuple, verify() excluded only (hash, sig), recomputed the hash over a
# body that now also held hw_sig, and reported every signed line as
# "broken" (found by cp33/cp34's first run, 2026-08-25).
UNHASHED_FIELDS: tuple[str, ...] = ("hash", "sig", "hw_sig", "hw_backend")
_canonical = config.canonical_json


def _keychain_read() -> str | None:
    try:
        out = subprocess.run(
            [
                "security", "find-generic-password",
                "-a", config.RECEIPTS_KEYCHAIN_ACCOUNT,
                "-s", config.RECEIPTS_KEYCHAIN_SERVICE,
                "-w",
            ],
            capture_output=True, text=True, timeout=config.RECEIPTS_KEYCHAIN_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode == 0 and out.stdout.strip():
        return out.stdout.strip()
    return None


def _keychain_write(hex_key: str) -> bool:
    try:
        out = subprocess.run(
            [
                "security", "add-generic-password",
                "-a", config.RECEIPTS_KEYCHAIN_ACCOUNT,
                "-s", config.RECEIPTS_KEYCHAIN_SERVICE,
                "-w", hex_key,
                "-U",
            ],
            capture_output=True, text=True, timeout=config.RECEIPTS_KEYCHAIN_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def _software_key_path() -> Path:
    return config.SOVEREIGN_HOME / "receipts.key"


def get_or_create_key() -> tuple[bytes, str]:
    """Returns (key_bytes, backend) where backend is "keychain" or
    "software_file". Never logs or returns the key as a printable secret
    to a caller that would print it -- callers here use it only for HMAC.
    cp20: the only OS-detection call anywhere in sovereign/ lives in
    sovereign/trust/anchor.py; this asks HardwareTrustAnchor().backend
    rather than making that call itself -- secure_enclave is the only
    backend anchor.py ever detects on a Keychain-bearing OS, so it is the
    same condition the old direct OS-name check here used to stand in
    for, without a second such branch out here."""
    if HardwareTrustAnchor().backend == "secure_enclave":
        existing = _keychain_read()
        if existing:
            return bytes.fromhex(existing), "keychain"
        new_key = secrets.token_hex(config.RECEIPTS_KEY_BYTES)
        if _keychain_write(new_key):
            return bytes.fromhex(new_key), "keychain"
        # fall through to the file backend if Keychain is unusable here
    path = _software_key_path()
    if path.exists():
        return bytes.fromhex(path.read_text().strip()), "software_file"
    new_key = secrets.token_hex(config.RECEIPTS_KEY_BYTES)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_key)
    path.chmod(config.RECEIPTS_KEY_FILE_MODE)
    return bytes.fromhex(new_key), "software_file"


def _lock_path() -> Path:
    return config.SB_RECEIPTS.parent / (config.SB_RECEIPTS.name + ".lock")


def _head_anchor(counter: int, line_hash: str, key: bytes) -> dict[str, Any]:
    body = {"counter": counter, "hash": line_hash}
    sig = hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()
    return {"counter": counter, "hash": line_hash, "sig": sig}


def _write_head_anchor(anchor: dict[str, Any]) -> None:
    """Called only from inside append()'s own lock, so this never races the
    next append. Written to a tmp file and moved into place with os.replace
    so a crash mid-write leaves the old anchor (a stale-but-valid anchor
    fails closed as "truncated", never a silent pass) rather than a
    half-written one."""
    config.RECEIPTS_HEAD.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.RECEIPTS_HEAD.with_suffix(config.RECEIPTS_HEAD.suffix + ".tmp")
    tmp.write_text(json.dumps(anchor, sort_keys=True))
    os.replace(tmp, config.RECEIPTS_HEAD)


def _read_head_anchor() -> dict[str, Any] | None:
    if not config.RECEIPTS_HEAD.exists():
        return None
    try:
        return json.loads(config.RECEIPTS_HEAD.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _watermark_body(counter: int, key: bytes) -> dict[str, Any]:
    body = {"counter": counter}
    return {"counter": counter, "sig": hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()}


def read_watermark(key: bytes) -> int:
    """The high-water mark of every counter ever issued. An unsigned or
    edited watermark is worth nothing, so it reads as 0 and the chain
    falls back to the log and the anchor -- fail closed on trust, never
    fail closed on availability."""
    if not config.RECEIPTS_COUNTER.exists():
        return 0
    try:
        blob = json.loads(config.RECEIPTS_COUNTER.read_text())
    except (OSError, json.JSONDecodeError):
        return 0
    counter = int(blob.get("counter", 0))
    expected = _watermark_body(counter, key)
    if not hmac.compare_digest(str(blob.get("sig", "")), expected["sig"]):
        return 0
    return counter


def _write_watermark(counter: int, key: bytes) -> None:
    """Called only from inside append()'s lock. Never lowers the value on
    disk: monotonic means monotonic, including against a caller that
    passes something stale."""
    current = read_watermark(key)
    if counter <= current:
        return
    config.RECEIPTS_COUNTER.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.RECEIPTS_COUNTER.with_suffix(config.RECEIPTS_COUNTER.suffix + ".tmp")
    tmp.write_text(json.dumps(_watermark_body(counter, key), sort_keys=True))
    os.replace(tmp, config.RECEIPTS_COUNTER)


def next_counter(key: bytes) -> int:
    """The next counter to issue: one past the highest of the three
    sources. Exposed (not private) because test_receipts.py asserts the
    monotonicity property directly against it."""
    highest = read_watermark(key)
    anchor = _read_head_anchor()
    if anchor is not None:
        highest = max(highest, int(anchor.get("counter", 0)))
    if config.SB_RECEIPTS.exists():
        with open(config.SB_RECEIPTS) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    highest = max(highest, int(json.loads(raw_line).get("counter", 0)))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
    return highest + 1


def append(record: dict[str, Any]) -> dict[str, Any]:
    """Append one signed line. `record` carries the caller's fields
    (session_id, kind, by, text, step, status, task, runner, ts, and
    optionally state_hash); counter, prev_hash, hash, sig, backend are
    computed here under the lock."""
    config.SB_RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            key, backend = get_or_create_key()
            prev_hash = GENESIS_HASH
            if config.SB_RECEIPTS.exists():
                with open(config.SB_RECEIPTS) as f:
                    last_line = None
                    for raw_line in f:
                        raw_line = raw_line.strip()
                        if raw_line:
                            last_line = raw_line
                    if last_line:
                        prev_hash = json.loads(last_line).get("hash", prev_hash)
            counter = next_counter(key)
            line = dict(record)
            line["counter"] = counter
            line["prev_hash"] = prev_hash
            line["backend"] = backend
            body = {k: v for k, v in line.items() if k not in UNHASHED_FIELDS}
            line_hash = hashlib.sha256(_canonical(body)).hexdigest()
            line["hash"] = line_hash
            if record.get("signed"):
                line["hw_sig"], line["hw_backend"] = HardwareTrustAnchor().sign(line_hash)
            line["sig"] = hmac.new(key, line_hash.encode(), hashlib.sha256).hexdigest()
            with open(config.SB_RECEIPTS, "a") as out:
                out.write(json.dumps(line, sort_keys=True) + "\n")
            _write_head_anchor(_head_anchor(counter, line_hash, key))
            _write_watermark(counter, key)
            return line
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)


def read_all(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or config.SB_RECEIPTS
    if not p.exists():
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def episodes(kind: str | None = None) -> list[dict[str, Any]]:
    rows = read_all()
    if kind:
        rows = [r for r in rows if r.get("kind") == kind]
    out = []
    for r in rows:
        out.append(
            {
                "session_id": r.get("session_id"),
                "task": r.get("task", ""),
                "reason": r.get("text", r.get("reason", "")),
                "step": r.get("step", 0),
                "kind": r.get("kind"),
                "by": r.get("by"),
                "ts": r.get("ts"),
            }
        )
    return out


def verify(path: Path | None = None) -> dict[str, Any]:
    """A hash chain proves nothing about entries missing from its own tail
    (see the module docstring): every prev_hash link among the rows that
    are still present can be perfectly intact while the last N rows were
    simply deleted. That defect (cp19) is why every return below carries
    "reason", and why a clean walk of `rows` is *not* the end of this
    function -- the walk is checked against the signed head anchor before
    anything is called ok."""
    rows = read_all(path)
    if not rows:
        anchor = _read_head_anchor()
        if anchor is not None:
            return {"ok": False, "count": 0, "first_broken_counter": None, "reason": "truncated"}
        return {"ok": True, "count": 0, "first_broken_counter": None, "reason": None}
    key, _backend = get_or_create_key()
    expected_prev = GENESIS_HASH
    # The chain may legitimately start above 1 after a rotation: the
    # watermark (R23) guarantees counters never repeat, not that the file
    # on disk always begins at 1. Seed from the first row's own counter
    # and require every later row to follow it by exactly one.
    expected_counter = int(rows[0].get("counter", 1)) - 1
    for row in rows:
        expected_counter += 1
        counter = row.get("counter")
        if counter != expected_counter:
            return {"ok": False, "count": len(rows), "first_broken_counter": expected_counter, "reason": "broken"}
        if row.get("prev_hash") != expected_prev:
            return {"ok": False, "count": len(rows), "first_broken_counter": counter, "reason": "broken"}
        body = {k: v for k, v in row.items() if k not in UNHASHED_FIELDS}
        recomputed = hashlib.sha256(_canonical(body)).hexdigest()
        if recomputed != row.get("hash"):
            return {"ok": False, "count": len(rows), "first_broken_counter": counter, "reason": "broken"}
        expected_sig = hmac.new(key, recomputed.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, str(row.get("sig", ""))):
            return {"ok": False, "count": len(rows), "first_broken_counter": counter, "reason": "broken"}
        expected_prev = row["hash"]

    last = rows[-1]
    anchor = _read_head_anchor()
    if anchor is None:
        return {"ok": False, "count": len(rows), "first_broken_counter": None, "reason": "no_anchor"}
    expected_anchor = _head_anchor(int(last.get("counter", 0)), str(last.get("hash", "")), key)
    if not hmac.compare_digest(str(anchor.get("sig", "")), expected_anchor["sig"]):
        # the anchor file itself was edited (or belongs to a different
        # chain/key) -- indistinguishable from tail-truncation to a reader
        # who only has this file, so it fails the same way, not silently.
        return {"ok": False, "count": len(rows), "first_broken_counter": None, "reason": "truncated"}
    if anchor.get("counter") != last.get("counter") or anchor.get("hash") != last.get("hash"):
        return {"ok": False, "count": len(rows), "first_broken_counter": None, "reason": "truncated"}
    return {"ok": True, "count": len(rows), "first_broken_counter": None, "reason": None}
