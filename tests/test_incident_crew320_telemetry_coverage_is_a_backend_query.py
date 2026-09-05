"""Incident 2026-08-27 (crew#320, LAW 50): the data map graded the cluster by scanning files and
called the whole cluster_live domain BLIND while SigNoz was already storing traces. Founder: the
coverage is verified by querying the backend, not by scanning files. Rule (rung 4, incident
test): the collector in platform/observability/telemetry-coverage.yaml marks a pod Running for
longer than the grace period and absent from both ClickHouse tables as missing (FAIL); a pod
either table has seen is covered (ok); and a backend that answers neither query is BLIND,
never ok. The three verdicts come from the same function over the same pod list."""
import pathlib
import types
from datetime import datetime, timedelta, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform" / "observability" / "telemetry-coverage.yaml"
NOW = datetime(2026, 8, 27, 1, 0, tzinfo=timezone.utc)


def _collector():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    cm = next(d for d in docs if d["kind"] == "ConfigMap")
    mod = types.ModuleType("collect")
    exec(compile(cm["data"]["collect.py"], "collect.py", "exec"), mod.__dict__)
    return mod


def _pod(ns, name, minutes_old, phase="Running"):
    start = (NOW - timedelta(minutes=minutes_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"metadata": {"namespace": ns, "name": name}, "status": {"phase": phase, "startTime": start}}


PODS = {"items": [_pod("kini", "kini-worker-1", 30), _pod("llm", "litellm-router-1", 30),
                  _pod("llm", "just-started", 2), _pod("backstage", "done-job", 30, phase="Succeeded")]}


def test_incident_crew320_backend_query_grades_both_ways():
    mod = _collector()
    kube = lambda path: PODS  # noqa: E731

    # ok: the logs table saw one pod, the metrics table the other; the young pod and the finished job are not graded.
    # crew#539 CP12: the same run counts Hubble series naming a radio-room workload (a TSV count row).
    seen = {"logs": {("kini", "kini-worker-1")}, "metrics": {("llm", "litellm-router-1")}, "hubble": {("7",)}}
    route = lambda sql: seen["hubble" if "hubble" in sql else "logs" if "logs" in sql else "metrics"]  # noqa: E731
    head, body = mod.main(kube=kube, clickhouse=route, now=NOW)
    assert head.startswith("ok telemetry-coverage") and "pods=2 seen=2 missing=0 hubble_radio_flows=7" in head, head
    assert body["missing"] == [] and body["backend_errors"] == {} and body["hubble_radio_flows"] == 7

    # FAIL: neither table has heard from the router in the window, and the receipt names it.
    head, body = mod.main(kube=kube, clickhouse=lambda sql: {("7",)} if "hubble" in sql else {("kini", "kini-worker-1")}, now=NOW)
    assert head.startswith("FAIL telemetry-coverage") and "missing=1" in head, head
    assert body["missing"] == [{"ns": "llm", "pod": "litellm-router-1"}]

    # FAIL: every pod is covered but Hubble named no radio-room flow in the window (crew#539 CP12).
    seen["hubble"] = {("0",)}
    head, body = mod.main(kube=kube, clickhouse=route, now=NOW)
    assert head.startswith("FAIL telemetry-coverage") and "missing=0 hubble_radio_flows=0" in head, head
    seen["hubble"] = {("7",)}

    # BLIND: the backend cannot be queried. Never ok, never FAIL.
    def down(sql):
        raise ConnectionError("signoz-clickhouse:8123 refused")

    head, body = mod.main(kube=kube, clickhouse=down, now=NOW)
    assert head.startswith("BLIND telemetry-coverage"), head
    assert set(body["backend_errors"]) == {"traces", "logs", "metrics", "hubble"}

    # One table down is still a verdict, with the error recorded.
    def half(sql):
        if "logs" in sql:
            raise ConnectionError("logs table missing")
        if "hubble" in sql:
            return {("3",)}
        return {("kini", "kini-worker-1"), ("llm", "litellm-router-1")}

    head, body = mod.main(kube=kube, clickhouse=half, now=NOW)
    assert head.startswith("ok telemetry-coverage") and body["backend_errors"] == {"logs": "logs table missing"}


def test_incident_crew320_reader_grades_missing_not_nodes():
    text = (ROOT / "bin" / "idp-telemetry-coverage").read_text()
    assert 'kv.get("missing") != "0"' in text
    assert "state/telemetry-coverage" in text
    assert 'line1.startswith("BLIND ")' in text
