"""Tests for platform/estate/bin/estate-converge (docs/tickets/2026-09-27-merged-is-operating.md).

Hermetic: a local git origin, a tmp prefix standing in for /usr/local/estate, a tmp home standing
in for the console user's. No network, no sleep, no launchd.
"""

from __future__ import annotations

import fcntl
import importlib.machinery
import io
import json
import os
import shutil
import stat
import subprocess  # noqa: S404 -- fixed argv, no shell
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONVERGER = REPO_ROOT / "platform" / "estate" / "bin" / "estate-converge"

GIT_CONFIG_ARGS = [
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@t",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
]


def make_writable(path: Path) -> None:
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            p = Path(root) / name
            if p.is_symlink():
                continue
            try:
                p.chmod(p.stat().st_mode | stat.S_IWUSR)
            except OSError:
                pass


def _bare_git_env() -> dict:
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _git(repo: Path, args: list) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(repo)] + GIT_CONFIG_ARGS + args,  # noqa: S607
        check=True,
        env=_bare_git_env(),
        capture_output=True,
        text=True,
    )


def commit(origin: Path, rel: str, text: str, msg: str, mode: int = 0o644) -> None:
    path = origin / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)
    _git(origin, ["add", "-A"])
    _git(origin, ["commit", "-q", "-m", msg])


@pytest.fixture
def origin(tmp_path: Path):
    repo = tmp_path / "origin"
    repo.mkdir()
    subprocess.run(  # noqa: S603
        ["git"] + GIT_CONFIG_ARGS + ["init", "-q", "-b", "main", str(repo)],  # noqa: S607
        check=True,
        env=_bare_git_env(),
    )
    estate_dir = repo / "platform" / "estate"
    (estate_dir / "intents").mkdir(parents=True)
    (estate_dir / "libexec").mkdir(parents=True)
    (estate_dir / "bin").mkdir(parents=True)
    (estate_dir / "intents" / "a.yaml").write_text("name: a\nversion: 1\n")
    helper = estate_dir / "libexec" / "h.sh"
    helper.write_text("#!/bin/sh\necho hi\n")
    helper.chmod(0o755)
    tool = estate_dir / "bin" / "tool"
    tool.write_text("#!/bin/sh\necho tool\n")
    tool.chmod(0o755)
    _git(repo, ["add", "-A"])
    _git(repo, ["commit", "-q", "-m", "first (#11)"])
    yield repo
    make_writable(tmp_path)


def env_for(tmp_path: Path, origin: Path) -> dict:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "ESTATE_PREFIX": str(tmp_path / "prefix"),
        "ESTATE_LINK_HOMES": str(home),
        "ESTATE_REMOTE": str(origin),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }


def run_converger(
    tmp_path: Path, origin: Path, extra_env=None, script: Path = CONVERGER, args=()
) -> subprocess.CompletedProcess:
    env = env_for(tmp_path, origin)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script)] + list(args),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def state_of(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "prefix" / "converge" / "state.json").read_text())


def ledger_lines(tmp_path: Path) -> list:
    path = tmp_path / "prefix" / "converge" / "ledger.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_first_run_converges_read_only_release_linked_into_home(
    tmp_path: Path, origin: Path
) -> None:
    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("converged")

    estate = tmp_path / "home" / ".estate"
    assert (estate / "intents" / "a.yaml").read_text() == "name: a\nversion: 1\n"
    assert (estate / "intents").is_symlink()
    assert (estate / "libexec").is_symlink()
    assert (estate / "bin" / "tool").is_symlink()
    current = tmp_path / "prefix" / "releases" / "current"
    assert os.readlink(str(estate / "intents")) == str(current / "intents")

    release = current.resolve()
    assert stat.S_IMODE(release.stat().st_mode) == 0o555
    assert stat.S_IMODE((release / "intents" / "a.yaml").stat().st_mode) == 0o444
    assert stat.S_IMODE((release / "bin" / "tool").stat().st_mode) == 0o555
    with pytest.raises(PermissionError):
        (release / "intents" / "a.yaml").write_text("tampered")

    lines = ledger_lines(tmp_path)
    assert len(lines) == 1
    assert lines[0]["prs"] == [11]

    state = state_of(tmp_path)
    assert state["behind"] is False
    assert state["last_error"] is None
    assert state["homes"] == [str(tmp_path / "home")]
    assert state["current_sha"] == state["main_sha"]


