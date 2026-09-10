"""A toolset the door asks for is a toolset the door can actually have, so ask the gate.

`OTTO_TOOLSETS` on the gateway container names the tool families Otto is given each turn.
Some of those families are gated at load time by a check that reads only process environment.
`cronjob` is one: `tools/cronjob_tools.py:check_cronjob_requirements()` in the agent image
returns True only when one of HERMES_INTERACTIVE / HERMES_GATEWAY_SESSION / HERMES_EXEC_ASK is
truthy in the environment the process was started with. It does not know about the newer
per-session contextvar the Telegram platform binds, which is why skills and approvals already
behaved as a gateway surface on this pod and cron alone did not.

Measured in the running pod on 2026-09-10, reading the app's own environment from
`/proc/1/environ`: none of the three were set, and every single turn logged
`check_fn check_cronjob_requirements returned False; dependent tools will be unavailable this
turn`. Otto was asked for a toolset he was structurally unable to receive -- on every turn,
for as long as that container had existed.

This does not read the manifest and assert its wording. It takes the environment the manifest
actually renders for that container, starts a real process with exactly that environment and
nothing inherited, and runs the gate's own rule inside it. What is graded is the answer that
process gives -- which is the answer the agent's loader will get.
"""

import os
import subprocess
import sys

import pytest

yaml = pytest.importorskip("yaml")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEPLOY = os.path.join(ROOT, "platform", "otto-gateway", "deployment.yaml")

# The gate as the agent image writes it, lifted verbatim in shape: the three names, and
# truthiness by string. Run in a child process against the manifest's environment, so what is
# graded is the loader's real answer and not this file's opinion of it.
GATE = """
import os, sys
TRUTHY = {"1", "true", "yes", "on"}
flags = ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK")
ok = any(os.environ.get(f, "").strip().lower() in TRUTHY for f in flags)
print("cronjob_requirements", ok)
sys.exit(0 if ok else 1)
"""

# Toolset -> the gate that must answer yes for the agent to load it.
GATED_TOOLSETS = {"cronjob": GATE}


def _gateway_env():
    """Every literal-valued env var the Deployment renders on the gateway container."""
    with open(DEPLOY) as fh:
        for doc in yaml.safe_load_all(fh):
            if not doc or doc.get("kind") != "Deployment":
                continue
            for c in doc["spec"]["template"]["spec"]["containers"]:
                if c["name"] != "gateway":
                    continue
                return {
                    e["name"]: e["value"] for e in (c.get("env") or []) if "value" in e
                }
    raise AssertionError("no container named gateway in " + DEPLOY)


def test_a_gated_toolset_the_door_asks_for_is_one_the_door_can_be_given():
    env = _gateway_env()
    asked = {t.strip() for t in env.get("OTTO_TOOLSETS", "").split(",") if t.strip()}
    checked = 0
    for toolset, gate in GATED_TOOLSETS.items():
        if toolset not in asked:
            continue
        checked += 1
        # PATH only, so nothing of this machine's session leaks in and answers for the pod.
        child = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **env}
        proc = subprocess.run(
            [sys.executable, "-c", gate],
            env=child,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, (
            f"OTTO_TOOLSETS names {toolset!r}, but a process started with the environment this "
            f"Deployment renders answers {proc.stdout.strip()!r}: the agent's loader drops the "
            f"toolset and logs `check_fn returned False; dependent tools will be unavailable "
            f"this turn`, every turn. Set one of the flags the gate reads, or stop asking for "
            f"the toolset."
        )
    assert checked, "no gated toolset in OTTO_TOOLSETS; this test graded nothing"
