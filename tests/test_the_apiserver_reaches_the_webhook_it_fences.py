"""A namespace that serves an admission webhook must let the control plane call in.

The estate learned this the hard way on 2026-09-08. Every namespace had a both-ways
default-deny fence, and eight of them back an admission webhook. The apiserver calls those
webhooks from outside the pod network, where no namespace selector reaches it, so the fence
dropped the call. Kyverno's webhook is fail-closed, so every write to the cluster was refused
and Flux sat at 0 of 80 Kustomizations.

It stayed invisible for eleven days because flannel was still running alongside Calico, and
its FLANNEL-POSTRTG masquerade rewrote the source of every Calico packet to the node's own
address -- 6.74 million packets, 652MB, measured on the node. Remove flannel and the gap is a
total outage. The fence was never right; it was only ever unenforced.

The generator already emits allow-apiserver-egress for the other direction and explains why an
ipBlock is the only thing that can name the control plane. This grades the missing mirror.
"""

import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _gen():
    # Loaded by file path, not as a package: bin/idp-ns-fence-gen has no .py suffix and
    # workspace.yaml loads code locations the same way.
    spec = importlib.util.spec_from_loader(
        "ns_fence_gen",
        importlib.machinery.SourceFileLoader(
            "ns_fence_gen", str(ROOT / "bin" / "idp-ns-fence-gen")
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _policies(docs, name):
    return [
        d
        for d in docs
        if d.get("kind") == "NetworkPolicy" and d["metadata"]["name"] == name
    ]


def test_a_declared_webhook_port_becomes_an_apiserver_ingress_allow():
    gen = _gen()
    docs = gen.policy_docs("kyverno", {"ingress_apiserver": [9443]})
    got = _policies(docs, "allow-apiserver-webhook-ingress")
    assert len(got) == 1, "one policy, or the control plane has no route in"
    spec = got[0]["spec"]
    assert spec["policyTypes"] == ["Ingress"]
    assert spec["podSelector"] == {}
    rule = spec["ingress"][0]
    # Only an ipBlock can name the control plane: it is outside every namespace selector.
    assert rule["from"] == [{"ipBlock": {"cidr": gen.APISERVER_CIDR}}]
    assert rule["ports"] == [{"protocol": "TCP", "port": 9443}]


def test_a_namespace_that_declares_no_webhook_gets_no_hole():
    gen = _gen()
    docs = gen.policy_docs("llm", {"egress": ["observability"]})
    assert _policies(docs, "allow-apiserver-webhook-ingress") == [], (
        "a namespace with no webhook must not be handed apiserver ingress"
    )


def test_every_namespace_that_declares_a_webhook_port_carries_the_policy_on_disk():
    """The generated tree is what Flux applies, so grade the tree, not just the function."""
    allowances = yaml.safe_load(
        (ROOT / "platform" / "ns-fences" / "allowances.yaml").read_text()
    )
    declared = {
        ns: flows["ingress_apiserver"]
        for ns, flows in (allowances["flows"] or {}).items()
        if isinstance(flows, dict) and flows.get("ingress_apiserver")
    }
    assert declared, (
        "no namespace declares a webhook port; the eight that serve one regressed"
    )
    for ns, ports in declared.items():
        path = ROOT / "platform" / "ns-fences" / "network" / f"{ns}.yaml"
        docs = [d for d in yaml.safe_load_all(path.read_text()) if d]
        got = _policies(docs, "allow-apiserver-webhook-ingress")
        assert len(got) == 1, (
            f"{ns} declares a webhook port but its fence has no way in"
        )
        assert got[0]["spec"]["ingress"][0]["ports"] == [
            {"protocol": "TCP", "port": int(p)} for p in sorted(set(ports))
        ], f"{ns}: the fence opens different ports than the webhook listens on"
