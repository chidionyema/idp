"""routed-backend-rescue: bring back the public surfaces the ingress band-aid stranded.

gateway-one-node pins the ingress path to one node. Every routed backend left on the cordoned
node is then unreachable from outside, because externalTrafficPolicy is Local and the load
balancer has stopped using that node. On 2026-09-09 that was the shop: prospector-store-web had
a replica on the serving node but prospector-store-api's only replica was on the severed one, so
mumchimp.com returned nothing at all -- three consecutive requests, 000 after twelve seconds.

Not everything fits. Thirty one workloads were stranded needing 3022m of CPU against 32m free.
So the order is a decision, and it is written in platform/ingress-recovery-order.yaml rather
than left to pod priority, which had observability/langfuse-web at infrastructure-critical and
the shop at zero with no class at all.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oke-break-glass"
ORDER = ROOT / "platform" / "ingress-recovery-order.yaml"
WORKFLOW = ROOT / ".github" / "workflows" / "oke-check.yml"


def body() -> str:
    text = SCRIPT.read_text()
    start = text.index("pb_routed_backend_rescue() {")
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    raise AssertionError("pb_routed_backend_rescue never closes")


def test_listed_and_dispatchable():
    names = subprocess.run(
        [str(SCRIPT), "--list"], capture_output=True, text=True, check=True
    ).stdout.split()
    assert "routed-backend-rescue" in names
    assert "routed-backend-rescue) pb_routed_backend_rescue ;;" in SCRIPT.read_text()
    line = [
        ln
        for ln in WORKFLOW.read_text().splitlines()
        if "options:" in ln and "cni-resync" in ln
    ]
    assert line and "routed-backend-rescue" in line[0]


def test_touches_no_host():
    """The host-surgery variant was refused by the founder on 2026-09-09; it stays refused."""
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
    """R46: the cordoned node is discovered from the cluster, never typed in."""
    import re

    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", body())
    assert "spec.unschedulable" in body(), (
        "the cordoned node must be found, not assumed"
    )


def test_the_order_is_a_file_not_a_guess():
    b = body()
    assert "ingress-recovery-order.yaml" in b
    assert 'FAILED="$FAILED guard-order"' in b, (
        "a missing order file must fail, not improvise"
    )
    assert ORDER.exists()


def test_order_puts_revenue_before_observability():
    """The whole point: the cluster's own priorities had this backwards."""
    text = ORDER.read_text()
    order_block = text.split("order:")[1].split("yield:")[0]
    entries = [
        ln.split("#")[0].strip().lstrip("- ").strip() for ln in order_block.splitlines()
    ]
    entries = [e for e in entries if "/" in e]
    assert entries[0].startswith("prospector/"), "the shop is not first"
    for obs in ("observability/langfuse-web", "observability/superset"):
        assert entries.index(obs) > entries.index("prospector/prospector-store-api")


def test_nothing_customer_facing_yields():
    """A yield must never take down a surface someone is using."""
    text = ORDER.read_text()
    order_block = text.split("order:")[1].split("yield:")[0]
    routed = {
        ln.split("#")[0].strip().lstrip("- ").strip() for ln in order_block.splitlines()
    }
    yield_block = text.split("yield:")[1]
    yields = [
        ln.split("#")[0].strip().lstrip("- ").strip() for ln in yield_block.splitlines()
    ]
    yields = [y for y in yields if "/" in y]
    assert yields, "no yield list"
    for y in yields:
        assert y not in routed, (
            f"{y} is both a surface to restore and a thing to switch off"
        )
        assert not y.startswith("prospector/"), "the shop never yields its own room"
        assert not y.startswith("identity/"), "sign-in never yields its own room"


def test_the_plan_is_computed_before_anything_is_deleted():
    """A rescue that half-runs spends the room on the wrong thing."""
    b = body()
    plan = b.index('cat "$TMP/plan.txt"')
    assert plan < b.index("delete pod"), "pods are deleted before the plan is printed"
    assert plan < b.index("scale deploy"), (
        "workloads are scaled before the plan is printed"
    )


def test_yields_happen_before_the_rescue():
    b = body()
    assert b.index("^YIELD ") < b.index("^MOVE "), (
        "the room must exist before the pod is scheduled"
    )


def test_a_yield_prints_the_way_back():
    """Reversible, and the receipt says how."""
    assert "restore with: kubectl -n $ns scale deploy/$name --replicas=" in body()


def test_a_stranded_peer_is_evicted_not_skipped():
    """Half a service is still a broken service.

    After the first rescue run mumchimp.com answered two requests in three. The API had moved,
    but one storefront replica was still on the cordoned node and still an endpoint of the
    Service, so the gateway kept sending it traffic that went nowhere. The first version skipped
    a service that had any ready backend on the good node, which left exactly that black hole in
    rotation. Removing it costs no room: the pod is not being brought back, it is being taken out
    of the endpoint list.
    """
    b = body()
    assert "EVICT" in b, "no eviction path for a stranded peer"
    assert "already has" not in b, (
        "a service with a good peer is still skipped wholesale"
    )
    assert "blackhole-endpoint" in b


def test_eviction_needs_no_room():
    """The room check must not gate an eviction, or the black hole survives a full node."""
    b = body()
    branch = b[b.index("if on_good:") : b.index("blackhole-endpoint")]
    assert "free_c" not in branch and "free_m" not in branch, (
        "eviction is gated on capacity it does not need"
    )
