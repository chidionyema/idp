"""Incident idp#1027 (commit cd9911df): kustomize build re-emits every scalar plain, so the
quotes around `${githubAppID}` in platform/hermes-agent/gateway.yaml were gone by the time Flux's
envsubst substituted the value, and the bare numeral it inserted YAML-parsed as an int. Run
33339964930's own admission refusal was ".spec.appID: expected string, got 4740261" -- the CRD
(generators.external-secrets.io/v1alpha1 GithubAccessToken) declares `spec.appID` a string.
Nothing before that incident graded TYPE: Kyverno's `kyverno apply` only grades whether a
resource is POLICY-allowed, and both the pre-fix and post-fix shapes here are equally allowed.

Rule: kubeconform, run against the estate's vendored CRD schema for GithubAccessToken plus
kubeconform's own built-in Kubernetes schemas, refuses tests/fixtures/kubeconform/incident-
idp1027/bad.yaml (the pre-fix shape) and accepts good.yaml (the fix: `| quote` in the Helm
values, `appID: "4740261"`). Proved both ways in one test.

With no kubeconform binary the test is BLIND and says so -- never a silent pass (LAW 28)."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "kubeconform" / "incident-idp1027"
CRD_SCHEMAS = ROOT / "tests" / "fixtures" / "kubeconform" / "crd-schemas"
SCHEMA_TEMPLATE = f"{CRD_SCHEMAS}/{{{{.Group}}}}/{{{{.ResourceKind}}}}_{{{{.ResourceAPIVersion}}}}.json"


def _blind():
    if not shutil.which("kubeconform"):
        pytest.skip("BLIND: kubeconform is not installed; nothing was type-checked")
    if not (
        CRD_SCHEMAS
        / "generators.external-secrets.io"
        / "githubaccesstoken_v1alpha1.json"
    ).exists():
        pytest.skip(f"BLIND: no vendored CRD schema at {CRD_SCHEMAS}")


def _judge(fixture: pathlib.Path) -> dict:
    proc = subprocess.run(
        [
            "kubeconform",
            "-summary",
            "-output",
            "json",
            "-ignore-missing-schemas",
            "-kubernetes-version",
            "1.34.11",
            "-schema-location",
            "default",
            "-schema-location",
            SCHEMA_TEMPLATE,
            str(fixture),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(proc.stdout)


def test_the_prefix_idp1027_shape_is_still_refused():
    """The exact pre-fix shape (commit cd9911df's parent, run 33339964930) must still fail."""
    _blind()
    report = _judge(FIXTURES / "bad.yaml")
    assert report["summary"]["invalid"] == 1, report
    msg = report["resources"][0]["msg"]
    assert "/spec/appID" in msg and "want string" in msg, msg
    assert "/spec/installID" in msg, msg


def test_the_fix_is_accepted():
    """The `| quote` fix (commit cd9911df itself) must type-check clean."""
    _blind()
    report = _judge(FIXTURES / "good.yaml")
    assert report["summary"]["invalid"] == 0, report
    assert report["summary"]["valid"] == 1, report
