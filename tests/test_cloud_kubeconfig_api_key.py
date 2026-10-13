"""`bin/idp-cloud cluster kubeconfig` mints with the identity idp-oci-whoami chose.

Measured 2026-10-13: a Mac with no live session and a working API-key profile could not refresh
its kubeconfig. `oci_compartment` sourced whoami inside `$(...)`, so the api_key it chose died
with the subshell and create-kubeconfig ran `--auth security_token`; the oci CLI answered
"Config value for 'security_token_file' must be specified" and every refresh since 2026-09-19
failed. ai.estate.kubeapi ran on a hand-made kubeconfig until this was found.

A stub `oci` on PATH records each call, so the test grades the flags the real CLI would see.
"""

from __future__ import annotations

import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLUSTER = "ocid1.cluster.oc1.uk-london-1.example"

STUB = """#!/bin/sh
echo "$*" >> "$OCI_CALLS"
case "$*" in
  "iam region list --profile DEFAULT --auth api_key") exit 0 ;;
  "ce cluster create-kubeconfig "*)
    while [ $# -gt 0 ]; do [ "$1" = --file ] && f="$2"; shift; done
    cat > "$f" <<'EOF'
apiVersion: v1
kind: Config
users:
- name: user-1
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      args: [ce, cluster, generate-token, --cluster-id, x]
      command: oci
      env: []
EOF
    exit 0 ;;
esac
exit 1
"""


def _mint(tmp_path) -> tuple[subprocess.CompletedProcess, list[str], dict]:
    home = tmp_path / "home"
    (home / ".oci" / "sessions").mkdir(parents=True)  # no session in it
    (home / ".oci" / "config").write_text(
        "[DEFAULT]\nuser=u\nfingerprint=f\nkey_file=k\n"
    )
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "oci").write_text(STUB)
    (stub / "oci").chmod(0o755)
    calls = tmp_path / "calls"
    env = {k: v for k, v in os.environ.items() if not k.startswith("OCI_CLI_")} | {
        "HOME": str(home),
        "PATH": f"{stub}:{os.environ['PATH']}",
        "OCI_CALLS": str(calls),
        "OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..example",
        "IDP_CLOUD_BACKEND": "oci",
    }
    out = tmp_path / "kubeconfig"
    run = subprocess.run(
        [
            os.path.join(ROOT, "bin", "idp-cloud"),
            "cluster",
            "kubeconfig",
            CLUSTER,
            "--file",
            str(out),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = calls.read_text().splitlines() if calls.exists() else []
    doc = yaml.safe_load(out.read_text()) if out.exists() else {}
    return run, lines, doc


def test_create_kubeconfig_uses_the_api_key_whoami_chose(tmp_path):
    run, calls, _ = _mint(tmp_path)
    assert run.returncode == 0, run.stderr
    (create,) = [c for c in calls if c.startswith("ce cluster create-kubeconfig")]
    assert "--auth api_key" in create, create


def test_the_exec_plugin_is_pinned_to_that_auth_and_profile(tmp_path):
    run, _, doc = _mint(tmp_path)
    assert run.returncode == 0, run.stderr
    args = doc["users"][0]["user"]["exec"]["args"]
    assert args[:4] == ["--auth", "api_key", "--profile", "DEFAULT"], args
