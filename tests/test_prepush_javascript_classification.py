"""#7554: a *.js file is JavaScript, and the pre-push gate must parse it with node.

The gate classifies every file in the pushed diff: shell by shebang (bash -n), Python
(py_compile), TypeScript (node --experimental-strip-types --check) and everything else in
an unknown bucket that accepts a file only when one of those parsers can read it.
JavaScript had no class, so the estate's own OpenCode plugin
(`platform/estate/memory/opencode-estate-memory.js`) was refused when it was pushed:
"readable as neither shell nor Python" (measured 2026-10-30 while pushing
lane/plan-gate-session-identity).

The repair gives JavaScript its own class and a real parser: `node --check`. A broken
JavaScript file is still refused -- by the JavaScript parser, naming JavaScript -- and the
unknown bucket still refuses a file no parser can read. The gate is widened, not weakened.
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

VALID_JS = """export function publishSession(sessionID) {
  return sessionID;
}
"""

VALID_CJS = """module.exports = function () {
  return 1;
};
"""

BROKEN_JS = """export function broken( {
  return 1;
}
"""

BINARY = "\x00\x01\x02 not source code \xff\n"


def git(cwd: Path, *a: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


@pytest.fixture
def clone(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("node is not installed: the JavaScript class cannot be exercised")
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
    return work


def commit(work: Path, name: str, content: str) -> None:
    (work / name).write_text(content)
    git(work, "add", name)
    git(work, "commit", "-q", "-m", name)


def push(work: Path, branch: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IDP_CI_")}
    return git(work, "push", "origin", f"HEAD:{branch}", env=env, check=False)


def test_a_valid_javascript_file_is_accepted(clone):
    commit(clone, "plugin.js", VALID_JS)
    p = push(clone, "scratch/js-ok")
    assert p.returncode == 0, p.stderr


def test_a_valid_commonjs_file_is_accepted(clone):
    # The JavaScript class must not become a new false refusal: a CommonJS file is checked
    # as CommonJS, and a valid one is accepted.
    commit(clone, "common.js", VALID_CJS)
    p = push(clone, "scratch/js-cjs")
    assert p.returncode == 0, p.stderr


def test_a_broken_javascript_file_is_refused(clone):
    commit(clone, "broken.js", BROKEN_JS)
    p = push(clone, "scratch/js-broken")
    assert p.returncode != 0, p.stderr
    assert "JavaScript syntax error in broken.js" in p.stderr, p.stderr


def test_a_file_no_parser_can_read_is_still_refused(clone):
    commit(clone, "payload.bin", BINARY)
    p = push(clone, "scratch/bin")
    assert p.returncode != 0, p.stderr
    assert "readable as neither shell nor Python" in p.stderr, p.stderr
