"""crew#320 / oke-check 33029374693: telemetry-coverage said pods=45 seen=0 and cluster-state said
ok, while the k8s-infra-otel-agent DaemonSet had no pod at all. A DaemonSet at 0/1 is invisible
to a pods list (its pods do not exist) and to the Flux rows (the HelmRelease is Ready). Rule: the
receipt carries every DaemonSet's desired vs ready and the Warning events of the last hour; the
grader fails on any short DaemonSet and prints the events that name it. Rung 4, incident test."""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"
GRADER = ROOT / "bin/idp-cluster-state"


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def _grader_py():
    text = GRADER.read_text()
    return text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


def _grade(receipt: str):
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime
    head = json.dumps({"last-modified": format_datetime(datetime.now(timezone.utc) - timedelta(minutes=1)), "date": format_datetime(datetime.now(timezone.utc))})
    r = subprocess.run([sys.executable, "-c", _grader_py(), head, receipt, "60", "--json"],
                       capture_output=True, text=True, check=False, env={**os.environ, "IDP_LIB": str(ROOT / "bin" / "lib")})
    return r.returncode, r.stdout


def _receipt(ds_short: list, events: list, with_count: bool = True) -> str:
    head = "ok cluster-state at 2026-08-27T01:00:00Z nodes=1 ready=1 pods=45 pods_not_ready=0 flux=20 flux_not_ready=0"
    if with_count:
        head += f" ds=3 ds_short={len(ds_short)} events_warning={len(events)} monitoring_rules=1 alert_watchdog=1 cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"
    return head + "\n" + json.dumps({"flux_not_ready": [], "ds_short": ds_short, "events_warning": events})


def test_collector_lists_daemonsets_and_warning_events_and_the_role_can_read_them():
    docs = _docs()
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    compile(collect, "collect.py", "exec")
    assert '"/apis/apps/v1/daemonsets"' in collect
    assert "type%3DWarning" in collect
    assert "ds_short=" in collect and "events_warning=" in collect
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    granted = {(g, r) for rule in role["rules"] for g in rule["apiGroups"] for r in rule["resources"]
               if {"get", "list"} <= set(rule["verbs"])}
    assert ("apps", "daemonsets") in granted and ("", "events") in granted


def test_grader_fails_on_a_short_daemonset_and_prints_the_event_that_names_it():
    short = [{"ns": "observability", "name": "k8s-infra-otel-agent", "desired": 1, "ready": 0}]
    events = [{"at": "2026-08-27T00:59:00", "ns": "observability", "kind": "DaemonSet", "name": "k8s-infra-otel-agent",
               "reason": "FailedCreate", "count": 12,
               "message": "Error creating: admission webhook denied: policy require-run-as-nonroot"}]
    rc, out = _grade(_receipt(short, events))
    assert rc == 1 and out.startswith("FAIL"), out
    assert "observability/k8s-infra-otel-agent ready=0/1" in out and "FailedCreate x12" in out, out


def test_grader_fails_on_a_receipt_that_predates_the_daemonset_row():
    rc, out = _grade(_receipt([], [], with_count=False))
    assert rc == 1 and "no ds_short count" in out, out


def test_grader_passes_when_every_daemonset_is_at_desired():
    rc, out = _grade(_receipt([], []))
    assert rc == 0 and out.startswith("ok") and "ds_short=0" in out, out
