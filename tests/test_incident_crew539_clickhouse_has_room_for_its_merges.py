"""Incident test, crew#539 (2026-08-28): diagnose run 33140351385 showed ClickHouse looping on
`MEMORY_LIMIT_EXCEEDED: would use 1.39 GiB ... current RSS: 1.80 GiB, maximum: 1.80 GiB` under a
2Gi limit — the server ceiling is 90% of the container limit and one signoz_traces merge needs
1.39 GiB on top of table loading — so :8123 never opened and the startup probe killed it (x301).
Rule: the ClickHouse memory limit stays above the measured 1.80 + 1.39 GiB (>= 4Gi), it keeps
Guaranteed memory (request == limit; crew#584 made the CPU request micro), and it keeps at least one CPU so loading finishes inside the
probe window."""
from pathlib import Path

import yaml

VALUES = Path(__file__).resolve().parents[1] / "platform" / "observability" / "values.yaml"


def _gib(q: str) -> float:
    units = {"Gi": 1.0, "Mi": 1 / 1024, "G": 1e9 / 2**30, "M": 1e6 / 2**30}
    for u, f in units.items():
        if q.endswith(u):
            return float(q[: -len(u)]) * f
    return float(q) / 2**30


def _cpu(q: str) -> float:
    return float(q[:-1]) / 1000 if q.endswith("m") else float(q)


def test_clickhouse_memory_covers_the_measured_ceiling_plus_one_merge():
    r = yaml.safe_load(VALUES.read_text())["clickhouse"]["resources"]
    assert _gib(r["limits"]["memory"]) >= 4, "1.80 GiB ceiling + 1.39 GiB merge, measured in run 33140351385"
    assert r["requests"]["memory"] == r["limits"]["memory"], "Guaranteed QoS (crew#539 CP9)"
    assert _cpu(r["requests"]["cpu"]) <= _cpu(r["limits"]["cpu"]), "crew#584: the CPU request is micro, the limit is the ceiling"
    assert _cpu(r["limits"]["cpu"]) >= 1, "table loading at 500m did not finish inside the startup probe window"
