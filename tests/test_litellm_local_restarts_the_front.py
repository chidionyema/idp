"""bin/litellm-local install must make the staged front.py the RUNNING front.

WHY. 2026-10-30. The front on :4000 is the estate's own client towards the cloud route
(llm.mumchimp.com), which sits behind Cloudflare. Cloudflare's browser-signature rules refuse
some client signatures with "403 error code: 1010" before the request reaches the router, so
the front now presents ONE stable estate signature of its own (platform/llm/front.py,
CLOUD_USER_AGENT). A fix in the front that is staged but never run is a fix that is not
deployed: launchd keeps the old front process alive across a stage, and `install` staged
front.py without ever restarting the front, so the change looked deployed and was not.

WHAT THIS PROVES. Two things, each with a falsifier:
  1. restart_front() really kicks the front agent (a fake launchctl records the call).
  2. `install` really calls it, and says so -- the whole install runs in a sandbox with a fake
     HOME, a fake launchctl and a fake curl, so no real router, port or agent is touched.

The falsifier is the test itself: delete the kickstart from restart_front, or the call from
install, and one of these fails.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "litellm-local"
FRONT_LABEL = "com.estate.litellm-front"


def _fake_bin(tmp_path: Path, log: Path) -> Path:
    """A PATH with a launchctl that records its arguments and a curl that always says yes.

    The fake launchctl models the NORMAL machine: the front agent is loaded, the legacy
    single-router agent and the slots are not. `install` reads that state to decide between
    its one-time legacy move and the normal path, and the normal path is the one that has to
    restart the front.
    """
    fake = tmp_path / "fakebin"
    fake.mkdir()
    launchctl = fake / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        f'printf "launchctl %s\\n" "$*" >> "{log}"\n'
        'if [ "$1" = print ]; then\n'
        f'  if [ "$2" = "gui/{os.getuid()}/{FRONT_LABEL}" ]; then exit 0; fi\n'
        "  exit 1\n"
        "fi\n"
        "exit 0\n"
    )
    launchctl.chmod(0o755)
    curl = fake / "curl"
    curl.write_text(f'#!/bin/sh\nprintf "curl %s\\n" "$*" >> "{log}"\nexit 0\n')
    curl.chmod(0o755)
    return fake


def test_restart_front_kickstarts_the_front_agent(tmp_path: Path) -> None:
    """restart_front() restarts the front agent, and says that it did."""
    log = tmp_path / "calls.log"
    fake = _fake_bin(tmp_path, log)
    out = subprocess.run(
        [
            "bash",
            "-c",
            f'export PATH="{fake}:$PATH"\nsource "{SCRIPT}"\nrestart_front\n',
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    calls = log.read_text().splitlines()
    assert any(
        c == f"launchctl kickstart -k gui/{os.getuid()}/{FRONT_LABEL}" for c in calls
    ), f"the front agent was not restarted; calls were: {calls}"
    assert "restarted the front on :4000" in out.stdout, out.stdout


def test_install_restarts_the_front_it_staged(tmp_path: Path) -> None:
    """`install` stages the front and then restarts it: the staged code is the running code.

    The whole install runs against a sandbox HOME, a fake launchctl and a fake curl, so this
    touches no real router, no real port and no real launchd agent.
    """
    log = tmp_path / "calls.log"
    fake = _fake_bin(tmp_path, log)
    home = tmp_path / "home"
    home.mkdir()
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    litellm = venv / "bin" / "litellm"
    litellm.write_text("#!/bin/sh\nexit 0\n")
    litellm.chmod(0o755)

    out = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "install",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PATH": f"{fake}:{os.environ['PATH']}",
            "HOME": str(home),
            "LITELLM_LOCAL_VENV": str(venv),
            "ESTATE_SECRETS": str(tmp_path / "no-secrets"),
            "ESTATE_ROUTER_STATE": str(home / ".estate" / "router-state"),
        },
    )
    assert out.returncode == 0, out.stdout + out.stderr
    calls = log.read_text().splitlines()
    assert any(
        c == f"launchctl kickstart -k gui/{os.getuid()}/{FRONT_LABEL}" for c in calls
    ), f"install staged the front without restarting it; calls were: {calls}"
    assert "the staged front.py is the running one" in out.stdout, out.stdout
    # The front that was staged is the one that was staged from this tree.
    staged = home / ".estate" / "litellm-local" / "front.py"
    assert staged.exists(), f"install did not stage the front: {out.stdout}"
    assert staged.read_text() == (REPO / "platform" / "llm" / "front.py").read_text()
