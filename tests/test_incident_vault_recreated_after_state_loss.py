"""Incident test (rung 4): 2026-08-26 02:26Z, a lost-state apply created a second empty vault and
every ExternalSecret failed for ~90 minutes. Rule: an apply that would create oci_kms_vault.estate
while an ACTIVE vault of that display_name exists is refused with the import command; a create
with no live namesake passes; a plan that creates nothing passes and never asks the cloud.
crew#66 CP5c: the live side is read through the one cloud layer, so the fake here is a fake
bin/idp-cloud in a temp IDP tree, never a fake provider CLI."""
import os, shutil, stat, subprocess, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "bin" / "idp-recreate-guard"
LIVE = "ocid1.vault.oc1..live"

def _fake(bin_dir: Path, name: str, body: str) -> None:
    f = bin_dir / name
    f.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    f.chmod(f.stat().st_mode | stat.S_IEXEC)

def _tree(tmp: Path) -> tuple[Path, Path]:
    """A temp IDP tree: the guard resolves "$IDP/bin/idp-cloud" beside itself, so it is copied into
    tmp/bin and the layer next to it is the fake each case drives."""
    b = tmp / "bin"; b.mkdir(exist_ok=True); m = tmp / "mod"; m.mkdir(exist_ok=True)
    shutil.copy(GUARD, b / GUARD.name)
    (m / "terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.oc1..test"\n')
    return b, m

def _run(tmp: Path, creates: bool, live: bool) -> subprocess.CompletedProcess:
    b, m = _tree(tmp)
    show = '  # oci_kms_vault.estate will be created\n      + display_name = "estate-secrets"\nPlan: 1 to add.' if creates else "No changes."
    _fake(b, "tofu", f'''
        case "$1" in plan) for a in "$@"; do case "$a" in -out=*) : > "${{a#-out=}}";; esac; done; exit 0;;
                     show) printf '%s\\n' '{show}';; esac''')
    # the fake lists a decoy vault first (reviewer 5420357246: a fake whose rows all match could not
    # see the guard picking a vault by position instead of by display-name)
    rows = ["decoy-vault ocid1.vault.oc1..decoy"] + ([f"estate-secrets {LIVE}"] if live else [])
    _fake(b, "idp-cloud", f'''
        echo "$@" >> "{tmp}/cloud.calls"
        case "$1 $2" in
          "vault list") printf '%s\\n' {" ".join(f"'{r}'" for r in rows)};;
          *) echo "unexpected layer call: $*" >&2; exit 2;;
        esac''')
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    return subprocess.run(["bash", str(b / GUARD.name), str(m)], env=env, capture_output=True, text=True)

def test_incident_vault_recreated_after_state_loss(tmp_path: Path) -> None:
    r = _run(tmp_path, True, True)
    assert r.returncode == 1 and "REFUSE" in r.stdout and f"tofu import oci_kms_vault.estate {LIVE}" in r.stdout
    assert "decoy" not in r.stdout, "the guard took a row that is not the display_name it asked for"
    r = _run(tmp_path, True, False)
    assert r.returncode == 0 and "a create is a real create" in r.stdout
    assert '"$IDP/bin/idp-cloud" vault list' in GUARD.read_text()
    (tmp_path / "cloud.calls").unlink()
    r = _run(tmp_path, False, True)
    assert r.returncode == 0 and "creates nothing" in r.stdout and not (tmp_path / "cloud.calls").exists()

def _run_bucket(tmp: Path, exists: bool) -> subprocess.CompletedProcess:
    """Second instance of the class (crew#292, run 32965258786): the plan creates
    oci_objectstorage_bucket.drill_receipts while the bucket already exists -> 409."""
    b, m = _tree(tmp)
    show = '  # oci_objectstorage_bucket.drill_receipts will be created\n      + name = "estate-drill-receipts"\n      + namespace = (known after apply)\nPlan: 1 to add.'
    _fake(b, "tofu", f'''
        case "$1" in plan) for a in "$@"; do case "$a" in -out=*) : > "${{a#-out=}}";; esac; done; exit 0;;
                     show) printf '%s\\n' '{show}';; esac''')
    # `bucket head NAME`: exit 0 present, 1 absent (bin/idp-cloud's contract); the layer owns the namespace
    rc = 0 if exists else 1
    _fake(b, "idp-cloud", f'''
        case "$1 $2" in
          "bucket head")
            [ "$3" = estate-drill-receipts ] || {{ echo "wrong bucket name: $*" >&2; exit 2; }}
            [ {rc} = 0 ] && echo ok; exit {rc};;
          *) echo "unexpected layer call: $*" >&2; exit 2;;
        esac''')
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    return subprocess.run(["bash", str(b / GUARD.name), str(m)], env=env, capture_output=True, text=True)

def test_incident_bucket_recreated_after_state_loss(tmp_path: Path) -> None:
    r = _run_bucket(tmp_path, True)
    assert r.returncode == 1 and "REFUSE" in r.stdout
    assert "tofu import oci_objectstorage_bucket.drill_receipts n/<namespace>/b/estate-drill-receipts" in r.stdout
    assert '"$IDP/bin/idp-cloud" bucket head' in GUARD.read_text()
    r = _run_bucket(tmp_path, False)
    assert r.returncode == 0 and "a create is a real create" in r.stdout

def test_rebuild_runs_the_guard_before_every_apply() -> None:
    s = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    # The invariant is guard-before-every-apply, not the apply count: --surge-node (crew#516) added a third.
    n = s.count("step tofu-apply")
    assert n >= 2 and s.count('step recreate-guard "$IDP/bin/idp-recreate-guard"') == n
