"""The asking door, and the three places that have to agree about it.

WJ.2 says an agent that hits a wall does not fail and does not report back: it asks. On
2026-09-07 one could not. The CNI cutover left 97 pods still wired by flannel and needing a
restart, `restart-workload` in platform/jit/grants.yaml is exactly that grant, and there was
no address to request it at -- platform/jit/fence.yaml admitted namespaces `agents` and
`edge`, and the public route carries the Telegram webhook alone (`POST
https://otto.mumchimp.com/ask` answered 404, measured that day).

The door added for it is the tailnet's, and it only exists if four files agree: the Service
asks the operator for a device under one tag, the ACL names that same tag and port, the two
namespace fences declare the hop in both directions, and the client knows the hostname to look
the device up by. Any one of them drifting leaves a door that looks configured and refuses
every request, which is the failure this file is here to catch.

Reaching the door is not being granted anything, and the last test pins the part that must not
drift: the ACL admits the founder's devices and no one else.
"""

from __future__ import annotations

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
    assert doors[0] == mod.IN_CLUSTER, doors
    assert doors[-1] == f"http://{host}.tail0000.ts.net:8080", doors


def test_a_laptop_with_no_tailnet_still_gets_an_answer_rather_than_a_crash(monkeypatch):
    mod = _client()
    monkeypatch.delenv("JIT_BROKER_URL", raising=False)
    monkeypatch.setattr(mod.shutil, "which", lambda _: None)
    assert mod._doors() == [mod.IN_CLUSTER]


def test_a_caller_that_named_a_broker_gets_that_one_and_no_other(monkeypatch):
    """Falling through to a second broker because the named one refused would answer a
    different question than the caller asked."""
    mod = _client()
    monkeypatch.setenv("JIT_BROKER_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(mod.shutil, "which", lambda _: "/usr/bin/tailscale")
    assert mod._doors() == ["http://127.0.0.1:9"]
