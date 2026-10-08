"""bin/idp-read-shunt: a big whole-file Read becomes a digest, and nothing else ever changes.

The guard sits in front of every Read in every session, so the cases that matter are the
ones where it must stay out of the way: a small file, a ranged read, a binary the harness
renders itself, a worker that is down or answers with something that is not the digest.
Each of those has to let the Read through, and only a well-formed digest may replace it.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_loader = importlib.machinery.SourceFileLoader(
    "idp_read_shunt", os.path.join(ROOT, "bin", "idp-read-shunt")
)
shunt = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("idp_read_shunt", _loader)
)
_loader.exec_module(shunt)

DIGEST = "PURPOSE: x\nSTRUCTURE:\nL1-L400 body: lines\nREAD EXACTLY: L1-L5"


def _event(path, **extra):
    return {
        "tool_name": "Read",
        "session_id": "t",
        "tool_input": {"file_path": str(path), **extra},
    }


def _big(tmp_path, n=400):
    f = tmp_path / "big.py"
    f.write_text("".join(f"x = {i}\n" for i in range(n)))
    return f


def _isolate(monkeypatch, tmp_path, answer):
    monkeypatch.setattr(shunt, "STATE", str(tmp_path / "state"))
    monkeypatch.setattr(shunt, "LEDGER", str(tmp_path / "state" / "ledger.jsonl"))
    monkeypatch.setattr(shunt, "CACHE", str(tmp_path / "state" / "cache"))
    calls = []

    def fake(path, text, lines):
        calls.append(path)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(shunt, "_digest", fake)
    return calls


def test_a_big_whole_file_read_becomes_the_digest_and_is_cached(monkeypatch, tmp_path):
    calls = _isolate(monkeypatch, tmp_path, DIGEST)
    f = _big(tmp_path)
    out = shunt.decide(_event(f))
    hook = out["hookSpecificOutput"]
    assert hook["permissionDecision"] == "deny"
    assert DIGEST in hook["permissionDecisionReason"]
    assert shunt.decide(_event(f)) is not None
    assert len(calls) == 1  # the second read of an unchanged file is a cache hit
    rows = [json.loads(x) for x in open(shunt.LEDGER)]
    assert [r["outcome"] for r in rows] == ["shunted", "shunted"]


def test_small_ranged_and_binary_reads_pass_through(monkeypatch, tmp_path):
    calls = _isolate(monkeypatch, tmp_path, DIGEST)
    small = tmp_path / "small.py"
    small.write_text("x = 1\n")
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("".join("x\n" for _ in range(400)))
    big = _big(tmp_path)
    assert shunt.decide(_event(small)) is None
    assert shunt.decide(_event(big, offset=1, limit=50)) is None
    assert shunt.decide(_event(pdf)) is None
    assert shunt.decide(_event(tmp_path / "missing.py")) is None
    assert shunt.decide({"tool_name": "Bash", "tool_input": {}}) is None
    assert calls == []


def test_a_down_or_rambling_worker_lets_the_read_through(monkeypatch, tmp_path):
    big = _big(tmp_path)
    _isolate(monkeypatch, tmp_path, TimeoutError("timed out"))
    assert shunt.decide(_event(big)) is None
    _isolate(monkeypatch, tmp_path, "We need to produce a digest. Let's look at")
    assert shunt.decide(_event(big)) is None
    _isolate(monkeypatch, tmp_path, "")
    assert shunt.decide(_event(big)) is None


def test_the_opt_out_switch(monkeypatch, tmp_path):
    calls = _isolate(monkeypatch, tmp_path, DIGEST)
    monkeypatch.setenv("ESTATE_READ_SHUNT", "0")
    assert shunt.decide(_event(_big(tmp_path))) is None
    assert calls == []
