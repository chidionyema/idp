"""PROOF_2's seal must be a signature, not a CLI boolean (A09/G06).

Measured 2026-11-19 on main: the `--founder-seal` flag passed PROOF_2 for
`.github/workflows/agent-sandbox.yml` with no founder identity, no signature and no
replay protection, while the same change without the flag was refused.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "verify_three_proofs.py"


def run(*args):
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_the_boolean_flag_no_longer_exists():
    result = run("--files", "README.md", "--founder-seal")
    assert result.returncode != 0, "a bare --founder-seal flag must not be accepted"
    assert "unrecognized arguments" in result.stderr or "invalid" in result.stderr


def test_a_guarded_path_without_a_signature_is_refused():
    result = run("--files", ".github/workflows/pr-age.yml")
    assert result.returncode != 0
    assert "Guarded path" in result.stdout or "Guarded path" in result.stderr
