"""Incident 2026-08-26 (crew#325): langfuse.mumchimp.com answered 503 for four hours. Two causes,
found only after the SigNoz release was reinstalled and langfuse-web could reach ClickHouse:

* "Database langfuse does not exist": the langfuse chart creates its ClickHouse database only
  when it deploys its own ClickHouse. On the shared SigNoz ClickHouse nothing declared the
  database, so the very first migration failed and the pod crash-looped.
* "FATAL ERROR: Ineffective mark-compacts near heap limit": Node capped the V8 heap at ~500 MB
  under a 1Gi pod limit, and the ClickHouse migration needed more. A pod limit alone is not a
  heap limit.

Rules, not code: the database the chart is told to use is the one a declared Job creates, with
the password mounted the way Kyverno allows; and the web heap is set explicitly, below the pod
limit. Rung 4 (incident test), graded on the rendered Kustomization output.
"""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _rendered() -> list[dict]:
    out = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / "platform/observability")],
        check=True, capture_output=True, text=True,
    ).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def _values() -> dict:
    return yaml.safe_load((ROOT / "platform/observability/langfuse-values.yaml").read_text())


def _mib(q: str) -> int:
    n, unit = re.fullmatch(r"(\d+)(Mi|Gi)", q).groups()
    return int(n) * (1024 if unit == "Gi" else 1)


def test_incident_crew325_langfuse_database_has_a_declared_owner() -> None:
    docs = _rendered()
    values = _values()
    assert values["clickhouse"]["deploy"] is False, "external ClickHouse: the chart will not create the DB"
    job = next(d for d in docs if d["kind"] == "Job" and d["metadata"]["name"] == "langfuse-clickhouse-database")
    assert job["metadata"]["namespace"] == "observability"
    container = job["spec"]["template"]["spec"]["containers"][0]
    command = " ".join(container["command"])
    assert f"CREATE DATABASE IF NOT EXISTS {values['clickhouse']['database']}" in command
    assert f"--host {values['clickhouse']['host']}" in command
    # Kyverno secrets-not-from-env-vars refused the env form on 2026-08-26; the secret is a file.
    assert not container.get("env")
    secret_volumes = [v["secret"]["secretName"] for v in job["spec"]["template"]["spec"]["volumes"] if "secret" in v]
    assert secret_volumes == [values["clickhouse"]["auth"]["existingSecret"]]


def test_incident_crew325_langfuse_web_heap_is_explicit_and_below_the_pod_limit() -> None:
    web = _values()["langfuse"]["web"]
    node_options = next(e["value"] for e in web["additionalEnv"] if e["name"] == "NODE_OPTIONS")
    heap_mib = int(re.search(r"--max-old-space-size=(\d+)", node_options).group(1))
    limit_mib = _mib(web["resources"]["limits"]["memory"])
    assert heap_mib >= 1024, "the first ClickHouse migration died at 500 MB"
    assert heap_mib < limit_mib, "heap must leave room for the process outside V8"
