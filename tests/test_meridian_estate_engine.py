"""The compiled FLOW -> DOF -> LEGION -> KARMA engine, proved by its own cargo tests.

The workspace lives in crates/meridian-estate-engine. The root pytest suite is the one runner
the estate's CI already executes, so it is the door that makes a red unit in the engine block a
merge: this test runs the workspace's own `cargo test` and, once the army binary exists, requires
its sentinel line. A workspace member that is missing is simply not run yet; a member that is
present and red fails here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "crates" / "meridian-estate-engine"
SENTINEL = "optimus.estate.karma_dof_legion_flow_unified=1"


def _cargo() -> str:
    found = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
    if Path(found).exists():
        return found
    if os.environ.get("CI"):
        pytest.fail("cargo is missing on a CI runner: the engine cannot be proved")
    pytest.skip("cargo is not installed on this machine")


def _run(args: list[str], tmp_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CARGO_TARGET_DIR": str(tmp_path / "target")}
    return subprocess.run(
        [_cargo(), *args],
        cwd=ENGINE,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


@pytest.mark.skipif(
    not (ENGINE / "Cargo.toml").exists(), reason="engine workspace not landed"
)
def test_engine_workspace_tests_pass(tmp_path: Path) -> None:
    # Cargo.lock lands with the last member; once it exists the build must not drift from it.
    flags = ["--locked"] if (ENGINE / "Cargo.lock").exists() else []
    done = _run(["test", "--workspace", *flags], tmp_path)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    assert "test result: ok" in done.stdout


@pytest.mark.skipif(
    not (ENGINE / "crates" / "meridian-army" / "src" / "main.rs").exists(),
    reason="army binary not landed",
)
def test_army_prints_unified_sentinel(tmp_path: Path) -> None:
    done = _run(["run", "-q", "--locked", "-p", "meridian-army"], tmp_path)
    assert done.returncode == 0, done.stderr[-3000:]
    assert done.stdout.strip() == SENTINEL
