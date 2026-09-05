"""Branch policy: dev permissive, main strict (R39, R41; AGENTS.md [merge]).

Proved both ways in one run. The rule itself is a pure function
(conftest.pending_verdict), checked as a property over owners; the wiring
is checked by running pytest on the pending_unclaimed fixture directory
with and without SB_BDD_STRICT, which is exactly what ci.yml does.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import REPO_ROOT, STRICT_ENV, UNCLAIMED, pending_verdict

FIXTURE = REPO_ROOT / "sovereign" / "tests" / "fixtures" / "bdd" / "pending_unclaimed"


@pytest.mark.parametrize("owner", ["W1", "W6", "kini/w6-policy"])
def test_named_owner_skips_on_dev_and_fails_on_main(owner: str) -> None:
    mark = pytest.mark.pending("R0", owner=owner).mark
    assert pending_verdict(mark, strict=False)[0] == "skip"
    verdict, reason = pending_verdict(mark, strict=True)
    assert verdict == "fail" and "strict branch" in reason


@pytest.mark.parametrize("owner", [None, "", UNCLAIMED])
def test_missing_or_unclaimed_owner_fails_on_main_for_the_owner_reason(owner: str | None) -> None:
    kwargs = {} if owner is None else {"owner": owner}
    mark = pytest.mark.pending("R0", **kwargs).mark
    assert pending_verdict(mark, strict=False)[0] == "skip"
    verdict, reason = pending_verdict(mark, strict=True)
    assert verdict == "fail" and "no owner" in reason


def _run_fixture(strict: bool) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != STRICT_ENV}
    if strict:
        env[STRICT_ENV] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(FIXTURE), "-q", "-p", "no:cacheprovider"],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120,
    )


def test_the_wiring_skips_on_dev_and_fails_on_main() -> None:
    """The same directory, the same command ci.yml runs, two verdicts."""
    permissive = _run_fixture(strict=False)
    assert permissive.returncode == 0, permissive.stdout + permissive.stderr
    assert "1 skipped" in permissive.stdout, permissive.stdout

    strict = _run_fixture(strict=True)
    assert strict.returncode != 0, strict.stdout + strict.stderr
    assert "1 error" in strict.stdout and "no owner" in strict.stdout, strict.stdout
