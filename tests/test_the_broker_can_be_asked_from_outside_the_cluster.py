"""The asking door, and the three places that have to agree about it.

WJ.2 says an agent that hits a wall does not fail and does not report back: it asks. On
2026-09-07 one could not. The CNI cutover left 97 pods still wired by flannel and needing a
restart, `restart-workload` in platform/jit/grants.yaml is exactly that grant, and there was
no address to request it at -- platform/jit/fence.yaml admitted namespaces `agents` and
`edge`, and the public route carries the Telegram webhook alone (`POST
https://otto.${ESTATE_ZONE}/ask` answered 404, measured that day).

Two doors were added for it. The tailnet's is the founder's own devices, and it only exists if four files agree: the Service
asks the operator for a device under one tag, the ACL names that same tag and port, the two
namespace fences declare the hop in both directions, and the client knows the hostname to look
the device up by. Any one of them drifting leaves a door that looks configured and refuses
every request, which is the failure this file is here to catch.

The second is the public one, and it exists because the tailnet's does not answer a runner in
somebody's cloud -- which is most of the agents WJ.2 is written for, and the reason the ledger
was still empty. It is a path prefix on the hostname the estate already serves, because the
Gateway lives in another repository and a hostname of its own would be a cross-repo change plus
a certificate; the broker strips the prefix back off. Three files have to agree on that prefix
and the tests below grade all three, because a prefix that agreed in two places out of three is
a door that answers 404 while every file that names it looks right.

Reaching either door is not being granted anything, and the ACL test pins the part that must
not drift: the tailnet admits the founder's devices and no one else. What keeps the public door
from being a wider hole than the tailnet one is not the route -- it is that every path the
route carries refuses a caller without the estate's agent key, which
tests/test_the_jit_broker_cannot_be_talked_into_standing_access.py grades over a real socket.
"""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE = ROOT / "platform" / "jit" / "deployment.yaml"
FENCE = ROOT / "platform" / "jit" / "fence.yaml"
POLICY = ROOT / "platform" / "tailscale" / "policy.hujson"
ALLOWANCES = ROOT / "platform" / "ns-fences" / "allowances.yaml"
PUBLIC_DOOR = ROOT / "platform" / "jit" / "public-door.yaml"
KUSTOMIZATION = ROOT / "platform" / "jit" / "kustomization.yaml"


def _docs(path: pathlib.Path) -> list[dict]:
    with path.open() as fh:
        return [d for d in yaml.safe_load_all(fh) if d]


def _broker_service() -> dict:
    for doc in _docs(SERVICE):
        if doc.get("kind") == "Service" and doc["metadata"]["name"] == "jit-broker":
            return doc
    raise AssertionError(f"no jit-broker Service in {SERVICE}")


