# must-pass fixture for the executes gate: it leaves its own process and grades what came back.
import subprocess


def test_the_guard_refuses_a_missing_row() -> None:
    out = subprocess.run(["bin/always-on-guard"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
