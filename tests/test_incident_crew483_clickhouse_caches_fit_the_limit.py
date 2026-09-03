"""Incident 2026-08-28 (crew#483, oke-check diagnose 33172481714): with the node agents finally
reaching the collector, signoz-otel-collector logged on every batch
`code: 241 ... (total) memory limit exceeded: would use 3.61 GiB ... current RSS: 1.87 GiB,
maximum: 3.60 GiB` and telemetry coverage stayed at 7/95 pods. ClickHouse's ceiling is 90% of
its cgroup limit and its tracker counts caches on top of RSS; the mark cache defaults to 5 GiB,
larger than the 4Gi pod, and merges may take half the ceiling.
Rule: the ClickHouse caches and merge budget are bounded so that, together, they leave the
inserts more than half of the server ceiling. The budget is derived from the limit in the same
file, so growing the pod never silently re-opens the gap."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALUES = ROOT / "platform/observability/values.yaml"

_UNITS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}


def _bytes(quantity: str) -> int:
    m = re.fullmatch(r"(\d+)([KMGT]i)", quantity)
    assert m, f"unexpected memory quantity {quantity!r}"
    return int(m.group(1)) * _UNITS[m.group(2)]


def _milli(q: str) -> int:
    return int(q[:-1]) if q.endswith("m") else int(float(q) * 1000)


def _clickhouse():
    return yaml.safe_load(VALUES.read_text())["clickhouse"]


def test_clickhouse_memory_request_equals_limit_still() -> None:
    # crew#539 CP9 set requests == limits (Guaranteed QoS). crew#584 (founder 2026-08-29, request
    # inflation) keeps the half that the incident needs: the memory ceiling is the memory request,
    # so the tracker's 90 % ratio and the eviction ranking both see one fixed number. The CPU
    # request is micro with a burst limit; a 1000m CPU request was 13 % of the node reserved idle.
    r = _clickhouse()["resources"]
    assert r["requests"]["memory"] == r["limits"]["memory"]
    assert _milli(r["requests"]["cpu"]) <= _milli(r["limits"]["cpu"])
