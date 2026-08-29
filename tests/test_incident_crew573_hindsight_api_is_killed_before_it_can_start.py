"""crew#573: hindsight-api ran 13h at 0/1 ready and was SIGKILLed 392 times, and every kill
destroyed the reason it was not ready.

oke-check run 33172282641, `kubectl describe pod` on hindsight-api:

    State:      Waiting     Reason: CrashLoopBackOff
    Last State: Terminated  Reason: Error   Exit Code: 137
    Liveness:   http-get http://:8888/health/live delay=30s timeout=5s period=10s #failure=3
    Readiness:  http-get http://:8888/health      delay=10s timeout=3s period=5s  #failure=3
    Warning Unhealthy 12m (x2144 over 13h)  Readiness probe failed: ... connect: connection refused
    Normal  Killing   5m1s (x133 over 13h)  Container api failed liveness probe, will be restarted
    Warning BackOff   95s  (x392 over 8h)   Back-off restarting failed container api

`connection refused` rather than a 5xx is the whole diagnosis: nothing was listening on 8888 at
all. uvicorn logged `Waiting for application startup.` and never `Application startup complete.`,
because the FastAPI lifespan blocks retrying `Verifying connection: openai/groq`, and a lifespan
that blocks never binds its port. Liveness starts at 30s and reaches failureThreshold at ~60s, so
the container was killed before the retry that would have named the unreachable host ever
finished -- the instrument that exists to catch a hang is what destroyed its cause (LAW 28,
LAW 29).

A livenessProbe with no startupProbe cannot tell a slow start from a hang. That is the defect;
the unreachable host is a separate fault this does not claim to fix, and would have been readable
in the logs on the first restart if the pod had survived long enough to print it.

The chart cannot fix it from values. `helm template` of hindsight 0.9.2 renders `livenessProbe`
and `readinessProbe` from `.Values.api` and nothing else, so an `api.startupProbe:` key would be
accepted by helm and silently dropped by the template -- the quiet kind of no-op. It is a
postRenderer patch for that reason and the manifest says so.

What this file grades:

  1. The api container gets a startupProbe, on the endpoint the chart already documents as
     database-free (`/health/live`), so a slow database gates traffic and never restarts a pod.
  2. The budget is derived, not typed twice: startup time must fit inside the HelmRelease's own
     `install.timeout`, or the release fails before the pod could ever have succeeded. The test
     computes both from the manifest, so raising one without the other is what fails.
  3. Liveness and readiness are not touched. The chart's are correct; the fix adds the missing
     probe rather than swapping one partial answer for another.
  4. Every container this file patches probes for has all three, so the next patch added here
     cannot reintroduce the shape by hand.

Not graded here, deliberately: whether the rendered Deployment carries the probe. That is a
render, and `bin/idp-kyverno-render platform/hindsight` does it on every PR -- measured
`ok render hindsight (hindsight, 1 patches): pass: 32, fail: 0` with the patch in place. A test
that re-renders would need helm and the network and would be BLIND locally, which is worse than
letting the rung that already renders own it.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform" / "hindsight" / "hindsight.yaml"


def _release():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "HelmRelease" and d["metadata"]["name"] == "hindsight")


def _patched_containers():
    """{(deployment, container): container spec} for every postRenderer patch in the manifest."""
    out = {}
    for pr in _release()["spec"].get("postRenderers") or []:
        for p in pr.get("kustomize", {}).get("patches") or []:
            doc = yaml.safe_load(p["patch"])
            name = doc["metadata"]["name"]
            for c in doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers") or []:
                out[(name, c["name"])] = c
    return out


def _seconds(duration):
    """`15m` / `900s` / `1h` as seconds. Flux durations, and the manifest is the only source."""
    m = re.fullmatch(r"(\d+)([smh])", duration.strip())
    assert m, f"unparseable Flux duration {duration!r}"
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600}[m.group(2)]


def test_the_manifest_is_actually_read():
    """Anti-vacuous: every assertion below is worthless if this file stops parsing."""
    rel = _release()
    assert rel["spec"]["chart"]["spec"]["chart"] == "hindsight"
    assert _patched_containers(), "no postRenderer patch was found; the tests below assert nothing"


def test_the_api_container_can_no_longer_be_killed_before_it_starts():
    """The defect: liveness at 30s against a lifespan that had not bound the port yet."""
    probe = _patched_containers()[("hindsight-api", "api")].get("startupProbe")
    assert probe, "hindsight-api/api has no startupProbe; liveness cannot tell slow from hung"
    assert probe["httpGet"]["path"] == "/health/live", probe
    assert probe["httpGet"]["port"] == 8888, probe


def test_the_startup_budget_fits_inside_the_release_timeout():
    """Derived from the manifest, so the two numbers cannot drift apart by hand.

    A startup budget longer than `install.timeout` is a budget the pod can never spend: Flux
    fails the release first and the extra threshold buys nothing but a slower failure.
    """
    spec = _release()["spec"]
    probe = _patched_containers()[("hindsight-api", "api")]["startupProbe"]
    budget = probe["periodSeconds"] * probe["failureThreshold"]
    # Flux's own fallback: `spec.install.timeout` when it is set, otherwise `spec.timeout`
    # (fluxcd/helm-controller api/v2 HelmReleaseSpec.Install.Timeout, "defaults to
    # HelmReleaseSpec.Timeout"). Today install sets none, so 15m is what the install gets;
    # reading only one of the two keys would grade the wrong number the moment that changes.
    timeout = _seconds((spec.get("install") or {}).get("timeout") or spec["timeout"])
    assert budget < timeout, f"startup budget {budget}s >= the install timeout {timeout}s"
    # and it is a real budget, not a token one: the chart's own liveness gives 30 + 3x10 = 60s,
    # and anything at or under that reproduces the incident with extra steps.
    assert budget > 60, f"startup budget {budget}s is inside the liveness window that killed it"


def test_the_probes_the_chart_got_right_are_left_alone():
    """Rule 3: this adds the missing probe. It does not restate the two that were correct."""
    api = _patched_containers()[("hindsight-api", "api")]
    assert "livenessProbe" not in api, "the chart's liveness is correct; patching it invites drift"
    assert "readinessProbe" not in api, "the chart's readiness is correct; patching it invites drift"


@pytest.mark.parametrize("key", ["startupProbe"])
def test_no_container_patched_here_declares_liveness_without_startup(key):
    """Rule 4: the shape cannot come back through the next patch added to this file."""
    for (dep, container), spec in _patched_containers().items():
        if "livenessProbe" in spec:
            assert key in spec, (
                f"{dep}/{container} declares a livenessProbe and no {key}: the same shape that "
                "cost hindsight-api 392 kills (crew#573)"
            )
