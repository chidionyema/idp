"""Incident test (rung 4): 2026-08-26 02:26Z, a lost-state apply created a second empty vault and
every ExternalSecret failed for ~90 minutes. Rule: an apply that would create oci_kms_vault.estate
while an ACTIVE vault of that display_name exists is refused with the import command; a create
with no live namesake passes; a plan that creates nothing passes and never calls oci."""
import os, stat, subprocess, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "bin" / "idp-recreate-guard"

def _fake(bin_dir: Path, name: str, body: str) -> None:
    f = bin_dir / name
    f.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    f.chmod(f.stat().st_mode | stat.S_IEXEC)

def _run(tmp: Path, creates: bool, live_id: str) -> subprocess.CompletedProcess:
    b = tmp / "bin"; b.mkdir(exist_ok=True); m = tmp / "mod"; m.mkdir(exist_ok=True)
    (m / "terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.oc1..test"\n')
    show = '  # oci_kms_vault.estate will be created\n      + display_name = "estate-secrets"\nPlan: 1 to add.' if creates else "No changes."
    _fake(b, "tofu", f'''
        case "$1" in plan) for a in "$@"; do case "$a" in -out=*) : > "${{a#-out=}}";; esac; done; exit 0;;
                     show) printf '%s\\n' '{show}';; esac''')
    # the fake answers only when asked for the exact display_name (reviewer 5420357246: a fake that
    # ignores its arguments could not see the guard querying for '=' instead of the name)
    _fake(b, "oci", f'echo called >> "{tmp}/oci.calls"; case "$*" in *"==\'estate-secrets\'"*) printf "%s\\n" "{live_id}";; *) echo "null";; esac')
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    return subprocess.run(["bash", str(GUARD), str(m)], env=env, capture_output=True, text=True)

def test_incident_vault_recreated_after_state_loss(tmp_path: Path) -> None:
    r = _run(tmp_path, True, "ocid1.vault.oc1..live")
    assert r.returncode == 1 and "REFUSE" in r.stdout and "tofu import oci_kms_vault.estate ocid1.vault.oc1..live" in r.stdout
    r = _run(tmp_path, True, "null")
    assert r.returncode == 0 and "a create is a real create" in r.stdout
    (tmp_path / "oci.calls").unlink()
    r = _run(tmp_path, False, "ocid1.vault.oc1..live")
    assert r.returncode == 0 and "creates nothing" in r.stdout and not (tmp_path / "oci.calls").exists()

def _run_bucket(tmp: Path, exists: bool) -> subprocess.CompletedProcess:
    """Second instance of the class (crew#292, run 32965258786): the plan creates
    oci_objectstorage_bucket.drill_receipts while the bucket already exists -> 409."""
    b = tmp / "bin"; b.mkdir(exist_ok=True); m = tmp / "mod"; m.mkdir(exist_ok=True)
    (m / "terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.oc1..test"\n')
    show = '  # oci_objectstorage_bucket.drill_receipts will be created\n      + name = "estate-drill-receipts"\n      + namespace = (known after apply)\nPlan: 1 to add.'
    _fake(b, "tofu", f'''
        case "$1" in plan) for a in "$@"; do case "$a" in -out=*) : > "${{a#-out=}}";; esac; done; exit 0;;
                     show) printf '%s\\n' '{show}';; esac''')
    rc = 0 if exists else 1
    _fake(b, "oci", f'''case "$*" in
        "os ns get"*) echo "testns";;
        *"--bucket-name estate-drill-receipts"*) exit {rc};;
        *) echo "wrong bucket name: $*" >&2; exit 1;; esac''')
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    return subprocess.run(["bash", str(GUARD), str(m)], env=env, capture_output=True, text=True)

def test_incident_bucket_recreated_after_state_loss(tmp_path: Path) -> None:
    r = _run_bucket(tmp_path, True)
    assert r.returncode == 1 and "REFUSE" in r.stdout
    assert "tofu import oci_objectstorage_bucket.drill_receipts n/testns/b/estate-drill-receipts" in r.stdout
    r = _run_bucket(tmp_path, False)
    assert r.returncode == 0 and "a create is a real create" in r.stdout

def test_rebuild_runs_the_guard_before_every_apply() -> None:
    s = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    assert s.count('step recreate-guard "$IDP/bin/idp-recreate-guard"') == s.count("step tofu-apply") == 2
