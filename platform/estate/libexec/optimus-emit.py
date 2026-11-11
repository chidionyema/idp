#!/usr/bin/env python3
"""optimus-emit -- publish one optimus.metric.v1 from an idp capability.

AGENTS.md section 3a is binding: "Every operational capability MUST publish
`optimus.metric.v1` to the existing Argon Optimus service." It also says
"missing or stale metrics block a capability from being called operational"
and "BLIND is a measured inability to observe, never a zero."

Until 2026-11-10 nothing in idp published a metric. Measured on this machine:
~/.estate/optimus/metrics.jsonl held 859 rows, every one `source=pennyd-local`.
pennyd could write because PennydMetricIngest writes to the ledger in process;
every other capability has to come through POST /api/brain/optimus/metric,
which closes when ESTATE_BRAIN_ADMIN_KEY is unset -- and that key was never
minted anywhere. So the measurement plane had exactly one producer and was
structurally blind to the rest of the estate.

This is the emitter every idp capability uses. It is deliberately thin: it
validates against argon's own schema rules (so a bad metric is refused here,
not silently stored), derives an idempotent metricId, and POSTs to the one
write contract that already exists. It never reimplements the store.

Usage:
  optimus-emit.py --source idp-ci --subject gate:idp-ci --metric toolchain.missing \
      --value 4 --unit tools --status FAILED \
      --evidence "yamllint, kubeconform, kustomize, docker missing" \
      --label rung=1c.2

Exit codes (the verdict, per AGENTS.md section 3):
  0  metric accepted (or already present -- idempotent)
  2  BLIND: the brain is unreachable or its write path is closed. The metric
     was NOT recorded; the caller must not treat this as a zero.
  3  the metric was refused by the contract (bad identifier, secret in a
     label, bad status). A defect in the caller, never swallowed.

A caller that cannot reach the brain must degrade, never block (R6): the
emitter exits 2 and says BLIND, it does not raise.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

SAFE_ID = re.compile(r"^[A-Za-z0-9._:/@-]{2,180}$")
SECRET_LABEL = re.compile(r"(api[_-]?key|authorization|password|secret|token)", re.I)
STATUSES = ("OK", "DEGRADED", "FAILED", "BLIND")
DEFAULT_BRAIN = os.environ.get("ESTATE_BRAIN_URL", "http://127.0.0.1:4319")


def _admin_key() -> str:
    """The brain's write key, by name only (AGENTS.md section 4).

    Precedence: the env var (CI, the cluster, a founder-seeded vault), then the
    local 0600 file the brain provisions for itself. The value is never printed
    and never placed in a label -- the schema refuses credential-shaped labels
    for exactly this reason.
    """
    from_env = (os.environ.get("ESTATE_BRAIN_ADMIN_KEY") or "").strip()
    if from_env:
        return from_env
    for candidate in (os.path.expanduser("~/.estate/brain/admin.key"),):
        try:
            with open(candidate, encoding="utf-8") as handle:
                value = handle.read().strip()
            if value:
                return value
        except OSError:
            continue
    return ""


def _die(code: int, message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def _check_id(value: str, name: str) -> str:
    value = (value or "").strip()
    if not SAFE_ID.match(value):
        _die(3, f"optimus-emit: {name} {value!r} is not a safe identifier (2-180 of [A-Za-z0-9._:/@-])")
    return value


def build_metric(args: argparse.Namespace) -> dict:
    source = _check_id(args.source, "source")
    subject = _check_id(args.subject, "subject")
    metric = _check_id(args.metric, "metric")

    if args.status not in STATUSES:
        _die(3, f"optimus-emit: status {args.status!r} is not one of {', '.join(STATUSES)}")

    labels: dict[str, str] = {}
    for raw in args.label or []:
        if "=" not in raw:
            _die(3, f"optimus-emit: --label {raw!r} must be key=value")
        key, _, val = raw.partition("=")
        if SECRET_LABEL.search(key):
            _die(3, f"optimus-emit: label {key!r} may not carry credentials (schema forbids it)")
        labels[_check_id(key, "label key")] = val.strip()[:200]

    observed = args.observed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Idempotent by construction: the same observation of the same subject twice is
    # ONE metric, not two. The ledger rejects a duplicate metricId, so a retried
    # emit converges instead of inflating the count.
    metric_id = args.metric_id or f"{source}:{subject}:{metric}:{observed}"

    return {
        "schema": "optimus.metric.v1",
        "metricId": _check_id(metric_id, "metricId"),
        "observedAt": observed,
        "source": source,
        "subject": subject,
        "metric": metric,
        "value": float(args.value),
        "unit": (args.unit or "")[:40],
        "status": args.status,
        "window": (args.window or "PT1M")[:80],
        "evidence": (args.evidence or "")[:2000],
        "labels": labels,
    }


def post(metric: dict, brain: str, timeout: float) -> None:
    body = json.dumps(metric).encode()
    headers = {"Content-Type": "application/json"}
    key = _admin_key()
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(
        brain.rstrip("/") + "/api/brain/optimus/metric",
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode()).get("error", "")
        except Exception:  # noqa: BLE001 - a body we cannot read must not hide the status
            detail = ""
        if exc.code == 503:
            _die(2, f"BLIND  optimus-emit  brain write path closed: {detail or 'no admin key'}")
        if exc.code == 401:
            _die(2, f"BLIND  optimus-emit  brain rejected the admin key (401) -- check ESTATE_BRAIN_ADMIN_KEY or ~/.estate/brain/admin.key")
        if exc.code == 409 or "duplicate" in detail.lower():
            print(f"ok     optimus-emit  {metric['metricId']} already recorded")
            return
        _die(3, f"optimus-emit: brain refused the metric ({exc.code}): {detail}")
    except (urllib.error.URLError, TimeoutError) as exc:
        _die(2, f"BLIND  optimus-emit  brain unreachable at {brain}: {exc}")
    except OSError as exc:
        _die(2, f"BLIND  optimus-emit  brain unreachable at {brain}: {exc}")
    print(f"ok     optimus-emit  {metric['metricId']} = {metric['value']} {metric['unit']} [{metric['status']}]")
    if os.environ.get("OPTIMUS_EMIT_VERBOSE"):
        print(json.dumps(payload, indent=2))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="publish one optimus.metric.v1")
    p.add_argument("--source", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--metric", required=True)
    p.add_argument("--value", required=True, type=float)
    p.add_argument("--unit", default="")
    p.add_argument("--status", default="OK")
    p.add_argument("--window", default="PT1M")
    p.add_argument("--evidence", default="")
    p.add_argument("--observed-at", dest="observed_at", default="")
    p.add_argument("--metric-id", dest="metric_id", default="")
    p.add_argument("--label", action="append", default=[])
    p.add_argument("--brain", default=DEFAULT_BRAIN)
    p.add_argument("--timeout", type=float, default=5.0)
    args = p.parse_args(argv)
    post(build_metric(args), args.brain, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
