"""2026-09-02: `bin/idp-kyverno-render platform/dagster` printed `ok render dagster ...
pass: 302, fail: 0` while admission denied the very same Deployment. oke-check run 33618879684:

    admission webhook "validate.kyverno.svc-fail" denied the request: Deployment
    dagster/dagster-dagster-user-deployments-estate-scheduler was blocked ...
    require-availability: founder-facing-runs-two, founder-facing-spreads-across-nodes

HelmRelease dagster/dagster went Failed, Kustomization flux-system/scheduling went not-ready,
and dagster, notify and otto-staging all wedged behind the dependency.

Why the judge lied: require-availability matches by namespaceSelector
(availability.idp/tier: founder-facing). On the cluster, the API server resolves the selector
against the live Namespace. Offline, the Kyverno CLI knows no namespaces, so the rule reports
SKIP -- and a skip inside an "ok" line is the silent-green class on the estate ledger (4
occurrences before this one). The fix hands `kyverno apply` a values file listing every
labelled Namespace the cluster applies, so the selector resolves offline exactly as it does
at admission.

These tests hold the property both ways (LAW 15): the CLI with the values file refuses the
1-replica shape and passes the 2-replica-spread shape, and the render script keeps building
and passing that file.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RENDER = (ROOT / "bin" / "idp-kyverno-render").read_text()
POLICY = ROOT / "platform" / "scheduling" / "require-availability.yaml"

NS_VALUES = textwrap.dedent("""\
    apiVersion: cli.kyverno.io/v1alpha1
    kind: Values
    namespaceSelector:
      - name: dagster
        labels:
          availability.idp/tier: founder-facing
""")


def _deployment(replicas, spread):
    spec = {
        1: "  replicas: 1\n",
        2: "  replicas: 2\n",
    }[replicas]
    tpl = textwrap.dedent("""\
          template:
            metadata:
              labels: {app: d}
            spec:
              containers:
                - name: c
                  image: docker.io/library/busybox:1
    """)
    if spread:
        # indent(), not dedent(): dedent strips the 6 spaces that place this under spec.
        tpl += textwrap.indent(
            textwrap.dedent("""\
                topologySpreadConstraints:
                  - maxSkew: 1
                    topologyKey: kubernetes.io/hostname
                    whenUnsatisfiable: DoNotSchedule
                    labelSelector:
                      matchLabels: {app: d}
            """),
            "      ",
        )
    return (
        "apiVersion: apps/v1\nkind: Deployment\n"
        "metadata: {name: d, namespace: dagster}\n"
        "spec:\n" + spec + "  selector:\n    matchLabels: {app: d}\n" + tpl
    )


def _apply(tmp_path, resource, with_values):
    res = tmp_path / "r.yaml"
    res.write_text(resource)
    cmd = ["kyverno", "apply", str(POLICY), "--resource", str(res)]
    if with_values:
        vals = tmp_path / "v.yaml"
        vals.write_text(NS_VALUES)
        cmd += ["-f", str(vals)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


needs_cli = pytest.mark.skipif(
    shutil.which("kyverno") is None,
    reason="kyverno CLI not installed; ci.yml installs it before bin/idp-ci",
)


@needs_cli
def test_without_namespace_labels_the_rule_is_a_skip_that_reads_green(tmp_path):
    """The regression itself, held so nobody 'simplifies' the values file away."""
    out = _apply(tmp_path, _deployment(replicas=1, spread=False), with_values=False)
    assert "founder-facing-runs-two" not in out and "fail: 0" in out, out


@needs_cli
def test_with_namespace_labels_the_offline_judge_refuses_what_admission_refuses(
    tmp_path,
):
    out = _apply(tmp_path, _deployment(replicas=1, spread=False), with_values=True)
    assert (
        "founder-facing-runs-two" in out
        and "founder-facing-spreads-across-nodes" in out
    ), out


@needs_cli
def test_with_namespace_labels_the_compliant_shape_still_passes(tmp_path):
    """The other angle (LAW 15): the fence refuses the bad case AND passes the good one."""
    out = _apply(tmp_path, _deployment(replicas=2, spread=True), with_values=True)
    assert "failed" not in out, out


def test_the_render_script_builds_and_passes_the_namespace_values_file():
    """Text property: the collection and the -f flag cannot be dropped separately in silence."""
    assert 'ns_rows[d["metadata"]["name"]] = d["metadata"]["labels"]' in RENDER
    assert '-f "$S/ns-values.yaml"' in RENDER
