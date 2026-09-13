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
import shutil
import subprocess
import tempfile

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


def apply_startup_patch(component: str, patches: list[dict]) -> dict:
    """APPLY the manifest's own patch, the way Flux does, and return the result.

    This is the difference between grading the file and grading the behaviour. A
    test that regexes the patch text passes when someone reformats it and fails
    when someone reorders it, while saying nothing about whether the patch
    produces a working probe.

    `kustomize build` is run for real, over a tree this function writes: the
    chart's own Deployment shape, then the manifest's patch, applied by the same
    binary the estate's postRenderers use. `subprocess` is not incidental here --
    it is the point: the assertions read what kustomize produced, not what this
    file believes it would produce.
    """
    body = _probe_body(patches, component)
    if not body:
        raise AssertionError(f"{component} has no startupProbe patch to apply")

    # A real kustomize tree: the Deployment the chart renders (a container with the
    # component's name and nothing else enforced), and the manifest's patch beside
    # it. kustomize applies the JSON-Patch operations, exactly as Flux's
    # postRenderer does before the object reaches the cluster.
    work = Path(tempfile.mkdtemp(prefix=f"lago-{component}-"))
    try:
        (work / "deployment.yaml").write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": component, "namespace": "commerce"},
                    "spec": {
                        "template": {"spec": {"containers": [{"name": component}]}}
                    },
                }
            )
        )
        (work / "patch.yaml").write_text(body)
        (work / "kustomization.yaml").write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "kustomize.config.k8s.io/v1beta1",
                    "kind": "Kustomization",
                    "resources": ["deployment.yaml"],
                    "patches": [
                        {
                            "target": {"kind": "Deployment", "name": component},
                            "patch": body,
                        }
                    ],
                }
            )
        )
        r = subprocess.run(
            ["kubectl", "kustomize", str(work)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert r.returncode == 0, (
            f"the {component} startupProbe patch does not apply: {r.stderr[:400]}"
        )
        doc = next(
            d
            for d in yaml.safe_load_all(r.stdout)
            if d and d.get("kind") == "Deployment"
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    return doc


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
    """The applied patch puts a startupProbe on the container.

    Liveness does not run until startup passes, so boot gets 300 seconds.
    """
    doc = apply_startup_patch(component, postrender_patches)
    container = doc["spec"]["template"]["spec"]["containers"][0]
    assert "startupProbe" in container, (
        f"{component} has no startupProbe after applying its patch. The chart's liveness "
        f"probe gives it 30 seconds to boot (3 failures x 10s) and `bundle exec` does not "
        f"boot in 30, so the kubelet kills every boot and the HelmRelease reports Failed."
    )


@pytest.mark.parametrize("component", RAILS_COMPONENTS)
def test_the_startup_probe_allows_a_real_boot_window(
    postrender_patches, component
) -> None:
    """30 periods x 10s = 300 seconds, the same window langfuse uses."""
    probe = apply_startup_patch(component, postrender_patches)["spec"]["template"][
        "spec"
    ]["containers"][0]["startupProbe"]
    window = probe["periodSeconds"] * probe["failureThreshold"]
    assert window >= 300, (
        f"{component}'s boot window is {window}s. langfuse carries 300s for a slower process "
        f"than this one; anything less risks killing a cold boot on a loaded node."
    )


@pytest.mark.parametrize("component", RAILS_COMPONENTS)
def test_the_startup_probe_is_a_socket_check_not_an_http_path(
    postrender_patches, component
) -> None:
    """Sidekiq serves no HTTP, so a path probe could never pass for the workers.

    This is the detail that makes the fix work for all six rather than just the api:
    three of these components are Sidekiq and answer nothing on /health.
    """
    probe = apply_startup_patch(component, postrender_patches)["spec"]["template"][
        "spec"
    ]["containers"][0]["startupProbe"]
    assert "tcpSocket" in probe, (
        f"{component} probes {probe.get('httpGet')} -- a Sidekiq worker serves no HTTP and "
        f"would never pass an HTTP startup probe. Use tcpSocket on the container port."
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
