"""Incident 2026-08-26 02:26Z: bin/idp-oke-rebuild ran `tofu init -migrate-state -force-copy`
with a stale platform/oci/terraform.tfstate in the checkout and overwrote estate/terraform.tfstate
in the bucket (serial 7, 30 resources over serial 7, 34). Two live IAM resources left state and
every oke-check run on every branch failed tofu-plan rc=2 until they were imported back.
Rung 4, incident test, both ways: a non-empty local state is quarantined before init; an empty
or absent one is left alone; and no init in bin/ may force-copy again.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "bin" / "idp-state-guard"


def run(mod: Path):
    return subprocess.run([str(GUARD), str(mod)], capture_output=True, text=True)


def test_refuse_stale_local_state_is_quarantined(tmp_path: Path):
    (tmp_path / "terraform.tfstate").write_text('{"serial": 7, "resources": []}')
    (tmp_path / "terraform.tfstate.backup").write_text('{"serial": 6}')
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("GUARD   state") == 2, r.stdout
    assert not (tmp_path / "terraform.tfstate").exists()
    assert not (tmp_path / "terraform.tfstate.backup").exists()
    assert len(list(tmp_path.glob("terraform.tfstate*.quarantine-*"))) == 2


def test_allow_empty_or_absent_local_state(tmp_path: Path):
    (tmp_path / "terraform.tfstate").write_text("")   # what a finished migrate leaves behind
    r = run(tmp_path)
    assert r.returncode == 0 and "ok      state" in r.stdout, r.stdout
    assert not (tmp_path / "terraform.tfstate").exists()
    assert not list(tmp_path.glob("terraform.tfstate*.quarantine-*"))


def test_no_init_in_bin_force_copies_state():
    bad = re.compile(r"^[^#]*\binit\b[^#\n]*-(force-copy|migrate-state)", re.M)   # code, not comments
    offenders = [p.name for p in (ROOT / "bin").iterdir()
                 if p.is_file() and bad.search(p.read_text(errors="ignore"))]
    assert offenders == [], offenders
