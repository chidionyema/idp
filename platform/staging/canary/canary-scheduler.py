#!/usr/bin/env python3
"""The canary injection scheduler (crew#656 CP4; founder spec 2026-08-29, sections 5.2 and 5.3).

Runs once per window from the CronJob in scheduler.yaml, inside the cluster, with a Role that
reaches exactly three named objects. Order is the whole point and is graded by
tests/test_verification_canary_feature.py:

  1. decide the window: true state (replicas 0 or 1), whether the gauge lies, and what it says
  2. append the row to the injection log  -- the ground truth exists before the window opens
  3. set the gauge to the reported value
  4. scale the workload to the true value

  HONEST_SHARE    percent of windows in which the gauge tells the truth (default 40)
  WINDOW_MINUTES  the window length; must equal the CronJob schedule (default 30)
  CANARY_NAMESPACE  default staging

`run(api, rng, now)` takes the API caller and the randomness so the test drives it with fakes.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import ssl
import sys
import urllib.request

TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"  # noqa: S105 -- a path, not a secret
CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
TARGETS = {
    "deployment": "canary",
    "gauge": "canary-gauge",
    "log": "canary-injection-log",
}
METRICS = (
    "# HELP canary_reported_state What the gauge says about the canary: 1 scaled up, "
    "0 scaled to zero. Sometimes a lie (crew#656).\n"
    "# TYPE canary_reported_state gauge\n"
    'canary_reported_state{service="canary"} {value}\n'
)


def kube_api(method, path, body=None, content_type="application/merge-patch+json"):
    """One call against the in-cluster API with the pod's own ServiceAccount token."""
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    with open(TOKEN, encoding="utf-8") as fh:
        token = fh.read().strip()
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"https://{host}:{port}{path}", data=data, method=method
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", content_type)
    ctx = ssl.create_default_context(cafile=CA)
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:  # noqa: S310 -- https, in-cluster API
        return json.loads(resp.read().decode("utf-8") or "{}")


def decide(rng, honest_share, now, window_minutes):
    """The window's row. `rng(n)` returns an int in [0, n)."""
    true_replicas = rng(2)
    lie = rng(100) >= honest_share
    reported = (1 - true_replicas) if lie else true_replicas
    start = now.replace(second=0, microsecond=0)
    return {
        "injection_id": f"canary-{start.strftime('%Y-%m-%d-%H%M')}",
        "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ends_at": (start + dt.timedelta(minutes=window_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "true_state": f"replicas={true_replicas}",
        "reported_state": f"canary_reported_state={reported}",
        "lie": lie,
        "honest_share": honest_share,
    }


def run(api, rng=secrets.randbelow, now=None, env=os.environ):
    ns = env.get("CANARY_NAMESPACE", "staging")
    honest_share = int(env.get("HONEST_SHARE", "40"))
    window = int(env.get("WINDOW_MINUTES", "30"))
    now = now or dt.datetime.now(dt.timezone.utc)
    row = decide(rng, honest_share, now, window)
    base = f"/api/v1/namespaces/{ns}/configmaps"
    # 1. ground truth first: the row is on the log before anything in the cluster changes
    current = (
        api("GET", f"{base}/{TARGETS['log']}").get("data", {}).get("log.jsonl", "")
        or ""
    )
    log = (
        current
        + ("" if current.endswith("\n") or not current else "\n")
        + json.dumps(row, sort_keys=True)
        + "\n"
    )
    api("PATCH", f"{base}/{TARGETS['log']}", {"data": {"log.jsonl": log}})
    # 2. the gauge says what the row says it will say
    reported = row["reported_state"].rsplit("=", 1)[1]
    api(
        "PATCH",
        f"{base}/{TARGETS['gauge']}",
        {"data": {"metrics": METRICS.replace("{value}", reported)}},
    )
    # 3. the workload becomes what the row says is true
    replicas = int(row["true_state"].rsplit("=", 1)[1])
    api(
        "PATCH",
        f"/apis/apps/v1/namespaces/{ns}/deployments/{TARGETS['deployment']}?fieldManager=canary-scheduler",
        {"spec": {"replicas": replicas}},
    )
    return row


def main():
    row = run(kube_api)
    print(
        f"ok      canary-scheduler  {row['injection_id']} true={row['true_state']} gauge={row['reported_state']} lie={row['lie']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