def test_preexisting_hand_copies_are_moved_aside_never_deleted(
    tmp_path: Path, origin: Path
) -> None:
    estate = tmp_path / "home" / ".estate"
    (estate / "intents").mkdir(parents=True)
    (estate / "intents" / "hand.yaml").write_text("hand-made\n")
    (estate / "bin").mkdir(parents=True)
    (estate / "bin" / "tool").write_text("hand tool\n")

    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr

    pre_intents = list(estate.glob("intents.pre-converge-*"))
    assert len(pre_intents) == 1
    assert (pre_intents[0] / "hand.yaml").read_text() == "hand-made\n"
    pre_bin = list((estate / "bin").glob("tool.pre-converge-*"))
    assert len(pre_bin) == 1
    assert pre_bin[0].read_text() == "hand tool\n"
    assert (estate / "bin" / "tool").is_symlink()
    assert "intents" in state_of(tmp_path)["drift"]


def test_retargeted_link_is_repaired_and_reported_without_a_release(
    tmp_path: Path, origin: Path
) -> None:
    run_converger(tmp_path, origin)
    estate = tmp_path / "home" / ".estate"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (estate / "intents").unlink()
    (estate / "intents").symlink_to(elsewhere)

    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("up to date")
    assert (estate / "intents" / "a.yaml").is_file()
    assert state_of(tmp_path)["drift"] == ["intents"]
    assert len(ledger_lines(tmp_path)) == 1

    run_converger(tmp_path, origin)
    assert state_of(tmp_path)["drift"] == []


def test_second_commit_is_delivered_with_its_pr(tmp_path: Path, origin: Path) -> None:
    run_converger(tmp_path, origin)
    commit(
        origin,
        "platform/estate/intents/a.yaml",
        "name: a\nversion: 2\n",
        "second (#12)",
    )

    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("converged")
    estate = tmp_path / "home" / ".estate"
    assert (estate / "intents" / "a.yaml").read_text() == "name: a\nversion: 2\n"

    lines = ledger_lines(tmp_path)
    assert len(lines) == 2
    assert lines[1]["prs"] == [12]
    assert lines[1]["from_sha"] == lines[0]["to_sha"]
    assert isinstance(lines[1]["latency_s"], int)
    assert lines[1]["latency_s"] >= 0


def test_no_change_writes_no_ledger_line(tmp_path: Path, origin: Path) -> None:
    run_converger(tmp_path, origin)
    first_state = state_of(tmp_path)

    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("up to date")
    assert len(ledger_lines(tmp_path)) == 1
    assert state_of(tmp_path)["checked_at"] != first_state["checked_at"]


def test_unreachable_remote_changes_nothing_and_is_recorded(
    tmp_path: Path, origin: Path
) -> None:
    run_converger(tmp_path, origin)
    before = state_of(tmp_path)

    missing = tmp_path / "does-not-exist"
    result = run_converger(tmp_path, origin, extra_env={"ESTATE_REMOTE": str(missing)})
    assert result.returncode == 1

    after = state_of(tmp_path)
    assert after["last_error"]
    assert after["current_sha"] == before["current_sha"]
    cur = (tmp_path / "prefix" / "releases" / "current").resolve()
    assert cur.name == before["current_sha"][:12]
    assert (tmp_path / "home" / ".estate" / "intents" / "a.yaml").is_file()


def test_commit_outside_platform_estate_is_ignored(
    tmp_path: Path, origin: Path
) -> None:
    run_converger(tmp_path, origin)
    commit(origin, "README.md", "unrelated\n", "docs (#99)")

    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("up to date")
    assert len(ledger_lines(tmp_path)) == 1


def test_prune_keeps_at_most_five_releases_and_current(
    tmp_path: Path, origin: Path
) -> None:
    run_converger(tmp_path, origin)
    for i in range(2, 9):
        commit(
            origin,
            "platform/estate/intents/a.yaml",
            "name: a\nversion: {0}\n".format(i),
            "rev{0} (#{1})".format(i, i + 10),
        )
        result = run_converger(tmp_path, origin)
        assert result.returncode == 0, result.stderr

    rel = tmp_path / "prefix" / "releases"
    releases = [d for d in rel.iterdir() if d.is_dir() and not d.is_symlink()]
    assert len(releases) == 5
    assert (rel / "current").resolve() in [d.resolve() for d in releases]
    estate = tmp_path / "home" / ".estate"
    assert (estate / "intents" / "a.yaml").read_text() == "name: a\nversion: 8\n"


