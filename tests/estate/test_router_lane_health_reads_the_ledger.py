"""router-lane-health: the ledger read that used to need a raw shell (and a founder prompt)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "platform/estate/libexec/router-lane-health.py"


def _ledger(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
    return p


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_groups_outcomes_per_lane_with_refused_share_and_top_error(tmp_path):
    import time

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    old = "2020-01-01T00:00:00Z"
    rows = [
        {"kind": "outcome", "model": "voice", "at": now, "ok": True, "latency_ms": 340},
        {"kind": "outcome", "model": "voice", "at": now, "ok": True, "latency_ms": 500},
        {
            "kind": "outcome",
            "model": "voice",
            "at": now,
            "ok": False,
            "error": "RateLimitError: 429 Too Many Requests",
        },
        {
            "kind": "outcome",
            "model": "voice",
            "at": now,
            "ok": False,
            "error": "429 rate limit reached",
        },
        {
            "kind": "outcome",
            "model": "narrate",
            "at": now,
            "ok": True,
            "latency_ms": 120,
        },
        {
            "kind": "outcome",
            "model": "voice",
            "at": old,
            "ok": False,
            "error": "ancient",
        },
        {"kind": "pre", "model": "voice", "at": now},
    ]
    r = _run("--ledger", str(_ledger(tmp_path, rows)), "--json")
    assert r.returncode == 0, r.stderr
    lanes = json.loads(r.stdout)["lanes"]
    assert lanes["voice"]["calls"] == 4  # the old row and the pre row are not counted
    assert lanes["voice"]["refused_pct"] == 50.0
    assert lanes["voice"]["p50_ms"] == 420
    assert lanes["voice"]["top_error"] == "429 rate-limit"
    assert lanes["narrate"] == {
        "calls": 1,
        "ok": 1,
        "refused": 0,
        "refused_pct": 0.0,
        "p50_ms": 120,
        "p95_ms": 120,
        "top_error": "",
        "last_error": "",
    }


def test_lane_filter_and_text_table(tmp_path):
    import time

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = [
        {"kind": "outcome", "model": m, "at": now, "ok": True, "latency_ms": 10}
        for m in ("voice", "fast")
    ]
    r = _run("--ledger", str(_ledger(tmp_path, rows)), "--lane", "voice")
    assert r.returncode == 0
    assert "voice" in r.stdout and "fast" not in r.stdout
    assert r.stdout.startswith("lane")


def test_missing_ledger_is_exit_2(tmp_path):
    r = _run("--ledger", str(tmp_path / "nope.jsonl"))
    assert r.returncode == 2
    assert "ledger missing" in r.stderr
