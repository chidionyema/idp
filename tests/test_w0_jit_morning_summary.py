"""Prove the W0.10/WJ.11 morning-summary (LAW 3).

bin/idp-jit-morning-summary reads the JIT broker's append-only ledger and renders the WJ.11 digest:
what was asked, what was granted while he slept, what expired unused, what was denied (plus forged /
failed anomalies). It must only count over a VERIFIED hash chain -- a tampered ledger is a refusal,
not a quiet mis-count -- and be BLIND (never a silent pass) when it cannot read the ledger.

These tests build valid hash-chained ledger fixtures (replicating the broker's prev->this sha256
link, exactly as broker.py:Ledger.append does) and drive the summary over them.
"""

import hashlib
import json
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-jit-morning-summary")


def chain(events):
    """Build a valid ledger chain: list of (event, ts) -> list of ledger line dicts."""
    out = []
    prev = "0" * 64
    now = time.time() - 100
    for i, (event, rel_min) in enumerate(events):
        body = {
            "at": now + rel_min * 60,
            "event": event,
            "prev": prev,
            "request": f"r{i}",
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        body["this"] = hashlib.sha256((prev + payload).encode()).hexdigest()
        prev = body["this"]
        out.append(body)
    return out


def write_ledger(records):
    import tempfile

    fh = tempfile.NamedTemporaryFile("w", suffix=".ledger", delete=False)
    for r in records:
        fh.write(json.dumps(r, sort_keys=True) + "\n")
    fh.close()
    return fh.name


def run(ledger, since=""):
    argv = ["python3", BIN, ledger]
    if since:
        argv += ["--since", since]
    return subprocess.run(argv, capture_output=True, text=True)


def test_binary_present():
    assert os.path.exists(BIN)


def _counts(stdout):
    """Parse digest 'label N description' lines into {label: int}. Finds the first integer token
    after a bare word label; never alignment-sensitive."""
    out = {}
    for line in stdout.splitlines():
        toks = line.split()
        if not toks:
            continue
        if toks[0] in ("asked", "approved", "expired", "denied"):
            nums = [t for t in toks if t.lstrip("-").isdigit()]
            if nums:
                out[toks[0]] = int(nums[0])
    return out


def test_summary_counts_the_five_buckets_from_a_verified_chain():
    # 1 asked, 2 granted, 1 expired, 1 denied over one window
    recs = chain(
        [
            ("asked", -5),
            ("granted", -4),
            ("granted", -3),
            ("expired", -2),
            ("denied", -1),
        ]
    )
    p = write_ledger(recs)
    try:
        r = run(p)
        assert r.returncode == 0, r.stdout + r.stderr
        c = _counts(r.stdout)
        assert c["asked"] == 1 and c["approved"] == 2
        assert c["expired"] == 1 and c["denied"] == 1
    finally:
        os.unlink(p)


def test_expired_grant_is_counted_distinct_from_denied():
    recs = chain([("asked", -3), ("expired", -2), ("denied", -1)])
    p = write_ledger(recs)
    try:
        r = run(p)
        assert r.returncode == 0, r.stdout + r.stderr
        c = _counts(r.stdout)
        assert c["expired"] == 1 and c["denied"] == 1
    finally:
        os.unlink(p)


def test_tampered_ledger_is_a_refusal_not_a_miscount():
    recs = chain([("asked", -2), ("granted", -1)])
    # tamper: change one field on the last line, breaking the chain
    recs[-1]["request"] = "tampered"
    p = write_ledger(recs)
    try:
        r = run(p)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "FAIL" in r.stdout
    finally:
        os.unlink(p)
