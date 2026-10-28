"""disk-cleanup deletes only the regenerable-cache allow-list, and only when asked.

Runs the repo's platform/estate/libexec/disk-cleanup.sh against a fake HOME, so nothing real is
touched: a dry run deletes nothing, apply empties every allow-listed cache and proves it, and the
live tooling / user data beside them survives both.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time

import pytest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "platform/estate/libexec/disk-cleanup.sh"

CACHES = [
    ".yarn/berry/cache",
    "Library/Caches/go-build",
    "Library/Caches/pip",
    "Library/Caches/Homebrew",
    ".npm/_cacache",
    ".npm/_npx",
]
# a Cargo build dir (Cargo.toml beside it, cargo's stamp inside) is a cache; a directory that is
# merely called target is not
RUST = "Documents/code/crate/target"
KEPT = [
    ".cache/estate-tools/litellm-venv",
    ".ollama/models",
    "Documents/code/x",
    ".Trash/photo",
    "Documents/code/site/target",
    "Documents/code/crate/src",
    "Documents/code/crate/.claude/worktrees/wf/target",
]


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    for d in CACHES + KEPT + [RUST]:
        (home / d).mkdir(parents=True)
        (home / d / "blob").write_bytes(os.urandom(2 * 1024 * 1024))
    (home / "Documents/code/crate/Cargo.toml").write_text("[package]\n")
    # another agent's worktree: a real Cargo build dir, and still not ours to delete
    agent = home / "Documents/code/crate/.claude/worktrees/wf"
    (agent / "Cargo.toml").write_text("[package]\n")
    (agent / "target/CACHEDIR.TAG").write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n"
    )
    (home / RUST / "CACHEDIR.TAG").write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n"
    )
    return home


def _run(home: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "Documents/code"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        # The critical tier is off here: these tests are about the allow-list, and the tier must
        # not fire because of whatever free space the machine running them happens to have.
        "DISK_CLEANUP_CRIT_MB": "1",
    }
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_dry_run_lists_every_cache_and_deletes_nothing(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "false", "false")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("  would  ") == len(CACHES) + 1, r.stdout
    assert f"  would  rust-target  2M  {home / RUST}" in r.stdout, r.stdout
    for d in CACHES + KEPT + [RUST]:
        assert (home / d / "blob").exists(), d


def test_apply_empties_the_allow_list_and_nothing_else(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "true", "false")
    # a yarn/npm/go/pip/brew process running on this machine makes its cache SKIP, correctly;
    # every cache is either freed or skipped for a named process, never silently kept
    freed = r.stdout.count("  freed  ")
    skipped = r.stdout.count("  SKIP   ")
    assert freed + skipped == len(CACHES) + 1, r.stdout
    assert r.returncode == 0, r.stdout + r.stderr
    assert "free after:" in r.stdout
    gone = [
        d
        for d in CACHES + [RUST]
        if not (home / d).exists() or not any((home / d).iterdir())
    ]
    assert len(gone) == freed, (gone, r.stdout)
    for d in KEPT:
        assert (home / d / "blob").exists(), f"{d} must never be touched"


def test_trash_is_emptied_only_when_opted_in(tmp_path):
    home = _home(tmp_path)
    _run(home, "true", "false")
    assert (home / ".Trash/photo/blob").exists()
    r = _run(home, "true", "true")
    assert "  freed  trash" in r.stdout, r.stdout
    assert (home / ".Trash").is_dir() and not any((home / ".Trash").iterdir())
    assert (home / ".cache/estate-tools/litellm-venv/blob").exists()


def test_refuses_when_home_is_root(tmp_path):
    env = {**os.environ, "HOME": "/", "DISK_GUARD_PATH": str(tmp_path)}
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"], env=env, capture_output=True, text=True
    )
    assert r.returncode == 1 and "REFUSED" in r.stdout


def test_only_below_mb_deletes_nothing_while_there_is_room(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "true", "false", "1")
    assert r.returncode == 0 and "nothing deleted" in r.stdout, r.stdout
    for d in CACHES + KEPT + [RUST]:
        assert (home / d / "blob").exists(), d


def test_only_below_mb_applies_under_the_floor(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "true", "false", "999999999")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "free after:" in r.stdout and "nothing deleted" not in r.stdout, r.stdout


def test_only_below_mb_must_be_a_number(tmp_path):
    r = _run(_home(tmp_path), "true", "false", "10G")
    assert r.returncode == 1 and "REFUSED" in r.stdout, r.stdout


def _git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def _worktrees(tmp_path: Path):
    """A repo under a fake HOME with one worktree per keep-reason and one settled one."""
    home = tmp_path / "home"
    repo = home / "Documents/code/repo"
    repo.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=repo)
    _git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "base",
        cwd=repo,
    )
    wts = {}
    for name in [
        "settled",
        "dirty",
        "untracked",
        "ignored",
        "detached",
        "locked",
        "busy",
        "built",
    ]:
        wt = home / "wt" / name
        if name == "detached":
            _git("worktree", "add", "-q", "--detach", str(wt), cwd=repo)
            _git(
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "only here",
                cwd=wt,
            )
        else:
            _git("worktree", "add", "-q", "-b", name, str(wt), cwd=repo)
        wts[name] = wt
    (wts["dirty"] / "work.txt").write_text("x")
    _git("add", "work.txt", cwd=wts["dirty"])
    (wts["untracked"] / "notes.md").write_text("mine")
    for w in (wts["ignored"], wts["built"]):
        (w / ".gitignore").write_text(".env\nnode_modules/\n")
        _git("add", ".gitignore", cwd=w)
        _git(
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "ignore",
            cwd=w,
        )
    (wts["ignored"] / ".env").write_text("TOKEN_NAME_ONLY=1")
    (wts["built"] / "node_modules/pkg").mkdir(parents=True)
    (wts["built"] / "node_modules/pkg/index.js").write_text("1")
    _git("worktree", "lock", str(wts["locked"]), cwd=repo)
    return home, repo, wts


def _run_wt(
    home: Path, repo: Path, *args: str, idle: str = "0", **extra: str
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "none"),
        "DISK_CLEANUP_WT_REPOS": str(repo),
        "DISK_CLEANUP_WT_IDLE_MIN": idle,
        "DISK_CLEANUP_WT_FRESH_MIN": "0",
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        **{f"DISK_CLEANUP_{k.upper()}": v for k, v in extra.items()},
    }
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_worktrees_removes_only_the_settled_and_keeps_every_kind_of_work(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    busy = subprocess.Popen(["sleep", "60"], cwd=wts["busy"])
    # The busy check is handed a listing (a seam) instead of a live lsof: the walk of every open
    # file on the machine is slower under load, and a test that depends on the machine's load
    # is a flaky test. The listing is what the check consumes, so the test supplies it.
    cwds = tmp_path / "cwds.txt"
    cwds.write_text(f"n{wts['busy']}\n")
    try:
        dry = _run_wt(home, repo, "false", "false", "0", "true", cwds_file=str(cwds))
        assert dry.returncode == 0, dry.stdout + dry.stderr
        assert all(w.exists() for w in wts.values()), "a dry run removed a worktree"
        r = _run_wt(home, repo, "true", "false", "0", "true", cwds_file=str(cwds))
    finally:
        busy.kill()
    assert r.returncode == 0, r.stdout + r.stderr
    gone = {n for n, w in wts.items() if not w.exists()}
    # "ignored" holds only an ignored .env: it is archived to the quarantine, then removed
    assert gone == {"settled", "built", "ignored"}, r.stdout
    out = r.stdout
    for name, why in [
        ("dirty", "uncommitted or untracked files"),
        ("untracked", "uncommitted or untracked files"),
        ("detached", "commits reachable only from this checkout's HEAD"),
        ("locked", "locked"),
        ("busy", "a process is working inside it"),
    ]:
        assert f"{wts[name]}  ({why})" in out, (name, out)
    # the branch and its commits outlive the checkout: git worktree add brings it back
    _git("worktree", "add", "-q", str(wts["settled"]), "settled", cwd=repo)
    assert (wts["settled"] / ".git").exists()


def test_worktrees_used_recently_are_kept(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    r = _run_wt(home, repo, "true", "false", "0", "true", idle="360")
    assert r.returncode == 0, r.stdout + r.stderr
    assert all(w.exists() for w in wts.values()), r.stdout
    assert "used in the last 360m" in r.stdout


def test_a_worktree_already_merged_to_main_is_removed_without_the_idle_wait(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    _git("update-ref", "refs/remotes/origin/main", "main", cwd=repo)
    r = _run_wt(home, repo, "true", "false", "0", "true", idle="360")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not wts["settled"].exists(), (
        r.stdout
    )  # HEAD is in origin/main: nothing to lose
    # work that is not on main keeps its idle wait: "built" holds a commit only its branch has
    assert wts["built"].exists(), r.stdout
    assert wts["dirty"].exists(), (
        r.stdout
    )  # merged or not, uncommitted work is never removed


def test_worktrees_are_off_by_default(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    r = _run_wt(home, repo, "true", "false")
    assert r.returncode == 0 and all(w.exists() for w in wts.values()), r.stdout


# --- leftovers are archived, not a reason to keep 6.6G of checkouts (2026-10-14) ---

APPLY_WT = ("true", "false", "0", "true")


def _age(root: Path, days: float) -> None:
    """Back-date root and everything under it, so the idle and stale windows read it as old."""
    t = os.path.getmtime(root) - days * 86400
    for d, _dirs, files in os.walk(root):
        for f in files:
            os.utime(Path(d) / f, (t, t), follow_symlinks=False)
        os.utime(d, (t, t))


def _gitdir(repo: Path, wt: Path) -> Path:
    return repo / ".git/worktrees" / wt.name


def _quarantine(home: Path, name: str) -> Path:
    [q] = [
        q
        for q in (home / ".estate/quarantine/worktrees").iterdir()
        if q.name.endswith(f"-{name}")
    ]
    return q


def test_a_fresh_worktree_of_main_is_kept_until_the_fresh_floor_passes(tmp_path):
    """2026-10-14: `worktree add --detach origin/main` was removed mid-fetch, minutes after it was
    made: clean, merged, and no process had its cwd there yet."""
    home, repo, wts = _worktrees(tmp_path)
    _git("update-ref", "refs/remotes/origin/main", "main", cwd=repo)
    r = _run_wt(home, repo, *APPLY_WT, idle="360", wt_fresh_min="60")
    assert r.returncode == 0, r.stdout + r.stderr
    assert wts["settled"].exists(), r.stdout
    assert f"{wts['settled']}  (created or used in the last 60m)" in r.stdout, r.stdout
    _age(
        _gitdir(repo, wts["settled"]), 0.1
    )  # 2.4h old: past the floor, merged, so no idle wait
    r = _run_wt(home, repo, *APPLY_WT, idle="360", wt_fresh_min="60")
    assert not wts["settled"].exists(), r.stdout


def test_ignored_leftovers_are_archived_and_the_worktree_removed(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    r = _run_wt(home, repo, *APPLY_WT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not wts["ignored"].exists(), r.stdout
    q = _quarantine(home, "ignored")
    assert f"leftovers (ignored): {q}" in r.stdout, r.stdout
    assert oct(q.stat().st_mode & 0o777) == "0o700"
    names = subprocess.run(
        ["tar", "-tzf", q / "ignored.tgz"], capture_output=True, text=True
    ).stdout
    assert names.split() == [".env"], names
    # the branch comes back with git, the .env from the archive
    _git("worktree", "add", "-q", str(wts["ignored"]), "ignored", cwd=repo)
    subprocess.run(["tar", "-xzf", q / "ignored.tgz", "-C", wts["ignored"]], check=True)
    assert (wts["ignored"] / ".env").read_text() == "TOKEN_NAME_ONLY=1"


def test_ignored_files_written_recently_keep_the_worktree(tmp_path):
    """A server's log or db under an ignored path is live state while it is being written."""
    home, repo, wts = _worktrees(tmp_path)
    _age(_gitdir(repo, wts["ignored"]), 1)
    r = _run_wt(home, repo, *APPLY_WT, idle="360")
    assert wts["ignored"].exists(), r.stdout
    assert (
        "ignored files that are not build output, written in the last 360m" in r.stdout
    ), r.stdout


