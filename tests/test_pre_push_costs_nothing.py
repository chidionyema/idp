"""A push that moves nothing must cost nothing (#7503).

Measured 2026-11-11: 53% of lane-submit runs in 30d were not-ok, and exit 124 (the 100 s ceiling)
was the top outcome. Every retry and status probe launched the full pre-push gate -- 40-60 s of
CPU and disk -- even when the remote already had the commit. On a machine at 1013 MB free that is
the difference between a push and a deadlock.

These tests read the decision out of the SHIPPED hook. They do not restate the rule here: the hook
source is parsed and its skip logic is executed with the ref tuples git actually sends.
"""

import re
import subprocess
from pathlib import Path

REPO = Path("/Users/roseonyema/Documents/code/idp")
HOOK = REPO / ".githooks" / "pre-push"
ZERO = "0" * 40


def _src() -> str:
    assert HOOK.is_file(), f"the pre-push hook is missing at {HOOK}"
    return HOOK.read_text()


def _extract_fn(src: str, name: str) -> str:
    """Pull one bash function body out of the shipped hook, verbatim."""
    pat = re.compile(rf"^{name}\(\) \{{.*?^\}}", re.S | re.M)
    m = pat.search(src)
    assert m, f"{name}() is not in the shipped hook — the fix is missing"
    return m.group(0)


def test_the_hook_ships_the_skip_and_the_offload():
    src = _src()
    assert "_free_to_skip" in src, "no _free_to_skip in the shipped hook"
    assert re.search(r"^\s*if _free_to_skip; then", src, re.M), (
        "the hook never calls _free_to_skip — the check exists but is not wired"
    )
    assert "Greenlane CI" in src, "no low-disk offload in the shipped hook"


def test_nothing_to_push_exits_zero(tmp_path):
    """Delete-only or already-identical tuples: the gate must not run at all."""
    fn = _extract_fn(_src(), "_free_to_skip")
    script = f'set -uo pipefail\n{fn}\npush_refs="$(printf \'%s\' "$1")"\nif _free_to_skip; then echo SKIP; else echo GATE; fi\n'
    cases = {
        "identical": "refs/heads/lane/x abc123 refs/heads/lane/x abc123\n",
        "delete": f"(delete) {ZERO} refs/heads/lane/x abc123\n",
        "main-is-greenlane": "refs/heads/main abc123 refs/heads/main def456\n",
        "queue-is-greenlane": "refs/heads/queue/a abc123 refs/heads/queue/a def456\n",
    }
    for name, refs in cases.items():
        r = subprocess.run(
            ["bash", "-c", script, "_", refs],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert r.returncode == 0, f"{name}: bash failed: {r.stderr[:400]}"
        assert "SKIP" in r.stdout, (
            f"{name}: the hook would pay the gate for a push that moves nothing"
        )


def test_real_work_still_runs_the_gate():
    """A genuinely new commit on a lane branch must NOT be skipped — the gate still bites."""
    fn = _extract_fn(_src(), "_free_to_skip")
    script = f'set -uo pipefail\n{fn}\npush_refs="$(printf \'%s\' "$1")"\nif _free_to_skip; then echo SKIP; else echo GATE; fi\n'
    refs = f"refs/heads/lane/x {'b' * 40} refs/heads/lane/x {'a' * 40}\n"
    r = subprocess.run(
        ["bash", "-c", script, "_", refs], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr[:400]
    assert "GATE" in r.stdout, (
        "a real new commit was skipped — the hook stopped gating pushes"
    )


def test_the_hook_is_valid_bash():
    """A syntax error in the hook would make every push fail — it must parse."""
    r = subprocess.run(
        ["bash", "-n", str(HOOK)], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, f"the shipped hook does not parse: {r.stderr[:600]}"


def test_the_low_disk_offload_threshold_is_stated():
    """The offload must name its number, not fire on a vibe."""
    m = re.search(r"-lt\s+(\d+)", _src())
    assert m, "the low-disk offload has no numeric threshold"
    assert int(m.group(1)) >= 1500, "the offload threshold is below the executor floor"
