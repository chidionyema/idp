"""POST the conscience receipt to the estate collector as one OTLP log record (crew#586, LAW 50).

The record carries `science.source=conscience` so platform/science/science-facts.yaml counts it
from ClickHouse the way it counts the Mac's science tick: coverage is proved by querying the
backend, never by scanning files. The body is the receipt itself. Endpoint and credential come
from the environment (LAW 46): OTEL_EXPORTER_OTLP_ENDPOINT is `https://signoz.<zone>`, and
OTLP_INGEST_USER / OTLP_INGEST_PASSWORD are the edge's basic-auth pair, read from the vault by
name and never printed.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request


def payload(receipt: dict) -> dict:
    when = receipt["measured_at"]
    return {"resourceLogs": [{
        "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "conscience"}}]},
        "scopeLogs": [{"scope": {"name": "bin/idp-conscience"}, "logRecords": [{
            "timeUnixNano": str(int(__import__("datetime").datetime.fromisoformat(when).timestamp() * 1_000_000_000)),
            "severityText": "INFO" if receipt["score"]["green"] == receipt["score"]["total"] else "WARN",
            "body": {"stringValue": json.dumps(receipt, separators=(",", ":"))},
            "attributes": [
                {"key": "science.source", "value": {"stringValue": "conscience"}},
                {"key": "conscience.green", "value": {"intValue": str(receipt["score"]["green"])}},
                {"key": "conscience.total", "value": {"intValue": str(receipt["score"]["total"])}},
                {"key": "conscience.red", "value": {"stringValue": ",".join(t["name"] for t in receipt["tenets"] if not t["ok"])}},
            ]}]}]}]}


def emit(report: pathlib.Path) -> int:
    base = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    user, pw = os.environ.get("OTLP_INGEST_USER", ""), os.environ.get("OTLP_INGEST_PASSWORD", "")
    if not (base and user and pw):
        print("BLIND conscience emit: OTEL_EXPORTER_OTLP_ENDPOINT, OTLP_INGEST_USER or OTLP_INGEST_PASSWORD unset")
        return 2
    receipt = json.loads(report.read_text())
    req = urllib.request.Request(f"{base}/v1/logs", data=json.dumps(payload(receipt)).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except (urllib.error.URLError, OSError) as e:
        print(f"FAIL conscience emit: {base}/v1/logs -> {e}")
        return 1
    print(f"{'ok  ' if code // 100 == 2 else 'FAIL'} conscience emit: {base}/v1/logs -> HTTP {code}, score {receipt['score']['green']}/{receipt['score']['total']} as science.source=conscience")
    return 0 if code // 100 == 2 else 1


if __name__ == "__main__":
    sys.exit(emit(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "reports/conscience.json")))
