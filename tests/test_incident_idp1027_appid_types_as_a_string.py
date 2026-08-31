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


# --- the control has to actually run before a merge, or it is documentation (rung 5 = zero) ---
# The two tests above prove kubeconform refuses the incident shape. They say nothing about
# whether anything ever runs it. These four grade the wiring: bin/idp-ci rung 9c calls the
# script on rung 9's render, CI installs the binary, and the handover path is never a silent
# pass. Written after the first cut of this change shipped the script with no caller at all.

CI = ROOT / "bin" / "idp-ci"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SCRIPT = ROOT / "bin" / "idp-kubeconform"


def test_the_type_check_runs_before_merge_on_the_render_kyverno_already_paid_for():
    """One render, judged twice. A second render would cost the job ~160 s again (crew#584)."""
    ci = CI.read_text()
    assert 'IDP_RENDER_KEEP="$tmp/render" bin/idp-kyverno-render' in ci, (
        "rung 9 does not keep its render"
    )
    assert 'bin/idp-kubeconform --rendered "$tmp/render"' in ci, (
        "rung 9c does not judge that render"
    )
    # and it renders exactly once: the only IDP_RENDER_KEEP producer is rung 9's own call.
    assert ci.count("IDP_RENDER_KEEP=") == 1, "more than one render is being kept"


def test_ci_installs_the_binary_so_the_rung_is_never_blind_on_the_runner():
    wf = WORKFLOW.read_text()
    assert (
        "kubeconform-linux-amd64.tar.gz" in wf
        and "kubeconform/releases/download/v0.8.0" in wf
    )
    # BLIND counts as a failure in the rung, so an uninstalled binary can never read green.
    assert 'say "BLIND types' in CI.read_text()


def test_a_handover_that_judged_nothing_is_blind_not_a_pass(tmp_path):
    """silent-green is defect class 4 on this estate's ledger: exit 0 having measured nothing."""
    _blind()
    r = subprocess.run(
        [str(SCRIPT), "--rendered", str(tmp_path)], capture_output=True, text=True
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND" in r.stdout and "nothing was type-checked" in r.stdout


def test_the_entry_point_ci_uses_refuses_the_incident_shape_end_to_end(tmp_path):
    """Not the fixture through a bare kubeconform call -- the exact command bin/idp-ci runs."""
    _blind()
    shutil.copy(FIXTURES / "bad.yaml", tmp_path / "kz-platform_hermes-agent.yaml")
    r = subprocess.run(
        [str(SCRIPT), "--rendered", str(tmp_path)], capture_output=True, text=True
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "want string" in r.stdout and "invalid=1" in r.stdout, r.stdout
    shutil.copy(FIXTURES / "good.yaml", tmp_path / "kz-platform_hermes-agent.yaml")
    r = subprocess.run(
        [str(SCRIPT), "--rendered", str(tmp_path)], capture_output=True, text=True
    )
    assert r.returncode == 0 and "invalid=0" in r.stdout, r.stdout + r.stderr


def test_a_render_that_died_early_is_blind_not_an_ok_over_the_survivors(tmp_path):
    """main's own run 33355097800 died this way: two chart downloads reset by the peer, so
    bin/idp-kyverno-render copied out a partial render. Judging what survived and printing `ok`
    is a pass over a subset -- silent-green, defect class 4 on this estate's ledger."""
    _blind()
    shutil.copy(FIXTURES / "good.yaml", tmp_path / "kz-platform_hermes-agent.yaml")
    r = subprocess.run(
        [
            str(SCRIPT),
            "--rendered",
            str(tmp_path),
            "platform/hermes-agent",
            "platform/spire",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND" in r.stdout and "platform/spire" in r.stdout, r.stdout
    assert "no verdict is given for any of it" in r.stdout, r.stdout
    # and the same directory, with nothing missing, is a clean pass -- the guard discriminates.
    r = subprocess.run(
        [str(SCRIPT), "--rendered", str(tmp_path), "platform/hermes-agent"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "invalid=0" in r.stdout, r.stdout + r.stderr
