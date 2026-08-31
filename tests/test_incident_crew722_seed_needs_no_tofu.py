"""crew#722: the canary seed on a GitHub runner has no tofu (oke-check run 33353772359).

bin/idp-cloud resolved a brand-new secret's vault and key with `tofu output`; on the runner
that substituted an empty string and OCI refused create_secret with "keyId cannot be an empty
string" -- the drill never seeded rotation-canary and the ExternalSecret went red. These tests
pin the tofu-free road: the metadata every ACTIVE sibling secret already carries names the
vault and key (no state read); an empty compartment with no tofu goes loudly BLIND instead of
putting an empty id on the wire; an explicit env override is used untouched.
"""

import json
import pathlib
import stat
import subprocess

TOOL = pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-cloud"

VAULT_A = "ocid1.vault.oc1..estate"
KEY_A = "ocid1.key.oc1..estatekey"
VAULT_B = "ocid1.vault.oc1..stray"
KEY_B = "ocid1.key.oc1..straykey"

OCI_STUB = """#!/bin/bash
# Stub OCI CLI: answers the exact calls bin/idp-cloud makes on the secret put road.
args="$*"
case "$args" in
  *"secret create-base64"*)
    printf '%s\\n' "$@" > "$STUB_DIR/created"
    echo '{}' ;;
  *"secret list"*"--name"*)
    if [ -f "$STUB_DIR/created" ]; then echo '["ocid1.vaultsecret.oc1..seeded"]'; else echo '[]'; fi ;;
  *"secret list"*)
    cat "$STUB_DIR/siblings.json" ;;
  *"secret-bundle get"*)
    awk 'prev=="--secret-content-content"{print; exit} {prev=$0}' "$STUB_DIR/created" ;;
  *)
    echo "unexpected oci call: $args" >&2
    exit 9 ;;
esac
"""


def _arena(tmp_path, siblings):
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    (stub_dir / "siblings.json").write_text(json.dumps({"data": siblings}))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    oci = bindir / "oci"
    oci.write_text(OCI_STUB)
    oci.chmod(oci.stat().st_mode | stat.S_IEXEC)
    secret_file = tmp_path / "payload"
    secret_file.write_text("CANARY_VALUE=abc123\n")
    env = {
        # No tofu anywhere on this PATH: the incident's runner condition.
        "PATH": f"{bindir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "STUB_DIR": str(stub_dir),
        "OCI_CLI_PROFILE": "TEST",
        "OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..test",
        "IDP_CLOUD_BACKEND": "oci",
    }
    return stub_dir, secret_file, env


def _row(vault, key, state="ACTIVE"):
    return {"vault-id": vault, "key-id": key, "lifecycle-state": state}


def _flag(created, name):
    return created[created.index(name) + 1]


def _put(secret_file, env):
    return subprocess.run(
        [str(TOOL), "secret", "put", "rotation-canary", "--file", str(secret_file)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_a_new_secret_is_created_with_the_sibling_secrets_key_when_tofu_is_absent(
    tmp_path,
):
    siblings = [_row(VAULT_A, KEY_A), _row(VAULT_A, KEY_A), _row(VAULT_B, KEY_B)]
    stub_dir, secret_file, env = _arena(tmp_path, siblings)
    r = _put(secret_file, env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "created"
    created = (stub_dir / "created").read_text().splitlines()
    # The majority vault wins, so one stray secret in a second vault cannot steer the key.
    assert _flag(created, "--vault-id") == VAULT_A
    assert _flag(created, "--key-id") == KEY_A


def test_an_empty_compartment_with_no_tofu_is_blind_never_an_empty_key_on_the_wire(
    tmp_path,
):
    stub_dir, secret_file, env = _arena(tmp_path, [])
    r = _put(secret_file, env)
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert "BLIND" in r.stderr
    assert "no vault key for a new secret" in r.stderr
    assert not (stub_dir / "created").exists()


def test_the_env_override_is_used_untouched(tmp_path):
    stub_dir, secret_file, env = _arena(tmp_path, [_row(VAULT_B, KEY_B)])
    env["ESTATE_VAULT_OCID"] = VAULT_A
    env["ESTATE_VAULT_KEY_OCID"] = KEY_A
    r = _put(secret_file, env)
    assert r.returncode == 0, r.stderr
    created = (stub_dir / "created").read_text().splitlines()
    assert _flag(created, "--vault-id") == VAULT_A
    assert _flag(created, "--key-id") == KEY_A
    assert VAULT_B not in created and KEY_B not in created
