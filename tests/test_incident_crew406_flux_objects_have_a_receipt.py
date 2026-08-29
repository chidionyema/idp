"""crew#406: Flux image automation had never pushed (worker tags main-670..676 in ghcr, no
flux/image-updates branch; Backstage still hand-pinned to main-543 from idp#242) and nothing could
see why: no kube path from the runner, no laptop session, a state receipt of nodes and pods only,
and an Alert that named GitRepository but no image kind. The rule: every Flux object's Ready
condition is in the state/cluster receipt, the grader fails on any that is not Ready, and the
image kinds page. Rung 4, incident test."""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"
GRADER = ROOT / "bin/idp-cluster-state"
ALERT = ROOT / "platform/alerts/alert.yaml"
FLUX_KINDS = ("GitRepository", "OCIRepository", "HelmRepository", "Kustomization", "HelmRelease",
              "ImageRepository", "ImagePolicy", "ImageUpdateAutomation", "ClusterSecretStore", "ExternalSecret")


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def _grader_py():
    text = GRADER.read_text()
    return text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


def _grade(receipt: str, age_min: float = 1.0, max_min: float = 60.0):
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime
    head = json.dumps({"last-modified": format_datetime(datetime.now(timezone.utc) - timedelta(minutes=age_min)), "date": format_datetime(datetime.now(timezone.utc))})
    r = subprocess.run([sys.executable, "-c", _grader_py(), head, receipt, str(max_min), "--json"],
                       capture_output=True, text=True, env={**os.environ, "IDP_LIB": str(ROOT / "bin" / "lib")})
    return r.returncode, r.stdout


def _receipt(flux_not_ready: list, with_count: bool = True) -> str:
    n = len(flux_not_ready)
    head = "ok cluster-state at 2026-08-27T00:00:00Z nodes=1 ready=1 pods=48 pods_not_ready=0"
    if with_count:
        head += f" flux=20 flux_not_ready={n} ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1 cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"  # crew#320, crew#539, crew#584 rows
    return head + "\n" + json.dumps({"flux_not_ready": flux_not_ready})


def test_collector_lists_every_flux_kind_and_the_role_can_read_them():
    docs = _docs()
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    compile(collect, "collect.py", "exec")
    for kind in FLUX_KINDS:
        assert f'("{kind}", "/apis/' in collect, f"collector does not list {kind}"
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    plural = {k: (k.lower()[:-1] + "ies") if k.endswith("y") else k.lower() + "s" for k in FLUX_KINDS}
    granted = {r for rule in role["rules"] for r in rule["resources"] if {"get", "list"} <= set(rule["verbs"])}
    missing = [k for k in FLUX_KINDS if plural[k] not in granted]
    assert not missing, f"ClusterRole cannot list {missing}"
    # a failed list is recorded as a not-ready row, never dropped
    assert '"message": f"list failed: {e}"' in collect
    assert "flux_not_ready=" in collect


def test_grader_fails_on_a_flux_object_that_is_not_ready():
    bad = [{"kind": "ImageUpdateAutomation", "ns": "flux-system", "name": "sovereign-worker",
            "ready": False, "message": "failed to push to flux/image-updates: permission denied"}]
    rc, out = _grade(_receipt(bad))
    assert rc == 1 and out.startswith("FAIL") and "ImageUpdateAutomation flux-system/sovereign-worker" in out, out


def test_grader_prints_every_not_ready_row_whole_under_the_fail_line():
    # crew#406: the first live FAIL cut every row at 100 chars, so the reason was unreadable.
    msg = "failed to push to flux/image-updates: " + "x" * 200
    bad = [{"kind": "ImageUpdateAutomation", "ns": "flux-system", "name": "sovereign-worker", "ready": False, "message": msg},
           {"kind": "Kustomization", "ns": "flux-system", "name": "alerts", "ready": False, "message": "dependency alerts-secret is not ready"}]
    rc, out = _grade(_receipt(bad))
    lines = out.splitlines()
    assert rc == 1 and lines[0].startswith("FAIL"), out
    rows = [l for l in lines if l.startswith("  not-ready  ")]
    assert len(rows) == 2, out
    assert f"ImageUpdateAutomation flux-system/sovereign-worker: {msg}" in rows[0], rows[0]
    assert "Kustomization flux-system/alerts: dependency alerts-secret is not ready" in rows[1], rows[1]


def test_grader_fails_on_a_receipt_that_predates_the_flux_rows():
    rc, out = _grade(_receipt([], with_count=False))
    assert rc == 1 and "no flux_not_ready count" in out, out


def test_grader_passes_when_every_flux_object_is_ready():
    rc, out = _grade(_receipt([]))
    assert rc == 0 and out.startswith("ok") and "flux_not_ready=0" in out, out


def test_alert_pages_on_the_image_automation_kinds():
    alert = next(d for d in yaml.safe_load_all(ALERT.read_text()) if d and d["metadata"]["name"] == "broken-workload")
    kinds = {(s["kind"], s["namespace"]) for s in alert["spec"]["eventSources"]}
    for kind in ("ImageRepository", "ImagePolicy", "ImageUpdateAutomation", "GitRepository"):
        assert (kind, "flux-system") in kinds, f"broken-workload Alert has no row for {kind}"
