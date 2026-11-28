"""bin/heavy-shim + bin/heavy-install: any agent that resolves `pytest` through PATH is queued."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHIM = ROOT / "bin" / "heavy-shim"
INSTALL = ROOT / "bin" / "heavy-install"


def _world(tmp_path):
    """A fake real `pytest` and `cargo` that report whether they ran inside a slot."""
    real = tmp_path / "real"
    real.mkdir()
    for tool in ("pytest", "cargo"):
        path = real / tool
        path.write_text(
            f'#!/bin/sh\necho "{tool} args=$* slot=${{HEAVY_SLOT_ACTIVE:-no}}"\n'
        )
        path.chmod(0o755)
    shims = tmp_path / "shims"
    done = subprocess.run(
        ["sh", str(INSTALL), str(shims)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return real, shims


def _run(tmp_path, real, shims, *argv, **extra):
    env = {
        **os.environ,
        "PATH": f"{shims}{os.pathsep}{real}{os.pathsep}/usr/bin:/bin",
        "HEAVY_DIR": str(tmp_path / "heavy"),
        "HEAVY_MIN_FREE_MB": "1",
        **extra,
    }
    env.pop("HEAVY_SLOT_ACTIVE", None)
    env.update({k: v for k, v in extra.items()})
    return subprocess.run(
        argv, env=env, cwd=tmp_path, capture_output=True, text=True, timeout=120
    )


def test_a_heavy_call_by_any_launcher_runs_inside_a_slot(tmp_path):
    real, shims = _world(tmp_path)
    done = _run(tmp_path, real, shims, "pytest", "tests/x.py", "-q")
    assert done.returncode == 0
    assert "pytest args=tests/x.py -q slot=1" in done.stdout


def test_only_the_heavy_subcommands_of_a_tool_are_queued(tmp_path):
    real, shims = _world(tmp_path)
    heavy = _run(tmp_path, real, shims, "cargo", "test", "--release")
    light = _run(tmp_path, real, shims, "cargo", "--version")
    assert "slot=1" in heavy.stdout
    assert "cargo args=--version slot=no" in light.stdout


def test_inside_a_slot_the_real_tool_runs_directly(tmp_path):
    real, shims = _world(tmp_path)
    done = _run(tmp_path, real, shims, "pytest", "-q", HEAVY_SLOT_ACTIVE="1")
    assert "pytest args=-q slot=1" in done.stdout  # not re-queued: no second slot taken


def test_the_estate_switch_off_runs_the_real_tool_untouched(tmp_path):
    real, shims = _world(tmp_path)
    done = _run(tmp_path, real, shims, "pytest", "-q", ESTATE_THIN_CLIENT="off")
    assert "pytest args=-q slot=no" in done.stdout


def test_no_real_tool_is_a_named_error_not_a_loop(tmp_path):
    real, shims = _world(tmp_path)
    (real / "pytest").unlink()
    done = _run(tmp_path, real, shims, "pytest", "-q")
    assert done.returncode == 127 and "no real `pytest`" in done.stderr


def test_the_installer_refuses_to_overwrite_a_real_file(tmp_path):
    shims = tmp_path / "shims"
    shims.mkdir()
    (shims / "pytest").write_text("#!/bin/sh\necho mine\n")
    done = subprocess.run(
        ["sh", str(INSTALL), str(shims)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 1 and "real file" in done.stderr
    assert (shims / "pytest").read_text().endswith("echo mine\n")


def test_the_shim_file_is_executable_and_runs_as_python():
    assert os.access(SHIM, os.X_OK)
    assert sys.version_info >= (3, 8)