def test_stale_work_is_saved_then_removed_and_fresh_work_is_not(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    for name in ("dirty", "untracked", "detached"):
        _age(wts[name], 5)
        _age(_gitdir(repo, wts[name]), 5)
    only_here = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=wts["detached"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    r = _run_wt(home, repo, *APPLY_WT, idle="360")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(wts[n].exists() for n in ("dirty", "untracked", "detached")), (
        r.stdout
    )
    assert "work.txt" in (_quarantine(home, "dirty") / "work.patch").read_text()
    names = subprocess.run(
        ["tar", "-tzf", _quarantine(home, "untracked") / "untracked.tgz"],
        capture_output=True,
        text=True,
    ).stdout
    assert names.split() == ["notes.md"], names
    # the detached HEAD's own commit outlives the checkout on a ref, so gc cannot take it
    ref = f"refs/estate/kept/{_quarantine(home, 'detached').name}"
    kept = subprocess.run(
        ["git", "rev-parse", ref], cwd=repo, capture_output=True, text=True
    )
    assert kept.stdout.strip() == only_here, kept.stderr


def test_a_changed_file_touched_inside_three_days_keeps_stale_git_state(tmp_path):
    """An agent editing for days without `git add` moves no git file: the edit itself counts."""
    home, repo, wts = _worktrees(tmp_path)
    _age(_gitdir(repo, wts["untracked"]), 5)
    r = _run_wt(home, repo, *APPLY_WT, idle="360")
    assert wts["untracked"].exists(), r.stdout
    assert f"{wts['untracked']}  (uncommitted or untracked files)" in r.stdout, r.stdout


def test_an_archive_over_the_cap_keeps_the_worktree_and_leaves_nothing(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    (wts["ignored"] / ".env").write_bytes(os.urandom(3 * 1024 * 1024))
    r = _run_wt(home, repo, *APPLY_WT, wt_archive_max_mb="1")
    assert wts["ignored"].exists(), r.stdout
    assert "archive refused: 3M of leftovers, over the 1M archive cap" in r.stdout, (
        r.stdout
    )
    qroot = home / ".estate/quarantine/worktrees"
    assert not any(q.name.endswith("-ignored") for q in qroot.iterdir()), list(
        qroot.iterdir()
    )


def test_the_quarantine_and_its_refs_expire(tmp_path):
    home, repo, wts = _worktrees(tmp_path)
    q = home / ".estate/quarantine/worktrees/20260901T000000Z-old"
    q.mkdir(parents=True)
    (q / "work.patch").write_text("x")
    _git("update-ref", f"refs/estate/kept/{q.name}", "main", cwd=repo)
    _age(q, 40)
    r = _run_wt(home, repo, *APPLY_WT)
    assert not q.exists() and f"freed  quarantine  {q.name}" in r.stdout, r.stdout
    gone = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/estate/kept/{q.name}"], cwd=repo
    )
    assert gone.returncode != 0


def test_stale_temp_goes_and_live_or_foreign_temp_stays(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    t = tmp_path / "T"
    entries = {
        "go-build123": True,  # go's build dir, untouched 1d
        "tmp.Ab12Cd34": True,  # mktemp -d
        "tmpab_cd123": True,  # python tempfile.mkdtemp
        "tmp.Fresh123": False,  # an old dir with a file in it written just now
        "tmp.Hasgit12": False,  # holds a checkout: the worktree pass judges it
        "tmp.Opened12": False,  # a process holds a file open under it
        "kyverno-render": False,  # not a tool's temp name
    }
    for n in entries:
        (t / n / "sub").mkdir(parents=True)
        (t / n / "sub/blob").write_bytes(os.urandom(1024 * 1024))
    (t / "tmp.Hasgit12/wt").mkdir()
    (t / "tmp.Hasgit12/wt/.git").write_text("gitdir: elsewhere\n")
    for n in entries:
        _age(t / n, 1)
    os.utime(t / "tmp.Fresh123/sub/blob")
    holder = open(t / "tmp.Opened12/sub/blob", "rb")
    try:
        repo = tmp_path / "none"
        dry = _run_wt(home, repo, "false", "false", "0", "true", tmp_root=str(t))
        assert all((t / n).exists() for n in entries), dry.stdout
        r = _run_wt(home, repo, *APPLY_WT, tmp_root=str(t))
    finally:
        holder.close()
    for n, goes in entries.items():
        assert (t / n).exists() is not goes, (n, r.stdout)
    assert "(written in the last 360m)" in r.stdout
    assert "(holds a git checkout)" in r.stdout
    assert "(a process has a file open under it)" in r.stdout, r.stdout
    assert t.is_dir(), "the temp root itself is never removed"


@pytest.mark.parametrize("make", ["absent", "not-a-repo"])
def test_a_repo_it_cannot_read_is_blind_not_nothing_to_free(tmp_path, make):
    """2026-10-14: under launchd, macOS kept /bin/bash out of ~/Documents (TCC), `git worktree list`
    failed, and a silent `continue` printed nothing -- 0M freed every tick, read as a clean disk.
    A plain directory stands in for the refused repo: git fails on both the same way."""
    home = tmp_path / "home"
    home.mkdir()
    repo = tmp_path / "repo"
    if make == "not-a-repo":
        repo.mkdir()
    r = _run_wt(home, repo, "true", "false", "0", "true")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "BLIND  worktrees  cannot " in r.stdout and str(repo) in r.stdout, r.stdout


# --- Docker, the lock and the time limits (review by idp-57, 2026-09-30) ---


def _fake_docker(home: Path, prune_sleep: int = 0) -> Path:
    """A docker and rdctl that record their argv; `image prune` can be made to hang."""
    log = home / "docker.log"
    bin_ = home / ".rd/bin"
    bin_.mkdir(parents=True, exist_ok=True)
    (bin_ / "docker").write_text(
        "#!/bin/bash\n"
        f'echo "docker $*" >> "{log}"\n'
        f'case "$*" in *"image prune"*) sleep {prune_sleep};; esac\n'
        "exit 0\n"
    )
    (bin_ / "rdctl").write_text(f'#!/bin/bash\necho "rdctl $*" >> "{log}"\nexit 0\n')
    for f in ("docker", "rdctl"):
        (bin_ / f).chmod(0o755)
    return log


# The build check reads every process on the host, by design: a test that starts a fake build
# (below) is visible to every test running beside it under `-n auto`. Tests that need the prune
# to run pass a pattern nothing on the host can match.
NO_BUILD = {"DISK_CLEANUP_BUILDING": "^never-a-build-9f3c$"}


def _run_env(home: Path, extra: dict, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "Documents/code"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        **extra,
    }
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_docker_prunes_dangling_images_only_never_by_creation_age(tmp_path):
    # `image prune -a --filter until=24h` compares CREATION time: an old base image pulled a
    # minute ago for a queued build would be deleted under it.
    home = _home(tmp_path)
    log = _fake_docker(home)
    p = _run_env(home, NO_BUILD, "true")
    calls = log.read_text()
    assert "image prune -f" in calls and "image prune -af" not in calls, calls
    assert "builder prune -af --filter until=24h" in calls
    assert "rdctl shell sudo fstrim /mnt/data" in calls
    assert "freed  docker" in p.stdout


def test_a_wedged_docker_is_cut_off_and_counted_as_a_failure(tmp_path):
    home = _home(tmp_path)
    _fake_docker(home, prune_sleep=60)
    import time

    t0 = time.monotonic()
    p = _run_env(home, {**NO_BUILD, "DISK_CLEANUP_DOCKER_TIMEOUT": "2"}, "true")
    assert time.monotonic() - t0 < 30, "a hung docker call held the run"
    assert "!! docker image prune -f failed or timed out" in p.stdout
    assert p.returncode == 3


def test_a_blind_busy_check_keeps_every_worktree(tmp_path):
    """A busy check that could not be made must not delete a worktree (2026-10-28).

    `lsof -a -d cwd` walks every open file on the machine; under load it exceeds its bound, the
    listing comes back truncated, and an agent's worktree looks idle. The consequence in
    production is a checkout vanishing under a live agent, so a blind check keeps everything.
    """
    home, repo, wts = _worktrees(tmp_path)
    blind = tmp_path / "cwds.txt"
    blind.write_text("")
    r = _run_wt(home, repo, "true", "false", "0", "true", cwds_file=str(blind))
    assert r.returncode == 0, r.stdout + r.stderr
    assert all(w.exists() for w in wts.values()), r.stdout
    assert "the busy check is blind" in r.stdout, r.stdout


def test_a_second_run_waits_for_the_first(tmp_path):
    home = _home(tmp_path)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        lock = home / ".estate/disk-cleanup.lock"
        lock.mkdir(parents=True)
        (lock / "pid").write_text(str(holder.pid))
        p = _run(home, "true")
        assert f"another disk-cleanup (pid {holder.pid}) is running" in p.stdout
        assert all((home / c / "blob").exists() for c in CACHES), (
            "a second run deleted anyway"
        )
    finally:
        holder.kill()


def test_a_recycled_pid_does_not_close_the_door(tmp_path):
    """The pid in the lock is alive, but it is not the cleaner that wrote it (2026-10-28).

    Measured in production: the holder's pid had been RECYCLED onto an unrelated process, so
    `kill -0` was happy and the cleaner answered "another disk-cleanup is running" forever,
    while the volume sat under the executor's floor and every door in the estate was refused.
    The lock records the holder's start time next to its pid; a mismatch means the pid was
    recycled, and the lock is stale.
    """
    home = _home(tmp_path)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        lock = home / ".estate/disk-cleanup.lock"
        lock.mkdir(parents=True)
        (lock / "pid").write_text(str(holder.pid))
        (lock / "start").write_text("Tue Jan  1 00:00:00 2019")
        p = _run(home, "true")
        assert "another disk-cleanup" not in p.stdout, p.stdout
    finally:
        holder.kill()


def test_a_live_lock_with_the_holder_start_time_is_respected(tmp_path):
    home = _home(tmp_path)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        lock = home / ".estate/disk-cleanup.lock"
        lock.mkdir(parents=True)
        (lock / "pid").write_text(str(holder.pid))
        start = subprocess.run(
            ["ps", "-p", str(holder.pid), "-o", "lstart="],
            capture_output=True,
            text=True,
        ).stdout.strip()
        (lock / "start").write_text(start)
        p = _run(home, "true")
        assert f"another disk-cleanup (pid {holder.pid}) is running" in p.stdout, (
            p.stdout
        )
    finally:
        holder.kill()


def test_a_stale_lock_from_a_dead_run_is_taken_over(tmp_path):
    home = _home(tmp_path)
    dead = subprocess.Popen(["true"])
    dead.wait()
    lock = home / ".estate/disk-cleanup.lock"
    lock.mkdir(parents=True)
    (lock / "pid").write_text(str(dead.pid))
    p = _run(home, "true")
    assert "another disk-cleanup" not in p.stdout
    # One cache, not the whole list: a real yarn or go build on the host (the Fleet dev server, a
    # voice-router build) rightly protects its cache, and those guards are tested elsewhere.
    idle = [
        c
        for c, guard in (
            ("Library/Caches/go-build", "go (build|test|install|run|vet) "),
            ("Library/Caches/pip", "pip3? (install|download|wheel)|-m pip "),
            ("Library/Caches/Homebrew", r"Homebrew/brew\.rb|bin/brew( |$)"),
        )
        if subprocess.run(["pgrep", "-f", guard], capture_output=True).returncode != 0
    ]
    assert idle and not (home / idle[0]).exists(), (idle, p.stdout)
    assert not lock.exists(), "the lock outlived the run"


def test_a_running_compose_build_skips_docker(tmp_path):
    home = _home(tmp_path)
    log = _fake_docker(home)
    builder = subprocess.Popen(
        ["bash", "-c", 'exec -a "docker compose build web" sleep 30']
    )
    try:
        import time

        time.sleep(0.5)
        p = _run(home, "true")
        assert "SKIP   docker  an image build is running" in p.stdout
        assert "prune" not in log.read_text()
    finally:
        builder.kill()


@pytest.mark.parametrize(
    "cmd,building",
    [
        ("docker build -t x .", True),
        ("docker buildx build --push .", True),
        ("docker buildx bake", True),
        ("docker compose build web", True),
        ("docker-compose build", True),
        ("docker compose -f a.yml up -d --build", True),
        ("docker ps", False),
        ("docker compose logs", False),
    ],
)
def test_the_default_build_pattern_names_every_kind_of_build(cmd, building):
    src = SCRIPT.read_text()
    default = re.search(r'DISK_CLEANUP_BUILDING:-(.*?)\}"', src).group(1)
    assert bool(re.search(default, cmd)) is building, cmd


def test_worktrees_under_tmpdir_are_judged_and_others_outside_home_are_not(tmp_path):
    """The dry run of 2026-10-14 had the $TMPDIR check inverted: a checkout in $TMPDIR was
    refused, and one anywhere else outside HOME and /tmp would have been judged."""
    home, repo, wts = _worktrees(tmp_path)
    t = tmp_path / "T"
    inside, outside = t / "wt-in", tmp_path / "elsewhere/wt-out"
    for wt in (inside, outside):
        _git("worktree", "add", "-q", "--detach", str(wt), "main", cwd=repo)
    r = _run_wt(home, repo, *APPLY_WT, tmp_root=str(t))
    assert r.returncode == 0, r.stdout + r.stderr
    assert not inside.exists(), r.stdout
    assert outside.exists(), r.stdout
    assert f"{outside}  (not under HOME, /tmp or $TMPDIR)" in r.stdout, r.stdout


def test_with_no_resolvable_tmp_root_an_outside_worktree_is_kept(tmp_path):
    """The guard must keep a worktree outside HOME and /tmp even when $TMPDIR cannot be
    resolved (2026-10-14: the rewrite uses a single under= flag so both TMP_ROOT-set and
    TMP_ROOT-blank paths are explicit; the old `[ -n "$TMP_ROOT" ] && case ... || keep`
    chain was correct in the blank direction only by accident of operator precedence,
    and the prior tests put every worktree under HOME so the unset path was never hit)."""
    home, repo, wts = _worktrees(tmp_path)
    outside = tmp_path / "elsewhere/wt-out"
    _git("worktree", "add", "-q", "--detach", str(outside), "main", cwd=repo)
    # tmp_root points at a path that does not exist: the script's `else TMP_ROOT=; fi`
    # blanks TMP_ROOT, so the guard runs with no TMPDIR to test against
    r = _run_wt(home, repo, *APPLY_WT, tmp_root=str(tmp_path / "no-such-tmp"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert outside.exists(), r.stdout
    assert f"{outside}  (not under HOME, /tmp or $TMPDIR)" in r.stdout, r.stdout


# --- Chrome code-sign clones, the 2h worktree idle, and the "where the space is" report ---------


def _clones_home(tmp_path: Path) -> tuple[Path, Path]:
    home = _home(tmp_path)
    clones = tmp_path / "X/com.google.Chrome.code_sign_clone"
    for name in (
        "code_sign_clone.held",
        "code_sign_clone.old",
        "code_sign_clone.fresh",
    ):
        (clones / name / "Contents").mkdir(parents=True)
        (clones / name / "Contents/blob").write_bytes(os.urandom(1024 * 1024))
    old = 1_000_000_000  # 2001: well past any fresh floor
    for name in ("code_sign_clone.held", "code_sign_clone.old"):
        for d, _, files in os.walk(clones / name):
            for f in files:
                os.utime(Path(d) / f, (old, old))
            os.utime(d, (old, old))
    return home, clones


def test_chrome_clones_nobody_holds_go_and_the_running_one_stays(tmp_path):
    home, clones = _clones_home(tmp_path)
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "none"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        "DISK_CLEANUP_CHROME_CLONES": str(clones),
    }
    # the running Chrome holds a file in its own clone open for the whole run
    with open(clones / "code_sign_clone.held/Contents/blob", "rb"):
        dry = subprocess.run(
            ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120
        )
        assert (
            "would  chrome-clone" in dry.stdout
            and (clones / "code_sign_clone.old").exists()
        )
        p = subprocess.run(
            ["bash", str(SCRIPT), "true"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (clones / "code_sign_clone.old").exists(), p.stdout
    assert "freed  chrome-clone" in p.stdout
    assert (clones / "code_sign_clone.held").exists(), (
        "the clone a process holds open was deleted"
    )
    assert "held open" in p.stdout
    assert (clones / "code_sign_clone.fresh").exists(), (
        "a clone made minutes ago was deleted"
    )


def test_a_held_clone_reached_through_a_symlink_is_still_held(tmp_path):
    # $TMPDIR says /var/folders, a symlink to /private/var/folders, and lsof prints the physical
    # path: matched unresolved, the running Chrome's clone would read as nobody's and be deleted.
    home, clones = _clones_home(tmp_path)
    link = tmp_path / "via-link"
    link.symlink_to(clones)
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "none"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        "DISK_CLEANUP_CHROME_CLONES": str(link),
    }
    with open(clones / "code_sign_clone.held/Contents/blob", "rb"):
        p = subprocess.run(
            ["bash", str(SCRIPT), "true"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    assert p.returncode == 0, p.stdout + p.stderr
    assert (clones / "code_sign_clone.held").exists(), p.stdout
    assert not (clones / "code_sign_clone.old").exists(), p.stdout


def test_held_clones_are_found_without_walking_the_tree():
    # 2026-10-20: `lsof +D` over 15G of clones ran past its 60s cut-off on nearly every run,
    # went BLIND, kept every clone, and the volume refilled to 0G.
    src = SCRIPT.read_text()
    assert "lsof -Fn +D" not in src
    assert "tmo 60 lsof -nPw -Fn" in src


def test_no_tmpdir_means_the_real_chrome_clones_are_never_reached():
    src = SCRIPT.read_text()
    assert 'CLONES="${DISK_CLEANUP_CHROME_CLONES-${TMP_ROOT:+' in src


def test_worktrees_idle_two_hours_are_settled_by_default():
    src = SCRIPT.read_text()
    assert 'WT_IDLE_MIN="${DISK_CLEANUP_WT_IDLE_MIN:-120}"' in src


def _scan_env(home: Path, **extra: str) -> dict:
    return {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "none"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        "DISK_CLEANUP_BIG_FILE_MB": "1",
        **extra,
    }


def test_under_the_floor_the_log_names_where_the_space_actually_is(tmp_path):
    home = _home(tmp_path)
    big = home / "Library/Application Support/SomeApp"
    big.mkdir(parents=True)
    (big / "store").write_bytes(os.urandom(6 * 1024 * 1024))
    (home / ".estate").mkdir()
    (home / ".estate/fleetview-backend.err.log").write_bytes(b"x" * (3 * 1024 * 1024))
    p = subprocess.run(
        ["bash", str(SCRIPT), "true", "false", str(10**9)],
        env=_scan_env(home),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = p.stdout
    assert "where the space is" in out, out
    assert re.search(r"\d+M  .*/Library/Application Support\n", out), out
    assert re.search(r"\d+M  .*/\.estate/fleetview-backend\.err\.log", out), out
    # the report measures; it never deletes
    assert (big / "store").exists() and (
        home / ".estate/fleetview-backend.err.log"
    ).exists()


def test_the_scan_is_reprinted_not_rerun_inside_its_interval(tmp_path):
    home = _home(tmp_path)
    args = ["bash", str(SCRIPT), "true", "false", str(10**9)]
    first = subprocess.run(
        args, env=_scan_env(home), capture_output=True, text=True, timeout=120
    )
    stamp = re.search(r"measured (\S+)", first.stdout).group(1)
    (home / "late").mkdir()
    (home / "late/blob").write_bytes(os.urandom(4 * 1024 * 1024))
    second = subprocess.run(
        args, env=_scan_env(home), capture_output=True, text=True, timeout=120
    )
    assert f"measured {stamp}" in second.stdout
    assert "/late" not in second.stdout.split("where the space is")[1]
    third = subprocess.run(
        args,
        env=_scan_env(home, DISK_CLEANUP_SCAN_EVERY_MIN="0"),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert "/late" in third.stdout.split("where the space is")[1]


def test_a_healthy_disk_is_not_scanned(tmp_path):
    home = _home(tmp_path)
    p = subprocess.run(
        ["bash", str(SCRIPT), "true", "false", "1"],
        env=_scan_env(home),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert "where the space is" not in p.stdout


def test_system_spots_print_megabytes_or_unreadable(tmp_path):
    home = _home(tmp_path)
    spot = tmp_path / "Update"
    spot.mkdir()
    (spot / "blob").write_bytes(os.urandom(3 * 1024 * 1024))
    p = subprocess.run(
        ["bash", str(SCRIPT), "true", "false", str(10**9)],
        env=_scan_env(home, DISK_CLEANUP_SYSTEM_SPOTS=str(spot)),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert re.search(r"  system  \d+M  " + re.escape(str(spot)) + r"\n", p.stdout), (
        p.stdout
    )


# THE CRITICAL TIER. Measured 2026-10-24 on the founder's laptop: 7.7Gi free of 113Gi (92% used)
# with every allow-list cache empty, because the growers were never on it -- ~/.nvm/versions/node
# 2570M, ~/.rustup/toolchains 2659M, ~/.local/share/claude/versions 545M, ~/.ollama/models 3.5G
# before the founder killed the laptop's ollama on 2026-09-10. The tier exists for that, and it
# keeps four things for stated reasons: the newest of a family, a version the estate's own
# runtime names, anything a running process holds open, and rustup's default toolchain.
OLD_NODE = ".nvm/versions/node/v20.11.1"
NEW_NODE = ".nvm/versions/node/v22.15.1"
OLD_RUST = ".rustup/toolchains/1.70.0-x86_64-apple-darwin"
DEFAULT_RUST = ".rustup/toolchains/stable-aarch64-apple-darwin"
OLD_CLAUDE = ".local/share/claude/versions/2.1.307"
NEW_CLAUDE = ".local/share/claude/versions/2.1.400"
OLLAMA = ".ollama/models"


def _crit_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    for d in (
        OLD_NODE,
        NEW_NODE,
        OLD_RUST,
        DEFAULT_RUST,
        OLD_CLAUDE,
        NEW_CLAUDE,
        OLLAMA,
    ):
        (home / d).mkdir(parents=True)
        (home / d / "blob").write_bytes(os.urandom(2 * 1024 * 1024))
    (home / ".rustup/settings.toml").write_text(
        '[toolchain]\ndefault_toolchain = "stable"\n'
    )
    (home / ".estate/libexec").mkdir(parents=True)
    return home


# The critical tier's guards ask the machine's process table ("is a cargo/rustc/go/git-gc
# running?"). That is right in production and wrong in a test: the guard is machine-wide, so a
# test that asserts the RECLAIM branch fails whenever anything else on the machine is building
# -- including this file's own guard test, whose fake `cargo` is alive for 30s while the
# estate's runner runs the file in parallel. Measured 2026-10-26 on origin/main: 1 failed,
# 53 passed. So the pattern is a seam in the script (DISK_CLEANUP_CARGO_PROC and its three
# siblings) and a test points it at a name no process can have. The one test that PROVES the
# guard keeps the script's shipped defaults.
NO_BUILD_PROC = "^disk-cleanup-no-build-process-9f3c$"


def _crit_run(
    home: Path,
    apply: str = "true",
    crit_mb: str = "999999999",
    extra: dict | None = None,
    isolate_build_guard: bool = True,
):
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "Documents/code"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        "DISK_CLEANUP_CRIT_MB": crit_mb,
    }
    if isolate_build_guard:
        env.update(
            {
                "DISK_CLEANUP_CARGO_PROC": NO_BUILD_PROC,
                "DISK_CLEANUP_GO_PROC": NO_BUILD_PROC,
                "DISK_CLEANUP_GIT_BUSY": NO_BUILD_PROC,
                "DISK_CLEANUP_OLLAMA_PROC": NO_BUILD_PROC,
            }
        )
    env.update(extra or {})
    return subprocess.run(
        ["bash", str(SCRIPT), apply, "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_the_critical_tier_is_off_above_the_floor(tmp_path):
    home = _crit_home(tmp_path)
    r = _crit_run(home, "true", "1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "critical tier" not in r.stdout, r.stdout
    for d in (
        OLD_NODE,
        NEW_NODE,
        OLD_RUST,
        DEFAULT_RUST,
        OLD_CLAUDE,
        NEW_CLAUDE,
        OLLAMA,
    ):
        assert (home / d / "blob").exists(), d


def test_the_critical_tier_reclaims_the_old_toolchains_and_keeps_the_rest(tmp_path):
    home = _crit_home(tmp_path)
    r = _crit_run(home, "true")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "critical tier" in r.stdout, r.stdout
    # gone: the superseded node version, the superseded rustup toolchain, the superseded claude
    # build, and ollama's weights (no ollama server is running in the test)
    for d in (OLD_NODE, OLD_RUST, OLD_CLAUDE, OLLAMA):
        assert not (home / d).exists() or not any((home / d).iterdir()), d
    # kept: the newest of each family, and rustup's default toolchain
    for d in (NEW_NODE, NEW_CLAUDE, DEFAULT_RUST):
        assert (home / d / "blob").exists(), d
    assert "  freed  node-version" in r.stdout, r.stdout
    assert "  freed  rust-toolchain" in r.stdout, r.stdout
    assert "  freed  claude-version" in r.stdout, r.stdout
    assert "  freed  ollama-models" in r.stdout, r.stdout
    assert "(nvm install v20.11.1)" in r.stdout, r.stdout
    assert "rustup's default toolchain" in r.stdout, r.stdout


def test_the_version_the_estate_runtime_names_is_kept(tmp_path):
    home = _crit_home(tmp_path)
    # this is what ~/.estate/libexec/pi-real looks like: a pinned node path
    (home / ".estate/libexec/pi-real").write_text(
        '#!/bin/bash\nexec "$HOME"/.nvm/versions/node/v20.11.1/bin/pi "$@"\n'
    )
    r = _crit_run(home, "true")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (home / OLD_NODE / "blob").exists(), "the pinned node version must survive"
    assert "the estate's runtime names it" in r.stdout, r.stdout


def test_the_critical_tier_dry_run_reclaims_nothing(tmp_path):
    home = _crit_home(tmp_path)
    r = _crit_run(home, "false")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "  would  node-version" in r.stdout, r.stdout
    for d in (OLD_NODE, OLD_RUST, OLD_CLAUDE, OLLAMA):
        assert (home / d / "blob").exists(), d


def test_a_non_numeric_critical_floor_is_refused(tmp_path):
    home = _crit_home(tmp_path)
    r = _crit_run(home, "true", "soon")
    assert r.returncode == 1 and "REFUSED" in r.stdout, r.stdout


# --- the second round of the critical tier: the estate's own loose git objects, and the build
# tools' package caches. Measured 2026-10-24 on the founder's laptop: the graph clone held 5415
# loose objects = 3.05 GiB (its pack held 11 MiB) and ~/.cargo/registry + ~/go/pkg/mod held
# 1855M, while the volume sat at 8725M free -- under the floor with nothing the tier could give.

CARGO_REGISTRY = ".cargo/registry"
GO_MODCACHE = "go/pkg/mod"
GRAPH_REPO = ".estate/graph/estate-graph"


def _graph_repo(home: Path) -> Path:
    """A clone with loose objects: several similar transcripts, committed and never repacked."""
    repo = home / GRAPH_REPO
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    sessions = repo / "sessions"
    sessions.mkdir()
    for i in range(6):
        body = "".join(f"session {i} line {n} of the transcript\n" for n in range(6000))
        (sessions / f"2026102{i}T000000Z-no-session.md").write_text(body)
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=agent@estate",
            "-c",
            "user.name=agent",
            "commit",
            "-q",
            "-m",
            "graph-drain: 6 sessions",
        ],
        check=True,
        capture_output=True,
    )
    return repo


def _loose_count(repo: Path) -> int:
    out = subprocess.run(
        ["git", "-C", str(repo), "count-objects", "-v"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("count:"):
            return int(line.split()[1])
    return 0


def test_the_critical_tier_repacks_the_estate_clone_and_loses_nothing(tmp_path):
    home = _crit_home(tmp_path)
    repo = _graph_repo(home)
    assert _loose_count(repo) > 0, "the fixture must start with loose objects"
    r = _crit_run(home, "true", extra={"DISK_CLEANUP_REPACK_MIN_KB": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "git-repack" in r.stdout, r.stdout
    assert _loose_count(repo) == 0, "every object must be in the pack now"
    # and nothing was lost: the history and every byte of every transcript are still there
    log = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
    ).stdout
    assert "graph-drain: 6 sessions" in log, log
    blob = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "cat-file",
            "-p",
            "HEAD:sessions/20261020T000000Z-no-session.md",
        ],
        capture_output=True,
        text=True,
    ).stdout
    assert "session 0 line 5999 of the transcript" in blob, blob[:200]


def test_the_critical_tier_reclaims_the_build_tools_package_caches(tmp_path):
    home = _crit_home(tmp_path)
    for d in (CARGO_REGISTRY, GO_MODCACHE):
        (home / d).mkdir(parents=True)
        (home / d / "blob").write_bytes(os.urandom(2 * 1024 * 1024))
    r = _crit_run(home, "true")
    assert r.returncode == 0, r.stdout + r.stderr
    for d in (CARGO_REGISTRY, GO_MODCACHE):
        assert not (home / d).exists() or not any((home / d).iterdir()), d
    assert "  freed  cargo-registry" in r.stdout, r.stdout
    assert "  freed  go-modcache" in r.stdout, r.stdout
    assert "(cargo fetch)" in r.stdout, r.stdout
    assert "(go mod download)" in r.stdout, r.stdout


def test_a_running_cargo_or_go_keeps_its_package_cache(tmp_path):
    home = _crit_home(tmp_path)
    for d in (CARGO_REGISTRY, GO_MODCACHE):
        (home / d).mkdir(parents=True)
        (home / d / "blob").write_bytes(os.urandom(1024))
    # a build is running: the argv is what the tools look like to pgrep
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", "import os; os.execv('/bin/sleep', ['cargo', '30'])"]
        ),
        # `go build 30`: argv[0] is the program name pgrep sees ("go build 30") and
        # argv[1] is the one argument sleep parses, so the probe stays alive for 30s.
        # A bare "go build" makes sleep exit at once ("usage: sleep seconds") and the
        # probe proved nothing -- the cache was deleted under a process that was gone.
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import os; os.execv('/bin/sleep', ['go build', '30'])",
            ]
        ),
    ]
    # this is the one test that keeps the script's SHIPPED patterns (no seam): the guard must
    # refuse to reclaim while a build is running, with the defaults the estate runs.
    try:
        time.sleep(1.0)
        r = _crit_run(home, "true", isolate_build_guard=False)
        assert r.returncode == 0, r.stdout + r.stderr
        assert (home / CARGO_REGISTRY / "blob").exists(), (
            "a running cargo keeps its registry"
        )
        assert (home / GO_MODCACHE / "blob").exists(), (
            "a running go build keeps its module cache"
        )
        assert "a cargo/rustc process is running" in r.stdout, r.stdout
        assert "a go build is running" in r.stdout, r.stdout
    finally:
        for p in procs:
            p.kill()
            p.wait(timeout=10)


def test_the_critical_tier_dry_run_touches_none_of_the_new_families(tmp_path):
    home = _crit_home(tmp_path)
    repo = _graph_repo(home)
    for d in (CARGO_REGISTRY, GO_MODCACHE):
        (home / d).mkdir(parents=True)
        (home / d / "blob").write_bytes(os.urandom(1024))
    r = _crit_run(home, "false", extra={"DISK_CLEANUP_REPACK_MIN_KB": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "  would  git-repack" in r.stdout, r.stdout
    assert "  would  cargo-registry" in r.stdout, r.stdout
    assert "  would  go-modcache" in r.stdout, r.stdout
    assert _loose_count(repo) > 0, "a dry run must not repack anything"
    assert (home / CARGO_REGISTRY / "blob").exists()
    assert (home / GO_MODCACHE / "blob").exists()


# ---------------------------------------------------------------------------
# THE TARGET, THE RESULT LINE, THE INCREMENTAL MODE AND THE RESIDENT GUARDIAN (2026-10-28).
#
# The cleaner became target-driven and incremental because the old watcher was neither: it ran
# the FULL sweep with a 240s budget every five minutes, held the reclaim lock for 240 of every
# 300 seconds, and freed nothing, because the phases it reached first yield nothing and the
# tier that holds the weight was last. These tests pin the new contract: one machine-readable
# result, a target that stops the reclaim, an incremental mode that skips the slow phases, and
# a guardian that does nothing at all when the volume is healthy.

GUARDIAN = Path(__file__).resolve().parents[2] / "bin/idp-disk-watch"


def _target_env(home: Path, **extra: str) -> dict:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "Documents/code"),
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        "DISK_CLEANUP_CRIT_MB": "999999999",
        # the surface scan must look at a directory that exists and says nothing, so the estate
        # keeps every package that its OWN runtime does not name
        "DISK_CLEANUP_SURFACE_DIRS": str(home / "surface"),
        "DISK_CLEANUP_RUNTIME_TREE": str(home / "runtime"),
    }
    for k, v in extra.items():
        env[k] = str(v)
    return env


def _npm_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    nm = home / ".nvm/versions/node/v22.15.1/lib/node_modules"
    (nm / "promptfoo").mkdir(parents=True)
    (nm / "promptfoo" / "blob").write_bytes(os.urandom(30 * 1024 * 1024))
    (nm / "@openai/codex").mkdir(parents=True)
    (nm / "@openai/codex" / "blob").write_bytes(os.urandom(30 * 1024 * 1024))
    (home / ".estate/libexec").mkdir(parents=True)
    (home / "surface").mkdir(parents=True)
    (home / "runtime").mkdir(parents=True)
    return home


def test_the_result_line_is_machine_readable(tmp_path):
    """The guardian parses this line and nothing else, so its shape is a contract."""
    home = _home(tmp_path)
    r = _run(home, "false", "false")
    assert re.search(
        r"^RESULT mode=\S+ free_before_mb=\d+ free_after_mb=\d+ target_mb=\d+ met=\S+ freed_mb=-?\d+$",
        r.stdout,
        re.M,
    ), r.stdout


def test_an_unused_global_npm_package_is_reclaimed_and_the_keep_list_is_kept(tmp_path):
    """The measured 1702M (promptfoo) and the measured 672M (@openai/codex), in one fixture."""
    home = _npm_home(tmp_path)
    # a target the volume cannot reach, so the tier actually reclaims (a target already met
    # stops the reclaim on purpose -- that is the next test)
    env = _target_env(home, DISK_CLEANUP_TARGET_MB="999999999")
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (
        home / ".nvm/versions/node/v22.15.1/lib/node_modules/promptfoo"
    ).exists(), r.stdout
    assert (
        home / ".nvm/versions/node/v22.15.1/lib/node_modules/@openai/codex"
    ).exists(), r.stdout
    assert "keep   npm-global" in r.stdout and "@openai" in r.stdout, r.stdout


def test_a_package_the_estates_own_runtime_names_is_kept(tmp_path):
    home = _npm_home(tmp_path)
    surface = home / "surface"
    (surface / "epic.md").write_text("we run promptfoo in CI\n")
    env = _target_env(home, DISK_CLEANUP_TARGET_MB="999999999")
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert (home / ".nvm/versions/node/v22.15.1/lib/node_modules/promptfoo").exists(), (
        r.stdout
    )
    assert "the estate's own runtime names it" in r.stdout, r.stdout


def test_a_claude_build_is_a_file_and_is_reclaimed(tmp_path):
    """A claude build is a regular file (~273M each). The rule asked for a directory, so it
    could never fire and 546M of superseded builds was unreachable."""
    home = tmp_path / "home"
    versions = home / ".local/share/claude/versions"
    versions.mkdir(parents=True)
    (versions / "2.1.307").write_bytes(os.urandom(30 * 1024 * 1024))
    (versions / "2.1.400").write_bytes(os.urandom(30 * 1024 * 1024))
    (home / ".estate/libexec").mkdir(parents=True)
    env = _target_env(home, DISK_CLEANUP_TARGET_MB="999999999")
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (versions / "2.1.307").exists(), r.stdout
    assert (versions / "2.1.400").exists(), r.stdout


def test_a_met_target_stops_the_reclaim_and_says_so(tmp_path):
    """Reclaiming past the goal is disruption nobody asked for."""
    home = _npm_home(tmp_path)
    env = _target_env(home, DISK_CLEANUP_TARGET_MB="1")
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert (home / ".nvm/versions/node/v22.15.1/lib/node_modules/promptfoo").exists(), (
        r.stdout
    )
    assert "the target (1M free) is met" in r.stdout, r.stdout
    assert re.search(r"^RESULT .*met=yes ", r.stdout, re.M), r.stdout


def test_an_unreachable_target_prints_a_measured_blocked_by_table(tmp_path):
    home = _npm_home(tmp_path)
    env = _target_env(home, DISK_CLEANUP_TARGET_MB="999999999")
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert "blocked by" in r.stdout, r.stdout
    assert re.search(r"^    \d+M  \S+  \(.+\)$", r.stdout, re.M), r.stdout
    assert re.search(r"^RESULT .*met=no ", r.stdout, re.M), r.stdout


def test_the_incremental_mode_skips_the_slow_phases(tmp_path):
    """The guardian's mode: the two fast tiers only, no HOME scan, no worktree walk, no docker."""
    home = _home(tmp_path)
    env = _target_env(home, DISK_CLEANUP_INCREMENTAL="1")
    # worktrees=true: the phase is then WANTED, so the engine prints why it skipped it
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false", "0", "true"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert re.search(r"^RESULT mode=incremental ", r.stdout, re.M), r.stdout
    # the slow phases are SKIPPED BY NAME, not run and failed
    assert "SKIP   docker" in r.stdout, r.stdout
    assert "SKIP   worktrees" in r.stdout, r.stdout


def test_the_guardian_does_nothing_when_the_volume_is_healthy(tmp_path):
    home = tmp_path / "home"
    (home / ".estate").mkdir(parents=True)
    calls = tmp_path / "calls"
    cleaner = tmp_path / "cleaner.sh"
    cleaner.write_text(f"#!/bin/bash\necho called >> {calls}\necho 'RESULT mode=x'\n")
    cleaner.chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_WATCH_TARGET_MB": "1",  # met: the volume is above the goal
        "DISK_WATCH_CYCLE_S": "1",
        "DISK_WATCH_CLEANER": str(cleaner),
        "DISK_WATCH_RAM_FLOOR_MB": "0",  # the brake must not fire in a test
        "DISK_WATCH_SWAP_MAX_PCT": "100",
    }
    proc = subprocess.Popen(
        [sys.executable, str(GUARDIAN)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(4)
    finally:
        proc.terminate()
        proc.wait(timeout=15)
    hb = home / ".estate/heartbeats/disk-guardian.json"
    assert hb.is_file(), "the guardian must write its heartbeat"
    import json as _json

    data = _json.loads(hb.read_text())
    assert data["state"] == "healthy", data
    assert data["free_mb"] > 0, data
    assert not calls.exists(), "a healthy guardian must not run the cleaner"


def test_the_guardian_takes_one_bounded_step_when_the_volume_is_under_the_target(
    tmp_path,
):
    home = tmp_path / "home"
    (home / ".estate").mkdir(parents=True)
    cleaner = tmp_path / "cleaner.sh"
    cleaner.write_text(
        "echo 'RESULT mode=incremental free_before_mb=100 free_after_mb=142 "
        "target_mb=4000 met=no freed_mb=42'\n"
    )
    cleaner.chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_WATCH_TARGET_MB": "4000",  # never met here
        "DISK_WATCH_CYCLE_S": "1",
        "DISK_WATCH_CLEANER": str(cleaner),
        "DISK_WATCH_RAM_FLOOR_MB": "0",
        "DISK_WATCH_SWAP_MAX_PCT": "100",
    }
    proc = subprocess.Popen(
        [sys.executable, str(GUARDIAN)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(4)
    finally:
        proc.terminate()
        proc.wait(timeout=15)
    import json as _json

    hb = _json.loads((home / ".estate/heartbeats/disk-guardian.json").read_text())
    assert hb["state"] == "reclaiming", hb
    assert hb["last_freed_mb"] == "42", hb
    log = (home / ".estate/disk-watch.log").read_text()
    assert "freed=42M" in log, log
    assert "met=no" in log, log
