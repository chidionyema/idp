"""crew#387: datamap said cluster/*/ExternalSecret/* is WIRED_NEVER: a rotated upstream secret
fails silently. Since crew#406 the receipt grades every ExternalSecret's Ready condition, which
catches a refresh that errors; it did not catch a controller that simply stopped refreshing, where
Ready stays True and the Secret drifts from the vault. Rule: the ExternalSecret row carries
last_sync (status.refreshTime) and is not-ready once that is older than twice its refreshInterval
(floor 2h); the grader prints the row like any other not-ready Flux object. Rung 4, incident test."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"
GRADER = ROOT / "bin/idp-cluster-state"


def _collect():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"], docs


def _grade(receipt: str):
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime
    py = GRADER.read_text().split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    head = json.dumps({"last-modified": format_datetime(datetime.now(timezone.utc) - timedelta(minutes=1))})
    r = subprocess.run([sys.executable, "-c", py, head, receipt, "60", "--json"], capture_output=True, text=True, check=False)
    return r.returncode, r.stdout


def test_collector_rows_every_externalsecret_with_its_last_sync_and_the_role_can_read_them():
    collect, docs = _collect()
    compile(collect, "collect.py", "exec")
    assert '"/apis/external-secrets.io/v1/externalsecrets"' in collect
    assert 'row["last_sync"] = st.get("refreshTime")' in collect
    assert "max(2 * secs, 7200)" in collect, "stale rule is 2x refreshInterval with a 2h floor"
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    granted = {(g, r) for rule in role["rules"] for g in rule["apiGroups"] for r in rule["resources"]
               if {"get", "list"} <= set(rule["verbs"])}
    assert ("external-secrets.io", "externalsecrets") in granted


def test_stale_externalsecret_row_fails_the_receipt_and_names_the_secret():
    row = {"kind": "ExternalSecret", "ns": "llm", "name": "litellm-upstream", "ready": False, "last_sync": "2026-08-26T01:00:00Z",
           "message": "Ready but last sync 2026-08-26T01:00:00Z is older than 2x refreshInterval 1h"}
    head = "ok cluster-state at 2026-08-27T05:00:00Z nodes=1 ready=1 pods=45 pods_not_ready=0 flux=21 flux_not_ready=1 ds=3 ds_short=0 events_warning=0 cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"
    rc, out = _grade(head + "\n" + json.dumps({"flux_not_ready": [row], "ds_short": [], "events_warning": []}))
    assert rc == 1 and out.startswith("FAIL"), out
    assert "ExternalSecret llm/litellm-upstream" in out and "older than 2x refreshInterval" in out, out


def test_fresh_externalsecrets_leave_the_receipt_ok():
    head = "ok cluster-state at 2026-08-27T05:00:00Z nodes=1 ready=1 pods=45 pods_not_ready=0 flux=21 flux_not_ready=0 ds=3 ds_short=0 events_warning=0 monitoring_rules=1 alert_watchdog=1 cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"
    rc, out = _grade(head + "\n" + json.dumps({"flux_not_ready": [], "ds_short": [], "events_warning": []}))
    assert rc == 0 and out.startswith("ok"), out
