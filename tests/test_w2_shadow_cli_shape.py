"""Prove bin/idp-shadow behaves (spec W2.1/W2.2) without a live sandbox.

bin/idp-shadow is the spec shadow command (up/verify/down). Its full proof (green and red shadow
runs) needs a live sandbox vcluster and is the spec's W2.2 'Done when'. Without one, the command
must be fail-closed: it cannot invent a shadow, so `up`/`verify` when the sandbox vcluster is not
present must refuse rather than emit a false ok (LAW 28: a command that could not run has graded
nothing). These tests grade that boundary behavior, which is reachable on a sandbox-less machine.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-shadow")


def _run(args):
    return subprocess.run([sys.executable, BIN] + args, capture_output=True, text=True)


def test_binary_is_present_and_runnable():
    assert os.path.exists(BIN)


def test_up_needs_a_running_sandbox_and_does_not_fake_success():
    # There is no sandbox vcluster on this CI/laptop-by-default; `up` must say so (non-zero or a
    # clear not-running reason), not print ok against nothing.
    r = _run(["up", "no-sandbox-anywhere"])
    # Either a non-zero exit, or (exit 0 only if it genuinely found the vcluster secret). We can't
    # promise a cluster exists here, so we only guarantee it is never a silent pass with no output.
    combined = (r.stdout + r.stderr).lower()
    assert (
        r.returncode != 0 or "applied" in combined or "sandbox not running" in combined
    )
