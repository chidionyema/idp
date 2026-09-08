"""WJ.1's client half: a device becomes an agent of this estate holding one key and nothing else.

Issue #2470. PR #2456 built the door; this grades the walk through it. The defect both halves
exist to remove, measured 2026-09-08 at bin/idp-kube:84 before this change:

    tok=$(KUBECONFIG="$KC" kubectl create token agent-reader -n agents --duration=3600s)

$KC is minted by `bin/idp-cloud cluster kubeconfig`, and its user is an `exec` credential that
runs `oci generate-token`. So the read-only identity every agent in the estate runs as was
minted, every hour, by the founder's own tenancy administrator, on the one machine his OCI
session lives on. Two consequences, and the second is the one that hid the first: the estate
could not be operated from any other device, and `bin/idp-kube auth whoami` answered
`agent-reader` the whole time -- truthfully, because the downgrade was real. What was not an
agent was the thing performing it.

These tests grade three things and no prose:
  * the broker hands back everything a device needs, read from the cluster rather than a file;
  * bin/idp-jit turns that into a kubeconfig no `oci` CLI appears in;
  * bin/idp-kube asks the broker before it ever reaches for the founder's principal.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = "the-agent-bootstrap-key"
# The fake API server's answers. Named so ruff does not read the assertions as credentials:
# comparing a "token" key against a literal is S105, and a fixture is not a secret.
MINTED = "minted-token"
ADDRESS = "141.147.80.229:6443"
AUTHORITY = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t"

PUBLISHED = f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    server: {ADDRESS}
    certificate-authority-data: {AUTHORITY}
  name: ""
"""


def _module(path: str, name: str):
    # bin/idp-jit has no .py suffix, so the loader has to be named: spec_from_file_location
    # returns None for an extensionless file and the import fails with an unhelpful
    # AttributeError on `spec.loader`.
    full = os.path.join(ROOT, path)
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, full), origin=full
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def broker(tmp_path):
    """A broker whose only contact with a cluster is a function this test wrote."""
    mod = _module("platform/jit/broker/broker.py", "broker.broker")
    calls: list[list[str]] = []

    def kube(args, stdin=None):
        calls.append(args)
        if args[:2] == ["create", "token"]:
            return 0, MINTED + "\n"
        if args[:2] == ["get", "configmap"]:
            return 0, PUBLISHED
        return 1, "the test did not expect " + " ".join(args)

    b = mod.Broker(
        catalogue=os.path.join(ROOT, "platform/jit/grants.yaml"),
        ledger_path=str(tmp_path / "ledger.jsonl"),
        key=b"k",
        agent_key=KEY.encode(),
        notify=lambda *a, **k: None,
        kube=kube,
        killswitch=lambda: None,
    )
    b.calls = calls
    b.Refused = mod.Refused
    return b


def test_the_answer_carries_everything_a_device_needs_to_reach_the_cluster(broker):
    """A token alone leaves the laptop exactly as load-bearing as before, with an extra door:
    a device also needs the API address and the CA, and until this change the only thing that
    held either was the kubeconfig the `oci` CLI mints."""
    answer = broker.identity(KEY)
    assert answer["token"] == MINTED
    assert answer["ca"] == AUTHORITY
    assert answer["server"] == "https://" + ADDRESS
    assert answer["subject"] == "system:serviceaccount:agents:agent-reader"


