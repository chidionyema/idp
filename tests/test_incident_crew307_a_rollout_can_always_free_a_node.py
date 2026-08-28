"""crew#307, 2026-08-28. The cluster admitted an impossible arithmetic and said nothing.

catalogue carried `maxSurge: 1, maxUnavailable: 0` beside a required podAntiAffinity on
`kubernetes.io/hostname` at `replicas: 2`, on a two-node pool. A surge asks the scheduler for a
THIRD pod before any old one is deleted; hard hostname anti-affinity forbids placing it beside
either existing replica; `maxUnavailable: 0` forbids freeing one first. There is no legal move,
so catalogue-8647bbdc59-kjc9j sat `Pending` with node `<none>` -- and because the old ReplicaSet
is never touched at maxUnavailable 0, the site answered 200 while serving a seventeen-hour-old
portal. Flux said `timeout waiting for: [Deployment/backstage/catalogue status: 'InProgress']`
(oke-check run 33161593926; login-drill 33161396123 and 33161592024 both drew 0 of 15 surfaces).

idp#564 (c6e6026) fixed the manifest. This file is the other half the founder asked for: the
cluster itself refuses the shape at admission, so no PR, no review and no agent stands between
the bad arithmetic and its rejection. The rule lives beside the rule that CAUSED the exposure --
`founder-facing-spreads-across-nodes` mandates the hard hostname anti-affinity and never said
what update strategy such a Deployment then needs.

Every assertion here runs the real `kyverno apply` CLI against the real policy file. Nothing is
graded by reading YAML.
"""
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform" / "scheduling" / "require-availability.yaml"
FIXTURES = ROOT / "tests" / "fixtures" / "kyverno-rollout"
RULE = "a-rollout-can-always-free-a-node"

if subprocess.run(["which", "kyverno"], capture_output=True).returncode != 0:
    pytest.skip("kyverno CLI is not installed", allow_module_level=True)


def _apply(resource: Path):
    out = subprocess.run(["kyverno", "apply", str(POLICY), "--resource", str(resource)],
                         capture_output=True, text=True, timeout=180)
    assert "panic" not in out.stdout + out.stderr, out.stdout + out.stderr
    tally = {}
    for line in out.stdout.splitlines():
        if line.startswith("pass:"):
            tally = {k.strip(): int(v) for k, v in
                     (p.split(":") for p in line.split(","))}
    assert tally, f"kyverno printed no tally:\n{out.stdout}\n{out.stderr}"
    return tally, out.stdout


BAD = sorted(FIXTURES.glob("*.bad.yaml"))
GOOD = sorted(FIXTURES.glob("*.good.yaml"))


def test_the_fixtures_exist():
    """A parametrised test over an empty glob is a green test that grades nothing."""
    assert len(BAD) >= 3 and len(GOOD) >= 4, (BAD, GOOD)


@pytest.mark.parametrize("fixture", BAD, ids=lambda p: p.name)
def test_the_deadlocked_shape_is_refused(fixture):
    tally, stdout = _apply(fixture)
    assert tally["fail"] == 1, f"{fixture.name} was admitted:\n{stdout}"
    assert tally["error"] == 0, stdout


@pytest.mark.parametrize("fixture", GOOD, ids=lambda p: p.name)
def test_a_rollout_that_can_complete_is_admitted(fixture):
    """LAW 38: a guard that refuses correct work is an outage. `skip` is the correct verdict for
    a Deployment the preconditions put out of scope -- what must never appear is `fail`."""
    tally, stdout = _apply(fixture)
    assert tally["fail"] == 0, f"{fixture.name} was refused:\n{stdout}"
    assert tally["error"] == 0, stdout


def test_unset_is_refused_and_not_only_a_literal_zero():
    """The reason this policy is not a one-line pattern match. apps/v1 defaults maxUnavailable
    AND maxSurge to 25%; ResolveFenceposts rounds maxUnavailable DOWN and maxSurge UP, so at
    replicas 2 the default IS (0, 1) -- the incident, written by typing nothing."""
    tally, stdout = _apply(FIXTURES / "deployment-no-strategy-at-all.bad.yaml")
    assert tally["fail"] == 1, stdout


def test_the_estate_as_it_stands_today_is_admitted(tmp_path):
    """The live rendered overlay, not a fixture. If this ever fails, the policy is refusing
    something the cluster is already running and it is the policy that is wrong."""
    if subprocess.run(["which", "kustomize"], capture_output=True).returncode != 0:
        pytest.skip("kustomize is not installed")
    built = subprocess.run(["kustomize", "build", "platform/backstage/overlays/oke"],
                           cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert built.returncode == 0, built.stderr
    deployments = [d for d in yaml.safe_load_all(built.stdout)
                   if d and d.get("kind") == "Deployment"]
    assert deployments, "the oke overlay rendered no Deployment at all"
    resource = tmp_path / "oke-deployments.yaml"
    resource.write_text(yaml.safe_dump_all(deployments))
    tally, stdout = _apply(resource)
    assert tally["fail"] == 0, stdout
    assert tally["pass"] >= 1, f"nothing was graded, only skipped:\n{stdout}"


def test_the_rule_is_enforced_not_audited():
    """Audit would have printed a line into a report nobody reads while the portal stayed stale
    (LAW 28). The founder's instruction on 2026-08-28 was one word: enforce it."""
    policy = yaml.safe_load(POLICY.read_text())
    rule = next(r for r in policy["spec"]["rules"] if r["name"] == RULE)
    assert rule["validate"]["failureAction"] == "Enforce"
    assert policy["spec"].get("validationFailureAction") != "Audit"


def test_the_rule_is_in_the_kustomization_the_cluster_reconciles():
    """A policy file no Kustomization lists is a file, not an admission controller."""
    k = yaml.safe_load((ROOT / "platform" / "scheduling" / "kustomization.yaml").read_text())
    assert "require-availability.yaml" in k["resources"]
