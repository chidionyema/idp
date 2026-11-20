"""The pre-commit proof certifies the index; a flag buys no exemption.

Two defects, one class (idp#8273, idp#8274): the hook passed --founder-seal,
which the verifier never accepted, and it hashed the working tree while
stamping HEAD.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VERIFIER = REPO / "bin" / "verify_three_proofs.py"
HOOK = REPO / ".githooks" / "pre-commit"

def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout

def test_the_seal_flag_is_gone_from_the_hook():
    text = HOOK.read_text()
    assert "FOUNDER_DIRECT_SEAL" not in text
    assert "--founder-seal" not in text
    assert "--staged" in text

def test_the_index_bytes_are_what_get_certified(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    f = repo / "f.txt"
    f.write_text("STAGED\n")
    git(repo, "add", "f.txt")
    f.write_text("UNSTAGED\n")  # the working tree now differs from the index
    done = subprocess.run(
        [sys.executable, str(VERIFIER), "--repo-root", str(repo),
         "--commit-sha", "HEAD", "--staged", "--files", "f.txt"],
        capture_output=True, text=True, check=False,
    )
    # Proof 1 passes on the staged bytes; the unstaged edit is not what is
    # certified. Read the hash the verifier itself printed.
    assert "UNSTAGED" not in done.stdout
    import hashlib
    staged = hashlib.sha256(b"STAGED\n").hexdigest()
    assert staged in done.stdout
