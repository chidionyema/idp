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


def test_incident_crew325_langfuse_release_waits_for_the_clickhouse_it_uses() -> None:
    values = _values()
    docs = _rendered()
    langfuse = next(d for d in docs if d["kind"] == "HelmRelease" and d["metadata"]["name"] == "langfuse")
    signoz = next(d for d in docs if d["kind"] == "HelmRelease" and d["metadata"]["name"] == "signoz")
    assert values["clickhouse"]["host"] == "signoz-clickhouse"
    assert [d["name"] for d in langfuse["spec"]["dependsOn"]] == [signoz["metadata"]["name"]]


def test_incident_crew325_otel_collector_can_write_the_paths_it_writes() -> None:
    # signoz-otel-collector copies its config to /var/tmp at start (signozotelcollector/main.go).
    docs = _rendered()
    hr = next(d for d in docs if d["kind"] == "HelmRelease" and d["metadata"]["name"] == "signoz")
    patch = next(p for p in hr["spec"]["postRenderers"][0]["kustomize"]["patches"]
                 if p["target"].get("name") == "signoz-otel-collector")
    spec = yaml.safe_load(patch["patch"])["spec"]["template"]["spec"]
    collector = next(c for c in spec["containers"] if c["name"] == "collector")
    assert collector["securityContext"]["readOnlyRootFilesystem"] is True
    mounts = {m["mountPath"] for m in collector["volumeMounts"]}
    assert {"/tmp", "/var/tmp"} <= mounts


def test_incident_crew325_langfuse_accepts_the_legacy_ingestion_the_router_uses() -> None:
    # Langfuse 4.x rejects trace events on /api/public/ingestion unless the write mode is legacy
    # or dual; the router's `langfuse` callback posts exactly there (platform/llm/config.yaml).
    router = yaml.safe_load((ROOT / "platform/llm/config.yaml").read_text())
    callbacks = set(router["litellm_settings"]["success_callback"])
    env = {e["name"]: e["value"] for e in _values()["langfuse"].get("additionalEnv", [])}
    if "langfuse" in callbacks:
        assert env.get("LANGFUSE_MIGRATION_V4_WRITE_MODE") in {"dual", "legacy"}, \
            "events_only drops every trace the legacy callback sends"
    else:
        assert "langfuse_otel" in callbacks
