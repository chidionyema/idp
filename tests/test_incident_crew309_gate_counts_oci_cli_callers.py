"""Audit 2026-08-27 (crew#309, crew#66): the platform manifests name no cloud (gate: 0 lines), but 30
bin/ scripts and 6 workflows call the `oci` CLI, and the gate never looked there. The number is now
printed on every gate run as a ratchet: a floor the vendor-agnostic lane watches go down. The gate
still passes on it (a counter, not a threshold) so correct work is never refused (LAW 38). Rung 4."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "cloud-agnostic-gate"


def _gate(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(GATE)], env={**os.environ, "CLOUD_AGNOSTIC_ROOT": str(root)},
        capture_output=True, text=True,
    )


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "platform").mkdir()
    (tmp_path / "bin").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "bin" / "idp-caller").write_text("#!/bin/sh\nsid=$(oci vault secret list --compartment-id x)\n")
    (tmp_path / "bin" / "idp-comment-only").write_text("#!/bin/sh\n# oci os object get is not called here\necho hi\n")
    (tmp_path / "bin" / "idp-clean").write_text("#!/bin/sh\nrclone lsf :s3:bucket/\n")
    (tmp_path / "bin" / "idp-py").write_text('import subprocess\nsubprocess.run(["oci", "limits", "value", "list"])\n')
    (tmp_path / ".github" / "workflows" / "drill.yml").write_text("run: |\n  oci os object put --bucket-name b\n")
    (tmp_path / ".github" / "workflows" / "prose.yml").write_text("steps:\n  - name: oci cli and a headless browser\n    run: pip install oci-cli\n")
    return tmp_path


def test_callers_are_counted_and_comments_prose_and_clean_files_are_not(tmp_path):
    r = _gate(_tree(tmp_path))
    assert r.returncode == 0, r.stdout
    assert "cloud-agnostic-gate: 3 operator file(s) bound to the oci CLI" in r.stdout, r.stdout


def test_an_untracked_caller_in_a_checkout_is_not_counted(tmp_path):
    root = _tree(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "bin/idp-clean", "bin/idp-py", ".github/workflows/drill.yml"], cwd=root, check=True)
    r = _gate(root)
    assert "cloud-agnostic-gate: 2 operator file(s) bound to the oci CLI" in r.stdout, r.stdout


def test_the_live_number_is_the_one_the_audit_measured():
    """crew#309 audit, 2026-08-27: 23 scripts + 2 workflows call the CLI (a grep for files merely
    naming OCI said 36; env names and step titles are not calls). Moves only when a caller is removed
    or added — either way the change is deliberate and this line is edited in the same PR."""
    r = subprocess.run([str(GATE)], capture_output=True, text=True, cwd=ROOT)
    line = [l for l in r.stdout.splitlines() if "bound to the oci CLI" in l]
    assert line, r.stdout
    n = int(line[0].split(":")[1].split()[0])
    # 25 audited on main (crew#309); idp#441 adds two on merge (recover-drill.yml, bin/idp-recover-drill: the
    # clean-runner recovery drill reads the vault and R2 keys through the CLI until the primitive layer lands).
    assert n <= 27, f"{n} operator files call the oci CLI; the audited ceiling is 27 — a new one needs its own reason"
