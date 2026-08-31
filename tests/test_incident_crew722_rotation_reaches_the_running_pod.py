"""crew#722 (founder 2026-08-31: "poorly designed enterprise-wide secrets rotation strategy, this
will harm us badly if we let it slide"). Twice in one week a rotation "succeeded" at the vault and
never reached the running program: crew#506 CP4 (pod kept the old key) and crew#684 (rotated key
reached neither consumer). Two controls close the class and this file grades both:

  backstop (CP2)  the cluster-state receipt counts running pods older than a Secret they consume;
                  the grader FAILs on any such pod, on a receipt that could not read secrets
                  metadata (-1, never a silent 0), and on a receipt that predates the count.
  canary  (CP3)   platform/state/rotation-canary.yaml consumes a secret the daily rotation-drill
                  job rotates for real; the drill is graded by drills/catalogue.yaml.

Rung 4, incident test. Proof obligation (founder doc c08d08d9): the first test below is the
pre-fix state -- a receipt whose pods predate a rotated Secret -- shown FAILING the grader."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"
CANARY = ROOT / "platform/state/rotation-canary.yaml"
GRADER = ROOT / "bin/idp-cluster-state"
WORKFLOW = ROOT / ".github/workflows/oke-check.yml"
CATALOGUE = ROOT / "drills/catalogue.yaml"

FULL_OK_HEAD = (
    "ok cluster-state at 2026-08-27T05:00:00Z nodes=1 ready=1 pods=45 pods_not_ready=0 "
    "flux=21 flux_not_ready=0 ds=3 ds_short=0 deploy_short=0 events_warning=0 "
    "monitoring_rules=1 alert_watchdog=1 cpu_used_pct=12 cpu_req_pct=45 mem_used_pct=30 mem_req_pct=50"
)
EMPTY_BODY = {"flux_not_ready": [], "ds_short": [], "events_warning": []}


def _collect():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"], docs


def _grade(receipt: str):
    from email.utils import format_datetime

    py = GRADER.read_text().split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    head = json.dumps(
        {
            "last-modified": format_datetime(
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ),
            "date": format_datetime(datetime.now(timezone.utc)),
        }
    )
    r = subprocess.run(
        [sys.executable, "-c", py, head, receipt, "60", "--json"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "IDP_LIB": str(ROOT / "bin" / "lib")},
    )
    return r.returncode, r.stdout


def _stale_section():
    """The collector's stale-consumer pass, extracted so it runs against fake API answers."""
    collect, _ = _collect()
    start = collect.index("def secret_refs(")
    endmark = "secret_stale_count = -1 if secrets_error else len(secret_stale)"
    return collect[start : collect.index(endmark) + len(endmark)]


def _ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pod(ns, name, start, refs=None, vols=None, phase="Running", owner=None, ann=None):
    spec = {
        "containers": [
            {
                "name": "c",
                "env": [
                    {
                        "name": "K",
                        "valueFrom": {"secretKeyRef": {"name": r, "key": "k"}},
                    }
                    for r in (refs or [])
                ],
            }
        ]
    }
    if vols:
        spec["volumes"] = [{"name": v, "secret": {"secretName": v}} for v in vols]
    md = {"namespace": ns, "name": name}
    if owner:
        md["ownerReferences"] = [{"kind": owner}]
    if ann:
        md["annotations"] = ann
    return {
        "metadata": md,
        "spec": spec,
        "status": {"phase": phase, "startTime": _ts(start) if start else None},
    }


def _run_section(secret_items, pods):
    def fake_get(path, accept=None):
        assert path == "/api/v1/secrets"
        assert accept and "PartialObjectMetadataList" in accept, (
            "values must never be requested"
        )
        return {"items": secret_items}

    ns = {"datetime": datetime, "timezone": timezone, "get": fake_get, "pods": pods}
    exec(_stale_section(), ns)  # noqa: S102 -- the estate's own collector code, under test
    return ns


