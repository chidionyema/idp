"""gateway-one-node: the band-aid that keeps the ingress path off the severed cross-node link.

It must stay a plain kubectl playbook. The host-level variant was refused by the founder on
2026-09-09 ("agents should never dynamically manipulate host operating systems during an active
fire"), so these grade both what it does and what it must never do.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oke-break-glass"
WORKFLOW = ROOT / ".github" / "workflows" / "oke-check.yml"


def body() -> str:
    text = SCRIPT.read_text()
    start = text.index("pb_gateway_one_node() {")
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    raise AssertionError("pb_gateway_one_node never closes")


def test_listed_and_dispatchable():
    names = subprocess.run(
        [str(SCRIPT), "--list"], capture_output=True, text=True, check=True
    ).stdout.split()
    assert "gateway-one-node" in names
    assert "gateway-one-node) pb_gateway_one_node ;;" in SCRIPT.read_text()
    line = [
        ln
        for ln in WORKFLOW.read_text().splitlines()
        if "options:" in ln and "cni-resync" in ln
    ]
    assert line and "gateway-one-node" in line[0]


def test_touches_no_host():
    b = body()
    for forbidden in (
        "privileged",
        "hostNetwork",
        "hostPID",
        "nsenter",
        "ip link",
        "ip route",
        "iptables",
    ):
        assert forbidden not in b, f"{forbidden} has no place in this playbook"


def test_names_no_node_literal():
    b = body()
    import re

    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", b), (
        "the node is derived, never typed (R46)"
    )


def test_guards_before_cordon():
    b = body()
    cordon = b.index("step cordon")
    for guard in ("guard-backend", "guard-nodes", "guard-etp"):
        assert b.index(guard) < cordon, (
            f"{guard} must be graded before the node is cordoned"
        )


def test_traffic_policy_guard_is_fail_closed():
    b = body()
    seg = b[b.index("guard-etp") - 400 : b.index("guard-etp") + 200]
    assert "externalTrafficPolicy" in seg
    assert "FAILED=" in seg, "a Service that is not Local must fail, never proceed"


def test_dns_moves_one_pod_at_a_time():
    b = body()
    dns = b[b.index("dns-move-") : b.index("gateway-settle")]
    assert "rollout status deploy/coredns" in dns, (
        "each DNS pod waits for the deployment before the next"
    )


def test_does_not_uncordon():
    b = body()
    assert "uncordon" not in b.replace("node-uncordon", ""), (
        "uncordoning re-schedules the gateway onto the severed node and restores the outage"
    )
