"""disk-cleanup deletes only the regenerable-cache allow-list, and only when asked.

Runs the repo's platform/estate/libexec/disk-cleanup.sh against a fake HOME, so nothing real is
touched: a dry run deletes nothing, apply empties every allow-listed cache and proves it, and the
live tooling / user data beside them survives both.
"""

from __future__ import annotations

import os
import re
import subprocess

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
    home: Path, repo: Path, *args: str, idle: str = "0"
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "none"),
        "DISK_CLEANUP_WT_REPOS": str(repo),
        "DISK_CLEANUP_WT_IDLE_MIN": idle,
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
    try:
        dry = _run_wt(home, repo, "false", "false", "0", "true")
        assert dry.returncode == 0, dry.stdout + dry.stderr
        assert all(w.exists() for w in wts.values()), "a dry run removed a worktree"
        r = _run_wt(home, repo, "true", "false", "0", "true")
    finally:
        busy.kill()
    assert r.returncode == 0, r.stdout + r.stderr
    gone = {n for n, w in wts.items() if not w.exists()}
    assert gone == {"settled", "built"}, r.stdout
    out = r.stdout
    for name, why in [
        ("dirty", "uncommitted or untracked files"),
        ("untracked", "uncommitted or untracked files"),
        ("ignored", "ignored files that are not build output"),
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


def test_a_stale_lock_from_a_dead_run_is_taken_over(tmp_path):
    home = _home(tmp_path)
    dead = subprocess.Popen(["true"])
    dead.wait()
    lock = home / ".estate/disk-cleanup.lock"
    lock.mkdir(parents=True)
    (lock / "pid").write_text(str(dead.pid))
    p = _run(home, "true")
    assert "another disk-cleanup" not in p.stdout
    # go-build, not the whole list: a real yarn on the host (the Fleet dev server) rightly
    # protects the yarn cache, and that guard is tested elsewhere.
    assert not (home / "Library/Caches/go-build").exists()
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
        assert "SKIP   docker  a docker build is running" in p.stdout
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
