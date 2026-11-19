"""Executable producer-preparation regressions; external tools are explicit doubles."""

import os
import subprocess
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "bin/idp-machine-submit"
MARKER = "# ---- 2. Deterministic preparation"
BLOCK = MARKER + ENGINE.read_text().split(MARKER, 1)[1]


def call(cwd, *args, **kwargs):
    return subprocess.run(
        args, cwd=cwd, text=True, capture_output=True, check=True, **kwargs
    )


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    call(r, "git", "init", "-q")
    call(r, "git", "config", "user.name", "test")
    call(r, "git", "config", "user.email", "test@example.org")
    for p in ["bin", "catalog", "tests"]:
        (r / p).mkdir()
    (r / "tests/a.py").write_text("a=1\n")
    (r / "tests/b.py").write_text("b=1\n")
    (r / "catalog/estate-capability-registry.json").write_text("{}\n")
    (r / "bin/capability-index").write_text(
        'from pathlib import Path\n'
        'Path("catalog/estate-capability-registry.json").write_text('
        '"fresh\\n")\n'
    )
    (r / "bin/registry-gate").write_text(
        'from pathlib import Path\n'
        'assert "fresh" in Path("catalog/estate-capability-registry.json").read_text()\n'
    )
    call(r, "git", "add", ".")
    call(r, "git", "commit", "-qm", "base")
    base = call(r, "git", "rev-parse", "HEAD").stdout.strip()
    tool = tmp_path / "tools"
    tool.mkdir()
    fake = tool / "ruff"
    fake.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$RUFF_LOG"\n'
        'case "$*" in *"$RUFF_FAIL"*) [ -z "$RUFF_FAIL" ] || exit 1;; esac\n'
        '[ "$1" != "--version" ] || echo "ruff 0.15.18"\nexit 0\n'
    )
    fake.chmod(0o755)
    return r, base, tool, tmp_path / "ruff.log"


def run_block(repo, fail=""):
    r, base, tool, log = repo
    env = dict(os.environ, BASE_SHA=base, RUFF_LOG=str(log), RUFF_FAIL=fail)
    env["PATH"] = str(tool) + ":" + env["PATH"]
    return subprocess.run(
        ["bash", "-ec", 'say() { printf "%s\\n" "$*"; }\n' + BLOCK],
        cwd=r,
        env=env,
        text=True,
        capture_output=True,
    )


def test_staged_only_is_normalized(repo):
    r, _, _, log = repo
    (r / "tests/a.py").write_text("a=2\n")
    call(r, "git", "add", "tests/a.py")
    p = run_block(repo)
    assert p.returncode == 0, p.stderr
    assert "format -- tests/a.py" in log.read_text()
    assert "tests/b.py" not in log.read_text()


@pytest.mark.parametrize("failure", ["format -- tests/a.py", "check --select"])
def test_ruff_failure_halts_before_staging(repo, failure):
    r, _, _, _ = repo
    (r / "tests/a.py").write_text("a=2\n")
    p = run_block(repo, failure)
    assert p.returncode != 0
    assert "PREPARED" not in p.stdout
    assert call(r, "git", "diff", "--cached", "--name-only").stdout == ""


def test_registry_regenerated_and_staged(repo):
    r, _, _, _ = repo
    (r / "bin/input").write_text("change")
    p = run_block(repo)
    assert p.returncode == 0, p.stderr
    assert "fresh" in (r / "catalog/estate-capability-registry.json").read_text()
    assert set(call(r, "git", "diff", "--cached", "--name-only").stdout.splitlines()) == {
        "bin/input",
        "catalog/estate-capability-registry.json",
    }


def test_registry_failure_halts(repo):
    r, _, _, _ = repo
    (r / "bin/registry-gate").write_text("raise SystemExit(7)\n")
    p = run_block(repo)
    assert p.returncode != 0
    assert "PREPARED" not in p.stdout


def test_deleted_python_staged_without_ruff(repo):
    r, _, _, log = repo
    (r / "tests/a.py").unlink()
    p = run_block(repo)
    assert p.returncode == 0, p.stderr
    assert not log.exists()
    assert call(r, "git", "diff", "--cached", "--name-status").stdout.startswith("D\t")


def test_symlink_refused(repo):
    r, _, _, _ = repo
    (r / "tests/link.py").symlink_to("/etc/passwd")
    p = run_block(repo)
    assert p.returncode != 0
    assert "unsafe preparation path" in p.stderr


def test_generated_out_of_scope_file_refused(repo):
    r, _, _, _ = repo
    (r / "bin/capability-index").write_text(
        'from pathlib import Path\n'
        'Path("catalog/estate-capability-registry.json").write_text("fresh")\n'
        'Path("unplanned.txt").write_text("oops")\n'
    )
    p = run_block(repo)
    assert p.returncode != 0
    assert "out-of-scope" in p.stderr
    assert call(r, "git", "diff", "--cached", "--name-only").stdout == ""


def test_staged_then_reverted_worktree_reconciles_index(repo):
    r, _, _, _ = repo
    (r / "tests/a.py").write_text("a=2\n")
    call(r, "git", "add", "tests/a.py")
    (r / "tests/a.py").write_text("a=1\n")
    p = run_block(repo)
    assert p.returncode == 0, p.stderr
    assert call(r, "git", "diff", "--cached", "--name-only").stdout == ""


def test_wrong_formatter_version_is_refused(repo):
    r, _, tool, _ = repo
    (r / "tests/a.py").write_text("a=2\n")
    (tool / "ruff").write_text('#!/bin/sh\necho ruff 0.1.0\n')
    p = run_block(repo)
    assert p.returncode != 0
    assert "incorrect Ruff version" in p.stderr
