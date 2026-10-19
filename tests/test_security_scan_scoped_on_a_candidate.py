"""idp#6606: ESTATE_SCAN_BASE scopes the gitleaks walk to the commits a candidate adds.

A Greenlane candidate is main plus its lanes; every commit already on main was scanned in the
candidate that landed it. So on queue/** the walk is base..HEAD, and on main (no base) it is all
of history. A base that does not resolve must widen the scan back to everything, never narrow it.
`gitleaks` is a stub on PATH that records the range it was asked to walk.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCAN = Path(__file__).resolve().parents[1] / "bin" / "estate-security-scan"
GIT = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]


@pytest.fixture
def scan(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    subprocess.run([*GIT, "init", "-q", "-b", "main"], cwd=src, check=True)
    for n in ("base", "lane-1", "lane-2"):
        (src / f"{n}.txt").write_text(n)
        subprocess.run([*GIT, "add", "-A"], cwd=src, check=True)
        subprocess.run([*GIT, "commit", "-qm", n], cwd=src, check=True)
        if n == "base":
            subprocess.run([*GIT, "branch", "base"], cwd=src, check=True)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gitleaks.argv"
    stub = bin_dir / "gitleaks"
    stub.write_text(
        '#!/bin/sh\n[ "$1" = version ] && { echo 8.30.1; exit 0; }\n'
        f'printf "%s\\n" "$@" > {log}\nexit 0\n'
    )
    stub.chmod(0o755)

    def run(base: str | None) -> tuple[str, list[str]]:
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
        env.pop("ESTATE_SCAN_BASE", None)
        if base is not None:
            env["ESTATE_SCAN_BASE"] = base
        out = subprocess.run(
            [str(SCAN), "--source", str(src)], capture_output=True, text=True, env=env
        ).stdout
        secrets = next(l for l in out.splitlines() if " secrets " in l)
        return secrets, log.read_text().split()

    return run


def test_a_candidate_walks_only_the_commits_it_adds(scan):
    line, argv = scan("base")
    assert "--log-opts=base..HEAD" in argv, argv
    assert line.startswith("ok") and "2 commit(s)" in line, line


def test_main_walks_all_of_history(scan):
    line, argv = scan(None)
    assert "--log-opts=HEAD" in argv, argv
    assert "no leaks in git history" in line, line


def test_an_unresolvable_base_widens_to_all_of_history(scan):
    line, argv = scan("origin/does-not-exist")
    assert "--log-opts=HEAD" in argv, argv
    assert "does not resolve" in line, line
