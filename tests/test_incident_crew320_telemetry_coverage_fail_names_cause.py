"""Incident test, crew#320 / oke-check 33027001825.

The telemetry-coverage row printed `pods=45 seen=0 missing=45` and nothing else, so nobody
could tell a misnamed ClickHouse table from an estate that emits no telemetry. The receipt
body already carried both answers. Rule: a FAIL names the backend errors and the pods never
seen; an ok receipt still passes untouched (LAW 28, LAW 38).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

READER = Path(__file__).resolve().parents[1] / "bin" / "idp-telemetry-coverage"


def _embedded_python() -> str:
    src = READER.read_text()
    return src.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]


def _run(body: str) -> tuple[int, str]:
    lm = dt.datetime.now(dt.UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    head = json.dumps({"last-modified": lm, "date": lm})
    proc = subprocess.run(
        [sys.executable, "-", head, body, "30", ""],
        input=_embedded_python(), capture_output=True, text=True, check=False,
        env={**os.environ, "IDP_LIB": str(READER.parent / "lib")},
    )
    return proc.returncode, proc.stdout


def test_fail_receipt_names_backend_error_and_missing_pods() -> None:
    body = "FAIL telemetry-coverage at X pods=45 seen=0 missing=45\n" + json.dumps({
        "backend_errors": {"logs": "Code: 60. Table signoz_logs.distributed_logs_v2 does not exist"},
        "missing": [{"ns": "observability", "pod": "signoz-otel-collector-0"}],
    })
    rc, out = _run(body)
    assert rc == 1
    assert "backend logs: Code: 60" in out
    assert "never seen: observability/signoz-otel-collector-0" in out


def test_ok_receipt_still_passes_with_no_cause_lines() -> None:
    rc, out = _run("ok telemetry-coverage at X pods=45 seen=45 missing=0 hubble_radio_flows=12\n{}")
    assert rc == 0
    assert out.startswith("ok      telemetry-coverage")
    assert "backend " not in out and "never seen" not in out


def test_receipt_without_the_hubble_row_is_a_miss_and_zero_names_it() -> None:
    # crew#539 CP12: a receipt from a collector that predates the Hubble count is never clean
    # (the crew#406 rule), and a count of 0 says what Hubble did not see.
    rc, out = _run("ok telemetry-coverage at X pods=45 seen=45 missing=0\n{}")
    assert rc == 1 and "hubble_radio_flows=absent" in out, out
    rc, out = _run('ok telemetry-coverage at X pods=45 seen=45 missing=0 hubble_radio_flows=0\n{"hubble_radio_flows": 0}')
    assert rc == 1 and "hubble_radio_flows=0" in out and "named a radio-room workload" in out, out
