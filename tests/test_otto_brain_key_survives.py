"""The door must still hold the brain's key after every other mount has loaded.

The gateway container derives the loopback brain's master key from the router
key, and then loads every file under HERMES_ENV_DIR as an environment variable.
That mount carries a file called LITELLM_API_KEY too -- the ESTATE router's old
virtual key -- and it used to land last and win. The brain runs with no
database, so a key that is not its master key cannot be looked up at all: it
answered `400 No connected db.`, the router counted its two attempts and
returned needs_human. One real founder turn died that way on 2026-09-10
15:06:09Z (task 01M25XNN0ZXTPG95B32FAF41VB).

This test does not read the comment that says so. It cuts the two shell
fragments out of the manifest, runs them against a fake mount that carries the
conflict, and grades the value the app would actually have been handed.
"""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess

import pytest

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
DEPLOYMENT = REPO / "platform" / "otto-gateway" / "deployment.yaml"

ROUTER_KEY = "sk-estate-router-virtual-key-for-the-test"
AGENT_ENV_KEY = "sk-a-different-key-the-agent-env-mount-carries"


def _gateway_script() -> str:
    for doc in yaml.safe_load_all(DEPLOYMENT.read_text()):
        if not doc or doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            if container["name"] == "gateway":
                return "\n".join(container["args"])
    raise AssertionError("no gateway container in " + str(DEPLOYMENT))


def _fragment(script: str, first: str, last: str) -> str:
    """The lines from the one starting with ``first`` to the one that IS ``last``.

    Both boundaries are matched on the stripped line, never as a substring: a
    prose comment inside the block contains "fi" and would end it early.
    """
    lines = script.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith(first))
    end = next(i for i, l in enumerate(lines) if i >= start and l.strip() == last)
    return "\n".join(lines[start : end + 1])


def _run(tmp_path: pathlib.Path) -> str:
    """Run the door's own key handling and report the key the app would get."""
    script = _gateway_script()

    router_dir = tmp_path / "otto-gateway-router"
    router_dir.mkdir()
    (router_dir / "LITELLM_API_KEY").write_text(ROUTER_KEY)

    env_dir = tmp_path / "hermes-agent-env"
    env_dir.mkdir()
    (env_dir / "LITELLM_API_KEY").write_text(AGENT_ENV_KEY)
    (env_dir / "EXA_API_KEY").write_text("sk-exa-must-still-load")

    derive = _fragment(script, "OTTO_ROUTER_KEY=$(cat", "export LITELLM_API_KEY")
    derive = derive.replace("/run/secrets/otto-gateway-router", str(router_dir))
    load = _fragment(script, 'if [ -d "$HERMES_ENV_DIR" ]', "fi")

    program = "\n".join(
        [
            "set -eu",
            f'HERMES_ENV_DIR="{env_dir}"',
            derive,
            load,
            'printf "%s\\n%s\\n" "$LITELLM_API_KEY" "${EXA_API_KEY:-MISSING}"',
        ]
    )
    out = subprocess.run(
        ["/bin/sh", "-c", program], capture_output=True, text=True, check=True
    )
    return out.stdout


@pytest.mark.skipif(
    shutil.which("sha256sum") is None,
    reason="the door derives the brain key with sha256sum; grade it where that exists",
)
def test_the_agent_env_mount_does_not_overwrite_the_brain_key(tmp_path):
    derived = "sk-" + hashlib.sha256(ROUTER_KEY.encode()).hexdigest()[:40]
    key, exa = _run(tmp_path).splitlines()[:2]

    assert key == derived, (
        "the door handed the brain a key it cannot validate; "
        "the brain has no database, so this is 400 No connected db. "
        "on every lane and needs_human on every turn"
    )
    assert key != AGENT_ENV_KEY
    # The skip is one name wide: everything else on that mount still loads.
    assert exa == "sk-exa-must-still-load"
