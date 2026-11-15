"""Falsifier for bin/estate-stranded.

The founder's rule (2026-11-15): a local commit that has sat unpushed for more than ten minutes
must trigger recovery. A detector that cannot tell a fresh commit from a stale one, or cannot
tell an unpushed commit from a pushed one, is not a detector.
"""

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / "bin" / "estate-stranded"
STALE_S = 11 * 60


def run(*args, cwd, env=None):
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, env=env, check=True
    )


def repo(tmp_path):
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    run("git", "init", "--bare", str(origin), cwd=tmp_path)
    run("git", "clone", str(origin), str(work), cwd=tmp_path)
    run("git", "config", "user.email", "t@example.com", cwd=work)
    run("git", "config", "user.name", "t", cwd=work)
    (work / "seed.txt").write_text("seed\n")
    run("git", "add", "seed.txt", cwd=work)
    run("git", "commit", "-m", "seed", cwd=work)
    run("git", "push", "-u", "origin", "HEAD", cwd=work)
    return work


def commit(work, name, age_s=0):
    (work / name).write_text(name + "\n")
    run("git", "add", name, cwd=work)
    env = dict(os.environ)
    if age_s:
        stamp = f"@{int(time.time()) - age_s} +0000"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    run("git", "commit", "-m", name, cwd=work, env=env)


def detect(work, *extra):
    p = subprocess.run(
        [str(DETECTOR), "--path", str(work), "--json", *extra],
        capture_output=True,
        text=True,
    )
    return p.returncode, json.loads(p.stdout)


def test_a_fresh_unpushed_commit_is_not_stranded(tmp_path):
    work = repo(tmp_path)
    commit(work, "fresh.txt")
    code, body = detect(work)
    assert code == 0, body
    assert body["stranded"] == []


def test_a_commit_unpushed_for_eleven_minutes_is_stranded(tmp_path):
    work = repo(tmp_path)
    commit(work, "stale.txt", age_s=STALE_S)
    code, body = detect(work)
    assert code == 1, body
    assert len(body["stranded"]) == 1
    row = body["stranded"][0]
    assert row["unpushed_commits"] == 1
    assert row["oldest_unpushed_age_s"] >= STALE_S


def test_a_pushed_commit_is_not_stranded_even_when_old(tmp_path):
    work = repo(tmp_path)
    commit(work, "pushed.txt", age_s=STALE_S)
    run("git", "push", "origin", "HEAD", cwd=work)
    code, body = detect(work)
    assert code == 0, body
    assert body["stranded"] == []


def test_the_threshold_is_the_argument_not_a_constant(tmp_path):
    work = repo(tmp_path)
    commit(work, "stale.txt", age_s=STALE_S)
    code, body = detect(work, "--max-age", "99999")
    assert code == 0, body
    assert body["threshold_s"] == 99999
