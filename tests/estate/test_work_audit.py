"""work-audit tells landed, landed-then-deleted and never-landed work apart, on a real git repo.

The intent exists because work went missing for weeks with nothing saying so (founder,
2026-09-29). Each verdict below is produced by the real script against real commits; a LOST that
cannot be told from a REMOVED would send agents chasing work that was deleted on purpose.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "platform/estate/libexec/work-audit.py"
spec = importlib.util.spec_from_file_location("work_audit", SCRIPT)
wa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wa)


def g(repo: Path, *a: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *a], check=True, capture_output=True, text=True
    ).stdout


def commit(repo: Path, name: str, body: str, msg: str) -> None:
    (repo / name).write_text(body)
    g(repo, "add", "-A")
    g(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        msg,
        "--no-verify",
    )


def branch_diff(repo: Path, br: str) -> str:
    return g(repo, "diff", g(repo, "merge-base", "main", br).strip(), br)


def test_landed_removed_lost(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    g(repo, "init", "-q", "-b", "main")
    commit(repo, "base.txt", "the base line of this repository\n", "base")

    for br, line in (
        ("landed", "feature that reached main intact"),
        ("removed", "feature that reached main then was deleted"),
        ("lost", "feature that never reached main at all"),
    ):
        g(repo, "checkout", "-q", "-b", br, "main")
        commit(repo, f"{br}.txt", line + "\n", br)
        g(repo, "checkout", "-q", "main")

    for br in (
        "landed",
        "removed",
    ):  # squash-land two of them, the way merge-when-green does
        g(repo, "merge", "-q", "--squash", br)
        g(
            repo,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            f"land {br}",
            "--no-verify",
        )
    g(repo, "rm", "-q", "removed.txt")
    g(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "delete removed",
        "--no-verify",
    )

    got = {
        br: wa.landed(repo, "main", branch_diff(repo, br))["verdict"]
        for br in ("landed", "removed", "lost")
    }
    assert got == {"landed": "LANDED", "removed": "REMOVED", "lost": "LOST"}, got


def test_noise_paths_and_short_lines_prove_nothing():
    diff = (
        "+++ b/packages/x/target/debug/foo.json\n+a line long enough to count\n"
        "+++ b/src/real.py\n+}\n+fi\n+a line long enough to count\n"
    )
    assert wa.added_by_file(diff) == {"src/real.py": ["a line long enough to count"]}
