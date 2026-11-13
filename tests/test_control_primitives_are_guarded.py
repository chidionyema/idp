"""Every control primitive is guarded: an agent can read it, never land a change to it unsigned.

Founder, 2026-11-13: an agent rewrote the estate's control files with no founder seal (49 commits
on main 2026-11-05..13, 44 by estate-agents[bot]). This test runs the REAL guard list and the REAL
prefix rule bin/idp-ci-guarded-paths applies, so the two cannot drift. Removing a row from
bin/idp-guarded-paths fails here; that removal itself is a guarded change needing X-Idp-Auth.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# One real file per control primitive: what agents read as law, and what decides what lands.
CONTROL_PRIMITIVES = [
    "AGENTS.md",
    "CLAUDE.md",
    "CODEOWNERS",
    ".github/workflows/guarded-paths.yml",
    ".github/workflows/founder-passkey-deploy.yml",
    "docs/keys/founder.pub",
    "bin/claim-gate",
    "bin/claim-open",
    "bin/dof-gate",
    "bin/idp-ci",
    "bin/idp-ci-guarded-paths",
    "bin/idp-guarded-paths",
    "bin/idp-auth",
    "bin/idp-auth-verify",
    "bin/idp-greenlane",
    "bin/estate-memory-enforce",
    "catalog/dof-registry.json",
    "catalog/critical-functions.json",
    "platform/estate/protocolkit/protocolkit/gates.py",
    "platform/estate/memory/handback.py",
    "platform/founder-passkey/worker.js",
    ".githooks/pre-push",
]

# Paths that are NOT control primitives must stay unguarded, or every lane needs a signature.
ORDINARY = [
    "docs/runbooks/greenlane.md",
    "tests/test_control_primitives_are_guarded.py",
    "README.md",
]


def _guards() -> list[str]:
    out = subprocess.run(
        [str(REPO / "bin/idp-guarded-paths")],
        capture_output=True,
        text=True,
        check=True,
    )
    return [g for g in out.stdout.splitlines() if g]


def _guarded(path: str, guards: list[str]) -> bool:
    # Same predicate as bin/idp-ci-guarded-paths: grep -E "^${g}" against the changed path.
    return any(re.match(g, path) for g in guards)


def test_every_control_primitive_exists_and_is_guarded() -> None:
    guards = _guards()
    missing = [p for p in CONTROL_PRIMITIVES if not (REPO / p).exists()]
    assert missing == [], (
        f"control primitive list names files that do not exist: {missing}"
    )
    unguarded = [p for p in CONTROL_PRIMITIVES if not _guarded(p, guards)]
    assert unguarded == [], (
        f"control primitives an agent can change unsigned: {unguarded}"
    )


def test_ordinary_paths_stay_unguarded() -> None:
    guards = _guards()
    over = [p for p in ORDINARY if _guarded(p, guards)]
    assert over == [], f"ordinary paths wrongly need a founder signature: {over}"


def test_unguarded_list_fails_before_this_change() -> None:
    # Falsifier: the guard list as it stood on main 8eaf70d2 leaves AGENTS.md and workflows open.
    old = [
        "platform/edge/otel-endpoint-exception.yaml",
        "platform/edge/inject-otel-endpoint.yaml",
        "platform/edge/require-otel-endpoint.yaml",
        "platform/policies/kyverno/",
        ".githooks/",
        "bin/idp-auth",
        "bin/idp-guarded-paths",
        "bin/idp-ci-guarded-paths",
    ]
    assert not _guarded("AGENTS.md", old)
    assert not _guarded(".github/workflows/argon-guardian-relay.yml", old)


CHECKER = REPO / "bin/idp-ci-guarded-paths"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)  # noqa: S603,S607


def _repo_with_pubkey(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)  # noqa: S603,S607
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "user.name", "agent")
    _git(repo, "config", "user.email", "agent@example.com")
    (repo / "docs/keys").mkdir(parents=True)
    (repo / "docs/keys/founder.pub").write_text(
        (REPO / "docs/keys/founder.pub").read_text()
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base: carry the pubkey")
    return repo


def test_the_real_checker_refuses_an_unsigned_agents_md_change(tmp_path: Path) -> None:
    """THE DEFECT (2026-10-28, #7328 to 2026-11-13): the checker diffed `$BASE...HEAD_REV`.

    HEAD_REV without `$` is not a ref, git diff failed, `|| true` swallowed it, and the list of
    changed files was always empty, so no guarded path was ever detected. This commit carries a
    valid-looking X-Idp-Signed stamp, so the ONLY thing that can refuse it is guarded-path
    detection. It must refuse.
    """
    repo = _repo_with_pubkey(tmp_path)
    (repo / "AGENTS.md").write_text("agents may rewrite their own law\n")
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        "agent rewrites AGENTS.md\n\nX-Idp-Signed: " + "0" * 64,
    )
    done = subprocess.run(  # noqa: S603
        ["bash", str(CHECKER), "HEAD~1"],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
    )
    out = done.stdout + done.stderr
    assert done.returncode != 0, (
        f"an unsigned AGENTS.md change passed guarded-paths:\n{out}"
    )
    assert "AGENTS.md" in out, f"refusal must name the guarded path; got:\n{out}"


def test_one_law_file_per_repo() -> None:
    """Founder, 2026-11-13: shrink the attack surface. CLAUDE.md is not a second law file.

    A per-vendor instruction file is a second copy of the law that only one vendor's agents read,
    and a second place an agent can rewrite. The Claude harness needs a file by that name, so it
    is a symlink to AGENTS.md: same bytes, one law, one guarded path.
    """
    claude = REPO / "CLAUDE.md"
    assert claude.is_symlink(), (
        "CLAUDE.md must be a symlink to AGENTS.md, not its own file"
    )
    assert claude.resolve() == (REPO / "AGENTS.md").resolve()
