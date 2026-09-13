"""The commerce Rails components had 30 seconds to boot and never made it.

Measured on the live estate 2026-09-13, once the commerce rows were switched on:

    lago-api-7df7476995-dt6q9              0/1   CrashLoopBackOff   93 restarts
    lago-billing-worker-5466fbb9b7-bc8gx   0/1   CrashLoopBackOff   91 restarts
    lago-clock-worker-7cdbd8f85-n9z2w      0/1   CrashLoopBackOff   91 restarts
    commerce/lago: InstallFailed -- Deployment/commerce/lago-api status: 'Failed'

and events:

    Warning  Unhealthy  Readiness probe failed: dial tcp :3000: connect: connection refused
    Warning  Unhealthy  Liveness probe failed:  dial tcp :3000: connect: connection refused
    Normal   Killing    Container lago-api failed liveness probe, will be restarted

The chart's liveness probe carries no `initialDelaySeconds` and there is no
`startupProbe`: 3 failures x 10s gives `bundle exec` 30 seconds to boot a Rails
app on a cold image. The kubelet killed every boot, forever, and `Failed` on the
HelmRelease is what held the whole commerce Kustomization out.

The database was never the problem -- the app's own DATABASE_URL authenticated
against estate-rw and `select 1` answered -- which is exactly why the logs showed
only the meilisearch warning: Rails buffers in production and the process was
SIGKILLed before it could say what was wrong.

WHAT IS GRADED HERE. The postRenderer patch, out of the manifest itself: every
Rails Deployment that CrashLooped must carry a startupProbe, and it must be a
`tcpSocket` rather than an HTTP path, because Sidekiq serves no HTTP and a path
probe could never pass for the worker components. The fix is the same one
langfuse carries, for the same reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "platform" / "commerce" / "app" / "lago.yaml"

# The components that were measured CrashLoopBackOff. Every one of them runs Rails
# or Sidekiq and needs a boot window; lago-clock and lago-front are excluded because
# lago-clock was Running and lago-front is nginx.
RAILS_COMPONENTS = [
    "lago-api",
    "lago-worker",
    "lago-clock-worker",
    "lago-billing-worker",
    "lago-webhook-worker",
    "lago-payment-worker",
]


@pytest.fixture(scope="module")
def postrender_patches() -> list[dict]:
    """Every postRenderer patch in the lago HelmRelease, as (target, patch text)."""
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    hr = next(d for d in docs if d.get("kind") == "HelmRelease")
    out = []
    for renderer in hr["spec"].get("postRenderers") or []:
        for patch in (renderer.get("kustomize") or {}).get("patches", []):
            target = patch.get("target") or {}
            body = patch.get("patch") or ""
            out.append(
                {"kind": target.get("kind"), "name": target.get("name"), "body": body}
            )
    return out


def _probe_body(postrender_patches: list[dict], name: str) -> str:
    for p in postrender_patches:
        if (
            p["kind"] == "Deployment"
            and p["name"] == name
            and "startupProbe" in p["body"]
        ):
            return p["body"]
    return ""


# --- the fix ----------------------------------------------------------------


@pytest.mark.parametrize("component", RAILS_COMPONENTS)
def test_every_rails_component_gets_a_startup_probe(
    postrender_patches, component
) -> None:
    """Liveness does not run until startup passes, so boot gets 300 seconds."""
    body = _probe_body(postrender_patches, component)
    assert body, (
        f"{component} has no startupProbe patch. The chart's liveness probe gives it 30 seconds "
        f"to boot (3 failures x 10s) and `bundle exec` does not boot in 30, so the kubelet kills "
        f"every boot and the HelmRelease reports Failed forever."
    )
    assert "startupProbe" in body


@pytest.mark.parametrize("component", RAILS_COMPONENTS)
def test_the_startup_probe_allows_a_real_boot_window(
    postrender_patches, component
) -> None:
    """30 periods x 10s = 300 seconds, the same window langfuse uses."""
    body = _probe_body(postrender_patches, component)
    doc = yaml.safe_load(body)
    probe = doc[-1]["value"]
    window = probe["periodSeconds"] * probe["failureThreshold"]
    assert window >= 300, (
        f"{component}'s boot window is {window}s. langfuse carries 300s for a slower process than "
        f"this one; anything less risks killing a cold boot on a loaded node."
    )


@pytest.mark.parametrize("component", RAILS_COMPONENTS)
def test_the_startup_probe_is_a_socket_check_not_an_http_path(
    postrender_patches, component
) -> None:
    """Sidekiq serves no HTTP, so a path probe could never pass for the workers.

    This is the detail that makes the fix work for all six rather than just the api:
    three of these components are Sidekiq and answer nothing on /health.
    """
    body = _probe_body(postrender_patches, component)
    doc = yaml.safe_load(body)
    probe = doc[-1]["value"]
    assert "tcpSocket" in probe, (
        f"{component} probes {probe.get('httpGet')} -- a Sidekiq worker serves no HTTP and would "
        f"never pass an HTTP startup probe. Use tcpSocket on the container port."
    )
    assert "httpGet" not in probe


# --- what must NOT change ---------------------------------------------------


def test_the_api_keeps_its_health_endpoint_so_kubernetes_still_restarts_a_wedged_process(
    postrender_patches,
) -> None:
    """The startup probe is a gate, not a replacement.

    Removing the chart's liveness probe would trade a boot failure for a process
    that hangs forever and is never restarted -- a worse defect than the one fixed.
    """
    assert not any(
        p["kind"] == "Deployment"
        and "livenessProbe" in p["body"]
        and "remove" in p["body"]
        for p in postrender_patches
    ), "the liveness probe must stay; the startupProbe only gates it"


def test_no_patch_targets_a_component_this_chart_disables(postrender_patches) -> None:
    """`lago-pdf` and `lago-events-worker` render at zero replicas by design.

    A patch targeting them would either fail the render or resurrect a component
    the manifest deliberately removes.
    """
    disabled = {"lago-pdf", "lago-events-worker"}
    assert not any(
        p["name"] in disabled and "startupProbe" in p["body"]
        for p in postrender_patches
    ), "no startup probe belongs on a component this manifest removes or scales to zero"