def test_collector_flags_the_pod_that_predates_its_secret_and_respects_every_exemption():
    now = datetime.now(timezone.utc)
    old, older, recent = (
        now - timedelta(hours=2),
        now - timedelta(hours=3),
        now - timedelta(minutes=5),
    )
    secrets = [
        {
            "metadata": {
                "namespace": "llm",
                "name": "litellm-env",
                "managedFields": [
                    {"time": _ts(now - timedelta(days=3))},
                    {"time": _ts(old)},
                ],
            }
        },
        {
            "metadata": {
                "namespace": "llm",
                "name": "fresh-secret",
                "managedFields": [{"time": _ts(recent)}],
            }
        },
        {
            "metadata": {
                "namespace": "kyverno",
                "name": "webhook-cert",
                "managedFields": [{"time": _ts(old)}],
            }
        },
        # no managedFields at all: creationTimestamp is the fallback write time
        {
            "metadata": {
                "namespace": "backstage",
                "name": "volume-secret",
                "creationTimestamp": _ts(old),
            }
        },
    ]
    pods = [
        _pod(
            "llm", "consumer-old", older, refs=["litellm-env"]
        ),  # STALE: started before the write
        _pod(
            "llm", "consumer-new", now - timedelta(hours=1), refs=["litellm-env"]
        ),  # restarted after: fine
        _pod(
            "llm", "grace-pod", older, refs=["fresh-secret"]
        ),  # write < 15m old: grace
        _pod(
            "llm",
            "opt-out",
            older,
            refs=["litellm-env"],
            ann={"reloader.stakater.com/auto": "false"},
        ),
        _pod(
            "llm", "job-pod", older, refs=["litellm-env"], owner="Job"
        ),  # Jobs run to completion
        _pod(
            "kyverno", "kyverno-pod", older, refs=["webhook-cert"]
        ),  # exempt namespace
        _pod("llm", "pending-pod", None, refs=["litellm-env"], phase="Pending"),
        _pod(
            "backstage", "vol-pod", older, vols=["volume-secret"]
        ),  # STALE via volume mount
        _pod(
            "llm", "unknown-ref", older, refs=["never-written"]
        ),  # secret unknown: skip
    ]
    ns = _run_section(secrets, pods)
    flagged = {(r["ns"], r["pod"], r["secret"]) for r in ns["secret_stale"]}
    assert flagged == {
        ("llm", "consumer-old", "litellm-env"),
        ("backstage", "vol-pod", "volume-secret"),
    }, flagged
    assert ns["secret_stale_count"] == 2 and ns["secrets_error"] == ""


def test_collector_reports_a_failed_secrets_list_as_minus_one_never_zero():
    def broken_get(path, accept=None):
        raise RuntimeError("api server said 403")

    ns = {"datetime": datetime, "timezone": timezone, "get": broken_get, "pods": []}
    exec(_stale_section(), ns)  # noqa: S102
    assert ns["secret_stale_count"] == -1, (
        "a failed read must be BLIND, never a clean 0 (silent-green class)"
    )
    assert "403" in ns["secrets_error"]


def test_rbac_grants_list_on_secrets_metadata_and_nothing_that_could_read_a_value():
    _, docs = _collect()
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    secret_rules = [r for r in role["rules"] if "secrets" in r.get("resources", [])]
    assert secret_rules, "the collector needs list on secrets metadata"
    for r in secret_rules:
        assert set(r["verbs"]) == {"list"}, (
            f"secrets verbs must be list alone, got {r['verbs']}"
        )
    collect, _ = _collect()
    assert "PartialObjectMetadataList" in collect, (
        "the list must ask for metadata only, never values"
    )


def test_a_receipt_with_a_stale_consumer_fails_and_names_the_pod_and_the_secret():
    """Proof obligation: this receipt is the crew#506 CP4 world -- the vault write happened,
    the pod kept running on the old value -- and the grader refuses it."""
    rows = [
        {
            "ns": "llm",
            "pod": "litellm-7f9c-x2v",
            "secret": "litellm-env",
            "secret_written": "2026-08-27T03:00:00Z",
            "pod_started": "2026-08-25T01:00:00Z",
        },
        {
            "ns": "hermes-agent",
            "pod": "gateway-5d-k8p",
            "secret": "hermes-agent-env",
            "secret_written": "2026-08-27T03:00:00Z",
            "pod_started": "2026-08-24T09:00:00Z",
        },
    ]
    head = FULL_OK_HEAD + " secret_stale_consumers=2"
    rc, out = _grade(
        head + "\n" + json.dumps({**EMPTY_BODY, "secret_stale_consumers": rows})
    )
    assert rc == 1 and "FAIL    secret-freshness" in out, out
    assert "llm/litellm-7f9c-x2v" in out and "litellm-env" in out, out
    assert "hermes-agent/gateway-5d-k8p" in out, (
        "every row is printed, not a summary count"
    )


