"""`guarded-paths` never saw a changed file: it diffed against the literal ref `HEAD_REV`.

bin/idp-ci-guarded-paths listed the changed files with `git diff --name-only "$BASE"...HEAD_REV`
(no `$`). git exited 128, `|| true` hid it, `changed` was always empty, and the guarded-path
signature check could never fire: #8700 changed `.githooks/` and the required check passed.

These tests build a real repository and run the REAL checker, so the verdict cannot drift from a
hand-copied predicate. The falsifier runs the pre-fix line through the same harness and requires
it to accept the change the fixed checker refuses.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BOT = "estate-agents[bot]@users.noreply.github.com"
FIXED_LINE = 'changed="$(git diff --name-only "$BASE"..."$HEAD_REV" 2>/dev/null)" || {'
OLD_LINE = 'changed="$(git diff --name-only "$BASE"...HEAD_REV 2>/dev/null || true)"'


def _git(repo: Path, *args: str, committer: str | None = None) -> str:
    env = dict(os.environ)
    env.pop("GIT_DIR", None)
    if committer:
        env["GIT_COMMITTER_NAME"] = "bot"
        env["GIT_COMMITTER_EMAIL"] = committer
    return subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-c",
            "core.hooksPath=/dev/null",  # a throwaway repo must not run the machine's global hooks
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def _repo_with(tmp_path: Path, checker_text: str | None = None) -> Path:
    """A repo whose base commit carries the founder key and its own copy of the checker's helpers."""
    repo = tmp_path / "r"
    (repo / "bin").mkdir(parents=True)
    (repo / "docs/keys").mkdir(parents=True)
    for name in ("idp-guarded-paths", "idp-auth-verify"):
        shutil.copy(REPO / "bin" / name, repo / "bin" / name)
    text = checker_text or (REPO / "bin/idp-ci-guarded-paths").read_text()
    (repo / "bin/idp-ci-guarded-paths").write_text(text)
    shutil.copy(REPO / "docs/keys/founder.pub", repo / "docs/keys/founder.pub")
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base carries the founder key")
    return repo


def _change(repo: Path, path: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n")
    _git(repo, "add", "-A")
    # A server-written commit, so the unsigned-HEAD step passes and only the guarded-path step
    # can decide.
    _git(repo, "commit", "-q", "-m", f"touch {path}", committer=BOT)


def _verdict(repo: Path, base: str = "HEAD~1") -> tuple[int, str]:
    done = subprocess.run(  # noqa: S603
        ["bash", str(repo / "bin/idp-ci-guarded-paths"), base],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return done.returncode, done.stdout + done.stderr


def test_a_guarded_change_without_a_signature_is_refused(tmp_path: Path) -> None:
    repo = _repo_with(tmp_path)
    _change(repo, ".githooks/pre-commit")
    rc, out = _verdict(repo)
    assert rc != 0 and "WITHOUT valid X-Idp-Auth" in out, out


def test_an_unguarded_change_is_accepted(tmp_path: Path) -> None:
    repo = _repo_with(tmp_path)
    _change(repo, "docs/readme.md")
    rc, out = _verdict(repo)
    assert rc == 0, out


def test_an_unlistable_diff_is_refused_not_passed(tmp_path: Path) -> None:
    repo = _repo_with(tmp_path)
    _change(repo, "docs/readme.md")
    rc, out = _verdict(repo, base="no-such-ref-anywhere")
    assert rc != 0 and "BLIND" in out, out


def test_falsifier_the_pre_fix_line_accepts_the_guarded_change(tmp_path: Path) -> None:
    fixed = (REPO / "bin/idp-ci-guarded-paths").read_text()
    assert FIXED_LINE in fixed, "the fixed diff line moved; update the falsifier"
    block_start = fixed.index(FIXED_LINE)
    block_end = fixed.index("}\n", block_start) + 2
    old = fixed[:block_start] + OLD_LINE + "\n" + fixed[block_end:]
    repo = _repo_with(tmp_path, old)
    _change(repo, ".githooks/pre-commit")
    rc, out = _verdict(repo)
    assert rc == 0, (
        "the pre-fix checker was expected to accept a guarded change (that is the defect); "
        f"if it now refuses, this falsifier no longer proves the test discriminates:\n{out}"
    )


if __name__ == "__main__":
    import sys
    import tempfile

    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/test_guarded_paths_sees_the_changed_files.py --optimus [--source PATH]"
        )
    src = (
        Path(sys.argv[sys.argv.index("--source") + 1]).read_text()
        if "--source" in sys.argv
        else None
    )
    with tempfile.TemporaryDirectory() as d:
        r = _repo_with(Path(d), src)
        _change(r, ".githooks/pre-commit")
        rc, _ = _verdict(r)
    # 1 when a guarded change with no signature is accepted (the checker cannot see it), else 0.
    print(f"optimus.guarded_paths.unseen_guarded_changes={1 if rc == 0 else 0}")