def _policy() -> dict:
    """The ACL file, which is HuJSON: JSON plus comments and trailing commas.

    Parsed rather than grepped, because every assertion below is about structure -- which tag
    owns what, which source reaches which port -- and a substring match would pass just as
    happily on a rule that sits inside a comment.
    """
    text = POLICY.read_text()
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def _client():
    spec = importlib.util.spec_from_loader(
        "idp_jit",
        importlib.machinery.SourceFileLoader("idp_jit", str(ROOT / "bin" / "idp-jit")),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_service_asks_for_a_tailnet_device_under_its_own_tag():
    ann = _broker_service()["metadata"].get("annotations") or {}
    assert ann.get("tailscale.com/expose") == "true", ann
    assert ann.get("tailscale.com/hostname"), ann
    tag = ann.get("tailscale.com/tags")
    assert tag and tag != "tag:k8s", (
        "tag:k8s is the operator's default and every egress proxy carries it, so an ACL "
        f"naming it would open this port on all of them: {ann}"
    )


def test_the_tag_the_service_asks_for_is_one_the_tailnet_will_mint():
    """An unowned tag does not fail loudly: the authkey mint 400s and the proxy crashloops
    (P0 idp#586). Owning it by tag:k8s is what the two tags before it needed, because the root
    OAuth client carries tag:k8s and may only request tags its own tags own (kb/1215)."""
    tag = _broker_service()["metadata"]["annotations"]["tailscale.com/tags"]
    owners = _policy()["tagOwners"]
    assert tag in owners, f"{tag} is not in tagOwners: {sorted(owners)}"
    assert owners[tag] == ["tag:k8s"], owners[tag]


def test_the_acl_opens_the_port_the_broker_actually_serves():
    tag = _broker_service()["metadata"]["annotations"]["tailscale.com/tags"]
    port = _broker_service()["spec"]["ports"][0]["port"]
    dsts = {d for rule in _policy()["acls"] for d in rule["dst"]}
    assert f"{tag}:{port}" in dsts, dsts


def test_the_acl_names_the_tagged_mac_and_not_only_the_founders_login():
    """The agents run on the founder's Mac and that Mac is tagged. A tagged device has no user
    identity (kb/1068), so a rule written against `group:founder` alone matches his phone and
    never matches the machine the asking is done from -- the door would be open and unreachable
    from the one place that needs it."""
    tag = _broker_service()["metadata"]["annotations"]["tailscale.com/tags"]
    port = _broker_service()["spec"]["ports"][0]["port"]
    srcs = {
        s
        for rule in _policy()["acls"]
        if f"{tag}:{port}" in rule["dst"]
        for s in rule["src"]
    }
    assert "tag:founder-mac" in srcs, srcs
    assert srcs <= {"tag:founder-mac", "group:founder"}, (
        f"the asking door reaches the founder's own devices and nothing else: {srcs}"
    )


def test_both_namespace_fences_declare_the_hop_the_proxy_makes():
    """The operator's ingress proxy runs in `tailscale` and dials `jit`. A NetworkPolicy is
    one-directional, so a hop declared on one side only is refused at the other end -- the
    defect already recorded against otto-gateway in allowances.yaml."""
    admitted = {
        ns["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"]
        for doc in _docs(FENCE)
        if doc.get("kind") == "NetworkPolicy"
        for rule in doc["spec"].get("ingress") or []
        for ns in rule.get("from") or []
        if "namespaceSelector" in ns
    }
    assert "tailscale" in admitted, admitted

    with ALLOWANCES.open() as fh:
        allow = yaml.safe_load(fh)
    ts = allow["flows"]["tailscale"]
    assert "jit" in (ts.get("egress") or []), ts


def test_the_client_looks_the_tailnet_address_up_instead_of_carrying_it(monkeypatch):
    """The tailnet's domain differs per estate, so a literal in the client would be the machine
    fact LAW 46 keeps out of files. It comes from the local daemon, and the hostname it matches
    on is the one the Service asked for."""
    mod = _client()
    monkeypatch.delenv("JIT_BROKER_URL", raising=False)
    host = _broker_service()["metadata"]["annotations"]["tailscale.com/hostname"]
    monkeypatch.setattr(mod.shutil, "which", lambda _: "/usr/bin/tailscale")

    class Done:
        stdout = json.dumps(
            {
                "Peer": {
                    "k1": {"DNSName": "some-other-box.tail0000.ts.net."},
                    "k2": {"DNSName": f"{host}.tail0000.ts.net."},
                }
            }
        )

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: Done())
    doors = mod._doors()
    # In front of the public one: a pod that can reach the tailnet proxy is inside the estate
    # already, and that hop costs nothing and leaves the cluster's own network. Ordering it
    # after the public door would send every in-estate ask out to the internet and back.
    assert doors[0] == mod.IN_CLUSTER, doors
    assert f"http://{host}.tail0000.ts.net:8080" in doors, doors
    assert doors.index(f"http://{host}.tail0000.ts.net:8080") < doors.index(
        mod._public_door()
    ), doors


def test_a_laptop_with_no_tailnet_still_gets_an_answer_rather_than_a_crash(monkeypatch):
    """No tailnet is not no door: the public one is what an agent on somebody else's runner
    has, and it is the whole reason WJ.2's ledger was empty."""
    mod = _client()
    monkeypatch.delenv("JIT_BROKER_URL", raising=False)
    monkeypatch.setattr(mod.shutil, "which", lambda _: None)
    assert mod._doors() == [mod.IN_CLUSTER, mod._public_door()]


def test_a_client_that_cannot_find_the_zone_still_dials_the_doors_it_has(monkeypatch):
    """An agent on a runner with no checkout and no ESTATE_ZONE in its environment gets no
    public door. That is a thinner client, not a crashing one -- and the estate's own zone is
    the one thing LAW 46 forbids this file to carry as a literal, so guessing is not an option.
    """
    mod = _client()
    monkeypatch.delenv("JIT_BROKER_URL", raising=False)
    monkeypatch.setenv("ESTATE_ZONE", "")
    monkeypatch.setenv("IDP_ROOT", "/nonexistent-checkout")
    monkeypatch.setattr(mod.shutil, "which", lambda _: None)
    assert mod._public_door() is None
    assert mod._doors() == [mod.IN_CLUSTER]


