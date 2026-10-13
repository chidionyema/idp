"""Binds features/gates/launchd-off-documents.feature. Steps run bin/idp-install-launchd for real
against a scratch HOME, with launchctl stubbed on PATH so nothing is loaded on this machine."""

from __future__ import annotations

import os
import plistlib
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/launchd-off-documents.feature")

IDP = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.skipif(
    not (shutil.which("plutil") and shutil.which("envsubst")),
    reason="the installer renders with envsubst and lints with plutil (macOS)",
)


def _tree(root: Path) -> Path:
    (root / "launchd").mkdir(parents=True)
    for t in (IDP / "launchd").glob("*.plist.tmpl"):
        shutil.copy(t, root / "launchd" / t.name)
    return root


@pytest.fixture
def state(tmp_path: Path) -> dict:
    # tmp_path sits under /var/folders, which the installer refuses as a temporary checkout, so
    # the scratch home is what the jobs see as $HOME and the trees live inside it.
    home = tmp_path / "home"
    stub = tmp_path / "stub"
    stub.mkdir()
    launchctl = stub / "launchctl"
    launchctl.write_text(f'#!/bin/sh\necho "$@" >> {tmp_path}/launchctl.calls\n')
    launchctl.chmod(launchctl.stat().st_mode | stat.S_IXUSR)
    return {"home": home, "stub": stub, "calls": tmp_path / "launchctl.calls"}


def _install(state: dict, *labels: str, idp_root: Path | None = None) -> None:
    # A Documents entry on the caller's PATH must not reach the job (launchd cannot read it).
    path = (
        f"{state['stub']}:{state['home']}/Documents/code/idp/bin:{os.environ['PATH']}"
    )
    env = {**os.environ, "HOME": str(state["home"]), "PATH": path}
    env.pop("IDP_ROOT", None)
    if idp_root:
        env["IDP_ROOT"] = str(idp_root)
    state["run"] = subprocess.run(
        ["bash", str(IDP / "bin" / "idp-install-launchd"), *labels],
        env=env,
        capture_output=True,
        text=True,
    )


def _agents(state: dict) -> list[Path]:
    d = state["home"] / "Library" / "LaunchAgents"
    return sorted(d.glob("*.plist")) if d.exists() else []


@given("a home with a runtime tree at .estate/runtime/idp")
def _runtime(state: dict) -> None:
    state["runtime"] = _tree(state["home"] / ".estate" / "runtime" / "idp")


@given("a home with no runtime tree and a checkout under Documents")
def _documents(state: dict) -> None:
    state["checkout"] = _tree(state["home"] / "Documents" / "code" / "idp")


@when("bin/idp-install-launchd installs cockpit")
def _cockpit(state: dict) -> None:
    _install(state, "cockpit")


@when("bin/idp-install-launchd installs cockpit from that checkout")
def _cockpit_documents(state: dict) -> None:
    _install(state, "cockpit", idp_root=state["checkout"])


@when("bin/idp-install-launchd installs idp, scheduler and sovereign-worker")
def _cluster_owned(state: dict) -> None:
    _install(state, "idp", "scheduler", "sovereign-worker")


@then("the rendered plist runs from the runtime tree, not the checkout")
def _points_at_runtime(state: dict) -> None:
    assert state["run"].returncode == 0, state["run"].stdout + state["run"].stderr
    (plist,) = _agents(state)
    job = plistlib.loads(plist.read_bytes())
    runtime = str(state["runtime"])
    assert job["ProgramArguments"][0].startswith(runtime + "/"), job["ProgramArguments"]
    assert job["WorkingDirectory"] == runtime
    assert str(IDP) not in plist.read_text()
    assert f"{state['home']}/Documents" not in job["EnvironmentVariables"]["PATH"]
    assert "bootstrap" in state["calls"].read_text()


@then("its log directory exists before launchd opens it")
def _log_dir(state: dict) -> None:
    (plist,) = _agents(state)
    log = Path(plistlib.loads(plist.read_bytes())["StandardErrorPath"])
    assert log.parent.is_dir(), log


@then("it exits 2 and names macOS TCC")
def _refused(state: dict) -> None:
    assert state["run"].returncode == 2, state["run"].stdout + state["run"].stderr
    assert "macOS TCC" in state["run"].stdout


@then("each is skipped because it runs on the cluster")
def _skipped(state: dict) -> None:
    assert state["run"].returncode == 0, state["run"].stdout + state["run"].stderr
    for label in ("idp", "scheduler", "sovereign-worker"):
        assert f"skipped ai.estate.{label}: runs on the cluster" in state["run"].stdout


@then("nothing is written to Library/LaunchAgents")
def _nothing(state: dict) -> None:
    assert _agents(state) == []
    assert not state["calls"].exists()
