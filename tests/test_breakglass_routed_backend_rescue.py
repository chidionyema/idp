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

import re
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


def sections():
    """The three lists in platform/ingress-recovery-order.yaml, parsed the way the playbook parses
    them: comments stripped, `- ns/name` rows only. Grepping the file text grades its prose."""
    out, cur = {"order": [], "yield": [], "internal": []}, None
    for line in (
        (ROOT / "platform" / "ingress-recovery-order.yaml").read_text().splitlines()
    ):
        head = line.split("#")[0].rstrip()
        if re.match(r"^(order|yield|internal):\s*$", head):
            cur = out[head[:-1]]
            continue
        m = re.match(r"^\s*-\s*(\S+/\S+)\s*$", head)
        if m and cur is not None:
            cur.append(m.group(1))
    return out


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
    # 2026-09-09: these were ranked below the shop and still took its room, so they left the
    # recovery order altogether and became sheddable. What we watch the estate with yields to
    # what the estate is for.
    s = sections()
    assert s["order"][0] == "prospector/prospector-store-api"
    for dashboard in (
        "observability/superset",
        "observability/langfuse-web",
        "observability/signoz",
    ):
        assert dashboard not in s["order"], (
            f"{dashboard} is what we watch with, not what pays"
        )
    assert "observability/superset" in s["yield"]
    assert "observability/langfuse-web" in s["yield"]


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
    assert "restore with: kubectl -n $ns scale $kind/$name --replicas=" in body()
    assert "kind=deploy" in body(), (
        "observability/signoz is a StatefulSet; scale deploy would miss it"
    )


def test_a_stranded_peer_is_evicted_not_skipped():
    # A stranded pod is still an endpoint, so the gateway keeps sending it traffic that goes
    # nowhere. mumchimp.com came back at two requests in three for exactly this: one storefront
    # replica served, the other was a black hole.
    src = body()
    branch = src[src.index("if on_good:") : src.index("blackhole-endpoint")]
    assert "EVICT" in branch
    assert "free_c" not in branch and "free_m" not in branch, (
        "taking a pod out of rotation needs no room; it is not being brought back"
    )


def test_eviction_needs_no_room():
    """The room check must not gate an eviction, or the black hole survives a full node."""
    b = body()
    branch = b[b.index("if on_good:") : b.index("blackhole-endpoint")]
    assert "free_c" not in branch and "free_m" not in branch, (
        "eviction is gated on capacity it does not need"
    )


# --- 2026-09-09, the second time the shop went dark -------------------------------------------
# The storefront API was preempted by hermes-agent-gateway (infrastructure-critical, 1088Mi) and
# its replacement sat Pending on no node at all. The rescue walked past it: every question it
# asked was "what is stranded on the cordoned node", and this pod was stranded on nothing.


def _plan_source():
    b = body()
    return b[b.index("PYPLAN") : b.rindex("PYPLAN")]


def test_a_pending_pod_on_no_node_is_rescued_by_making_room():
    src = _plan_source()
    assert 'not p["spec"].get("nodeName")' in src, (
        "a Pending pod belongs to no node; the plan must look for that"
    )
    assert "ROOM " in src, "making room is its own directive: nothing needs moving"


def test_room_is_an_action_the_executor_counts():
    # the guard that decides whether the playbook does anything at all
    assert "^(YIELD|MOVE|EVICT|ROOM) " in body(), (
        "a plan of only ROOM lines must not be read as an empty plan"
    )


def test_rank_is_never_read_as_a_sacrifice_list():
    # Run against the live cluster, the rank-based version proposed scaling prospector-store-web
    # to zero to seat prospector-store-api, and external-secrets to zero for a Langfuse dashboard.
    src = _plan_source()
    fn = src[
        src.index("def yield_sources") : src.index("def owned_by")
        if "def owned_by" in src
        and src.index("def owned_by") > src.index("def yield_sources")
        else len(src)
    ]
    fn = src[src.index("def yield_sources") :].split("\ndef ")[0]
    assert "return list(yields)" in fn
    body_lines = [
        l for l in fn.splitlines() if l.strip() and not l.strip().startswith("#")
    ]
    assert not any("order" in l for l in body_lines), (
        "room may only come from the declared yield list, never from the recovery rank"
    )


def test_a_workload_is_not_matched_by_bare_prefix():
    # `external-secrets` prefixes `external-secrets-cert-controller` and `external-secrets-webhook`
    src = _plan_source()
    assert "def owned_by" in src
    ns = {}
    exec(src[src.index("def owned_by") :].split("\ndef yield_sources")[0], ns)
    owned = ns["owned_by"]
    pod = lambda n: {"metadata": {"namespace": "external-secrets", "name": n}}
    assert owned(
        pod("external-secrets-74866d8fb8-nxd88"), "external-secrets", "external-secrets"
    )
    assert not owned(
        pod("external-secrets-webhook-656ffd67c9-kfhns"),
        "external-secrets",
        "external-secrets",
    )
    assert not owned(
        pod("external-secrets-cert-controller-84498f9656-v44ts"),
        "external-secrets",
        "external-secrets",
    )
    assert owned(
        pod("external-secrets-webhook-656ffd67c9-kfhns"),
        "external-secrets",
        "external-secrets-webhook",
    )
    assert owned(pod("signoz-0"), "external-secrets", "signoz"), (
        "a StatefulSet ordinal is generated too"
    )


def test_internal_controllers_are_a_list_of_their_own():
    # external-secrets sat on the cordoned node while the server it calls for every value sat on
    # the serving one: every secret in the estate stopped resolving, with nothing on any hostname
    # to show for it. No HTTPRoute names it, so the Service-driven order could never see it.
    assert "internal" in body()
    assert "external-secrets/external-secrets" in sections()["internal"]


def test_clickhouse_is_never_yielded():
    # owned by a ClickHouseInstallation; scaling its StatefulSet is undone by the operator
    assert not [y for y in sections()["yield"] if "clickhouse" in y.lower()]


def test_the_rescue_says_which_surface_came_back():
    assert "seated-" in body(), (
        "a rescue that does not name the surface it restored is a receipt for nothing"
    )
