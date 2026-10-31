"""The governed handover must prove the remote ref, including on retry."""

import subprocess
import sys
from pathlib import Path


HELPER = Path(__file__).resolve().parents[1] / "bin/lane-submit-handover"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)


def test_pushes_claimed_head_and_observes_the_same_remote_sha(tmp_path):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    run("git", "init", "-q", "--bare", str(remote), cwd=tmp_path)
    run("git", "init", "-q", str(work), cwd=tmp_path)
    run("git", "config", "user.name", "Test", cwd=work)
    run("git", "config", "user.email", "test@example.invalid", cwd=work)
    (work / "fact.txt").write_text("evidence\n")
    run("git", "add", "fact.txt", cwd=work)
    run("git", "commit", "-q", "-m", "test", cwd=work)
    run("git", "remote", "add", "origin", str(remote), cwd=work)
    sha = run("git", "rev-parse", "HEAD", cwd=work).stdout.strip()

    first = run(sys.executable, str(HELPER), "--lane", "lane/proof", cwd=work)
    assert f"lane/proof={sha} on origin" in first.stdout
    assert (
        run(
            "git",
            "--git-dir",
            str(remote),
            "rev-parse",
            "refs/heads/lane/proof",
            cwd=tmp_path,
        ).stdout.strip()
        == sha
    )

    second = run(sys.executable, str(HELPER), "--lane", "lane/proof", cwd=work)
    assert f"lane/proof={sha} on origin" in second.stdout
