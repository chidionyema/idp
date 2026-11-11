"""Rust is a first-class language in the pre-push gate, checked by cargo.

The gate classifies every file in the pushed diff. A `.rs` file is Rust, and the real check is
`cargo check` on the nearest crate (a `.rs` file cannot be parsed in isolation: crate siblings
are reached via `use crate::`). Before this class existed, the estate's own DX crate
(`platform/dx/**`) was refused when pushed: "readable as neither shell nor Python".

The repair gives Rust its own class and a real checker. A crate that does not type-check is
still refused, a `.rs` file sitting outside any crate is refused, and a missing cargo is a
REFUSAL, never a silent pass. The gate is widened, not weakened.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-push"

STUB = """#!/bin/sh
exit 0
"""

CARGO_TOML = """[package]
name = "probe"
version = "0.1.0"
edition = "2021"
"""

VALID_RS = """pub fn add(a: u64, b: u64) -> u64 {
    a + b
}
"""

BROKEN_RS = """pub fn add(a: u64, b: u64) -> u64 {
    a + mismatched_identifier
}
"""


def git(cwd: Path, *a: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


@pytest.fixture
def clone(tmp_path):
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo is not installed: the Rust class cannot be exercised")
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    hooks = work / ".hooks"
    hooks.mkdir()
    shutil.copy(HOOK, hooks / "pre-push")
    git(work, "config", "core.hooksPath", str(hooks))
    (work / "bin").mkdir()
    ci = work / "bin" / "idp-ci"
    ci.write_text(STUB)
    ci.chmod(0o755)
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt", "bin/idp-ci")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    # A minimal, dependency-free crate so `cargo check` needs no network.
    crate = work / "crate"
    crate.mkdir()
    (crate / "Cargo.toml").write_text(CARGO_TOML)
    src = crate / "src"
    src.mkdir()
    (src / "lib.rs").write_text(VALID_RS)
    git(work, "add", "crate")
    git(work, "commit", "-q", "-m", "crate base")
    return work


def commit(work: Path, name: str, content: str) -> None:
    (work / name).write_text(content)
    git(work, "add", name)
    git(work, "commit", "-q", "-m", name)


def push(work: Path, branch: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IDP_CI_")}
    return git(work, "push", "origin", f"HEAD:{branch}", env=env, check=False)


def test_a_valid_rust_crate_is_accepted(clone):
    commit(clone, "crate/src/lib.rs", VALID_RS + "\n")
    p = push(clone, "scratch/rs-ok")
    assert p.returncode == 0, p.stderr


def test_a_broken_rust_crate_is_refused(clone):
    commit(clone, "crate/src/lib.rs", BROKEN_RS)
    p = push(clone, "scratch/rs-broken")
    assert p.returncode != 0, p.stderr
    assert "cargo check failed" in p.stderr, p.stderr


def test_a_rust_file_outside_any_crate_is_refused(clone):
    commit(clone, "loose.rs", VALID_RS)
    p = push(clone, "scratch/rs-loose")
    assert p.returncode != 0, p.stderr
    assert "outside any crate" in p.stderr, p.stderr