def test_a_receipt_with_zero_stale_consumers_is_ok():
    head = FULL_OK_HEAD + " secret_stale_consumers=0"
    rc, out = _grade(head + "\n" + json.dumps(EMPTY_BODY))
    assert rc == 0 and out.startswith("ok"), out
    assert "ok      secret-freshness" in out, out


def test_a_receipt_that_predates_the_count_fails_rather_than_passing_silently():
    rc, out = _grade(FULL_OK_HEAD + "\n" + json.dumps(EMPTY_BODY))
    assert rc == 1 and "predates crew#722" in out, out


def test_an_unreadable_secrets_list_fails_the_receipt_with_the_recorded_error():
    head = FULL_OK_HEAD + " secret_stale_consumers=-1"
    rc, out = _grade(
        head
        + "\n"
        + json.dumps(
            {**EMPTY_BODY, "secrets_error": "secrets metadata list failed: 403"}
        )
    )
    assert rc == 1 and "not graded" in out and "403" in out, out


def _canary_docs():
    return [d for d in yaml.safe_load_all(CANARY.read_text()) if d]


def test_canary_consumes_the_secret_the_way_the_worst_consumer_does():
    docs = _canary_docs()
    es = next(d for d in docs if d["kind"] == "ExternalSecret")
    assert es["spec"]["refreshInterval"] == "10m", (
        "the 25-minute SLO is built on a 10m refresh"
    )
    assert es["spec"]["target"]["name"] == "rotation-canary"
    dep = next(d for d in docs if d["kind"] == "Deployment")
    assert dep["metadata"]["annotations"]["reloader.stakater.com/auto"] == "true", (
        "the canary rides the estate's own reload standard, not a private mechanism"
    )
    assert dep["spec"]["replicas"] >= 2, (
        "backstage is founder-facing: require-availability demands two"
    )
    assert any(
        c["topologyKey"] == "kubernetes.io/hostname"
        and c["whenUnsatisfiable"] == "DoNotSchedule"
        for c in dep["spec"]["template"]["spec"]["topologySpreadConstraints"]
    )
    tpl = dep["spec"]["template"]["spec"]
    vols = {v["name"]: v for v in tpl["volumes"]}
    assert vols["canary"]["secret"]["secretName"] == "rotation-canary", (
        "value arrives as a file, never env"
    )
    (c,) = tpl["containers"]
    assert not any("secretKeyRef" in json.dumps(e) for e in c.get("env", [])), (
        "secrets-not-from-env-vars flips to Enforce; the canary must outlive the flip"
    )
    assert "read ONCE" in c["args"][0] and "/canary/value" in c["args"][0], (
        "the value is captured at start: a re-reading canary would go green without any restart"
    )
    assert c["readinessProbe"] and c["livenessProbe"], (
        "require-pod-probes refuses probe-less pods"
    )
    assert ":" in c["image"] and not c["image"].endswith(":latest"), "image is pinned"
    cpu = c["resources"]["requests"]["cpu"]
    assert cpu.endswith("m") and int(cpu[:-1]) <= 250, (
        "capacity policy caps platform requests"
    )
    pdb = next(d for d in docs if d["kind"] == "PodDisruptionBudget")
    assert pdb["spec"]["minAvailable"] == 1


def test_the_drill_job_exists_never_runs_on_a_pull_request_and_the_catalogue_row_matches():
    wf = yaml.safe_load(WORKFLOW.read_text())
    job = wf["jobs"]["rotation-drill"]
    assert "pull_request" in job["if"], "a PR must never rotate anything"
    run = json.dumps(job["steps"])
    assert "idp-vault-put rotation-canary" in run, (
        "the rotation goes through the estate's own writer"
    )
    assert "state/rotation-canary" in run, (
        "the poll reads the receipt the running pod publishes"
    )
    crons = [s["cron"] for s in (wf.get("on") or wf.get(True))["schedule"]]
    row = next(
        r
        for r in yaml.safe_load(CATALOGUE.read_text())["drills"]
        if r["name"] == "rotation-canary"
    )
    assert row["schedule"] in crons, (
        f"catalogue cron {row['schedule']!r} is not a cron of the workflow itself"
    )
    assert row["workflow"] == "oke-check.yml" and row["max_age_hours"] == 26
    assert row.get("owner"), "an unowned drill is the crew#584 mistake again"
