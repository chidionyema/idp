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
  * the estate's own doors judged as if an agent typed them -> test_an_estate_authored_redirect_in_an_intent_step_is_not_refused
  * an agent smuggling a redirect through a raw slot  -> test_an_agent_cannot_smuggle_a_redirect_through_a_raw_slot
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


def _executor_env(tmp_path: Path) -> dict:
    """The environment for a real estate-execute run.

    HOME is isolated because the executor's ticket ledger is Path.home() / ".estate" /
    "estate.db" -- it does not honor ESTATE_HOME -- and writing real ticket state into the
    real home races every other parallel run. But on a laptop PyYAML lives in the USER
    site-packages, which is under HOME, so isolating HOME takes `import yaml` with it: the
    executor then dies before it runs a step. The interpreter's own user site-packages go
    on PYTHONPATH so the isolation costs the test nothing.
    """
    import os
    import site

    env = _env(tmp_path)
    env["HOME"] = str(tmp_path)
    user_site = site.getusersitepackages()
    if isinstance(user_site, str) and user_site:
        env["PYTHONPATH"] = os.pathsep.join(
            [p for p in (env.get("PYTHONPATH", ""), user_site) if p]
        )
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


def test_fs_guard_does_not_false_positive_on_quoted_operators(tmp_path):
    # Found live, not in a unit test: a real SEARCH/REPLACE payload whose *replacement
    # text* contains `if used >= limit:` was refused as a raw write-redirect, because the
    # original pattern scanned the whole command string for a bare `>` with no notion of
    # quoting. A `>` inside a single-quoted printf payload never reaches the shell as an
    # operator, so it is not a redirect this layer should refuse.
    fs_guard = _load_fs_guard()
    allowed_cmds = [
        "printf 'if used >= limit:\\n    return 0\\n' | bin/estate-patch f.py --receipt x",
        "printf 'a << b; List<int> x;' | bin/estate-patch f.py --receipt x",
        'git commit -m "uses >= and <= and << in the message"',
    ]
    for cmd in allowed_cmds:
        allowed, reason = fs_guard.check_command_allowed(cmd)
        assert allowed, f"expected {cmd!r} to be allowed, got: {reason}"
    # the fix must not open a real hole: an UNQUOTED redirect is still refused
    blocked_cmds = [
        "echo hi > AGENTS.md",
        "echo hi >> src/sample.py",
        "printf 'safe text' > src/sample.py",
    ]
    for cmd in blocked_cmds:
        allowed, reason = fs_guard.check_command_allowed(cmd)
        assert not allowed, f"expected {cmd!r} to still be blocked"


def test_an_estate_authored_redirect_in_an_intent_step_is_not_refused(tmp_path):
    """The class fix, first half: the estate's own step text is estate-authored code -- it
    reaches the shell through a claim and a lane -- so the agent-facing heuristic must not
    judge it. Measured 2026-10-31: 103 of the 451 installed intent steps matched a banned
    pattern and the estate's canonical doors refused THEMSELVES; pr-list, agent-invoke and
    lane-submit each died with "REFUSED: RAW_WRITE_REDIRECT_BANNED" on their own redirect.

    This test is the falsifier for that class: a step whose own text writes a file runs.
    """
    _sandbox(tmp_path)
    intents_dir = tmp_path / "platform" / "estate" / "intents"
    intents_dir.mkdir(parents=True)
    (intents_dir / "_write.yaml").write_text(
        "name: _write\n"
        "description: test fixture\n"
        "halt_on_failure: true\n"
        "steps:\n"
        "  - name: write\n"
        "    cmd: |\n"
        "      printf 'written by the estate' > \"$HOME/estate-write-proof.txt\"\n"
    )
    env = _executor_env(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "platform" / "estate" / "bin" / "estate-execute"),
            "--from",
            str(tmp_path),
            "_write",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    out = result.stdout + result.stderr
    assert "REFUSED" not in out, out
    assert (tmp_path / "estate-write-proof.txt").read_text() == "written by the estate"


def test_an_agent_cannot_smuggle_a_redirect_through_a_raw_slot(tmp_path):
    """The class fix, second half: the guard must still judge the AGENT's own content.
    A <<var>> slot is injected raw, so an agent's value can reach the shell as an
    operator; that value is exactly what the boundary refuses."""
    _sandbox(tmp_path)
    intents_dir = tmp_path / "platform" / "estate" / "intents"
    intents_dir.mkdir(parents=True)
    (intents_dir / "_raw.yaml").write_text(
        "name: _raw\n"
        "description: test fixture\n"
        "halt_on_failure: true\n"
        "args:\n"
        "  payload:\n"
        "    help: a raw payload\n"
        "    default: nothing\n"
        "steps:\n"
        "  - name: write\n"
        "    cmd: |\n"
        "      printf '%s\\n' <<payload>>\n"
    )
    env = _executor_env(tmp_path)
    smuggled = tmp_path / "guard-pwned"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "platform" / "estate" / "bin" / "estate-execute"),
            "--from",
            str(tmp_path),
            "_raw",
            f"payload=x > {smuggled}",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    out = result.stdout + result.stderr
    assert "REFUSED" in out, out
    assert "RAW_WRITE_REDIRECT_BANNED" in out, out
    assert not smuggled.exists()


def test_a_real_patch_round_trips_through_the_live_executor(tmp_path):
    """End-to-end through the actual dispatch path (platform/estate/bin/estate-execute),
    not just the two CLI tools in isolation: a read, then a patch whose replacement text
    contains `>=`, through a real intent, exactly as an agent would run it. This is the
    path test_fs_guard_* above cannot reach on its own -- fs_guard only matters inside
    estate-execute's subprocess dispatch, and the false positive above only showed up
    here, not in a direct subprocess.run of bin/estate-patch."""
    _sandbox(tmp_path)
    intents_dir = tmp_path / "platform" / "estate" / "intents"
    intents_dir.mkdir(parents=True)
    (intents_dir / "_proof.yaml").write_text(
        "name: _proof\n"
        "description: test fixture\n"
        "tools: [bin/estate-patch]\n"
        "halt_on_failure: true\n"
        "steps:\n"
        "  - name: patch\n"
        "    cmd: |\n"
        "      printf '<<<< SEARCH\\n    remaining = limit - used\\n    return max(0, "
        "remaining)\\n====\\n    if used >= limit:\\n        return 0\\n    return limit - "
        f'used\\n>>>>\\n\' | {ESTATE_PATCH} src/sample.py --receipt "{{receipt}}"\n'
    )
    receipt = _receipt_from(_read(tmp_path, "src/sample.py", "1:3").stdout)
    (intents_dir / "_proof.yaml").write_text(
        (intents_dir / "_proof.yaml").read_text().replace("{receipt}", receipt)
    )
    estate_execute = ROOT / "platform" / "estate" / "bin" / "estate-execute"
    env = _executor_env(tmp_path)
    result = subprocess.run(
        [sys.executable, str(estate_execute), "--from", str(tmp_path), "_proof"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "REFUSED" not in result.stdout, result.stdout
    assert "if used >= limit:" in (tmp_path / "src" / "sample.py").read_text(), (
        result.stdout
    )
