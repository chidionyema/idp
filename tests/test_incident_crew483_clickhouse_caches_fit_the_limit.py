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


def _clickhouse():
    return yaml.safe_load(VALUES.read_text())["clickhouse"]


def test_clickhouse_caches_and_merges_leave_inserts_more_than_half_the_ceiling() -> None:
    ch = _clickhouse()
    limit = _bytes(ch["resources"]["limits"]["memory"])
    ceiling = limit * 0.9  # max_server_memory_usage_to_ram_ratio default
    settings = ch.get("settings") or {}
    assert "mark_cache_size" in settings, "mark_cache_size unset: ClickHouse's default is 5 GiB"
    marks = int(settings["mark_cache_size"]) + int(settings.get("index_mark_cache_size", 0))
    merges = float(settings.get("merges_mutations_memory_usage_to_ram_ratio", 0.5)) * ceiling
    reserved = marks + merges
    assert reserved < ceiling / 2, (
        f"caches {marks/2**20:.0f} MiB + merges {merges/2**20:.0f} MiB reserve {reserved/ceiling:.0%} of the "
        f"{ceiling/2**30:.2f} GiB ceiling; inserts get the rest and were refused with code 241"
    )


def test_clickhouse_requests_equal_limits_still() -> None:
    # crew#539 CP9: Guaranteed QoS; the cache bound is not a licence to loosen it.
    r = _clickhouse()["resources"]
    assert r["requests"] == r["limits"]