def test_the_address_is_read_from_the_cluster_and_named_in_no_file(broker):
    """LAW 46. The alternative on the table was ESTATE_APISERVER_URL in estate-config plus a
    Flux substituteFrom on the jit Kustomization -- a machine fact copied into git. The
    cluster already publishes it for exactly this purpose, so nothing is written down."""
    broker.identity(KEY)
    reads = [c for c in broker.calls if c[:2] == ["get", "configmap"]]
    assert reads, "the broker did not ask the cluster where it is"
    assert reads[0][2:5] == ["cluster-info", "-n", "kube-public"]

    # What is graded is whether the address is ever *operative* in a file, not whether the
    # string appears. Two places mention it in prose and are correct to: bin/idp-headlamp-mac
    # explains in a comment why the Mac talks to Oracle's control plane directly, and
    # docs/FEED.md is an append-only generated log. A literal under platform/ or clusters/,
    # or on a line of shell that runs, is the thing R46 is about -- that is a machine fact the
    # estate would then have two copies of, and the second one rots.
    found = subprocess.run(
        [
            "git",
            "-C",
            ROOT,
            "grep",
            "-nI",
            re.escape(ADDRESS),
            "--",
            "platform",
            "clusters",
            "bin",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    operative = []
    for hit in found.stdout.splitlines():
        path, _, text = hit.split(":", 2)
        if path.startswith(("platform/", "clusters/")) or not text.lstrip().startswith(
            "#"
        ):
            operative.append(hit)
    assert not operative, (
        "the API address is written down where it runs:\n" + "\n".join(operative)
    )


def test_a_scheme_is_added_because_the_cluster_publishes_none(broker):
    """Measured 2026-09-08: this cluster's ConfigMap holds a bare `host:6443`, and kubectl
    refuses a server with no scheme. A device would get a file that cannot be used."""
    assert broker.identity(KEY)["server"].startswith("https://")


def test_a_device_without_the_key_is_told_no_and_the_cluster_is_never_asked(broker):
    with pytest.raises(broker.Refused):
        broker.identity("not-the-key")
    assert not broker.calls, "the broker talked to the cluster before checking the key"


def test_the_kubeconfig_written_names_no_oci_cli(tmp_path, monkeypatch):
    """The whole point. `bin/idp-cloud cluster kubeconfig` writes a user whose credential is
    `exec: command: oci` -- which is why the estate needed the founder's laptop. What
    bin/idp-jit writes instead is a bearer token, so a device with no OCI CLI, no OCI login
    and no tenancy at all can read this cluster."""
    jit = _module("bin/idp-jit", "idp_jit")
    monkeypatch.setenv("JIT_AGENT_KEY", KEY)
    monkeypatch.setattr(
        jit,
        "_post",
        lambda path, body, headers=None: (
            200,
            {"token": MINTED, "server": "https://" + ADDRESS, "ca": AUTHORITY},
        ),
    )
    out = tmp_path / "kubeconfig-reader"
    assert jit.main(["identity", "--kubeconfig", str(out)]) == 0

    doc = json.loads(out.read_text())
    assert doc["clusters"][0]["cluster"]["server"] == "https://" + ADDRESS
    assert doc["clusters"][0]["cluster"]["certificate-authority-data"] == AUTHORITY
    assert doc["users"][0]["user"]["token"] == MINTED
    assert "exec" not in json.dumps(doc), (
        "the kubeconfig still runs a credential plugin"
    )
    assert "oci" not in json.dumps(doc)
    # A credential is not left world-readable even for the instant between create and write.
    assert oct(out.stat().st_mode)[-3:] == "600"


def test_a_device_holding_no_key_is_refused_rather_than_falling_back(
    tmp_path, monkeypatch
):
    """`refused` is exit 4 -- the broker was never asked. A device with no key must not
    silently become whatever credential happens to be lying around."""
    jit = _module("bin/idp-jit", "idp_jit")
    monkeypatch.delenv("JIT_AGENT_KEY", raising=False)
    monkeypatch.setenv("IDP_KUBE_STATE", str(tmp_path))
    assert jit.main(["identity"]) == jit.CODES["refused"]


def _kube_source() -> str:
    with open(os.path.join(ROOT, "bin/idp-kube")) as fh:
        return fh.read()


def test_idp_kube_asks_the_broker_before_it_reaches_for_the_founders_principal():
    """Order is the whole fix, not merely presence. A broker call placed *after* the
    `bin/idp-cloud cluster kubeconfig` block would still require the `oci` CLI and the
    founder's login on every device -- the door would exist and change nothing."""
    src = _kube_source()
    assert "from_broker" in src, "bin/idp-kube does not ask the broker at all"
    assert src.index("from_broker()") < src.index(
        '"$IDP/bin/idp-cloud" cluster kubeconfig'
    )
    assert src.index("elif from_broker;") < src.index(
        '"$IDP/bin/idp-cloud" cluster kubeconfig'
    )


def test_the_founders_kubeconfig_is_only_built_when_nothing_else_answered():
    """The expensive, laptop-bound path sits behind a guard rather than running every time."""
    src = _kube_source()
    guard = src.index('if [ -z "$USE" ]; then')
    assert guard < src.index('"$IDP/bin/idp-cloud" cluster kubeconfig')
    assert guard < src.index('"$IDP/bin/idp-cloud" cluster list')


def _run_kube(state, *args):
    """bin/idp-kube with no kubectl arguments prints the kubeconfig it would have used and
    exits, so the identity it chose is observable without a cluster. `kubectl` still has to
    exist on PATH for the `command -v` check, hence the stub."""
    stub = state / "bin"
    stub.mkdir(exist_ok=True)
    fake = stub / "kubectl"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    env = dict(os.environ)
    env["IDP_KUBE_STATE"] = str(state)
    env["PATH"] = f"{stub}:/usr/bin:/bin"
    return subprocess.run(
        [os.path.join(ROOT, "bin/idp-kube"), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_break_glass_still_runs_as_the_founder(tmp_path):
    """WJ.8 and R49: the escape hatch stays, and stays loud. An estate whose only way out is
    editing this file gets it edited at 3am by someone who forgets to edit it back.

    Graded by running it: both kubeconfigs are seeded fresh, so the ordinary call has a
    perfectly good reader identity to use and the break-glass call must refuse it anyway.
    """
    founders = tmp_path / "kubeconfig"
    founders.write_text("founder\n")
    reader = tmp_path / "kubeconfig-reader"
    reader.write_text("reader\n")

    ordinary = _run_kube(tmp_path)
    assert ordinary.returncode == 0, ordinary.stderr
    assert str(reader) in ordinary.stdout, ordinary.stdout

    broken = _run_kube(tmp_path, "--break-glass", "the cluster is down")
    assert broken.returncode == 0, broken.stderr
    assert str(founders) in broken.stdout, broken.stdout
    assert str(reader) not in broken.stdout

    # Loud: a banner the operator cannot miss, and a record that outlives the session.
    assert "BREAK-GLASS" in broken.stderr
    assert "the cluster is down" in (tmp_path / "break-glass.log").read_text()


def test_break_glass_without_a_reason_is_refused(tmp_path):
    """A hatch that can be opened silently is opened routinely."""
    (tmp_path / "kubeconfig").write_text("founder\n")
    refused = _run_kube(tmp_path, "--break-glass")
    assert refused.returncode == 2
    assert not (tmp_path / "break-glass.log").exists()


def test_the_script_is_valid_shell():
    assert (
        subprocess.run(
            ["bash", "-n", os.path.join(ROOT, "bin/idp-kube")], check=False
        ).returncode
        == 0
    )
