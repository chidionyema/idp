"""crew#583: bin/law32-gate failed the PR that introduced bin/lib/receipt_age.py, demanding a
docs/tutorials/demo page for it (offline-gate 33189215410). The module is 0644 and imported by four readers;
it is not a command anyone runs, so that page would have been prose about nothing -- a guard
refusing correct work, which LAW 38 calls an outage.

Check 1 of the gate has always read "every EXECUTABLE added under bin/" in its own docstring; the
code never looked at the bit. It does now. These tests pin the exemption to exactly that bit, so it
cannot widen into a way of shipping a feature with no demo by hiding it under bin/lib.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin/law32-gate"


def _gate(*added: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE), "--added", *added], capture_output=True, text=True)


def test_an_imported_library_needs_no_demo_page():
    r = _gate("bin/lib/receipt_age.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "receipt_age" not in r.stdout, r.stdout


def test_the_same_file_with_the_executable_bit_is_a_command_again(tmp_path):
    """The exemption is the mode bit, not the directory. chmod +x and the demo is owed again.
    Proved on a copy of the tree: the first version chmod'ed the real file, and under `-n auto`
    the sibling test read it executable in another worker (red on main from ed198a3)."""
    import shutil
    (tmp_path / "bin/lib").mkdir(parents=True)
    for d in ("tutorials/demo", "how-to/onboarding"):
        (tmp_path / "docs" / d).mkdir(parents=True)
    shutil.copy(GATE, tmp_path / "bin/law32-gate")
    f = tmp_path / "bin/lib/receipt_age.py"
    shutil.copy(ROOT / "bin/lib/receipt_age.py", f)
    f.chmod(0o644)
    r = subprocess.run([sys.executable, str(tmp_path / "bin/law32-gate"), "--added", "bin/lib/receipt_age.py"], capture_output=True, text=True)
    assert "receipt_age.py: no docs/tutorials/demo" not in r.stdout, r.stdout + r.stderr
    f.chmod(0o755)
    r = subprocess.run([sys.executable, str(tmp_path / "bin/law32-gate"), "--added", "bin/lib/receipt_age.py"], capture_output=True, text=True)
    assert r.returncode == 1 and "receipt_age.py: no docs/tutorials/demo" in r.stdout, r.stdout + r.stderr


def test_a_name_with_no_file_behind_it_is_still_graded():
    """bin/idp-ci proves the gate both ways with bin/feature-with-no-pages, which does not exist on
    disk. If a missing path were read as 'not executable, therefore a library', that proof would
    silently stop proving anything and the gate would pass everything."""
    assert not (ROOT / "bin/feature-with-no-pages").exists()
    r = _gate("bin/feature-with-no-pages")
    assert r.returncode == 1 and "feature-with-no-pages: no docs/tutorials/demo" in r.stdout, r.stdout + r.stderr


def test_a_real_command_with_its_pages_still_passes():
    assert (ROOT / "bin/supply-chain").exists() and os.access(ROOT / "bin/supply-chain", os.X_OK)
    assert _gate("bin/supply-chain").returncode == 0
