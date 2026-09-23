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
so its EFFECTIVE `maxUnavailable` has to be at least 1. Every rendered overlay is walked, so the
shape cannot be written anywhere else either.

Effective, not literal, and that distinction is this guard's own incident. The first version of
this file read `rolling.get("maxUnavailable", 1)`, so a Deployment that simply omits `strategy`
graded safe. Kubernetes does not default it to 1: `maxUnavailable` and `maxSurge` both default to
`25%`, and ResolveFenceposts rounds maxUnavailable DOWN and maxSurge UP. At `replicas: 2` that is
maxUnavailable 0, maxSurge 1 -- the deadlocked shape exactly, arrived at by writing nothing at
all. The default IS the bug, so the next Deployment written the ordinary way would have walked
straight past the guard that was written for this incident (found by session 59cfc4 reviewing
idp#564; it fed the rule a no-strategy manifest and a 25% manifest and both came back False).
"""

import math
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAYS = sorted(
    p.parent for p in ROOT.glob("platform/*/overlays/*/kustomization.yaml")
)
HOSTNAME_KEYS = ("kubernetes.io/hostname",)

# apps/v1 DeploymentSpec defaults, as the API server applies them when the field is absent.
# https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-update-deployment
DEFAULT_MAX_UNAVAILABLE = "25%"
DEFAULT_MAX_SURGE = "25%"
DEFAULT_REPLICAS = 1

pytestmark = pytest.mark.skipif(
    shutil.which("kubectl") is None,
    reason="kubectl renders the overlays; ubuntu-latest ships it and CI must never skip this",
)


def _render(overlay):
    out = subprocess.run(
        ["kubectl", "kustomize", str(overlay)], capture_output=True, text=True
    )
    if out.returncode != 0:
        pytest.skip(
            f"{overlay.relative_to(ROOT)} does not render here: {out.stderr.strip()[:200]}"
        )
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def _scaled(value, replicas: int, *, round_up: bool) -> int:
    """Resolve an IntOrString the way the deployment controller does.

    k8s.io/apimachinery intstr.GetScaledValueFromIntOrPercent, called from
    pkg/controller/deployment/util.ResolveFenceposts: a percentage is taken against the replica
    count, and the caller chooses the rounding -- UP for maxSurge, DOWN for maxUnavailable. The
    asymmetry is the whole reason the default is dangerous at small replica counts.
    """
    if isinstance(value, str) and value.strip().endswith("%"):
        exact = float(value.strip()[:-1]) * replicas / 100.0
        return (
            int(math.ceil(exact - 1e-9)) if round_up else int(math.floor(exact + 1e-9))
        )
    return int(value)


def _effective_fenceposts(spec):
    """(maxUnavailable, maxSurge) as pod counts, or None when the strategy never surges.

    `type: Recreate` is not a rolling update at all: every old pod is deleted before any new one
    is created, so it can always complete, whatever the anti-affinity says.
    """
    strategy = spec.get("strategy") or {}
    if strategy.get("type") == "Recreate":
        return None
    replicas = spec.get("replicas", DEFAULT_REPLICAS)
    rolling = strategy.get("rollingUpdate") or {}
    return (
        _scaled(
            rolling.get("maxUnavailable", DEFAULT_MAX_UNAVAILABLE),
            replicas,
            round_up=False,
        ),
        _scaled(rolling.get("maxSurge", DEFAULT_MAX_SURGE), replicas, round_up=True),
    )


def _requires_its_own_node(spec) -> bool:
    anti = (spec.get("affinity") or {}).get("podAntiAffinity") or {}
    rules = anti.get("requiredDuringSchedulingIgnoredDuringExecution") or []
    return any(r.get("topologyKey") in HOSTNAME_KEYS for r in rules)


def _deadlocked(deployment) -> bool:
    """True when this Deployment can never complete a rollout. The whole rule, in one place,
    so the incident shape itself can be fed to it below and not only the live overlays."""
    spec = deployment["spec"]
    if not _requires_its_own_node(spec.get("template", {}).get("spec", {})):
        return False
    fenceposts = _effective_fenceposts(spec)
    if fenceposts is None:
        return False
    unavailable, _surge = fenceposts
    return unavailable == 0


def test_at_least_one_overlay_was_rendered_and_graded():
    """A guard that skips everything is not a guard (crew#539: BLIND is never a pass).

    This asserts a render happened, not that the glob found directories. The first version
    asserted `OVERLAYS` was non-empty, which is true on any checkout and stays true when every
    single overlay refuses to render -- a test that could not fail for the reason it is named.
    """
    rendered, refused = [], []
    for overlay in OVERLAYS:
        out = subprocess.run(
            ["kubectl", "kustomize", str(overlay)], capture_output=True, text=True
        )
        name = str(overlay.relative_to(ROOT))
        (rendered if out.returncode == 0 else refused).append(
            name
            if out.returncode == 0
            else f"{name}: {out.stderr.strip().splitlines()[-1][:120]}"
        )
    assert rendered, (
        "no platform overlay rendered, so this guard graded nothing at all. Refused:\n  "
        + "\n  ".join(refused or ["(no overlay found by the glob either)"])
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


def _variant(**spec_changes):
    d = yaml.safe_load(yaml.safe_dump(INCIDENT))
    d["spec"].update(spec_changes)
    return d


def test_the_shape_that_broke_the_portal_is_refused():
    """The manifest exactly as it stood at 2026-08-28T09:00Z, when catalogue-8647bbdc59-kjc9j
    sat Pending with node <none>. Without this the guard could pass by covering nothing."""
    assert _deadlocked(INCIDENT) is True


def test_the_fix_is_accepted():
    assert (
        _deadlocked(
            _variant(
                strategy={
                    "type": "RollingUpdate",
                    "rollingUpdate": {"maxSurge": 0, "maxUnavailable": 1},
                }
            )
        )
        is False
    )


def test_writing_no_strategy_at_all_is_the_same_bug():
    """The hole session 59cfc4 found in the first version of this guard. Omitting `strategy`
    does not mean `maxUnavailable: 1`: it means 25% of 2 rounded down, which is 0, beside 25%
    of 2 rounded up, which is 1 -- the incident, reached by writing nothing."""
    bare = yaml.safe_load(yaml.safe_dump(INCIDENT))
    del bare["spec"]["strategy"]
    assert _deadlocked(bare) is True
    assert _effective_fenceposts(bare["spec"]) == (0, 1)

    spelled_out = _variant(
        strategy={
            "type": "RollingUpdate",
            "rollingUpdate": {"maxSurge": "25%", "maxUnavailable": "25%"},
        }
    )
    assert _deadlocked(spelled_out) is True


def test_the_fenceposts_round_the_way_the_controller_rounds():
    """maxUnavailable DOWN, maxSurge UP. If these two ever agree, the rule above is wrong."""
    assert _scaled("25%", 2, round_up=False) == 0
    assert _scaled("25%", 2, round_up=True) == 1
    assert _scaled("25%", 4, round_up=False) == 1
    assert _scaled("50%", 3, round_up=False) == 1
    assert _scaled("50%", 3, round_up=True) == 2
    assert _scaled(0, 2, round_up=False) == 0
    assert _scaled("100%", 2, round_up=False) == 2


def test_more_replicas_than_nodes_worth_of_rounding_is_fine():
    """LAW 38: the guard must not refuse correct work. At replicas 4 the same default 25%
    yields maxUnavailable 1, which can roll, so it stays legal."""
    assert _deadlocked(_variant(replicas=4, strategy={})) is False


def test_recreate_never_surges_so_it_never_deadlocks():
    assert _deadlocked(_variant(strategy={"type": "Recreate"})) is False


def test_a_deployment_without_hard_hostname_anti_affinity_may_surge():
    """maxUnavailable: 0 is a good default and stays legal -- it is only the combination that
    deadlocks. A guard that refuses correct work is an outage (LAW 38)."""
    soft = yaml.safe_load(yaml.safe_dump(INCIDENT))
    soft["spec"]["template"]["spec"]["affinity"]["podAntiAffinity"] = {
        "preferredDuringSchedulingIgnoredDuringExecution": [
            {
                "weight": 100,
                "podAffinityTerm": {"topologyKey": "kubernetes.io/hostname"},
            }
        ]
    }
    assert _deadlocked(soft) is False

    zonal = yaml.safe_load(yaml.safe_dump(INCIDENT))
    zonal["spec"]["template"]["spec"]["affinity"]["podAntiAffinity"][
        "requiredDuringSchedulingIgnoredDuringExecution"
    ][0]["topologyKey"] = "topology.kubernetes.io/zone"
    assert _deadlocked(zonal) is False
