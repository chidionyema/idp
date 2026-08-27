"""crew#539 CP9 (founder, 2026-08-27: Guaranteed QoS on the radio-room set). The kubelet evicts
BestEffort first, Burstable next, Guaranteed last; Guaranteed is requests == limits for cpu and
memory on every container. Proved three ways, no sockets:
  1. every radio-room manifest, and the Postgres/ClickHouse values under them, carry equal
     requests and limits;
  2. the Kyverno rule that refuses a widened limit exists and is Enforce;
  3. `kyverno apply` (the CLI, offline) passes a Guaranteed synthetic Deployment/CronJob and
     fails a Burstable one -- the guard is proved to refuse, not only to allow.
"""
import pathlib
import shutil
import subprocess

import pytest
import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
POLICY = IDP / "platform/scheduling/require-priority-class.yaml"
RADIO_ROOM = {
    "agentgateway": ("platform/mcp/agentgateway-deploy.yaml", "Deployment"),
    "hermes-agent-gateway": ("platform/hermes-agent/gateway.yaml", "Deployment"),
    "telemetry-coverage": ("platform/observability/telemetry-coverage.yaml", "CronJob"),
    "cluster-state": ("platform/state/cluster-state.yaml", "CronJob"),
}
NODE_MILLICPU = 4000


def docs(rel):
    return [d for d in yaml.safe_load_all((IDP / rel).read_text()) if d]


def containers(obj):
    spec = obj["spec"]
    tmpl = spec["template"] if "template" in spec else spec["jobTemplate"]["spec"]["template"]
    return tmpl["spec"]["containers"]


def assert_guaranteed(res, where):
    req, lim = res.get("requests") or {}, res.get("limits") or {}
    for k in ("cpu", "memory"):
        assert req.get(k), f"{where}: no {k} request"
        assert req.get(k) == lim.get(k), f"{where}: {k} request {req.get(k)} != limit {lim.get(k)}"


def millicpu(v):
    return int(v[:-1]) if v.endswith("m") else int(float(v) * 1000)


def test_the_four_plain_manifests_are_guaranteed_and_fit_one_node():
    total = 0
    for name, (rel, kind) in RADIO_ROOM.items():
        (obj,) = [d for d in docs(rel) if d["kind"] == kind and d["metadata"]["name"] == name]
        for c in containers(obj):
            assert_guaranteed(c["resources"], f"{name}/{c['name']}")
            total += millicpu(c["resources"]["requests"]["cpu"])
    assert total < NODE_MILLICPU, total


def test_langfuse_web_worker_and_its_databases_are_guaranteed():
    v = yaml.safe_load((IDP / "platform/observability/langfuse-values.yaml").read_text())
    for key in ("web", "worker"):
        assert_guaranteed(v["langfuse"][key]["resources"], f"langfuse-{key}")
    assert_guaranteed(v["postgresql"]["resources"], "langfuse-postgresql")
    assert_guaranteed(v["redis"]["resources"], "langfuse-redis")


def test_backstage_postgres_and_signoz_clickhouse_are_guaranteed():
    (sts,) = [d for d in docs("platform/backstage/base/postgres.yaml") if d["kind"] == "StatefulSet"]
    for c in containers(sts):
        assert_guaranteed(c["resources"], f"backstage-postgres/{c['name']}")
    sv = yaml.safe_load((IDP / "platform/observability/values.yaml").read_text())
    assert_guaranteed(sv["clickhouse"]["resources"], "signoz-clickhouse")


def test_kyverno_rule_is_enforce_on_exactly_the_radio_room_names():
    (pol,) = docs(POLICY.relative_to(IDP).as_posix())
    rules = {r["name"]: r for r in pol["spec"]["rules"]}
    crit, qos = rules["radio-room-set-is-critical"], rules["radio-room-set-is-guaranteed"]
    assert qos["validate"]["failureAction"] == "Enforce"
    assert qos["match"]["any"][0]["resources"]["names"] == crit["match"]["any"][0]["resources"]["names"]
    assert "CronJob" in qos["match"]["any"][0]["resources"]["kinds"]


def _workload(kind, name, requests, limits):
    pod = {
        "spec": {
            "priorityClassName": "infrastructure-critical",
            "containers": [{"name": "c", "image": "x", "resources": {"requests": requests, "limits": limits}}],
        }
    }
    if kind == "Deployment":
        spec = {"selector": {"matchLabels": {"a": "b"}}, "template": {"metadata": {"labels": {"a": "b"}}, **pod}}
    else:
        spec = {"schedule": "* * * * *", "jobTemplate": {"spec": {"template": pod}}}
    return {
        "apiVersion": "apps/v1" if kind == "Deployment" else "batch/v1",
        "kind": kind,
        "metadata": {"name": name, "namespace": "t"},
        "spec": spec,
    }


@pytest.mark.skipif(shutil.which("kyverno") is None, reason="kyverno CLI not on PATH")
@pytest.mark.parametrize("kind,name", [("Deployment", "agentgateway"), ("CronJob", "cluster-state")])
def test_kyverno_cli_refuses_burstable_and_passes_guaranteed(tmp_path, kind, name):
    good = _workload(kind, name, {"cpu": "100m", "memory": "256Mi"}, {"cpu": "100m", "memory": "256Mi"})
    bad = _workload(kind, name, {"cpu": "100m", "memory": "256Mi"}, {"cpu": "500m", "memory": "256Mi"})
    for label, obj, want in (("good", good, "pass"), ("bad", bad, "fail")):
        f = tmp_path / f"{label}.yaml"
        f.write_text(yaml.safe_dump(obj))
        out = subprocess.run(
            ["kyverno", "apply", str(POLICY), "--resource", str(f), "--policy-report"],
            capture_output=True, text=True, timeout=60,
        )
        reports = [d for d in yaml.safe_load_all(out.stdout) if d and d.get("results")]
        assert reports, out.stdout + out.stderr
        rows = [r for r in reports[0]["results"] if r.get("rule") == "radio-room-set-is-guaranteed"]
        assert rows, reports[0]["results"]
        assert {r["result"] for r in rows} == {want}, (label, rows)
