"""crew#66 CP5c: the two apply-time guards, bin/idp-recreate-guard and bin/idp-vault-split-guard,
read the live side through the one cloud layer (bin/idp-cloud) and no longer name a provider CLI.
Every case here drives a fake bin/idp-cloud in a temp IDP tree: no network, no oci CLI."""

import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECREATE = ROOT / "bin" / "idp-recreate-guard"
SPLIT = ROOT / "bin" / "idp-vault-split-guard"
TOFU = "ocid1.vault.oc1..tofu00"
OTHER = "ocid1.vault.oc1..other0"


def _fake(bin_dir: Path, name: str, body: str) -> None:
    f = bin_dir / name
    f.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    f.chmod(f.stat().st_mode | stat.S_IEXEC)


def _tree(tmp: Path, guard: Path) -> tuple[Path, Path]:
    """A temp IDP tree: a guard resolves "$IDP/bin/idp-cloud" beside itself, so the guard is copied
    into tmp/bin and the layer next to it is the fake the case drives."""
    b = tmp / "bin"
    b.mkdir(exist_ok=True)
    m = tmp / "mod"
    m.mkdir(exist_ok=True)
    shutil.copy(guard, b / guard.name)
    (m / "terraform.tfvars").write_text(
        'compartment_ocid = "ocid1.compartment.oc1..test"\n'
    )
    return b, m


@pytest.mark.parametrize("guard", [RECREATE, SPLIT], ids=lambda p: p.name)
def test_neither_guard_names_the_provider_cli(guard: Path) -> None:
    code = [l for l in guard.read_text().splitlines() if not l.lstrip().startswith("#")]
    assert not [l for l in code if "oci " in l], f"{guard.name} still names the oci CLI"
    assert '"$IDP/bin/idp-cloud"' in "\n".join(code), (
        f"{guard.name} does not read through the layer"
    )


def test_recreate_guard_is_blind_when_the_layer_cannot_read_the_bucket(
    tmp_path: Path,
) -> None:
    """`bucket head` exit 2 is BLIND (the namespace could not be read): the guard says BLIND and
    never calls the bucket absent. Its exit code stays 0 on BLIND, as its header states and as
    bin/idp-oke-rebuild needs (any non-zero there is read as "recreate-guard refused")."""
    b, m = _tree(tmp_path, RECREATE)
    show = '  # oci_objectstorage_bucket.drill_receipts will be created\n      + name = "estate-drill-receipts"\nPlan: 1 to add.'
    _fake(
        b,
        "tofu",
        f"""
        case "$1" in plan) for a in "$@"; do case "$a" in -out=*) : > "${{a#-out=}}";; esac; done; exit 0;;
                     show) printf '%s\\n' '{show}';; esac""",
    )
    _fake(
        b,
        "idp-cloud",
        """
        case "$1 $2" in
          "bucket head") echo "BLIND   cloud  namespace unreadable" >&2; exit 2;;
          *) echo "unexpected layer call: $*" >&2; exit 2;;
        esac""",
    )
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    r = subprocess.run(
        ["bash", str(b / RECREATE.name), str(m)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert "BLIND" in r.stdout, r.stdout + r.stderr
    assert (
        "BLIND   recreate  oci_objectstorage_bucket.drill_receipts: bin/idp-cloud bucket head failed"
        in r.stdout
    ), r.stdout
    assert "REFUSE" not in r.stdout and "a create is a real create" not in r.stdout, (
        r.stdout
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_vault_split_guard_names_a_secret_held_by_two_vaults(tmp_path: Path) -> None:
    """Two ACTIVE vaults, both listing router-keys: the guard refuses and its REFUSE line names the
    secret (names only, never a value) and the import for the vault that is not the tofu vault."""
    b, m = _tree(tmp_path, SPLIT)
    _fake(b, "tofu", f'[ "$1 $2" = "output -raw" ] && printf "%s" "{TOFU}"')
    _fake(
        b,
        "idp-cloud",
        f"""
        case "$1 $2" in
          "vault list") printf '%s\\n' 'estate-secrets {TOFU}' 'estate-secrets {OTHER}';;
          "secret list") printf '%s\\n' 'router-keys';;
          *) echo "unexpected layer call: $*" >&2; exit 2;;
        esac""",
    )
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    r = subprocess.run(
        ["bash", str(b / SPLIT.name), str(m)], env=env, capture_output=True, text=True
    )
    assert r.returncode == 1, r.stdout + r.stderr
    refuse = [l for l in r.stdout.splitlines() if l.startswith("REFUSE")]
    assert len(refuse) == 1, r.stdout
    assert (
        "router-keys" in refuse[0]
        and f"tofu import oci_kms_vault.estate {OTHER}" in refuse[0]
    )
    assert "...other0" in refuse[0] and OTHER not in r.stdout.split("REFUSE")[0]
    assert "        secret: router-keys" in r.stdout, (
        "the tofu vault's own row still lists its names"
    )
