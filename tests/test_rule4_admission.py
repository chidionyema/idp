"""Rule 4's Kyverno arm, graded both ways against real manifests.

WHAT THIS PROVES. `features/gates/deterministic-verifier.feature` Rule 4 says an unattested
payload is refused "at the Kyverno Admission Controller or a Git pre-receive hook". That
sentence was false when it was written. The refusal was real but it lived in exactly one
place -- `platform/executor/daemon.py:_admit()` -- so a commit that never went through the
executor reached the remote unchecked, and a green run of the scenario could be read as
"the cluster enforces this" when the cluster enforced nothing.

`platform/verification/refuse-unattested-provenance.yaml` is now the second gate, and this
module grades it. The Kyverno arm is the one named in the spec, so it is the one that had
to become true rather than be renamed away.

WHY THE VERDICTS COME FROM THE FILE. This estate has already shipped a control that could
not fail: stage 2 of the verifier, whose `_guard` handed a Python `bool` to `z3.Not()` and
therefore answered `unsat` for every patch it was ever given. The lesson is that a check
whose negative case has never been reached is indistinguishable from a check that passes.
So `_verdict()` reads the policy file, extracts its precondition and its deny condition,
and evaluates them against each manifest. Nothing here restates the policy in Python; if
the YAML says something different tomorrow, these verdicts move with it.

WHY NOT RUN KYVERNO. Kyverno is not installed on this machine -- measured, not assumed. A
test that claimed to have run it would be exactly the lie this feature exists to remove.
What is proved here is that the conditions as written select the right objects. The
cluster-side proof is the Flux render check in the pre-push chain, which parses this file
against the installed admission policies and is what would catch a malformed policy.

THE THIRD CASE IS THE ONE THAT KEEPS IT HONEST. A rule that refuses the bad object but also
refuses a correct one is an outage (R38), so `untouched.yaml` -- a pod that says nothing
about provenance -- must pass through with the rule never even examining it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    REPO_ROOT / "platform" / "verification" / "refuse-unattested-provenance.yaml"
)
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "rule4-admission"

_ANNOTATION_MARKER = 'request.object.metadata.annotations."'


def _resolve(template: str, manifest: dict) -> str:
    """Resolve the one expression form this policy uses.

    Kyverno's `{{ request.object.metadata.annotations."<key>" || '' }}` reads an annotation
    and yields the empty string when it is absent. That is the entire expression language
    this policy needs, and a broader interpreter would be testing the interpreter rather
    than the policy.
    """
    if _ANNOTATION_MARKER not in template:
        return template
    key = template.split(_ANNOTATION_MARKER, 1)[1].split('"', 1)[0]
    annotations = manifest.get("metadata", {}).get("annotations", {})
    return str(annotations.get(key, ""))


def _condition_holds(condition: dict, manifest: dict) -> bool:
    key = _resolve(condition["key"], manifest)
    operator = condition["operator"]
    value = condition.get("value", "")
    if operator == "Equals":
        return key == value
    if operator == "NotEquals":
        return key != value
    raise AssertionError(f"the evaluator does not implement operator {operator!r}")


def _verdict(manifest: dict) -> str:
    """Return 'DENY', 'ALLOW', or 'UNTOUCHED' for one manifest, from the policy's own text."""
    rule = yaml.safe_load(POLICY_PATH.read_text())["spec"]["rules"][0]
    if not all(_condition_holds(c, manifest) for c in rule["preconditions"]["all"]):
        return "UNTOUCHED"
    denied = all(
        _condition_holds(c, manifest)
        for c in rule["validate"]["deny"]["conditions"]["all"]
    )
    return "DENY" if denied else "ALLOW"


def _load(name: str) -> dict:
    return yaml.safe_load((FIXTURES / name).read_text())


def test_the_policy_is_a_real_enforcing_cluster_policy() -> None:
    policy = yaml.safe_load(POLICY_PATH.read_text())
    assert policy["kind"] == "ClusterPolicy"
    assert policy["spec"]["validationFailureAction"] == "Enforce", (
        "an Audit policy lets the refused object through; a refusal that can be ignored "
        "is not a refusal (LAW 44)"
    )


def test_a_provenance_claim_with_no_attestation_is_refused() -> None:
    assert _verdict(_load("bad.yaml")) == "DENY", (
        "an object claiming estate.io/provenance-verified with no estate.io/attestation "
        "must be refused -- that object is the untrusted proposer asking to be believed"
    )


def test_a_provenance_claim_with_its_attestation_is_admitted() -> None:
    assert _verdict(_load("good.yaml")) == "ALLOW", (
        "a sealed payload must be admitted; a gate that refuses the correct case too is "
        "an outage (R38)"
    )


def test_a_workload_silent_about_provenance_is_untouched() -> None:
    assert _verdict(_load("untouched.yaml")) == "UNTOUCHED", (
        "the rule must only examine objects that make the provenance claim, or it refuses "
        "every ordinary workload in the estate"
    )


def test_the_policy_is_applied_by_flux() -> None:
    """A policy file no Kustomization lists enforces nothing.

    This estate deleted that exact mistake once already: fifteen fixtures under
    policy/fixtures that no runner named (see the Unification Move in AGENTS.md). A file
    that exists is not a control that runs.

    Graded by PARSING the Kustomization, not by searching its text for a filename (R76). The
    parsed `resources` list is the thing Flux acts on; a substring check would pass against a
    comment or a path that is wrong in every way except its spelling.
    """
    kustomization = yaml.safe_load(
        (REPO_ROOT / "platform" / "verification" / "kustomization.yaml").read_text()
    )
    resources = kustomization["resources"]
    assert "refuse-unattested-provenance.yaml" in resources, (
        "the Rule 4 policy is not in the parsed resources list of "
        "platform/verification/kustomization.yaml, so Flux never applies it and it enforces "
        f"nothing. Listed: {resources!r}"
    )

    # The listed name must be a file that exists and parses, or Flux fails the whole path.
    policy_path = (
        REPO_ROOT / "platform" / "verification" / "refuse-unattested-provenance.yaml"
    )
    listed = yaml.safe_load(policy_path.read_text())
    assert listed["kind"] == "ClusterPolicy"
