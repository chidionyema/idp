"""bin/language-gate proves it can fail before any lane is graded by it.

The founder's ruling (2026-10-30): Rust over Python for new estate capability code unless
the reason is compelling, and written down -- not a habit, not a verbal mandate nobody
checks. bin/estate-read and bin/estate-patch (idp#7585) shipped as stdlib Python hours
before this gate existed, with no such reason on record; this is the mechanical enforcement
so that does not repeat silently.

Each test runs the real script (not a re-implementation) against a throwaway git repo, the
same shape as tests/test_read_write_boundary.py uses for bin/estate-read/estate-patch.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "bin" / "language-gate"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _init(repo: Path) -> None:
    _git(repo, "init", "-q")
    # A CI runner has no global git identity, so every commit below failed there (10/10, reproduced
    # 2026-10-30 with GIT_CONFIG_GLOBAL=/dev/null) while passing on a machine that has one. Same
    # repo-local identity tests/test_worker_pool.py sets.
    _git(repo, "config", "user.email", "agent@estate")
    _git(repo, "config", "user.name", "agent")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "base")
    _git(repo, "tag", "base_point")


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _run_gate(
    repo: Path, base: str = "base_point", head: str = "HEAD"
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), base, head],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_new_python_file_without_trailer_is_refused(tmp_path):
    _init(tmp_path)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "newtool.py").write_text("print('hi')\n")
    _commit_all(tmp_path, "add newtool")
    result = _run_gate(tmp_path)
    assert result.returncode == 1, result.stderr
    assert "bin/newtool.py" in result.stderr


def test_new_python_file_with_trailer_is_allowed(tmp_path):
    _init(tmp_path)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "newtool.py").write_text("print('hi')\n")
    _commit_all(
        tmp_path, "add newtool\n\nLanguage-Exception: bin/newtool.py -- test fixture\n"
    )
    result = _run_gate(tmp_path)
    assert result.returncode == 0, result.stderr


def test_a_new_non_python_file_needs_no_trailer(tmp_path):
    _init(tmp_path)
    (tmp_path / "main.rs").write_text("fn main() {}\n")
    _commit_all(tmp_path, "add rust file")
    result = _run_gate(tmp_path)
    assert result.returncode == 0, result.stderr


def test_modifying_an_existing_python_file_needs_no_trailer(tmp_path):
    _init(tmp_path)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "existing.py").write_text("x = 1\n")
    _commit_all(tmp_path, "add existing.py")
    _git(tmp_path, "tag", "with_existing")
    (tmp_path / "bin" / "existing.py").write_text("x = 2\n")
    _commit_all(tmp_path, "modify existing.py, no trailer")
    result = _run_gate(tmp_path, base="with_existing")
    assert result.returncode == 0, result.stderr


def test_a_new_test_file_is_exempt(tmp_path):
    _init(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_new.py").write_text("def test_x():\n    pass\n")
    _commit_all(tmp_path, "add test, no trailer")
    result = _run_gate(tmp_path)
    assert result.returncode == 0, result.stderr


def test_extensionless_shebang_python_file_without_trailer_is_refused(tmp_path):
    # bin/'s own convention is an extensionless script with a #!/usr/bin/env python3 shebang
    # (bin/estate-read, bin/estate-patch, bin/language-gate itself) -- a `*.py`-only filter
    # would miss exactly the files this gate exists to catch.
    _init(tmp_path)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "newtool").write_text('#!/usr/bin/env python3\nprint("hi")\n')
    _commit_all(tmp_path, "add extensionless python tool")
    result = _run_gate(tmp_path)
    assert result.returncode == 1, result.stderr
    assert "bin/newtool" in result.stderr


def test_extensionless_non_python_shebang_needs_no_trailer(tmp_path):
    _init(tmp_path)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "newtool2").write_text("#!/usr/bin/env bash\necho hi\n")
    _commit_all(tmp_path, "add bash tool, no trailer")
    result = _run_gate(tmp_path)
    assert result.returncode == 0, result.stderr


def _greenlane_squash(repo: Path, lane_trailer: str) -> None:
    """The exact shape the Greenlane lands (greenlane/github.py): the lane's tree squashed onto
    base as one commit whose message is only the subject and `Greenlane-Head: <lane head>`."""
    _git(repo, "checkout", "-q", "-b", "lane", "base_point")
    (repo / "bin").mkdir()
    (repo / "bin" / "newtool").write_text('#!/usr/bin/env python3\nprint("hi")\n')
    _commit_all(repo, "add newtool" + (f"\n\n{lane_trailer}\n" if lane_trailer else ""))
    lane_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "checkout", "-q", "--detach", "base_point")
    _git(repo, "checkout", "-q", lane_head, "--", "bin/newtool")
    _commit_all(repo, f"add newtool\n\nGreenlane-Head: {lane_head}\n")


def test_greenlane_squash_reads_the_lane_trailer(tmp_path):
    # Found live 2026-10-30, queue/b4693: the squash dropped the trailer and the gate refused the
    # commit that introduced it. The lane's own message carries the reason; the gate must read it.
    _init(tmp_path)
    _greenlane_squash(tmp_path, "Language-Exception: bin/newtool -- test fixture")
    result = _run_gate(tmp_path)
    assert result.returncode == 0, result.stderr


def test_greenlane_squash_without_lane_trailer_is_still_refused(tmp_path):
    # Following Greenlane-Head must not become a way around the gate.
    _init(tmp_path)
    _greenlane_squash(tmp_path, "")
    result = _run_gate(tmp_path)
    assert result.returncode == 1, result.stderr
    assert "bin/newtool" in result.stderr


def test_trailer_must_name_the_exact_path(tmp_path):
    _init(tmp_path)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "newtool.py").write_text("print('hi')\n")
    _commit_all(
        tmp_path, "add newtool\n\nLanguage-Exception: bin/other.py -- wrong path\n"
    )
    result = _run_gate(tmp_path)
    assert result.returncode == 1, result.stderr
    assert "bin/newtool.py" in result.stderr
