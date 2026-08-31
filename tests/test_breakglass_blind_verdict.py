"""A break-glass row whose probe never reached the workload reads BLIND, never FAIL.

Incident: run 33384482689 (2026-08-31) printed 13 FAIL rows for otto-parity that were all one
dead kubelet -- the probe never ran, but the receipt said the feature was broken. The grader
must separate measured-broken (FAIL) from cannot-measure (BLIND), and BLIND must still fail
the playbook: BLIND is never green.
"""

import pathlib
import shutil
import subprocess

BASH = shutil.which("bash") or "/bin/bash"

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-oke-break-glass"


def _helpers() -> str:
    src = SCRIPT.read_text()
    start = src.index('FAILED=""')
    end = src.index("show() {")
    return src[start:end]


def _run(snippet: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - runs the script under test's own helpers plus fixed literals
        [BASH, "-c", _helpers() + "\n" + snippet],
        capture_output=True,
        text=True,
        check=False,
    )


def test_watch_timeout_reads_blind_not_fail():
    r = _run(
        'step key-usable sh -c "echo error: watch closed before UntilWithoutRetry timeout; exit 1";'
        ' echo "BLIND_LIST=$BLIND"; echo "FAIL_LIST=$FAILED"'
    )
    assert r.stdout.startswith("BLIND"), r.stdout
    assert "BLIND_LIST= key-usable" in r.stdout, r.stdout
    assert "FAIL_LIST= key-usable" not in r.stdout, r.stdout
    assert "unmeasured" in r.stdout, r.stdout


def test_kubelet_dial_error_reads_blind():
    r = _run(
        'step git-in-pod sh -c "echo error dialing backend: dial tcp: i/o timeout; exit 1"; echo "BLIND_LIST=$BLIND"'
    )
    assert r.stdout.startswith("BLIND"), r.stdout
    assert "BLIND_LIST= git-in-pod" in r.stdout, r.stdout


def test_real_failure_still_reads_fail():
    r = _run(
        'step boot-line sh -c "echo no estate-state line in the gateway log; exit 1"; echo "FAIL_LIST=$FAILED"'
    )
    assert r.stdout.startswith("FAIL"), r.stdout
    assert "FAIL_LIST= boot-line" in r.stdout, r.stdout


def test_success_still_reads_ok():
    r = _run(
        'step gateway-ready sh -c "echo rolled out; exit 0"; echo "FAIL_LIST=$FAILED"; echo "BLIND_LIST=$BLIND"'
    )
    assert r.stdout.startswith("ok"), r.stdout
    assert "FAIL_LIST=\n" in r.stdout and "BLIND_LIST=\n" in r.stdout, r.stdout


def test_blind_alone_still_fails_the_playbook():
    src = SCRIPT.read_text()
    assert '[ -z "$FAILED" ] && [ -z "$BLIND" ]' in src
    assert "unmeasured:$BLIND" in src