def test_a_caller_that_named_a_broker_gets_that_one_and_no_other(monkeypatch):
    """Falling through to a second broker because the named one refused would answer a
    different question than the caller asked."""
    mod = _client()
    monkeypatch.setenv("JIT_BROKER_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(mod.shutil, "which", lambda _: "/usr/bin/tailscale")
    assert mod._doors() == ["http://127.0.0.1:9"]


# --- the public door -------------------------------------------------------------------


def _route() -> dict:
    for doc in _docs(PUBLIC_DOOR):
        if doc.get("kind") == "HTTPRoute":
            return doc
    raise AssertionError(f"no HTTPRoute in {PUBLIC_DOOR}")


def _prefix_in_deployment() -> str:
    for doc in _docs(SERVICE):
        if doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            for env in container.get("env") or []:
                if env.get("name") == "JIT_PUBLIC_PREFIX":
                    return env["value"]
    raise AssertionError(f"no JIT_PUBLIC_PREFIX in {SERVICE}")


def test_the_three_files_agree_on_the_prefix():
    """The client dials it, the route matches on it, the broker strips it. Two out of three
    agreeing is a door that answers 404 while every file that names it reads correctly."""
    prefix = _prefix_in_deployment()
    assert _client().PUBLIC_PREFIX == prefix
    paths = [
        match["path"]["value"]
        for rule in _route()["spec"]["rules"]
        for match in rule["matches"]
    ]
    assert paths, _route()
    assert all(p.startswith(prefix + "/") for p in paths), paths


def _agent_doors() -> set[str]:
    """The handler's AGENT_DOORS, read out of the source rather than imported.

    serve.py is a module of a package this repository also imports elsewhere, and loading it a
    second time under a name the package already holds builds a second set of class objects --
    the trap that made #2485 green locally and red in CI. Reading the literal costs one ast
    walk and cannot collide with anything.
    """
    tree = ast.parse((ROOT / "platform" / "jit" / "broker" / "serve.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if "AGENT_DOORS" in names and node.value is not None:
                return set(ast.literal_eval(node.value))
    raise AssertionError("no AGENT_DOORS in serve.py")


def test_the_route_carries_every_door_the_client_can_dial():
    """A path the client posts to and the route does not carry is a grant an agent cannot ask
    for from outside, found the day it needs it rather than the day it is written."""
    prefix = _prefix_in_deployment()
    carried = {
        match["path"]["value"][len(prefix) :]
        for rule in _route()["spec"]["rules"]
        for match in rule["matches"]
    }
    assert carried == _agent_doors(), carried


def test_the_route_matches_exactly_and_not_by_prefix():
    """A PathPrefix match on `/jit` would put every future path this handler grows on the
    public internet the moment it is written, including one added by somebody who never read
    this file."""
    kinds = {
        match["path"].get("type")
        for rule in _route()["spec"]["rules"]
        for match in rule["matches"]
    }
    assert kinds == {"Exact"}, kinds


def test_the_public_route_does_not_carry_healthz():
    """`/healthz` is the kubelet's, from the node, and it answers with the ledger's verdict on
    itself. Nothing outside needs it, and an unauthenticated path on a public route is a probe
    for whether this broker exists at all."""
    paths = [
        match["path"]["value"]
        for rule in _route()["spec"]["rules"]
        for match in rule["matches"]
    ]
    assert not [p for p in paths if p.endswith("/healthz")], paths


def test_the_route_sends_traffic_to_the_service_the_fence_admits():
    """The route naming a Service that does not exist, or a port the fence closes, is the same
    404 by a different road."""
    service = _broker_service()
    backends = [
        ref for rule in _route()["spec"]["rules"] for ref in rule["backendRefs"]
    ]
    assert backends, _route()
    ports = {p["port"] for p in service["spec"]["ports"]}
    for ref in backends:
        assert ref["name"] == service["metadata"]["name"], ref
        assert ref["port"] in ports, (ref, ports)


def test_the_route_arrives_through_a_namespace_the_fence_admits():
    """A route is not a hole in a NetworkPolicy. The gateway's own pods dial the Service, so
    the fence has to admit the namespace they run in or the door is configured and closed."""
    admitted = {
        ns["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"]
        for doc in _docs(FENCE)
        if doc.get("kind") == "NetworkPolicy"
        for rule in doc["spec"].get("ingress") or []
        for ns in rule.get("from") or []
        if "namespaceSelector" in ns
    }
    assert "edge" in admitted, admitted


def test_the_route_is_reconciled_and_not_just_written():
    """A manifest no kustomization names is a file, not a route."""
    with KUSTOMIZATION.open() as fh:
        resources = yaml.safe_load(fh).get("resources") or []
    assert PUBLIC_DOOR.name in resources, resources
