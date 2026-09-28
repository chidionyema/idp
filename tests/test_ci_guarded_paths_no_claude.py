"""bin/idp-ci-guarded-paths: the .claude/ and claude-code/ ban, and the diff-range bug it exposed.

Founder, 2026-09-28: ".claude keeps coming back, causing split-brain, needs to be eliminated and
CI/CD [must] reject any attempts to reinstate it." The estate is model-agnostic (AGENTS.md R6);
.claude/ is a second execution boundary and the only guard against it was `.githooks/pre-push`
Layer 0 -- a client-side hook a bot commit, a hookless machine, or a GitHub-UI merge never runs,
which is exactly how the directory kept coming back. This adds the same ban to the already-
required `guarded-paths` CI check, server-side and with no signature/bot/founder override.

While reading the script to extend it, line 34 (`git diff --name-only "$BASE"...HEAD_REV`) turned
out to reference the bare word HEAD_REV, not $HEAD_REV -- git always failed to resolve the range,
`2>/dev/null || true` swallowed the error, and `changed` was always empty. Check 1 (the guarded-
path signature check) had therefore never matched anything since it was written. Fixing the `$`
is what makes the new .claude/ check (which reads the same `changed` variable) able to see a
diff at all; a test proving the .claude/ ban fires is also proof the bug is fixed, since it would
stay silent forever on the pre-fix code path.

No repository fixture depends on the founder-signature machinery (openssl keys, the commit-msg
HMAC secret): these cases only need the script's exit code and stderr/stdout, run against a
throwaway git repo, never the real one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "idp-ci-guarded-paths"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repo: `main` at one base commit, no founder.pub (bootstrap state), and HEAD
    checked out onto a feature branch ahead of it -- the shape a real PR diffs against."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    (r / "README.md").write_text("base\n")
    _git(r, "add", "README.md")
    _git(r, "commit", "-q", "-m", "base")
    _git(r, "branch", "-q", "-m", "main")
    _git(r, "checkout", "-q", "-b", "feature")
    return r


def run(repo: Path, base: str = "main") -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [str(SCRIPT), base],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _commit_file(repo: Path, path: str, content: str = "x\n") -> None:
    """-f: this machine's global gitignore excludes .claude/, but a bot commit or another
    machine without that ignore rule is exactly the path this ban has to catch regardless."""
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    _git(repo, "add", "-f", path)
    _git(repo, "commit", "-q", "-m", "add " + path)


def test_dot_claude_path_fails_even_in_bootstrap_state(repo: Path):
    """No docs/keys/founder.pub yet (bootstrap) does not exempt the .claude/ ban."""
    _commit_file(repo, ".claude/settings.json", '{"model": "opusplan"}\n')
    result = run(repo)
    assert result.returncode == 1
    assert ".claude/settings.json" in result.stdout
    assert "FAIL" in result.stdout


def test_claude_code_path_fails(repo: Path):
    _commit_file(repo, "claude-code/hooks/pre_tool_call.py", "pass\n")
    result = run(repo)
    assert result.returncode == 1
    assert "claude-code/hooks/pre_tool_call.py" in result.stdout


def test_nested_dot_claude_path_fails(repo: Path):
    """A .claude/ dir need not be at repo root to be caught."""
    _commit_file(repo, "subdir/.claude/worktrees/x/settings.json", "{}\n")
    result = run(repo)
    assert result.returncode == 1
    assert "subdir/.claude/worktrees/x/settings.json" in result.stdout


def test_unrelated_change_is_not_flagged_by_the_claude_ban(repo: Path):
    """A change with no .claude/ or claude-code/ path still reaches the bootstrap exit at 0.

    This is also the regression check for the diff-range bug: before the `$HEAD_REV` fix,
    `changed` was always empty, so this case passed for the wrong reason (nothing was ever
    read). It's the two .claude/-hit tests above -- which require `changed` to be genuinely
    non-empty -- that prove the fix, not this one; this one guards against the ban being so
    broad it flags everything.
    """
    _commit_file(repo, "platform/foo/bar.py", "pass\n")
    result = run(repo)
    assert result.returncode == 0
    assert "bootstrap" in result.stdout


def test_dot_claude_and_unrelated_change_together_still_fails(repo: Path):
    """The ban looks at the whole diff, not just the last file touched."""
    _commit_file(repo, "platform/foo/bar.py", "pass\n")
    _commit_file(repo, ".claude/settings.local.json", "{}\n")
    result = run(repo)
    assert result.returncode == 1
    assert ".claude/settings.local.json" in result.stdout
