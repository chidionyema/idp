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

WHY THE VERDICTS COME FROM KYVERNO ITSELF. This estate has already shipped a control that
could not fail: stage 2 of the verifier, whose `_guard` handed a Python `bool` to `z3.Not()`
and therefore answered `unsat` for every patch it was ever given. This module used to repeat
that mistake in a quieter form -- it re-implemented the policy's precondition and deny
condition in Python and asserted against its own re-implementation. That graded a
*transcription* of the policy, never the policy: a `kyverno apply` that crashed, a policy
whose `validate` block was misspelled, or an uninstallable policy would all have passed.

So the verdicts now come from the Kyverno CLI -- the same binary `bin/idp-kyverno-render`
runs in the pre-push chain and offline gate. `_kyverno_verdict()` writes the policy to a temp
dir, shells out to `kyverno apply`, and reads the CLI's own `pass/fail/skip` counters. If the
CLI is not installed the test SKIPS rather than silently passing, because a verdict nothing
produced is the lie this feature exists to remove.

THE THIRD CASE IS THE ONE THAT KEEPS IT HONEST. A rule that refuses the bad object but also
refuses a correct one is an outage (R38), so `untouched.yaml` -- a pod that says nothing
about provenance -- must be skipped: the rule must not even examine it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    REPO_ROOT / "platform" / "verification" / "refuse-unattested-provenance.yaml"
)
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "rule4-admission"

_COUNTERS = re.compile(
    r"pass:\s*(\d+),\s*fail:\s*(\d+),\s*warn:\s*(\d+),\s*error:\s*(\d+),\s*skip:\s*(\d+)"
)


class KyvernoVerdict:
    """What the CLI decided about one manifest, read from the CLI's own counters."""

    def __init__(self, fails: int, skips: int, passes: int, output: str) -> None:
        self.fails = fails
        self.skips = skips
        self.passes = passes
        self.output = output

    @property
    def is_denied(self) -> bool:
        return self.fails >= 1

    @property
    def is_allowed(self) -> bool:
        return self.passes >= 1 and self.fails == 0

    @property
    def is_untouched(self) -> bool:
        return self.skips >= 1 and self.fails == 0 and self.passes == 0

    def has_violation(self, code: str) -> bool:
        return code in self.output


@pytest.fixture(scope="module")
def kyverno_bin() -> str:
    binary = shutil.which("kyverno")
    if binary is None:
        pytest.skip(
            "the kyverno CLI is not installed, so no verdict can be produced. Skipping "
            "rather than asserting against a Python re-implementation of the policy, "
            "which would grade the transcription and not the control."
        )
    return binary


def _kyverno_verdict(kyverno: str, fixture: str) -> KyvernoVerdict:
    """Run the real admission control over one fixture and read its counters."""
    with tempfile.TemporaryDirectory() as scratch:
        policy = Path(scratch) / "policy.yaml"
        policy.write_text(POLICY_PATH.read_text())
        proc = subprocess.run(
            [
                kyverno,
                "apply",
                str(policy),
                "--resource",
                str(FIXTURES / fixture),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    output = f"{proc.stdout}\n{proc.stderr}"
    match = _COUNTERS.search(output)
    assert match, (
        f"kyverno apply produced no counters for {fixture}, so this test has no verdict. "
        f"rc={proc.returncode}\n{output}"
    )
    passed, failed, _warn, errored, skipped = (int(g) for g in match.groups())
    assert errored == 0, (
        f"kyverno errored judging {fixture} (a malformed policy?):\n{output}"
    )
    return KyvernoVerdict(fails=failed, skips=skipped, passes=passed, output=output)


def test_the_policy_is_a_real_enforcing_cluster_policy() -> None:
    policy = yaml.safe_load(POLICY_PATH.read_text())
    assert policy["kind"] == "ClusterPolicy"
    assert policy["spec"]["validationFailureAction"] == "Enforce", (
        "an Audit policy lets the refused object through; a refusal that can be ignored "
        "is not a refusal (LAW 44)"
    )


def test_a_provenance_claim_with_no_attestation_is_refused(kyverno_bin: str) -> None:
    verdict = _kyverno_verdict(kyverno_bin, "bad.yaml")
    assert verdict.is_denied, (
        "an object claiming estate.io/provenance-verified with no estate.io/attestation "
        f"must be refused -- that object is the untrusted proposer asking to be believed.\n"
        f"{verdict.output}"
    )
    assert verdict.has_violation("UNATTESTED"), (
        "the refusal must carry the UNATTESTED code the spec names, or a caller cannot "
        f"tell this refusal from any other.\n{verdict.output}"
    )


def test_a_provenance_claim_with_its_attestation_is_admitted(kyverno_bin: str) -> None:
    verdict = _kyverno_verdict(kyverno_bin, "good.yaml")
    assert verdict.is_allowed, (
        "a sealed payload must be admitted; a gate that refuses the correct case too is "
        f"an outage (R38).\n{verdict.output}"
    )


def test_a_workload_silent_about_provenance_is_untouched(kyverno_bin: str) -> None:
    verdict = _kyverno_verdict(kyverno_bin, "untouched.yaml")
    assert verdict.is_untouched, (
        "the rule must only examine objects that make the provenance claim, or it refuses "
        f"every ordinary workload in the estate.\n{verdict.output}"
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
