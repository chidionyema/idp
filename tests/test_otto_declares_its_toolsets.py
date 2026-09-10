"""Every toolset the door asks for must be one the door can actually have.

`OTTO_TOOLSETS` is the estate's list of what Otto may use. The fork gates some
of those toolsets behind a surface check, and one of them -- cronjob -- reads
only the three legacy process-env flags (`tools/cronjob_tools.py`). The door
never set any of them, so it asked for cronjob and was refused on every turn:

    check_fn check_cronjob_requirements returned False;
    dependent tools will be unavailable this turn

Measured in the live pod 2026-09-10: none of HERMES_INTERACTIVE,
HERMES_GATEWAY_SESSION or HERMES_EXEC_ASK were set, while OTTO_TOOLSETS named
cronjob. This test grades the manifest's own two declarations against each
other, so the pair can never drift apart again.
"""

from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
DEPLOYMENT = REPO / "platform" / "otto-gateway" / "deployment.yaml"

TRUTHY = {"1", "true", "yes", "on"}

# The toolsets the fork gates behind the gateway-surface flags, and the flags
# any one of which satisfies the gate.
GATED_TOOLSETS = {
    "cronjob": ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK"),
}


def _gateway_env() -> dict[str, str]:
    for doc in yaml.safe_load_all(DEPLOYMENT.read_text()):
        if not doc or doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            if container["name"] == "gateway":
                return {e["name"]: str(e.get("value", "")) for e in container["env"]}
    raise AssertionError("no gateway container in " + str(DEPLOYMENT))


def test_a_gated_toolset_the_door_asks_for_is_a_toolset_the_door_may_have():
    env = _gateway_env()
    asked = {t.strip() for t in env.get("OTTO_TOOLSETS", "").split(",") if t.strip()}

    for toolset, flags in GATED_TOOLSETS.items():
        if toolset not in asked:
            continue
        satisfied = [f for f in flags if env.get(f, "").strip().lower() in TRUTHY]
        assert satisfied, (
            f"OTTO_TOOLSETS asks for '{toolset}' but the door sets none of "
            f"{list(flags)}, so the fork refuses it on every turn and Otto "
            f"answers without it"
        )
