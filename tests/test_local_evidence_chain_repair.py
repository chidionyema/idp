"""idp#5953 defect 11: a git merge stapled two evidence chains into one.

`.aevum/local.jsonl` is appended to on every branch and text-merged by git, so merging
two branches that each appended turns one chain into two: measured on main
2026-10-16, record 373 carries seq=125 and the 14-record tail of a second chain. The
grader honours that the file is broken -- fail-closed, correctly -- and so `bin/idp-ci`'s
local-evidence rung reddens on the developer's laptop on a tree where no payload is
actually wrong. Two things are pinned here:

  * the grader refuses a stapled chain, and `bin/idp-evidence-write --repair` re-links
    `seq`/`prior_hash` until it verifies, touching no payload byte;
  * a chain whose PAYLOAD was altered cannot be laundered by the repair: the grader
    still refuses it afterwards, and the file is left exactly as it was;
  * the writer heals before it appends, so the recoil never recurs.

The grader (bin/idp-local-evidence-gate) is the only authority invoked on validity; the
fixture builder below is the contract restated, and its own test fails loudly if the two
ever disagree.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-local-evidence-gate"
WRITER = ROOT / "bin" / "idp-evidence-write"
GENESIS = "0" * 64


def _record(seq, prior, tree="a" * 40):
    payload = {
        "tree": tree,
        "author": "agent@estate",
        "staged": [f"f{seq}"],
        "event": "commit.staged",
    }
    rec = {
        "seq": seq,
        "ts": "2026-10-16T00:00:00Z",
        "event": "commit.staged",
        "tree": payload["tree"],
        "author": payload["author"],
        "staged": payload["staged"],
        "payload_hash": hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest(),
        "prior_hash": prior,
    }
    line = json.dumps(rec, separators=(",", ":"))
    return line, hashlib.sha256(line.encode()).hexdigest()


def _chain(n, start_seq=0):
    """A valid chain of n records, returning its lines."""
    lines, prior = [], GENESIS
    for i in range(n):
        line, prior = _record(start_seq + i, prior)
        lines.append(line)
    return lines, prior


def _stapled(tmp_path):
    """A merge of two chains: a tail whose counter restarts, exactly as measured on main."""
    a, _ = _chain(5)
    b, _ = _chain(3, start_seq=2)
    p = tmp_path / "local.jsonl"
    p.write_text("".join(l + "\n" for l in a + b))
    return p


def _run(*args, env=None):
    return subprocess.run(
        [sys.executable, *args], capture_output=True, text=True, timeout=120, env=env
    )


def _grade(p):
    r = _run(str(GATE), str(p))
    return r.returncode, (r.stdout + r.stderr).strip()


def _payload_hashes(p):
    return [
        json.loads(l)["payload_hash"] for l in p.read_text().splitlines() if l.strip()
    ]


def test_the_fixture_builder_speaks_the_grader_s_contract(tmp_path):
    """If the builder and the grader ever disagree, that must fail here, not silently."""
    lines, _ = _chain(3)
    p = tmp_path / "local.jsonl"
    p.write_text("".join(l + "\n" for l in lines))
    rc, why = _grade(p)
    assert rc == 0, (
        "the grader defines the contract and the fixture no longer meets it: " + why
    )


def test_the_grader_refuses_a_stapled_chain(tmp_path):
    p = _stapled(tmp_path)
    rc, why = _grade(p)
    assert rc == 1, "a chain with a restarted counter must not verify"
    assert "seq=" in why, (
        "the refusal must name the record and the counter it found: " + why
    )


def test_repair_relinks_the_chain_and_the_grader_accepts_it(tmp_path):
    p = _stapled(tmp_path)
    before = _payload_hashes(p)
    r = _run(str(WRITER), "--repair", str(p))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "renumbered" in r.stdout, (
        "the repair must say what it re-linked: " + r.stdout
    )
    rc, why = _grade(p)
    assert rc == 0, "the repaired chain must verify: " + why
    assert _payload_hashes(p) == before, "not one payload byte may change in a re-link"
    assert len(before) == 8, "a re-link loses no record"


def test_the_repair_refuses_to_launder_a_tampered_payload(tmp_path):
    lines, _ = _chain(4)
    rec = json.loads(lines[1])
    rec["tree"] = (
        "deadbeef" * 5
    )  # a field in that record's payload; payload_hash now stale
    lines[1] = json.dumps(rec, separators=(",", ":"))
    p = tmp_path / "local.jsonl"
    p.write_text("".join(l + "\n" for l in lines))
    rc, why = _grade(p)
    assert rc == 1 and "payload_hash" in why, why

    before = p.read_bytes()
    r = _run(str(WRITER), "--repair", str(p))
    assert r.returncode == 1, (
        "a tampered payload must not be repaired into a passing chain: " + r.stdout
    )
    assert p.read_bytes() == before, "the file must be left exactly as it was"
    assert _grade(p)[0] == 1, "the grader must keep refusing it"


def test_the_writer_heals_before_it_appends(tmp_path):
    """The recoil never recurs: appending to a stapled chain re-links it first."""
    p = _stapled(tmp_path)
    env = {**os.environ, "IDP_EVIDENCE_FILE": str(p)}
    r = _run(str(WRITER), "--event", "commit.staged", env=env)
    assert r.returncode == 0, "the writer fails open (LAW 38): " + r.stdout + r.stderr
    rc, why = _grade(p)
    assert rc == 0, "after an append the chain must verify, healed first: " + why
    assert len(_payload_hashes(p)) == 9, (
        "the repair must not lose a record, and the append must land"
    )
    assert "chain" in r.stderr or "re-linked" in r.stdout, (
        "healing must say so: " + r.stdout + r.stderr
    )
