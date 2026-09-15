"""P0-03 (idp#3525 CP10, spec section 9). ACCEPT, verbatim (features/battalion/
cp10-p0-prerequisites.feature): "the UX-02 fault-injection suite covering every enumerated
edge case ... is green before any 'reliable as electricity' claim is made. And until every
enumerated edge case has a passing degradation test, that claim is not verified." METHOD: this
test runs UX-02's own suite (test_ux02_edge_case_matrix.py, CP9) as a real subprocess through
`python -m pytest` -- reusing pytest itself as the proven test-running platform rather than
re-implementing one -- and asserts it exits green. A regression in that suite after CP9 fails
this test before any downstream "reliable as electricity" claim can be made, not after.

sys.executable (not a bare "python"/"pytest") is used deliberately: this box's bare `python`
resolves to an interpreter without z3-solver installed, which fails even pre-existing,
already-merged verifier tests unrelated to UX-02 (CP9 evidence, idp#3525). sys.executable is
always the interpreter already running this test, so the suite runs the same way it is being
verified right now.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

UX02_SUITE = Path(__file__).resolve().parent / "test_ux02_edge_case_matrix.py"


def test_ux02_fault_injection_suite_is_green() -> None:
    assert UX02_SUITE.exists(), (
        "P0-03: UX-02's own suite is missing -- nothing to verify green"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(UX02_SUITE)],
        capture_output=True,
        text=True,
        timeout=55,
    )
    assert result.returncode == 0, (
        "P0-03: UX-02's fault-injection suite is not green -- 'reliable as electricity' is "
        f"not a verified claim until it is.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
