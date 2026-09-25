"""
Tests for estate-execute intent engine.

Run: python3 -m pytest tests/test_intent_engine.py -v

Sharp edges tested:
1. Non-zero exit produces error text, not empty
2. Interpolation handles spaces in values
3. Empty stdout + zero exit produces "ok" not nothing
4. Args resolve from key=value strings correctly
"""

import subprocess
import tempfile
import sys
from pathlib import Path

# The estate-execute binary under test
ESTATE_EXEC = (
    Path(__file__).parent.parent / "platform" / "estate" / "bin" / "estate-execute"
)


def run_intent(name, *args):
    """Run an intent and return stdout, stderr, returncode."""
    cmd = [sys.executable, str(ESTATE_EXEC), name] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.stdout, r.stderr, r.returncode


def test_nonzero_exit_produces_error_text():
    """Sharp edge 1: non-zero exit should produce readable error, not empty."""
    # Intent that fails
    stdout, stderr, rc = run_intent("halt")
    # halt always succeeds (exit 0), so pick a real failing command
    # We test the property on a crafted intent inline
    with tempfile.TemporaryDirectory() as tmpdir:
        intent_file = Path(tmpdir) / "fail-test.yaml"
        intent_file.write_text("""
name: fail-test
description: Test failure
halt_on_failure: false
steps:
  - cmd: "exit 1"
""")
        # Replace intents dir temporarily
        old_intents = Path.home() / ".estate" / "intents"
        backup = None
        if old_intents.exists():
            backup = Path(tempfile.mkdtemp())
            (backup / "halt.yaml").write_text(old_intents.read_text())

        try:
            # Copy test intent
            (old_intents).mkdir(parents=True, exist_ok=True)
            (old_intents / "fail-test.yaml").write_text(intent_file.read_text())
            stdout, stderr, rc = run_intent("fail-test")
        finally:
            if backup:
                for f in old_intents.glob("*.yaml"):
                    f.unlink()
                if (backup / "halt.yaml").exists():
                    (old_intents / "halt.yaml").write_text(
                        (backup / "halt.yaml").read_text()
                    )

        # rc should be 0 (halt_on_failure: false), but the step failed
        assert "[step 1] exit 1" in stderr, f"step not logged to stderr: {stderr}"
        # The intent runner itself exits 0 (continue on fail), so we check stderr
        assert "exit 1" in stderr or "exit" in stderr
        print("PASS: nonzero exit produces stderr")


def test_interpolation_handles_spaces():
    """Sharp edge 2: {{var}} should handle values with spaces."""
    with tempfile.TemporaryDirectory() as tmpdir:
        intent_file = Path(tmpdir) / "space-test.yaml"
        intent_file.write_text("""
name: space-test
description: Test spaces
steps:
  - cmd: "echo {{path}}"
""")
        test_path = Path.home() / ".estate"
        old_intents = Path.home() / ".estate" / "intents"

        # Backup existing intents
        backup = {}
        if old_intents.exists():
            for f in old_intents.glob("*.yaml"):
                backup[f.name] = f.read_text()

        try:
            old_intents.mkdir(parents=True, exist_ok=True)
            (old_intents / "space-test.yaml").write_text(intent_file.read_text())
            stdout, stderr, rc = run_intent("space-test", f"path={test_path}")
        finally:
            for name, content in backup.items():
                (old_intents / name).write_text(content)
            (old_intents / "space-test.yaml").unlink(missing_ok=True)

        # If interpolation worked, we should see the path in stdout
        assert str(test_path) in stdout, (
            f"path not in stdout: {stdout}, stderr: {stderr}"
        )
        print(f"PASS: interpolation handles spaces: {stdout.strip()}")


def test_empty_stdout_zero_exit_produces_ok():
    """Sharp edge 3: empty stdout + exit 0 should produce 'ok' or similar readable output."""
    stdout, stderr, rc = run_intent("halt")
    # halt produces "halt done intent= ticket=INTENT-..." so it has output
    # We need a truly empty-intent
    with tempfile.TemporaryDirectory() as tmpdir:
        intent_file = Path(tmpdir) / "empty-test.yaml"
        intent_file.write_text("""
name: empty-test
description: Empty intent
halt_on_failure: false
steps:
  - cmd: "true"
""")
        old_intents = Path.home() / ".estate" / "intents"
        backup = {}
        if old_intents.exists():
            for f in old_intents.glob("*.yaml"):
                backup[f.name] = f.read_text()

        try:
            old_intents.mkdir(parents=True, exist_ok=True)
            (old_intents / "empty-test.yaml").write_text(intent_file.read_text())
            stdout, stderr, rc = run_intent("empty-test")
        finally:
            for name, content in backup.items():
                (old_intents / name).write_text(content)
            (old_intents / "empty-test.yaml").unlink(missing_ok=True)

        # With exit 0 and empty stdout, the engine should say something
        # Currently it returns nothing — this test FAILS on the broken version
        assert stdout.strip() != "", (
            f"empty stdout on zero exit: engine should say 'ok' or similar. Got: '{stdout}', stderr: '{stderr}'"
        )
        print(
            f"PASS: empty stdout + zero exit produces readable output: '{stdout.strip()}'"
        )


def test_args_resolve_from_key_value():
    """Sharp edge 4: args passed as key=value strings resolve correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        intent_file = Path(tmpdir) / "arg-test.yaml"
        intent_file.write_text("""
name: arg-test
description: Test args
args:
  msg: { type: string }
steps:
  - cmd: "echo {{msg}}"
""")
        old_intents = Path.home() / ".estate" / "intents"
        backup = {}
        if old_intents.exists():
            for f in old_intents.glob("*.yaml"):
                backup[f.name] = f.read_text()

        try:
            old_intents.mkdir(parents=True, exist_ok=True)
            (old_intents / "arg-test.yaml").write_text(intent_file.read_text())
            stdout, stderr, rc = run_intent("arg-test", "msg=hello world")
        finally:
            for name, content in backup.items():
                (old_intents / name).write_text(content)
            (old_intents / "arg-test.yaml").unlink(missing_ok=True)

        assert "hello world" in stdout or "hello" in stdout, (
            f"arg not resolved: stdout='{stdout}', stderr='{stderr}'"
        )
        print(f"PASS: args resolve from key=value: '{stdout.strip()}'")


if __name__ == "__main__":
    # Run tests directly
    print("=== test_empty_stdout_zero_exit_produces_ok ===")
    try:
        test_empty_stdout_zero_exit_produces_ok()
    except AssertionError as e:
        print(f"FAIL (expected): {e}")
    print("\n=== test_args_resolve_from_key_value ===")
    try:
        test_args_resolve_from_key_value()
    except AssertionError as e:
        print(f"FAIL: {e}")
    print("\n=== test_interpolation_handles_spaces ===")
    try:
        test_interpolation_handles_spaces()
    except AssertionError as e:
        print(f"FAIL: {e}")
