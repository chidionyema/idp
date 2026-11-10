"""The disk watcher is a bounded shell tick, not an agent-waking resident process."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WATCH = ROOT / "bin/idp-disk-watch"
LAUNCHER = ROOT / "launchd/ai.estate.disk-watch.plist.tmpl"


def _cleaner(tmp_path: Path, rc: int = 0) -> tuple[Path, Path, Path]:
    calls = tmp_path / "calls"
    args = tmp_path / "args"
    cleaner = tmp_path / "cleaner.sh"
    cleaner.write_text(
        "#!/bin/sh\n"
        'printf called >>"$CALLS"\n'
        'printf "%s\\n" "$@" >"$ARGS"\n'
        'printf "%s|%s|%s\\n" "$DISK_CLEANUP_PHASES" '
        '"$DISK_CLEANUP_TARGET_MB" "$DISK_CLEANUP_INCREMENTAL" >"$ENVIRONMENT"\n'
        "echo 'RESULT mode=incremental met=no'\n"
        f"exit {rc}\n"
    )
    cleaner.chmod(0o755)
    return cleaner, calls, args


def _run(
    tmp_path: Path,
    cleaner: Path,
    floor_mb: int,
    *,
    extra_env: dict[str, str] | None = None,
    path_prefix: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    heartbeat = home / ".estate/heartbeats/disk-guardian.json"
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_FLOOR_MB": str(floor_mb),
        "DISK_WATCH_CLEANER": str(cleaner),
        "DISK_WATCH_HEARTBEAT": str(heartbeat),
        "DISK_WATCH_BUDGET_S": "45",
        "CALLS": str(tmp_path / "calls"),
        "ARGS": str(tmp_path / "args"),
        "ENVIRONMENT": str(tmp_path / "environment"),
        **(extra_env or {}),
    }
    if path_prefix:
        env["PATH"] = f"{path_prefix}:{env['PATH']}"
    result = subprocess.run(
        ["/bin/sh", str(WATCH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result, heartbeat


def test_watcher_is_posix_and_contains_no_agent_or_incident_path():
    source = WATCH.read_text()
    assert source.startswith("#!/bin/sh\n")
    for forbidden in (
        "python",
        "launchctl",
        "agent-invoke",
        "incident",
        "escalat",
        "/private/tmp/claude-",
        "/private/tmp/idp-",
        "rm -rf",
    ):
        assert forbidden not in source, forbidden


def test_healthy_tick_does_not_run_the_cleaner(tmp_path):
    cleaner, calls, _ = _cleaner(tmp_path)
    result, heartbeat = _run(tmp_path, cleaner, 0)
    assert result.returncode == 0, result.stderr
    assert not calls.exists(), "a healthy tick must not delete anything"
    row = json.loads(heartbeat.read_text())
    assert row["state"] == "healthy"
    assert row["free_mb"] > 0
    assert row["at"].endswith("Z")


def test_under_floor_runs_one_bounded_allowlisted_cleaner(tmp_path):
    cleaner, calls, args = _cleaner(tmp_path)
    result, heartbeat = _run(tmp_path, cleaner, 999_999_999)
    assert result.returncode == 0, result.stderr
    assert calls.read_text() == "called"
    assert args.read_text().splitlines() == [
        "true",
        "false",
        "999999999",
        "false",
        "45",
    ]
    assert (tmp_path / "environment").read_text().strip() == "caches,temp|6000|1"
    assert json.loads(heartbeat.read_text())["state"] == "reclaiming"


@pytest.mark.parametrize("cleaner_rc", [3, 4, 5, 143])
def test_nonfatal_cleaner_outcomes_do_not_escalate(tmp_path, cleaner_rc):
    cleaner, calls, _ = _cleaner(tmp_path, cleaner_rc)
    result, _ = _run(tmp_path, cleaner, 999_999_999)
    assert result.returncode == 0
    assert calls.read_text() == "called"


def test_a_real_cleaner_failure_is_visible(tmp_path):
    cleaner, _, _ = _cleaner(tmp_path, 1)
    result, _ = _run(tmp_path, cleaner, 999_999_999)
    assert result.returncode == 1


def test_a_missing_cleaner_is_blind_not_silent(tmp_path):
    result, _ = _run(tmp_path, tmp_path / "missing", 999_999_999)
    assert result.returncode == 1
    assert "cleaner missing" in result.stdout


def test_a_blind_space_measurement_runs_no_cleaner(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "df").write_text("#!/bin/sh\nexit 1\n")
    (bin_dir / "df").chmod(0o755)
    cleaner, calls, _ = _cleaner(tmp_path)
    result, _ = _run(tmp_path, cleaner, 0, path_prefix=bin_dir)
    assert result.returncode == 0
    assert "BLIND" in result.stdout
    assert not calls.exists()


def test_launchd_is_a_sixty_second_tick_without_python_or_keepalive():
    template = LAUNCHER.read_text()
    parsed = plistlib.loads(template.encode())
    assert parsed["Label"] == "ai.estate.disk-watch"
    assert parsed["StartInterval"] == 60
    assert "KeepAlive" not in parsed
    assert parsed["ProgramArguments"][0] == "/bin/sh"
    assert parsed["ProgramArguments"][1].endswith("/.estate/bin/idp-disk-watch")
    assert "python" not in template.lower()
