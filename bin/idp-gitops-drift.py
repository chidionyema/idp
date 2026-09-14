#!/usr/bin/env python3
"""Read the estate's drift from the cluster and carry it to its cause.

Spec: docs/specs/2026-09-13-gitops-sync-engine.md

This is the CLI half of the sensor. It loads the module the tests grade
(`scheduler/estate_scheduler/gitops_sync.py`) and drives it, so the loader, the
attribution and the exit verdict are the SAME code whether they run from Dagster
or from a shell -- a second implementation for the command line is how a gate and
a sensor start disagreeing.

    bin/idp-gitops-drift                 every drift, with its pull request
    bin/idp-gitops-drift --json | jq .summary
    bin/idp-gitops-drift --notify        deliver through apprise

Exit codes are the contract:

    0   a real reading, and nothing a person needs to act on
    1   a real reading, with at least one drift naming a pull request
    2   BLIND -- kubectl is missing, or a list could not be read

2 exists because 0 does not mean the same thing as "could not look". That is the
2026-09-08 defect: bin/idp-compile-helm exited 0 while eleven of thirty-three
charts failed to render, so an estate that could not be seen reported as an empty
one. bin/idp-drift-blind grades this file's exit code for it and refused the first
version, which wrote BLIND to stderr alone.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

BLIND = "BLIND gitops-drift"


def load_module(root: Path):
    path = root / "scheduler" / "estate_scheduler" / "gitops_sync.py"
    spec = importlib.util.spec_from_file_location("gitops_sync", path)
    if spec is None or spec.loader is None:  # pragma: no cover -- import failure
        raise SystemExit(f"{BLIND}: cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gitops_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


def kubectl_items(args: list[str], timeout: int) -> list:
    """One `kubectl ... -o json` read. BLIND on every failure path.

    Raising rather than returning [] is the whole point: an empty list means the
    estate was read and is clean, and a failed read must never be able to say that.
    """
    try:
        r = subprocess.run(
            ["kubectl", *args], capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            f"{BLIND}: kubectl {' '.join(args)} could not run: {exc}"
        ) from exc
    if r.returncode != 0:
        raise SystemExit(
            f"{BLIND}: {' '.join(args)} exited {r.returncode}: {(r.stderr or '')[:300]}"
        )
    try:
        doc = json.loads(r.stdout or "{}")
    except ValueError as exc:
        raise SystemExit(
            f"{BLIND}: {' '.join(args)} answered with no JSON: {exc}"
        ) from exc
    items = doc.get("items")
    return items if isinstance(items, list) else []


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="idp-gitops-drift", add_help=True)
    ap.add_argument("--json", action="store_true", help="print the whole payload")
    ap.add_argument("--notify", action="store_true", help="deliver through apprise")
    ap.add_argument(
        "--namespace", default="", help="read Kustomizations in one namespace"
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("ESTATE_GITOPS_KUBECTL_TIMEOUT_SECONDS", "60")),
    )
    args = ap.parse_args(argv)

    root = Path(
        os.environ.get("IDP_GITOPS_ROOT") or Path(__file__).resolve().parents[1]
    ).resolve()
    sync = load_module(root)

    kust_scope = ["-n", args.namespace] if args.namespace else ["-A"]
    objects = [
        *kubectl_items(
            ["get", "kustomizations", *kust_scope, "-o", "json"], args.timeout
        ),
        *kubectl_items(["get", "helmreleases", "-A", "-o", "json"], args.timeout),
    ]

    payload = sync.drift_payload(objects)
    summary = payload["summary"]

    if args.json:
        print(json.dumps(payload, indent=2))

    if args.notify:
        # Delivery is best-effort per group: a notify service that is down is a
        # reason a message was not sent, and never a reason to lose the finding.
        for pr, drifts in sorted(sync.group_by_pull_request(payload["drifts"]).items()):
            if not pr:
                continue
            try:
                sync.publish(
                    f"{sync.SENDER}: drift on #{pr}", sync.comment_body(pr, drifts)
                )
            except Exception as exc:  # noqa: BLE001 -- one unreachable sink must not lose the finding
                print(f"warn  delivery to #{pr} failed: {exc}", file=sys.stderr)

    if not args.json:
        print(
            f"ok    gitops-drift {summary['drifts']} drift(s): "
            f"{summary['attributed']} attributed to a pull request, "
            f"{summary['unattributed']} unattributed"
        )
        for drift in payload["drifts"]:
            pr = drift.get("pull_request")
            where = f"#{pr}" if pr else "unattributed"
            print(
                f"      {drift['object']} ({drift['kind']}) -> {where}: "
                f"{drift['reason'][:110]}"
            )

    # 1 when a drift names a pull request: a drift with a named cause is something
    # a person can act on. A drift the estate cannot file is still reported above
    # and is not actionable, so it does not set the code.
    return 1 if summary["attributed"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
