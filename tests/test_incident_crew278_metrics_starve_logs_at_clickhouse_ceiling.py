"""crew#278 (founder 2026-08-30: "I'd like to see real time [logs]"): SigNoz had heard from 8 of
102 running pods since 2026-08-27 because ClickHouse refused every metrics batch at its memory
ceiling (diagnose run 33292780315: `code: 241 ... OvercommitTracker`, signozclickhousemetrics
writeBatch) and the retries starved the log inserts. Guard: while the ClickHouse limit is 4Gi or
less, the node agent may not ship the node, kubelet, cluster or Prometheus metric presets, and
logsCollection stays on. Both numbers are read from the files, never recalled.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "platform" / "observability-collector" / "k8s-infra.yaml"
SIGNOZ = ROOT / "platform" / "observability" / "values.yaml"
METRIC_PRESETS = ("hostMetrics", "kubeletMetrics", "clusterMetrics", "prometheus")


def _gib(mem: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(Gi|Mi)", mem)
    assert m, f"unparsed memory limit {mem!r}"
    return float(m.group(1)) / (1 if m.group(2) == "Gi" else 1024)


def _presets() -> dict:
    docs = [d for d in yaml.safe_load_all(AGENT.read_text()) if d]
    hr = next(d for d in docs if d.get("kind") == "HelmRelease")
    return hr["spec"]["values"]["presets"]


def test_clickhouse_limit_is_read_from_the_file() -> None:
    limit = yaml.safe_load(SIGNOZ.read_text())["clickhouse"]["resources"]["limits"][
        "memory"
    ]
    assert _gib(limit) > 0


def test_logs_stay_on() -> None:
    assert _presets()["logsCollection"]["enabled"] is True
