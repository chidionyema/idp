"""crew#307, 2026-08-28. A Deployment that could never roll, and never said so.

The catalogue Deployment carried `maxSurge: 1, maxUnavailable: 0` together with a
`requiredDuringSchedulingIgnoredDuringExecution` podAntiAffinity on `kubernetes.io/hostname`
and `replicas: 2`, on a node pool with two nodes. A surge asks the scheduler for a THIRD pod
before any old one is deleted, and hard hostname anti-affinity forbids putting it beside either
existing replica, so there was no node for it: pod catalogue-8647bbdc59-kjc9j sat `Pending` with
node `<none>` while the two old pods kept serving. `maxUnavailable: 0` is what makes it silent --
the old ReplicaSet is never touched, so the site answers 200 and the outage is invisible from
outside. Flux said `timeout waiting for: [Deployment/backstage/catalogue status: 'InProgress']`
(oke-check run 33161593926, login-drill runs 33161396123 and 33161592024).

The class, not the instance: any pod template whose anti-affinity is *required* on the node
hostname cannot surge, because a surge needs a node no other replica occupies and nothing in the
manifest can promise one. Such a Deployment must be able to give a pod back before it takes one,
so `maxUnavailable` has to be at least 1. Every rendered overlay is walked, so the shape cannot
be written anywhere else either.
"""
import subprocess
import shutil
import pathlib
import yaml
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAYS = sorted(p.parent for p in ROOT.glob("platform/*/overlays/*/kustomization.yaml"))
HOSTNAME_KEYS = ("kubernetes.io/hostname",)

pytestmark = pytest.mark.skipif(
    shutil.which("kubectl") is None,
    reason="kubectl renders the overlays; ubuntu-latest ships it and CI must never skip this",
)


def _render(overlay):
    out = subprocess.run(["kubectl", "kustomize", str(overlay)], capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip(f"{overlay.relative_to(ROOT)} does not render here: {out.stderr.strip()[:200]}")
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def _deadlocked(deployment) -> bool:
    """True when this Deployment can never complete a rollout. The whole rule, in one place,
    so the incident shape itself can be fed to it below and not only the live overlays."""
    spec = deployment["spec"]
    if not _requires_its_own_node(spec.get("template", {}).get("spec", {})):
        return False
    rolling = (spec.get("strategy") or {}).get("rollingUpdate") or {}
    return rolling.get("maxUnavailable", 1) in (0, "0", "0%")


def _requires_its_own_node(spec) -> bool:
    anti = ((spec.get("affinity") or {}).get("podAntiAffinity") or {})
    rules = anti.get("requiredDuringSchedulingIgnoredDuringExecution") or []
    return any(r.get("topologyKey") in HOSTNAME_KEYS for r in rules)


def test_at_least_one_overlay_rendered():
    """A guard that skips everything is not a guard (crew#539: BLIND is never a pass)."""
    assert OVERLAYS, "no platform overlay found to render"


@pytest.mark.parametrize("overlay", OVERLAYS, ids=lambda p: str(p.relative_to(ROOT)))
def test_a_deployment_pinned_to_its_own_node_can_still_roll(overlay):
    for d in _render(overlay):
        if d.get("kind") != "Deployment":
            continue
        rolling = (d["spec"].get("strategy") or {}).get("rollingUpdate") or {}
        unavailable = rolling.get("maxUnavailable", "unset")
        assert not _deadlocked(d), (
            f"Deployment/{d['metadata']['name']} in {overlay.relative_to(ROOT)} requires its own "
            f"node (podAntiAffinity required on kubernetes.io/hostname) and sets maxUnavailable "
            f"{unavailable!r}. A surge then needs a node no replica occupies, which no manifest "
            f"can promise: the new pod stays Pending for ever and the old ReplicaSet keeps "
            f"serving, so the stall is invisible. Set maxUnavailable to at least 1 and maxSurge "
            f"to 0 so a node is freed before it is needed (crew#307)."
        )


INCIDENT = yaml.safe_load("""
apiVersion: apps/v1
kind: Deployment
metadata: {name: catalogue, namespace: backstage}
spec:
  replicas: 2
  strategy: {type: RollingUpdate, rollingUpdate: {maxSurge: 1, maxUnavailable: 0}}
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - topologyKey: kubernetes.io/hostname
              labelSelector: {matchLabels: {app: catalogue}}
""")


def test_the_shape_that_broke_the_portal_is_refused():
    """The manifest exactly as it stood at 2026-08-28T09:00Z, when catalogue-8647bbdc59-kjc9j
    sat Pending with node <none>. Without this the guard could pass by covering nothing."""
    assert _deadlocked(INCIDENT) is True


def test_the_fix_is_accepted():
    fixed = yaml.safe_load(yaml.safe_dump(INCIDENT))
    fixed["spec"]["strategy"]["rollingUpdate"] = {"maxSurge": 0, "maxUnavailable": 1}
    assert _deadlocked(fixed) is False


def test_a_deployment_without_hard_hostname_anti_affinity_may_surge():
    """maxUnavailable: 0 is a good default and stays legal -- it is only the combination that
    deadlocks. A guard that refuses correct work is an outage (LAW 38)."""
    soft = yaml.safe_load(yaml.safe_dump(INCIDENT))
    soft["spec"]["template"]["spec"]["affinity"]["podAntiAffinity"] = {
        "preferredDuringSchedulingIgnoredDuringExecution": [
            {"weight": 100, "podAffinityTerm": {"topologyKey": "kubernetes.io/hostname"}}]}
    assert _deadlocked(soft) is False

    zonal = yaml.safe_load(yaml.safe_dump(INCIDENT))
    zonal["spec"]["template"]["spec"]["affinity"]["podAntiAffinity"][
        "requiredDuringSchedulingIgnoredDuringExecution"][0]["topologyKey"] = "topology.kubernetes.io/zone"
    assert _deadlocked(zonal) is False
