"""IDP-Estate.pkg installs the root converger and nothing else; its postinstall refuses a
converger that fails its self-test and survives launchd's slow bootout.

docs/tickets/2026-09-27-merged-is-operating.md. The postinstall tests run anywhere (fake
launchctl, tmp prefix). The pkg tests build the real pkg and need pkgbuild, so they run on macOS
only; ubuntu CI skips them.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess  # noqa: S404 -- fixed argv, no shell
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INSTALLER = REPO / "installer"
CONVERGE = REPO / "platform/estate/bin/estate-converge"
LABEL = "ai.estate.converge"

FAKE_LAUNCHCTL = """#!/bin/sh
echo "$*" >> "{log}"
if [ "$1" = bootstrap ]; then
    n=$(cat "{fails}" 2>/dev/null || echo 0)
    if [ "$n" -gt 0 ]; then
        echo $((n - 1)) > "{fails}"
        echo "Bootstrap failed: 5: Input/output error" >&2
        exit 5
    fi
    touch "{loaded}"
fi
if [ "$1" = print ]; then
    [ -f "{loaded}" ]
fi
"""


def postinstall(tmp_path: Path, converger: Path, bootstrap_fails: int = 0):
    prefix = tmp_path / "prefix"
    (prefix / "sbin").mkdir(parents=True)
    shutil.copyfile(converger, prefix / "sbin" / "estate-converge")
    daemons = tmp_path / "daemons"
    daemons.mkdir()
    shutil.copyfile(INSTALLER / f"{LABEL}.plist", daemons / f"{LABEL}.plist")
    log, fails, loaded = tmp_path / "calls", tmp_path / "fails", tmp_path / "loaded"
    fails.write_text(str(bootstrap_fails))
    launchctl = tmp_path / "launchctl"
    launchctl.write_text(FAKE_LAUNCHCTL.format(log=log, fails=fails, loaded=loaded))
    launchctl.chmod(0o755)
    env = dict(os.environ)
    env.update(
        ESTATE_PREFIX=str(prefix), ESTATE_DAEMONS=str(daemons), LAUNCHCTL=str(launchctl)
    )
    r = subprocess.run(  # noqa: S603
        ["/bin/sh", str(INSTALLER / "postinstall")],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    calls = log.read_text().splitlines() if log.exists() else []
    return r, calls, prefix, daemons


def test_postinstall_loads_the_converger_in_the_system_domain(tmp_path: Path) -> None:
    r, calls, prefix, daemons = postinstall(tmp_path, CONVERGE)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "self-test ok" in r.stdout
    assert calls == [
        f"bootout system/{LABEL}",
        f"bootstrap system {daemons}/{LABEL}.plist",
        f"print system/{LABEL}",
    ]
    assert (prefix / "converge").is_dir()
    assert (prefix / "logs").is_dir()


def test_postinstall_refuses_a_converger_that_fails_its_self_test(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "broken"
    broken.write_text("import sys\nprint('self-test FAILED')\nsys.exit(1)\n")
    r, calls, _, _ = postinstall(tmp_path, broken)
    assert r.returncode == 1
    assert "failed its self-test" in r.stderr
    assert not any(c.startswith("bootstrap") for c in calls)


def test_postinstall_retries_while_launchd_still_holds_the_old_label(
    tmp_path: Path,
) -> None:
    r, calls, _, _ = postinstall(tmp_path, CONVERGE, bootstrap_fails=2)
    assert r.returncode == 0, r.stdout + r.stderr
    assert sum(c.startswith("bootstrap") for c in calls) == 3


def test_postinstall_fails_when_launchd_never_takes_the_label(tmp_path: Path) -> None:
    r, calls, _, _ = postinstall(tmp_path, CONVERGE, bootstrap_fails=99)
    assert r.returncode == 1
    assert sum(c.startswith("bootstrap") for c in calls) == 10
    assert "launchd does not have" in r.stderr


def test_postinstall_removes_only_an_empty_leftover_0_1_0(tmp_path: Path) -> None:
    (tmp_path / "prefix" / "0.1.0").mkdir(parents=True)
    r, _, prefix, _ = postinstall(tmp_path, CONVERGE)
    assert r.returncode == 0, r.stderr
    assert not (prefix / "0.1.0").exists()

    other = tmp_path / "again"
    other.mkdir()
    (other / "prefix" / "0.1.0").mkdir(parents=True)
    (other / "prefix" / "0.1.0" / "keep").write_text("x")
    r, _, prefix, _ = postinstall(other, CONVERGE)
    assert r.returncode == 0, r.stderr
    assert (prefix / "0.1.0" / "keep").exists()


def test_daemon_runs_the_installed_converger_on_the_system_python() -> None:
    plist = plistlib.loads((INSTALLER / f"{LABEL}.plist").read_bytes())
    assert plist["Label"] == LABEL
    assert plist["ProgramArguments"] == [
        "/usr/bin/python3",
        "/usr/local/estate/sbin/estate-converge",
    ]
    assert plist["RunAtLoad"] is True
    assert plist["StartInterval"] == 120
    assert plist["StandardOutPath"].startswith("/usr/local/estate/logs/")
    # The converger self-updates only when it is the copy in <prefix>/sbin.
    assert '"/usr/local/estate"' in CONVERGE.read_text()


def test_preinstall_passes_on_a_mac_with_command_line_tools() -> None:
    r = subprocess.run(  # noqa: S603
        ["/bin/sh", str(INSTALLER / "preinstall")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr


needs_pkgbuild = pytest.mark.skipif(
    shutil.which("pkgbuild") is None, reason="pkgbuild ships with macOS only"
)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("pkg") / "IDP-Estate.pkg"
    r = subprocess.run(  # noqa: S603
        ["/bin/sh", str(INSTALLER / "build.sh")],
        env={**os.environ, "OUT": str(out)},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    expanded = out.parent / "x"
    subprocess.run(["pkgutil", "--expand", str(out), str(expanded)], check=True)  # noqa: S603,S607
    return expanded


@needs_pkgbuild
def test_payload_is_the_converger_and_its_daemon_owned_by_root(built: Path) -> None:
    bom = subprocess.run(  # noqa: S603
        ["lsbom", str(built / "idp-estate.pkg" / "Bom")],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rows = {line.split("\t")[0]: line.split("\t")[1:3] for line in bom.splitlines()}
    assert rows == {
        ".": ["40755", "0/0"],
        "./Library": ["40755", "0/0"],
        "./Library/LaunchDaemons": ["40755", "0/0"],
        f"./Library/LaunchDaemons/{LABEL}.plist": ["100644", "0/0"],
        "./usr": ["40755", "0/0"],
        "./usr/local": ["40755", "0/0"],
        "./usr/local/estate": ["40755", "0/0"],
        "./usr/local/estate/sbin": ["40755", "0/0"],
        "./usr/local/estate/sbin/estate-converge": ["100755", "0/0"],
    }
    scripts = built / "idp-estate.pkg" / "Scripts"
    for name in ("preinstall", "postinstall"):
        assert (scripts / name).read_bytes() == (INSTALLER / name).read_bytes()


@needs_pkgbuild
def test_installer_accepts_the_pkg_and_asks_for_the_password(built: Path) -> None:
    pkg = built.parent / "IDP-Estate.pkg"
    info = subprocess.run(  # noqa: S603
        ["installer", "-pkginfo", "-verbose", "-pkg", str(pkg)],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "Must Authenticate : YES" in info
    choices = subprocess.run(  # noqa: S603
        ["installer", "-showChoicesXML", "-pkg", str(pkg), "-target", "/"],  # noqa: S607
        capture_output=True,
        text=True,
    )
    assert "Error" not in choices.stdout + choices.stderr
