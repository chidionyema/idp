"""The gate repairs what a machine can repair before it judges.

2026-11-19: a release failed on ruff formatting and a stale registry after 86 tests
passed. The PR was discovering defects the gate could have removed. bin/idp-ci --fix is
that correction; this test fails if the repair stops happening.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
UGLY = "def add(a,b):\n    return a+b\nprint( add(1,2) )\n"
PRETTY = "def add(a, b):\n    return a + b\n\n\nprint(add(1, 2))\n"


def probe(tmp_path):
    rel = "tests/.fmt_probe_%s.py" % tmp_path.name.replace("-", "")[:8]
    f = REPO / rel
    f.write_text(UGLY)
    return rel, f


def run_fix(rel):
    return subprocess.run(
        ["bash", str(REPO / "bin" / "idp-ci"), "--fix"],
        cwd=REPO,
        env={"IDP_CI_FIX_FILES": rel, "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
    )


def test_unformatted_is_repaired(tmp_path):
    rel, f = probe(tmp_path)
    try:
        r = run_fix(rel)
        assert r.returncode == 3, r.stdout + r.stderr
        assert "fixed  ruff" in r.stdout
        assert f.read_text() == PRETTY
    finally:
        f.unlink()


def test_a_repair_is_idempotent(tmp_path):
    rel, f = probe(tmp_path)
    try:
        assert run_fix(rel).returncode == 3
        r2 = run_fix(rel)
        assert r2.returncode == 0, r2.stdout + r2.stderr
        assert "fixed  ruff" not in r2.stdout
    finally:
        f.unlink()
