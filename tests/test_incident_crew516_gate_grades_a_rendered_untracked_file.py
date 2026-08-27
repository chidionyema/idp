"""Incident 2026-08-27 (crew#516 CP6): bin/cloud-agnostic-gate reported one leak,
platform/<module>/backend_override.tf, a file bin/idp-oci-login renders for a login session with the
object-storage endpoint and credentials inside. It was never tracked and never shipped; the gate
graded the founder's laptop, not the platform. Rule: a file git does not hold is not scanned when the
root is a checkout; a plain directory (the fixtures) is scanned whole. Rung 4, incident test."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "cloud-agnostic-gate"
LEAK = 'endpoints = { s3 = "https://x.compat.objectstorage.uk-london-1.oraclecloud.com" }\n'


def _gate(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(GATE)], env={**os.environ, "CLOUD_AGNOSTIC_ROOT": str(root)},
        capture_output=True, text=True,
    )


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "platform" / "langfuse").mkdir(parents=True)
    (tmp_path / "platform" / "tracked.yaml").write_text("host: a.oraclecloud.com\n")
    (tmp_path / "platform" / "langfuse" / "backend_override.tf").write_text(LEAK)
    return tmp_path


def test_a_checkout_skips_the_untracked_rendered_file(tmp_path):
    root = _tree(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "platform/tracked.yaml"], cwd=root, check=True)
    r = _gate(root)
    assert r.returncode == 1, r.stdout
    assert "platform/tracked.yaml:1" in r.stdout
    assert "backend_override.tf" not in r.stdout, r.stdout


def test_a_plain_directory_is_scanned_whole(tmp_path):
    r = _gate(_tree(tmp_path))
    assert r.returncode == 1, r.stdout
    assert "platform/langfuse/backend_override.tf:1" in r.stdout, r.stdout
    assert "platform/tracked.yaml:1" in r.stdout


def test_the_rendered_override_is_gitignored():
    assert "platform/**/backend_override.tf" in (ROOT / ".gitignore").read_text()
