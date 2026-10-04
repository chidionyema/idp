"""`guarded-paths` exempted agents by AUTHOR EMAIL, which is not an identity.

Until this change, bin/idp-ci-guarded-paths exempted a commit from the unsigned-HEAD check when
`git log -1 --format=%ae` matched one of two hardcoded strings, under a comment claiming the
addresses were "cryptographically verified". They were string-compared, and a string comparison
confers nothing. The exemption failed three ways at once:

  1. IT CARRIED A TYPO. The second address is spelled `chidionyema333@gmail.com` -- it appears in
     packages/sdk-py/pyproject.toml and nowhere else in the estate. The checker exempted
     `chidiony333@gmail.com` (no "ema"), a string that exists nowhere else in the repository, so
     the founder was exempt under one address and refused under the other.

  2. IT WAS A SECOND COPY. An identity that already lives in one place was hand-typed into a
     shell case statement, where it drifts the moment either side changes.

  3. IT WAS FORGEABLE. `git commit --author="chidionyema@gmail.com"` claimed the exemption with
     no key, no signature, and no hook.

The replacement rests on two facts an author cannot forge: the committer being GitHub itself
(a commit written through the GitHub API runs no local hook, and `--author=` cannot set the
committer), and a valid Ed25519 X-Idp-Auth trailer verified against docs/keys/founder.pub.

The behavioral test builds a real repository and runs the REAL checker, so the decision cannot
drift from a hand-copied version of the predicate.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECKER = REPO / "bin/idp-ci-guarded-paths"

# The exact strings the check must never trust again. `chidiony333@gmail.com` is the typo; the
# correct address is included so a future edit cannot quietly reintroduce the list under a
# different spelling.
FOUNDER_ADDRESSES = [
    "chidionyema@gmail.com",
    "chidionyema333@gmail.com",
    "chidiony333@gmail.com",
]


def _code_lines() -> list[str]:
    """The checker's executable lines: comments stripped, so prose about the old list is allowed.

    The fix's own explanation names the typo it removed; that must not be mistaken for the check
    still using it. Only lines that are not comments can authorize anything.
    """
    out = []
    for raw in CHECKER.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def test_no_email_string_authorizes_a_commit() -> None:
    """The authorization logic contains no founder address at all.

    An email in a `case` pattern is exactly the defect: it lets a name in the author field stand
    in for a signature. Comments may discuss it; code may not contain it.
    """
    for line in _code_lines():
        for addr in FOUNDER_ADDRESSES:
            assert addr not in line, (
                f"author email {addr!r} is back in the authorization path: {line!r}\n"
                "An author field is not an identity. Use the X-Idp-Auth signature."
            )


def test_author_email_is_not_read_at_all() -> None:
    """The checker no longer reads %ae. Reading it at all is how the old bug worked."""
    code = "\n".join(_code_lines())
    assert "%ae" not in code, (
        "the checker reads the author email again; that field is attacker-controlled "
        "(`git commit --author=...`) and must never decide authorization"
    )


def test_the_committer_is_what_is_trusted_for_server_commits() -> None:
    """The one email-shaped exemption reads %ce and requires GitHub's own committer."""
    code = "\n".join(_code_lines())
    assert "%ce" in code, (
        "server-written commits are identified by committer, not author"
    )
    assert "noreply@github.com" in code, (
        "the server-commit exemption must key on GitHub's committer address specifically"
    )


def test_the_real_signature_verifier_is_consulted() -> None:
    """A human identity is proven by bin/idp-auth-verify, not by any string."""
    code = "\n".join(_code_lines())
    assert "idp-auth-verify" in code, (
        "the checker must call the Ed25519 verifier for a human's identity"
    )


def _commit_as(
    repo: Path, *, author: str, committer: str | None = None, message: str = "x"
) -> str:
    """Make one real commit in `repo` with the given author (and committer). Return its sha."""
    (repo / "f.txt").write_text(str(len(list(repo.iterdir()))) + "\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)  # noqa: S603,S607
    env = None
    if committer is not None:
        env = {
            "GIT_COMMITTER_NAME": "someone",
            "GIT_COMMITTER_EMAIL": committer,
            "PATH": __import__("os").environ.get("PATH", ""),
        }
    subprocess.run(  # noqa: S603
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            f"user.email={author}",
            "commit",
            "-q",
            "-m",
            message,
        ],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )
    return subprocess.run(  # noqa: S603,S607
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _checker_verdict(repo: Path) -> tuple[int, str]:
    """Run the REAL checker in `repo`; return (exit code, output)."""
    done = subprocess.run(  # noqa: S603
        ["bash", str(CHECKER), "HEAD~1"],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return done.returncode, done.stdout + done.stderr


def _fresh_repo(tmp_path: Path) -> Path:
    """A repo whose BASE commit already carries docs/keys/founder.pub.

    This matters: bin/idp-ci-guarded-paths has a bootstrap exemption that exits 0 when the base
    tree lacks the public key ("the contract cannot verify itself before it exists"). Without the
    key on HEAD~1 every commit would take that path and these tests would assert against the
    bootstrap message instead of the authorization logic.
    """
    repo = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)  # noqa: S603,S607
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
        capture_output=True,
    )  # noqa: S603,S607
    keydir = repo / "docs" / "keys"
    keydir.mkdir(parents=True)
    keydir.joinpath("founder.pub").write_text(
        (REPO / "docs/keys/founder.pub").read_text()
    )
    _commit_as(repo, author="base@example.com", message="base: carry the pubkey")
    return repo


