"""crew#584 CP-E (Playbook Phase 3, founder 2026-08-29): a laptop joins the cluster through mirrord,
and the cluster - not a doc - refuses a mirrord agent anywhere but a namespace that allows the dev
loop. The founder's worry, verbatim: "is th sustiabnalble breaking live services". It is not; so
production admits no agent at all, and the checked-in config cannot steal traffic or write files."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform/edge/dev-loop-policy.yaml"
CONFIG = ROOT / ".mirrord/hermes-agent.json"

AGENT_POD = """apiVersion: v1
kind: Pod
metadata:
  name: mirrord-agent-abc
  namespace: {ns}
spec:
  containers:
    - name: mirrord-agent
      image: ghcr.io/metalbear-co/mirrord:3.251.0
"""

NAMESPACE = """apiVersion: v1
kind: Namespace
metadata:
  name: {ns}
  labels:
    {labels}
"""


def _apply(tmp_path: Path, ns: str, labelled: bool) -> str:
    assert shutil.which("kyverno"), (
        "BLIND: the kyverno CLI is not installed; ci.yml installs it"
    )
    pod = tmp_path / f"{ns}-pod.yaml"
    pod.write_text(AGENT_POD.format(ns=ns))
    labels = "idp.platform/dev-loop: allowed" if labelled else "team: platform"
    nsf = tmp_path / f"{ns}-ns.yaml"
    nsf.write_text(NAMESPACE.format(ns=ns, labels=labels))
    values = tmp_path / f"{ns}-values.yaml"
    values.write_text(
        "apiVersion: cli.kyverno.io/v1alpha1\nkind: Values\nmetadata:\n  name: values\n"
        "namespaceSelector:\n  - name: %s\n    labels:\n      %s\n" % (ns, labels)
    )
    cmd = [
        "kyverno",
        "apply",
        str(POLICY),
        "--resource",
        str(pod),
        "--values-file",
        str(values),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout + r.stderr


def test_a_mirrord_agent_in_a_production_namespace_is_refused(tmp_path):
    out = _apply(tmp_path, "hermes-agent", labelled=False)
    assert "fail: 1" in out, out


def test_a_mirrord_agent_in_a_dev_loop_namespace_is_admitted(tmp_path):
    out = _apply(tmp_path, "hermes-agent", labelled=True)
    assert "fail: 0" in out and "error: 0" in out, out


def test_the_checked_in_config_cannot_break_the_live_pod():
    cfg = json.loads(CONFIG.read_text())
    assert cfg["feature"]["network"]["incoming"]["mode"] == "mirror"
    assert cfg["feature"]["fs"] == "read"
    assert cfg["target"]["path"] == "deployment/hermes-agent-gateway"


@pytest.mark.skipif(
    not shutil.which("mirrord"),
    reason="mirrord CLI not installed here; the how-to installs it",
)
def test_the_config_parses_with_the_real_cli():
    r = subprocess.run(
        ["mirrord", "verify-config", str(CONFIG)], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_production_namespace_carries_the_dev_loop_label():
    hits = [
        p
        for p in (ROOT / "platform").rglob("*.yaml")
        if "idp.platform/dev-loop" in p.read_text()
        and p != POLICY
        and "platform/staging/"
        not in str(p)  # staging is the dev-loop namespace by decision (ADR 0012)
    ]
    assert hits == [], hits
