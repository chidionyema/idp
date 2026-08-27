"""Incident 2026-08-27 21:07Z-21:24Z: every oke-check run red at `bin/idp-identity-apply plan` with
`jq: parse error: Invalid numeric literal at line 1, column 3` (runs 33116615830 main, 33116737099 idp#492,
33116235682 idp#490). Attribution: bin/idp-oci-whoami prints `ok      oci-whoami: live profile is '...'` on
stdout; bin/idp-cloud sources it inside the oci backend, so on a runner with no OCI_CLI_PROFILE the layer's
JSON answer to `secret describe` was preceded by that line and the caller's jq died at column 3 (right after
`ok`). The layer must never let the door's instrument line into the data channel: the source is redirected to
stderr. This test runs the real oci backend with a stub `oci` and a fake sessions dir (no network)."""
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD = ROOT / "bin" / "idp-cloud"

STUB_OCI = """#!/usr/bin/env bash
case "$*" in
  *"session validate"*|*"session refresh"*) exit 0;;
  *"vault secret list"*) printf '[{"id":"ocid1.vaultsecret.oc1..stub","vault-id":"ocid1.vault.oc1..stub","key-id":"ocid1.key.oc1..stub","lifecycle-state":"ACTIVE"}]\\n';;
  *) echo "stub oci: unexpected $*" >&2; exit 9;;
esac
"""


def test_secret_describe_stdout_is_json_when_whoami_is_sourced(tmp_path):
    home = tmp_path / "home"
    (home / ".oci" / "sessions" / "ci").mkdir(parents=True)
    (home / ".oci" / "sessions" / "ci" / "token").write_text("stub-token\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    oci = bindir / "oci"
    oci.write_text(STUB_OCI)
    oci.chmod(oci.stat().st_mode | stat.S_IXUSR)
    env = {k: v for k, v in os.environ.items() if k != "OCI_CLI_PROFILE"}
    env.update({
        "HOME": str(home),
        "PATH": f"{bindir}:{env['PATH']}",
        "IDP_CLOUD_BACKEND": "oci",
        "OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..stub",
    })
    r = subprocess.run([str(CLOUD), "secret", "describe", "oauth2-proxy-client-id"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["id"] == "ocid1.vaultsecret.oc1..stub", r.stdout
    assert "oci-whoami: live profile is 'ci'" in r.stderr


def test_no_caller_sources_the_door_into_its_stdout():
    for f in ("idp-cloud", "idp-vault-put"):
        for line in (ROOT / "bin" / f).read_text().splitlines():
            if "source" in line and "idp-oci-whoami" in line and not line.lstrip().startswith("#"):
                assert ">&2" in line, f"{f}: {line.strip()}"
