"""`guarded-paths` must SEE the change it judges (idp#8021).

Since 06b2a311 (2026-09-17) bin/idp-ci-guarded-paths diffed `"$BASE"...HEAD_REV` -- the literal
word, not the variable. git refused the unknown revision, `2>/dev/null || true` swallowed the
error, the changed-file list came back empty, and the founder-signature check never ran. 58
commits touched guarded paths after that day; none was judged.

These tests run the REAL checker against a real repository:
  1. an unsigned change to a guarded path is refused BY THE SIGNATURE CHECK (not by some other
     check that happens to fail too);
  2. a base the checker cannot diff against is refused, never read as "nothing changed".
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = ["bin/idp-ci-guarded-paths", "bin/idp-guarded-paths", "bin/idp-auth-verify"]
REFUSAL = "guarded paths touched WITHOUT valid X-Idp-Auth trailer"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],  # noqa: S607
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repo(tmp: Path) -> Path:
    repo = tmp / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    for rel in SCRIPTS:
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    keys = repo / "docs/keys"
    keys.mkdir(parents=True)
    (keys / "founder.pub").write_text("ssh-ed25519 AAAAplaceholder founder\n")
    (repo / "bin/idp-auth").write_text("#!/usr/bin/env bash\necho base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _run(repo: Path, base: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(  # noqa: S603
        ["bash", str(repo / "bin/idp-ci-guarded-paths"), base],
        cwd=repo, capture_output=True, text=True, env=env, timeout=60,
    )


def test_unsigned_change_to_a_guarded_path_is_refused_by_the_signature_check(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "branch", "base-ref")
    (repo / "bin/idp-auth").write_text("#!/usr/bin/env bash\necho tampered\n")
    _git(repo, "commit", "-q", "-am", "unsigned change to a guarded path")
    out = _run(repo, "base-ref")
    assert out.returncode != 0, out.stdout + out.stderr
    assert REFUSAL in out.stdout, (
        "the guard did not see the guarded change -- it must refuse it by the signature check:\n"
        + out.stdout + out.stderr
    )
    assert "bin/idp-auth" in out.stdout


def test_an_undiffable_base_is_refused_not_read_as_no_change(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    # A base that carries the key (so no bootstrap exemption) but shares no history with HEAD:
    # a three-dot diff has no merge base and git refuses it.
    _git(repo, "checkout", "-q", "--orphan", "island")
    _git(repo, "commit", "-q", "-m", "island with the same tree")
    _git(repo, "checkout", "-q", "main")
    (repo / "bin/idp-auth").write_text("#!/usr/bin/env bash\necho tampered\n")
    _git(repo, "commit", "-q", "-am", "unsigned change")
    out = _run(repo, "island")
    assert out.returncode != 0
    assert "cannot compute the changed paths" in out.stdout, out.stdout + out.stderr


def test_the_checker_never_diffs_against_a_literal_revision_name() -> None:
    code = [ln for ln in (REPO / "bin/idp-ci-guarded-paths").read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    assert not any("...HEAD_REV" in ln for ln in code), "literal HEAD_REV is back in the diff"