def test_lock_held_prints_busy_and_touches_nothing(
    tmp_path: Path, origin: Path
) -> None:
    conv = tmp_path / "prefix" / "converge"
    conv.mkdir(parents=True)
    fh = open(conv / "lock", "w")
    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        result = run_converger(tmp_path, origin)
        assert result.returncode == 0
        assert result.stdout.strip() == "busy"
        assert not (tmp_path / "home" / ".estate").exists()
        assert not (tmp_path / "prefix" / "releases").exists()
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def test_link_to_a_program_main_dropped_is_removed_but_foreign_links_stay(
    tmp_path: Path, origin: Path
) -> None:
    commit(origin, "platform/estate/bin/gone", "#!/bin/sh\n", "add gone (#20)", 0o755)
    run_converger(tmp_path, origin)
    bin_dir = tmp_path / "home" / ".estate" / "bin"
    assert (bin_dir / "gone").is_symlink()
    (bin_dir / "mine").symlink_to("/usr/bin/true")

    _git(origin, ["rm", "-q", "platform/estate/bin/gone"])
    _git(origin, ["commit", "-q", "-m", "drop gone (#21)"])
    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr

    assert not (bin_dir / "gone").is_symlink()
    assert (bin_dir / "mine").is_symlink()
    assert "bin/gone (removed)" in state_of(tmp_path)["drift"]


def install_copy(tmp_path: Path, text: str) -> Path:
    sbin = tmp_path / "prefix" / "sbin"
    sbin.mkdir(parents=True, exist_ok=True)
    installed = sbin / "estate-converge"
    installed.write_text(text)
    installed.chmod(0o755)
    return installed


def test_self_update_refused_when_mains_converger_fails_its_self_test(
    tmp_path: Path, origin: Path
) -> None:
    commit(
        origin,
        "platform/estate/bin/estate-converge",
        "import sys\nsys.exit(1)\n",
        "broken converger (#30)",
        0o755,
    )
    old = CONVERGER.read_text() + "\n# installed by the pkg\n"
    installed = install_copy(tmp_path, old)

    result = run_converger(tmp_path, origin, script=installed)
    assert result.returncode == 0, result.stderr
    assert installed.read_text() == old
    info = state_of(tmp_path)["self"]
    assert info["updated"] is False
    assert info["self_test"] == 1


def test_self_update_applied_after_mains_converger_passes_its_self_test(
    tmp_path: Path, origin: Path
) -> None:
    new = CONVERGER.read_text()
    commit(origin, "platform/estate/bin/estate-converge", new, "converger (#31)", 0o755)
    installed = install_copy(tmp_path, new + "\n# older copy\n")

    result = run_converger(tmp_path, origin, script=installed)
    assert result.returncode == 0, result.stderr
    assert installed.read_text() == new
    assert os.access(str(installed), os.X_OK)
    info = state_of(tmp_path)["self"]
    assert info["updated"] is True
    assert info["self_test"] == 0


def test_a_converger_outside_sbin_never_updates_sbin(
    tmp_path: Path, origin: Path
) -> None:
    commit(
        origin,
        "platform/estate/bin/estate-converge",
        CONVERGER.read_text(),
        "converger (#32)",
        0o755,
    )
    installed = install_copy(tmp_path, "# pkg copy\n")
    result = run_converger(tmp_path, origin)
    assert result.returncode == 0, result.stderr
    assert installed.read_text() == "# pkg copy\n"
    assert state_of(tmp_path)["self"]["updated"] is False


def test_cli_self_test_and_usage(tmp_path: Path, origin: Path) -> None:
    ok = run_converger(tmp_path, origin, args=["--self-test"])
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.strip() == "self-test ok"
    assert not (tmp_path / "prefix").exists()

    bad = run_converger(tmp_path, origin, args=["--bogus"])
    assert bad.returncode == 2


def test_extract_rejects_dotdot_member(tmp_path: Path) -> None:
    loader = importlib.machinery.SourceFileLoader("estate_converge_mod", str(CONVERGER))
    mod = loader.load_module()

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        data = b"evil"
        info = tarfile.TarInfo(name="platform/estate/../../etc/passwd")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

    with pytest.raises(ValueError):
        mod.safe_extract(buf.getvalue(), tmp_path / "extracted", "platform/estate/")


def test_runs_on_the_system_python() -> None:
    system = shutil.which("python3", path="/usr/bin")
    if system is None:
        pytest.skip("no /usr/bin/python3 on this machine")
    result = subprocess.run(  # noqa: S603
        [system, str(CONVERGER), "--self-test"],
        capture_output=True,
        text=True,
        timeout=120,
        env=_bare_git_env(),
    )
    assert result.returncode == 0, result.stdout + result.stderr
