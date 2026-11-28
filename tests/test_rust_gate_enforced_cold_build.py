"""A cold compile that outlives the judge's bound must not make the gate read 0 forever.

tests/rust_gate_enforced.py is the Optimus measure Greenlane runs under a 60 second bound in a
checkout that may have no compiled binary. A real cold build takes 1.5 to 2.5 minutes, so the
measure must start ONE detached build, report 0 honestly while it compiles, and read 1 on the
next reading. The fake `cargo` here stands in for the compiler only; the measure code, the lock
and the subprocess handling are the real ones.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import importlib.util
import os
import shutil
import stat
import time
from pathlib import Path

REAL = Path(__file__).resolve().parent / "rust_gate_enforced.py"

FAKE_CARGO = """#!/bin/sh
echo started >> "$FAKE_CARGO_LOG"
sleep "$FAKE_CARGO_SLEEP"
mkdir -p target/release
cat > target/release/meridian-gate <<'EOS'
#!/bin/sh
echo optimus.kernel.rust_invariant_gate_enforced=1
EOS
chmod +x target/release/meridian-gate
"""


def _sandbox(tmp_path: Path, monkeypatch, *, sleep_s: float, wait_s: float):
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    shutil.copy(REAL, root / "tests" / "rust_gate_enforced.py")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cargo = bin_dir / "cargo"
    cargo.write_text(FAKE_CARGO)
    cargo.chmod(cargo.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "cargo.log"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CARGO_LOG", str(log))
    monkeypatch.setenv("FAKE_CARGO_SLEEP", str(sleep_s))
    monkeypatch.delenv("MERIDIAN_GATE_BIN", raising=False)
    spec = importlib.util.spec_from_file_location(
        f"rge_{tmp_path.name}", root / "tests" / "rust_gate_enforced.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BUILD_WAIT_S = wait_s
    return module, root, log


def _wait_for(path: Path, seconds: float = 20.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def test_a_build_that_outlives_the_wait_reads_zero_then_one(tmp_path, monkeypatch):
    module, root, log = _sandbox(tmp_path, monkeypatch, sleep_s=1.5, wait_s=0.2)
    assert module.measure() == 0  # still compiling: honestly not enforced yet
    assert _wait_for(root / "target/release/meridian-gate")  # the build was NOT killed
    assert module.measure() == 1  # the next reading finds the finished binary
    assert log.read_text().count("started") == 1


def test_a_cold_build_that_fits_in_the_wait_reads_one_at_once(tmp_path, monkeypatch):
    module, _root, log = _sandbox(tmp_path, monkeypatch, sleep_s=0.1, wait_s=30)
    assert module.measure() == 1
    assert log.read_text().count("started") == 1


def test_a_concurrent_reading_does_not_start_a_second_build(tmp_path, monkeypatch):
    module, root, log = _sandbox(tmp_path, monkeypatch, sleep_s=1.5, wait_s=0.2)
    assert module.measure() == 0
    assert module.measure() == 0  # the lock is live: no competing compile
    assert _wait_for(root / "target/release/meridian-gate")
    assert log.read_text().count("started") == 1


def test_a_stale_lock_from_a_dead_build_is_retaken(tmp_path, monkeypatch):
    module, root, log = _sandbox(tmp_path, monkeypatch, sleep_s=0.1, wait_s=30)
    lock = root / "target" / ".meridian-gate-build.lock"
    lock.parent.mkdir()
    lock.write_text("999999")
    old = time.time() - module.LOCK_TTL_S - 60
    os.utime(lock, (old, old))
    assert module.measure() == 1
    assert log.read_text().count("started") == 1


def test_no_cargo_and_no_binary_reads_zero(tmp_path, monkeypatch):
    module, _root, log = _sandbox(tmp_path, monkeypatch, sleep_s=0.1, wait_s=30)
    monkeypatch.setenv("PATH", "/nonexistent")
    assert module.measure() == 0
    assert not log.exists()
