"""Falsifier for bin/estate-friction-measure, the friction producer for the live-state spine.

A measure that prints 0 for something it could not measure would show the founder a green board
over a broken fleet. Every BLIND case below is a known-bad input that must print no number and exit
2; every OK case is a known-good that must print the exact figure. The fixtures are synthetic
transcripts, so no recorded session text is read or committed.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "estate-friction-measure"

_loader = importlib.machinery.SourceFileLoader("estate_friction_measure", str(SCRIPT))
_spec = importlib.util.spec_from_loader("estate_friction_measure", _loader)
m = importlib.util.module_from_spec(_spec)
_loader.exec_module(m)

NOW_ISO = "2026-11-28T12:00:00Z"
NOW = dt.datetime.fromisoformat(NOW_ISO.replace("Z", "+00:00")).timestamp()
LINE = re.compile(r"^optimus\.friction\.[a-z0-9_]+=-?\d+(?:\.\d+)?\n$")


def iso(offset_s: float) -> str:
    return dt.datetime.fromtimestamp(NOW - offset_s, dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )


def session(path: pathlib.Path, calls, sid="s", dup_ids=()):
    """calls: list of (age_seconds, failed, text). One tool_use then its tool_result per call."""
    rows = []
    for i, (age, failed, text) in enumerate(calls):
        uid = f"{sid}-{i}"
        rows.append(
            {
                "type": "assistant",
                "timestamp": iso(age + 1),
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": uid,
                            "name": "Bash",
                            "input": {"command": "x"},
                        }
                    ]
                },
            }
        )
        rows.append(
            {
                "type": "user",
                "timestamp": iso(age),
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": uid,
                            "is_error": failed,
                            "content": text,
                        }
                    ]
                },
            }
        )
    body = "".join(json.dumps(r) + "\n" for r in rows)
    for r in rows:  # a resumed session copies earlier lines verbatim
        if r["type"] == "user" and r["message"]["content"][0]["tool_use_id"] in dup_ids:
            body += json.dumps(r) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    os.utime(path, (NOW, NOW))
    return path


def run(args):
    r = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args, "--now", NOW_ISO],
        capture_output=True,
        text=True,
    )
    if r.stdout == "" and r.stderr:
        print(
            "measure stderr:", r.stderr.strip()
        )  # pytest shows this on failure, so a BLIND is explained
    return r


def test_known_bad_75pct_failures_reads_exactly_75_and_pages(tmp_path):
    # 40 results in the last 30 minutes, 30 of them failed, spread across the 5m and 1h windows
    calls = [(60 + i * 40, i % 4 != 0, "x") for i in range(40)]
    session(tmp_path / "p" / "a.jsonl", calls)
    r = run(["--root", str(tmp_path), "--metric", "call_failure_rate_1h"])
    assert (
        r.returncode == 0 and r.stdout == "optimus.friction.call_failure_rate_1h=75\n"
    )
    p = run(["--root", str(tmp_path), "--metric", "page_state"])
    assert p.returncode == 0 and p.stdout == "optimus.friction.page_state=2\n"


def test_known_good_5pct_failures_reads_5_and_stays_ok(tmp_path):
    calls = [(60 + i * 20, i == 0, "x") for i in range(20)]
    session(tmp_path / "p" / "a.jsonl", calls)
    assert (
        run(["--root", str(tmp_path), "--metric", "call_failure_rate_1h"]).stdout
        == "optimus.friction.call_failure_rate_1h=5\n"
    )
    assert (
        run(["--root", str(tmp_path), "--metric", "page_state"]).stdout
        == "optimus.friction.page_state=0\n"
    )


def test_too_few_results_is_blind_not_zero(tmp_path):
    session(tmp_path / "p" / "a.jsonl", [(60 + i, True, "x") for i in range(5)])
    r = run(["--root", str(tmp_path), "--metric", "call_failure_rate_1h"])
    assert r.returncode == 2 and r.stdout == "" and r.stderr.startswith("BLIND:")
    r = run(["--root", str(tmp_path), "--metric", "page_state"])
    assert r.returncode == 2 and r.stdout == ""


def test_unreadable_root_is_blind_not_zero(tmp_path):
    r = run(["--root", str(tmp_path / "missing"), "--metric", "call_failure_rate_6h"])
    assert r.returncode == 2 and r.stdout == "" and "not readable" in r.stderr


def test_old_spike_that_has_ended_does_not_page(tmp_path):
    # 40 failures 40 minutes ago, then 8 clean results in the last 4 minutes
    calls = [(2400 + i, True, "x") for i in range(40)] + [
        (30 + i * 20, False, "ok") for i in range(8)
    ]
    session(tmp_path / "p" / "a.jsonl", calls)
    assert (
        run(["--root", str(tmp_path), "--metric", "page_state"]).stdout
        == "optimus.friction.page_state=0\n"
    )


def test_slow_burn_files_a_ticket_not_a_page(tmp_path):
    # about 30% failed across both the 6h and the last 30 minutes
    calls = [(60 + i * 30, i % 10 < 3, "x") for i in range(50)]
    session(tmp_path / "p" / "a.jsonl", calls)
    assert (
        run(["--root", str(tmp_path), "--metric", "page_state"]).stdout
        == "optimus.friction.page_state=1\n"
    )


def test_resumed_session_duplicates_are_counted_once(tmp_path):
    calls = [(60 + i * 20, i % 2 == 0, "x") for i in range(20)]  # 50%
    session(
        tmp_path / "p" / "a.jsonl", calls, dup_ids={f"s-{i}" for i in range(0, 20, 2)}
    )
    assert (
        run(["--root", str(tmp_path), "--metric", "call_failure_rate_1h"]).stdout
        == "optimus.friction.call_failure_rate_1h=50\n"
    )


def test_torn_last_line_costs_that_line_not_the_file(tmp_path):
    p = session(
        tmp_path / "p" / "a.jsonl", [(60 + i * 20, i < 2, "x") for i in range(20)]
    )
    with open(p, "a") as fh:
        fh.write(
            '{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id"'
        )
    os.utime(
        p, (NOW, NOW)
    )  # appending moved the mtime to the real clock, outside the fixture's window
    assert (
        run(["--root", str(tmp_path), "--metric", "call_failure_rate_1h"]).stdout
        == "optimus.friction.call_failure_rate_1h=10\n"
    )


def test_a_multi_chunk_file_with_an_old_head_reads_only_the_recent_tail(tmp_path):
    # about 3 MB of day-old failures, then 25 recent calls of which 5 failed: the 1h answer is 20
    old = [(72000 + i, True, "x" * 400) for i in range(5000)]
    recent = [(60 + i * 20, i < 5, "x") for i in range(25)]
    p = session(tmp_path / "p" / "a.jsonl", old + recent)
    assert p.stat().st_size > 2 * m.CHUNK
    assert (
        run(["--root", str(tmp_path), "--metric", "call_failure_rate_1h"]).stdout
        == "optimus.friction.call_failure_rate_1h=20\n"
    )


def test_first_call_refusal_rate_counts_only_first_calls(tmp_path):
    refuse = "PreToolUse:Bash hook error: No plan declared, so Bash is refused."
    for i in range(12):
        first_refused = i < 6
        calls = [
            (3000 + i, first_refused, refuse if first_refused else "ok"),
            (2000 + i, True, "File does not exist"),
        ]
        session(tmp_path / "p" / f"s{i}.jsonl", calls, sid=f"s{i}")
    r = run(["--root", str(tmp_path), "--metric", "first_call_refused_rate_24h"])
    assert (
        r.returncode == 0
        and r.stdout == "optimus.friction.first_call_refused_rate_24h=50\n"
    )


def test_first_call_refusal_blind_under_ten_sessions(tmp_path):
    for i in range(3):
        session(
            tmp_path / "p" / f"s{i}.jsonl", [(3000, True, "hook error")], sid=f"s{i}"
        )
    r = run(["--root", str(tmp_path), "--metric", "first_call_refused_rate_24h"])
    assert r.returncode == 2 and r.stdout == ""


def test_stdout_is_exactly_one_optimus_line(tmp_path):
    session(tmp_path / "p" / "a.jsonl", [(60 + i * 20, False, "x") for i in range(25)])
    for metric in ("call_failure_rate_1h", "call_failure_rate_6h", "page_state"):
        assert LINE.match(run(["--root", str(tmp_path), "--metric", metric]).stdout)


def test_selftest_reads_six_and_a_broken_rule_reads_less():
    r = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--selftest"],
        capture_output=True,
        text=True,
    )
    assert (
        r.returncode == 0
        and r.stdout == "optimus.friction.producer_falsifiers_passing=6\n"
    )
    broken = m.PAGE_PCT
    try:
        m.PAGE_PCT = (
            101.0  # a page rule that can never fire must lose the cases that need it
        )
        assert subprocess_free_selftest() < 6
    finally:
        m.PAGE_PCT = broken


def subprocess_free_selftest():
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.selftest()
    return int(buf.getvalue().strip().rsplit("=", 1)[1])


def test_catalogue_registers_every_metric_with_the_exact_argv():
    cat = json.loads((ROOT / "catalog" / "optimus-metrics.json").read_text())
    by_name = {x["name"]: x for x in cat["metrics"]}
    for metric in m.METRICS:
        entry = by_name[f"friction.{metric}"]
        assert entry["measure"] == [
            "python3",
            "bin/estate-friction-measure",
            "--metric",
            metric,
        ]
        assert entry["better"] == "lower" and entry["owner"] and entry["description"]
    own = by_name["friction.producer_falsifiers_passing"]
    assert (
        own["measure"] == ["python3", "bin/estate-friction-measure", "--selftest"]
        and own["better"] == "higher"
    )