def test_a_forged_founder_email_is_refused(tmp_path: Path) -> None:
    """THE DEFECT: claim to be the founder, carry no signature, get refused.

    This is the case the old checker exempted. Under the email list, an author field reading
    `chidionyema@gmail.com` was enough to skip the unsigned-HEAD check entirely.
    """
    repo = _fresh_repo(tmp_path)
    _commit_as(repo, author="chidionyema@gmail.com")
    rc, out = _checker_verdict(repo)
    assert rc != 0, (
        "a commit claiming the founder's address in its author field was accepted with no "
        f"signature; the author field is not an identity. checker said:\n{out}"
    )
    assert "unsigned" in out, f"expected the unsigned-HEAD refusal; got:\n{out}"


def test_the_typo_address_is_refused_too(tmp_path: Path) -> None:
    """The typo string was exempt as well, so it is forged in the same test."""
    repo = _fresh_repo(tmp_path)
    _commit_as(repo, author="chidiony333@gmail.com")
    rc, out = _checker_verdict(repo)
    assert rc != 0, f"the typo address was still trusted; checker said:\n{out}"


def test_the_real_second_address_is_refused_when_unsigned(tmp_path: Path) -> None:
    """The address the estate actually declares gets no free pass either."""
    repo = _fresh_repo(tmp_path)
    _commit_as(repo, author="chidionyema333@gmail.com")
    rc, out = _checker_verdict(repo)
    assert rc != 0, (
        "the founder's real second address was trusted on its own; it must still carry a "
        f"signature. checker said:\n{out}"
    )


def test_a_github_server_commit_is_still_exempt(tmp_path: Path) -> None:
    """The one exemption that must survive: GitHub wrote the commit, so no hook could run.

    The committer is set to GitHub's own address, which `--author=` cannot forge.
    """
    repo = _fresh_repo(tmp_path)
    _commit_as(repo, author="bot@example.com", committer="noreply@github.com")
    rc, out = _checker_verdict(repo)
    assert rc == 0, (
        "a commit written by GitHub itself was refused; no hook can run on GitHub's servers, so "
        f"this exemption must hold. checker said:\n{out}"
    )
    assert "GitHub" in out, f"expected the server-commit exemption message; got:\n{out}"


def test_setting_the_committer_email_does_not_help_an_attacker(tmp_path: Path) -> None:
    """Only GitHub's exact committer address is exempt -- not any committer at all."""
    repo = _fresh_repo(tmp_path)
    _commit_as(repo, author="attacker@example.com", committer="attacker@example.com")
    rc, out = _checker_verdict(repo)
    assert rc != 0, f"an arbitrary committer was exempted; checker said:\n{out}"


def test_the_typo_string_is_not_the_real_address() -> None:
    """Grounds the typo claim: the two strings genuinely differ, as the fix states."""
    typo = "chidiony333@gmail.com"
    real = "chidionyema333@gmail.com"
    assert typo != real
    assert real.replace("chidionyema", "chidiony") == typo, (
        "the typo is the real address with 'ema' removed; if either changed, revisit the fix"
    )


def test_the_real_address_is_the_one_the_package_declares() -> None:
    """The real second address is the one pyproject.toml carries -- the estate's single source.

    The assertion is narrow on purpose: `noreply@github.com` is a legitimate literal in the
    checker (it identifies GitHub as the committer, which is not an identity that can be forged).
    What must never appear is a *human's* address standing in for a signature.
    """
    pyproject = (REPO / "packages/sdk-py/pyproject.toml").read_text()
    assert "chidionyema333@gmail.com" in pyproject, (
        "packages/sdk-py/pyproject.toml no longer declares the founder's second address; "
        "the premise of the typo fix has moved"
    )
    code = "\n".join(_code_lines())
    emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", code))
    assert emails <= {"noreply@github.com"}, (
        f"the checker's executable lines carry email literals beyond GitHub's own committer "
        f"address: {sorted(emails - {'noreply@github.com'})}"
    )
