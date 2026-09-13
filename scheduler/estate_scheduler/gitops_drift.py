"""The GitOps drift sensor: the estate carries its drift back to its cause.

Spec: docs/specs/2026-09-13-gitops-sync-engine.md

This is the Dagster half of `scheduler/estate_scheduler/gitops_sync.py`. That
module reads, fingerprints, attributes and renders; this starts it on the
estate's one scheduler (LAW 43, `bin/idp-one-scheduler`) and delivers the result
through `apprise.notify`.

WHY A SENSOR ON THIS SCHEDULER AND NOT A TIMER. `holmes_watch.py` next door is
the standing proof of the shape: a Dagster sensor polls a live source,
fingerprints the situation so one problem is one run however long it burns, and
delivers once through the notify layer. A launchd timer running a shell script
would be a second scheduler, a second delivery path, and a thing with no memory
of what it had already said -- which is exactly the stitching THE HEADLINE names.

WHAT IT DOES NOT DO. It does not repair. Reverting a rollout is `execute_change`
and its graders (MUM-288, decision 0028), where a proposal is made, graded and
expires; a watcher with a revert button has no grader and no expiry.

A BLIND READING IS NOT A QUIET ESTATE. If the cluster cannot be read, the sensor
raises -- it does not return an empty drift list. The two must never print the
same thing: that is the defect `bin/idp-compile-helm` was written to end, where
eleven of thirty-three charts failed to render and the first version exited 0.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SkipReason,
    job,
    op,
    sensor,
)

# The estate's one scheduler runs this with the repo checked out; the module under
# test loads by path (LAW 45: a code location loads the way workspace.yaml loads
# it, by file path, never as a package).
_MODULE = Path(__file__).resolve().parent / "gitops_sync.py"


def _load_sync():
    spec = importlib.util.spec_from_file_location("gitops_sync", _MODULE)
    if spec is None or spec.loader is None:  # pragma: no cover -- import failure
        raise RuntimeError(f"cannot load {_MODULE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gitops_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


sync = _load_sync()

# How often the estate looks. Overridable by environment so this file names no
# machine and no magic interval (LAW 46).
POLL_SECONDS = int(os.environ.get("ESTATE_GITOPS_POLL_SECONDS", "300"))
KUBECTL_TIMEOUT_S = int(os.environ.get("ESTATE_GITOPS_KUBECTL_TIMEOUT_SECONDS", "60"))


def read_flux_objects() -> List[Dict[str, Any]]:
    """Both Flux kinds, read from the cluster. Raises when it cannot read.

    A Kustomization that is not Ready and a HelmRelease that is not Ready are both
    drifts. `kubectl get ... -o json` on a kind that does not exist exits non-zero,
    and that is a blind reading of that kind -- raised, never swallowed into an
    empty list, because "nothing is drifting" and "nothing could be read" must not
    print the same thing.
    """
    out: List[Dict[str, Any]] = []
    for args in (
        ["get", "kustomizations", "-A", "-o", "json"],
        ["get", "helmreleases", "-A", "-o", "json"],
    ):
        try:
            r = subprocess.run(
                ["kubectl", *args],
                capture_output=True,
                text=True,
                timeout=KUBECTL_TIMEOUT_S,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(
                f"kubectl {' '.join(args)} could not run: {exc}"
            ) from exc
        if r.returncode != 0:
            raise RuntimeError(
                f"kubectl {' '.join(args)} exited {r.returncode}: {(r.stderr or '')[:300]}"
            )
        try:
            doc = json.loads(r.stdout or "{}")
        except ValueError as exc:
            raise RuntimeError(
                f"kubectl {' '.join(args)} answered with no JSON: {exc}"
            ) from exc
        items = doc.get("items")
        if isinstance(items, list):
            out.extend(items)
    return out


@op(
    name="report_gitops_drift",
    description=(
        "Reads the cluster's own Flux objects, attributes each drift to the pull request "
        "that last touched the file owning it, and delivers one message per pull request "
        "through apprise. Started by gitops_drift_sensor; a clean estate costs nothing. "
        f"Reads: kubectl get kustomizations,helmreleases -A -o json. Delivers to: "
        f"{sync.APPRISE_URL}/notify/{sync.NOTIFY_CHANNEL}. "
        "Defined in: scheduler/estate_scheduler/gitops_drift.py."
    ),
)
def report_gitops_drift() -> Dict[str, Any]:
    objects = read_flux_objects()
    payload = sync.drift_payload(objects)
    summary = payload["summary"]

    if not summary["drifts"]:
        return summary

    # One message per pull request. A pull request that broke three objects gets
    # one message naming all three; a thread per object turns one cause into three
    # notifications and buries the thing that fixes all of them.
    #
    # DELIVERY IS BEST-EFFORT PER GROUP. The notify service being unreachable is a
    # reason a message was not sent, and it is not a reason to lose the finding: the
    # reading already happened, the counts are already returned, and the Dagster run
    # log holds the whole payload. Letting the exception out would turn a found drift
    # into a failed run that reports nothing -- the same mistake as reading a blind
    # cluster as a clean one.
    for pr, drifts in sorted(sync.group_by_pull_request(payload["drifts"]).items()):
        if not pr:
            continue
        try:
            sync.publish(
                f"{sync.SENDER}: drift on #{pr}", sync.comment_body(pr, drifts)
            )
        except Exception as exc:  # noqa: BLE001 -- one unreachable sink must not lose the finding
            summary.setdefault("delivery_errors", []).append(f"#{pr}: {exc}")
    return summary


@job(
    name="gitops_drift_job",
    description=(
        "Reads the estate's Flux drift and attributes each one to the pull request that "
        "caused it. Started by gitops_drift_sensor, never on a clock."
    ),
    tags={"estate/label": "ai.estate.gitops-drift", "estate/owner": "estate"},
)
def gitops_drift_job():
    report_gitops_drift()


@sensor(
    name="gitops_drift_sensor",
    job=gitops_drift_job,
    minimum_interval_seconds=POLL_SECONDS,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        f"Every {POLL_SECONDS}s, reads the cluster's own Flux objects and delivers each "
        "drift to the pull request that last touched the file owning it. A clean estate "
        "costs nothing and is silent."
    ),
)
def gitops_drift_sensor(context):
    try:
        objects = read_flux_objects()
    except RuntimeError:
        # Fail loudly. A cluster that could not be read is not a clean estate, and
        # the two must never print the same thing.
        raise
    drifts = sync.drifts_from(objects)
    if not drifts:
        return SkipReason("every Flux object the estate runs is reconciled")

    # The fingerprint of the whole set: the same set of drifts is the same
    # situation and is reported once, however long it burns. A new drift joining
    # makes it a new one.
    key = "|".join(sorted(sync.drift_fingerprint(d) for d in drifts))
    context.log.info("%d drift(s), fingerprint %s", len(drifts), key[:16])
    return RunRequest(
        run_key=key[:64],
        tags={"estate/gitops-drift-fingerprint": key[:16]},
    )
