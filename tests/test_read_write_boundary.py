"""The read/write boundary proves it can fail before any agent is graded by it.

bin/estate-read and bin/estate-patch are the two doors an agent uses to look at and change
estate code: a windowed, receipt-issuing reader and a receipt-gated, AST-checked patcher.
platform/estate/harness/fs_guard.py is the heuristic filter wired into
platform/estate/bin/estate-execute, right before its subprocess.run, so a raw `cat`,
`sed -i` or `>>` inside one command string cannot route around those two doors.

This file is the CI gate for that contract (the estate's own `gate_X` convention is to be a
pytest file under tests/ that bin/idp-tests-for collects, not a bash function nobody calls
from bin/idp-ci -- idp-ci's rungs are all inline; see tests/test_schema_conformance.py for the
same pattern against a different door). Each test is a reason to distrust the boundary:

  * a door that reads its own stale law              -> test_raw_markdown_read_is_blocked
  * a patch applied blind, with nothing read first   -> test_patch_without_receipt_is_refused
  * a receipt that lets you edit a file you never saw -> test_receipt_is_bound_to_the_exact_file_and_hash
  * a patch that compiles to broken code              -> test_broken_ast_patch_is_rejected_and_file_untouched
  * the one thing this exists to let through          -> test_windowed_read_then_anchored_patch_succeeds
  * a receipt reused after the file it named changed  -> test_stale_receipt_is_refused_after_the_file_moved
  * the kernel guard a command can still slip past    -> test_fs_guard_blocks_raw_redirects_and_allows_the_doors
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESTATE_READ = ROOT / "bin" / "estate-read"
ESTATE_PATCH = ROOT / "bin" / "estate-patch"


def _load_fs_guard():
    spec = importlib.util.spec_from_file_location(
        "fs_guard", ROOT / "platform" / "estate" / "harness" / "fs_guard.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _sandbox(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "AGENTS.md").write_text("stale rules\n")
    (tmp_path / "src" / "sample.py").write_text(
        "def compute_quota(limit: int, used: int) -> int:\n"
        "    remaining = limit - used\n"
        "    return max(0, remaining)\n"
    )
    return tmp_path


def _env(tmp_path: Path) -> dict:
    import os

    env = dict(os.environ)
    env["ESTATE_HOME"] = str(tmp_path / ".estate")
    env["ESTATE_RECEIPT_KEY"] = "test-secret-key"
    return env


def _read(
    tmp_path: Path, path: str, lines: str = "1:120"
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ESTATE_READ), path, "--lines", lines],
        cwd=tmp_path,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
    )


def _patch(
    tmp_path: Path,
    path: str,
    patch_text: str,
    receipt: str | None = None,
    create: bool = False,
) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(ESTATE_PATCH), path]
    if receipt is not None:
        cmd += ["--receipt", receipt]
    if create:
        cmd += ["--create"]
    return subprocess.run(
        cmd,
        cwd=tmp_path,
        env=_env(tmp_path),
        input=patch_text,
        capture_output=True,
        text=True,
    )


def _receipt_from(read_stdout: str) -> str:
    m = re.search(r'"READ_RECEIPT":\s*"([^"]+)"', read_stdout)
    assert m, f"no READ_RECEIPT in: {read_stdout!r}"
    return m.group(1)


def test_raw_markdown_read_is_blocked(tmp_path):
    _sandbox(tmp_path)
    result = _read(tmp_path, "AGENTS.md")
    assert result.returncode == 3, result.stderr
    assert "ESTATE-READ-STALE-DOC-BLOCKED" in result.stderr


def test_patch_without_receipt_is_refused(tmp_path):
    _sandbox(tmp_path)
    result = _patch(
        tmp_path,
        "src/sample.py",
        "<<<< SEARCH\n    remaining = limit - used\n    return max(0, remaining)\n"
        "====\n    return max(0, limit - used)\n>>>>\n",
    )
    assert result.returncode == 7, result.stderr
    assert "ESTATE-PATCH-NO-RECEIPT" in result.stderr


def test_receipt_is_bound_to_the_exact_file_and_hash(tmp_path):
    _sandbox(tmp_path)
    read_out = _read(tmp_path, "src/sample.py", "1:3")
    assert read_out.returncode == 0, read_out.stderr
    receipt = _receipt_from(read_out.stdout)
    disk_sha = hashlib.sha256((tmp_path / "src" / "sample.py").read_bytes()).hexdigest()
    assert receipt.split(":")[1] == disk_sha
    # a receipt forged for a different path is refused even with a correct hash
    forged = receipt.replace("src/sample.py", "src/other.py", 1)
    (tmp_path / "src" / "other.py").write_bytes(
        (tmp_path / "src" / "sample.py").read_bytes()
    )
    result = _patch(
        tmp_path,
        "src/other.py",
        "<<<< SEARCH\n    remaining = limit - used\n    return max(0, remaining)\n"
        "====\n    return max(0, limit - used)\n>>>>\n",
        receipt=forged,
    )
    assert result.returncode == 8, result.stderr
    assert "RECEIPT-INVALID" in result.stderr


def test_broken_ast_patch_is_rejected_and_file_untouched(tmp_path):
    _sandbox(tmp_path)
    receipt = _receipt_from(_read(tmp_path, "src/sample.py", "1:3").stdout)
    before = (tmp_path / "src" / "sample.py").read_bytes()
    result = _patch(
        tmp_path,
        "src/sample.py",
        "<<<< SEARCH\n    remaining = limit - used\n    return max(0, remaining)\n"
        "====\n    def broken_syntax(\n>>>>\n",
        receipt=receipt,
    )
    assert result.returncode == 13, result.stderr
    assert "AST-REJECTED" in result.stderr
    assert (tmp_path / "src" / "sample.py").read_bytes() == before


def test_windowed_read_then_anchored_patch_succeeds(tmp_path):
    _sandbox(tmp_path)
    receipt = _receipt_from(_read(tmp_path, "src/sample.py", "1:3").stdout)
    result = _patch(
        tmp_path,
        "src/sample.py",
        "<<<< SEARCH\n    remaining = limit - used\n    return max(0, remaining)\n"
        "====\n    if used >= limit:\n        return 0\n    return limit - used\n>>>>\n",
        receipt=receipt,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["status"] == "PATCHED"
    assert "if used >= limit:" in (tmp_path / "src" / "sample.py").read_text()


def test_stale_receipt_is_refused_after_the_file_moved(tmp_path):
    _sandbox(tmp_path)
    receipt = _receipt_from(_read(tmp_path, "src/sample.py", "1:3").stdout)
    first = _patch(
        tmp_path,
        "src/sample.py",
        "<<<< SEARCH\n    remaining = limit - used\n    return max(0, remaining)\n"
        "====\n    if used >= limit:\n        return 0\n    return limit - used\n>>>>\n",
        receipt=receipt,
    )
    assert first.returncode == 0, first.stderr
    replay = _patch(
        tmp_path,
        "src/sample.py",
        "<<<< SEARCH\n    if used >= limit:\n        return 0\n"
        "====\n    if used > limit:\n        return 0\n>>>>\n",
        receipt=receipt,  # the same, now-stale receipt
    )
    assert replay.returncode == 8, replay.stderr
    assert "STALE_FILE_STATE" in replay.stderr


def test_create_refuses_to_overwrite_an_existing_file(tmp_path):
    _sandbox(tmp_path)
    result = _patch(tmp_path, "src/sample.py", "anything", create=True)
    assert result.returncode == 4, result.stderr
    assert "ESTATE-PATCH-EXISTS" in result.stderr


def test_ambiguous_anchor_is_refused(tmp_path):
    _sandbox(tmp_path)
    (tmp_path / "src" / "dup.py").write_text("x = 1\nx = 1\n")
    receipt = _receipt_from(_read(tmp_path, "src/dup.py", "1:2").stdout)
    result = _patch(
        tmp_path,
        "src/dup.py",
        "<<<< SEARCH\nx = 1\n====\nx = 2\n>>>>\n",
        receipt=receipt,
    )
    assert result.returncode == 12, result.stderr
    assert "AMBIGUOUS-ANCHOR" in result.stderr


def test_fs_guard_blocks_raw_redirects_and_allows_the_doors():
    fs_guard = _load_fs_guard()
    blocked = [
        "cat AGENTS.md",
        "sed -i 's/x/y/' src/sample.py",
        "echo hi >> src/sample.py",
        "echo AGENTS.md",
    ]
    for cmd in blocked:
        allowed, reason = fs_guard.check_command_allowed(cmd)
        assert not allowed, f"expected {cmd!r} to be blocked"
        assert reason != "OK"
    allowed_cmds = [
        "bin/estate-read src/sample.py --lines 1:10",
        "bin/estate-patch src/sample.py --receipt abc",
        "git status --porcelain",
        "git commit -m 'msg'",
        "echo hi > /dev/null",
    ]
    for cmd in allowed_cmds:
        allowed, reason = fs_guard.check_command_allowed(cmd)
        assert allowed, f"expected {cmd!r} to be allowed, got: {reason}"
