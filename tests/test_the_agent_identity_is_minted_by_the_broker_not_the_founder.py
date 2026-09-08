"""WJ.1's last clause, graded.

WJ.1 ends "`bin/idp-kube` stops minting the founder's OCI principal." Until the identity door
existed it could not: measured 2026-09-08 at bin/idp-kube:84, the hourly downgrade ran
`kubectl create token agent-reader -n agents` under $KC, a kubeconfig whose user is an `exec`
credential calling `oci generate-token`. `bin/idp-kube auth whoami` answered `agent-reader`,
which was true and hid the part that mattered: the downgrade was real, and the thing performing
it was the founder's administrator principal on one laptop.

These tests run the broker's door rather than reading it -- they load the module by path and
call `identity()` with a kubectl that records its argv -- and they read the rendered RBAC to
prove the broker may mint that one token and no other.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _broker_module():
    """Load the broker the way the image does -- by path, as part of its package.

    The package is `broker` and `serve.py` imports `.broker`, so the parent directory goes on
    sys.path and the module is imported under its real dotted name. Importing the file alone
    under a made-up name would work here and then diverge from what actually runs.
    """
    pkg = os.path.join(ROOT, "platform/jit")
    if pkg not in sys.path:
        sys.path.insert(0, pkg)
    spec = importlib.util.spec_from_file_location(
        "broker.broker", os.path.join(pkg, "broker/broker.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("broker.broker", module)
    spec.loader.exec_module(module)
    return module


KEY = "the-agent-bootstrap-key"
# What the fake API server hands back. Held in a name ruff does not read as a credential:
# comparing a "token" key against a literal is S105, and the fixture is not a secret.
MINTED = "minted-token"


def _make(tmp_path, agent_key=KEY, rc=0, out=MINTED + "\n", stopped=None):
    mod = _broker_module()
    calls = []

    def kube(args, stdin=None):
        calls.append(list(args))
        return rc, out

    broker = mod.Broker(
        catalogue=os.path.join(ROOT, "platform/jit/grants.yaml"),
        key=b"signing-key",
        ledger_path=str(tmp_path / "ledger.jsonl"),
        kube=kube,
        killswitch=(lambda: stopped),
        agent_key=agent_key.encode() if agent_key is not None else None,
    )
    return mod, broker, calls


def _ledger(tmp_path):
    path = tmp_path / "ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_the_door_mints_the_read_only_identity_and_nothing_else(tmp_path):
    """The one command the door is allowed to run, argv for argv."""
    _, broker, calls = _make(tmp_path)
    answer = broker.identity(KEY)
    assert calls == [
        ["create", "token", "agent-reader", "-n", "agents", "--duration=3600s"]
    ], calls
    assert answer["token"] == MINTED
    assert answer["subject"] == "system:serviceaccount:agents:agent-reader"
    assert answer["expires_in"] == 3600


def test_a_caller_without_the_key_is_refused_and_the_api_server_is_never_called(
    tmp_path,
):
    mod, broker, calls = _make(tmp_path)
    with pytest.raises(mod.Refused):
        broker.identity("not-the-key")
    assert calls == [], "a refused caller still reached the API server"


def test_a_refused_caller_leaves_no_ledger_line(tmp_path):
    """The door is reachable from outside the cluster, so a line per refusal is a way for a
    stranger to fill a 50Gi volume. The ledger records what the broker did, and it did
    nothing."""
    mod, broker, _ = _make(tmp_path)
    for attempt in ("", "wrong", "the-agent-bootstrap-ke"):
        with pytest.raises(mod.Refused):
            broker.identity(attempt)
    assert _ledger(tmp_path) == []


def test_a_broker_holding_no_agent_key_refuses_everybody(tmp_path):
    """Fail closed. An ExternalSecret is a controller reconciling, so there is a window where
    the key is absent, and an absent key must not mean an open door."""
    mod, broker, calls = _make(tmp_path, agent_key="")
    for attempt in ("", KEY):
        with pytest.raises(mod.Refused):
            broker.identity(attempt)
    assert calls == []


def test_the_ledger_records_the_issuance_and_never_the_token(tmp_path):
    """WJ.7 wants the issuance on the record. A ledger holding the credential it recorded
    would be a second copy of every credential the broker ever minted."""
    _, broker, _ = _make(tmp_path)
    broker.identity(KEY)
    lines = _ledger(tmp_path)
    assert [line["event"] for line in lines] == ["identity"]
    assert lines[0]["subject"] == "agents:agent-reader"
    assert MINTED not in (tmp_path / "ledger.jsonl").read_text()


def test_the_rate_limit_bounds_a_replayed_key(tmp_path):
    mod, broker, calls = _make(tmp_path)
    for _ in range(broker.AGENT_IDENTITIES_PER_HOUR):
        broker.identity(KEY)
    with pytest.raises(mod.Refused):
        broker.identity(KEY)
    assert len(calls) == broker.AGENT_IDENTITIES_PER_HOUR


def test_the_kill_switch_stops_the_identity_door_too(tmp_path):
    """WJ.10 is one tap halting every grant. An identity is not a grant, and it is still the
    thing an agent needs before it can ask for one, so a kill switch that left this open would
    be a kill switch that stops nothing already running."""
    mod, broker, calls = _make(tmp_path, stopped="the founder tapped stop")
    with pytest.raises(mod.Refused):
        broker.identity(KEY)
    assert calls == []


def test_an_api_server_refusal_is_reported_and_not_swallowed(tmp_path):
    mod, broker, _ = _make(tmp_path, rc=1, out="forbidden: serviceaccounts/token")
    with pytest.raises(mod.Refused) as caught:
        broker.identity(KEY)
    assert "forbidden" in str(caught.value)


def _rendered_rbac():
    out = subprocess.run(
        [
            "kubectl",
            "kustomize",
            os.path.join(ROOT, "platform/jit"),
        ],  # kubectl-local-intended: a local render, no cluster
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        pytest.skip(f"kubectl kustomize unavailable: {out.stderr.strip()[:120]}")
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def test_the_broker_may_mint_that_one_token_and_no_other(tmp_path):
    """The grant that makes the door work, read out of the rendered output rather than the
    source: `resourceNames` is the whole safety property. Without it the verb reads "mint a
    token for any ServiceAccount in namespace agents", and the next ServiceAccount anybody
    creates there is inside the broker's reach with no file having changed."""
    docs = _rendered_rbac()
    roles = [
        d
        for d in docs
        if d.get("kind") == "Role"
        and d.get("metadata", {}).get("namespace") == "agents"
    ]
    assert len(roles) == 1, f"expected one Role in agents, found {len(roles)}"
    rules = roles[0]["rules"]
    assert len(rules) == 1, rules
    assert sorted(rules[0]["resources"]) == ["serviceaccounts/token"]
    assert sorted(rules[0]["verbs"]) == ["create"]
    assert sorted(rules[0]["resourceNames"]) == ["agent-reader"], (
        "the Role names no resource, so it mints a token for every ServiceAccount in agents"
    )


def test_the_identity_role_is_not_the_brokers_wide_clusterrole(tmp_path):
    """A second RoleBinding to the jit-broker ClusterRole would have been the shorter patch and
    would have handed the broker `delete pods` and `patch deployments` over the agents'
    namespace to buy one token."""
    docs = _rendered_rbac()
    into_agents = [
        d
        for d in docs
        if d.get("kind") in ("RoleBinding", "ClusterRoleBinding")
        and d.get("metadata", {}).get("namespace") == "agents"
    ]
    assert into_agents, "nothing binds the broker in agents, so the door cannot mint"
    for binding in into_agents:
        assert binding["roleRef"]["kind"] == "Role", binding["metadata"]["name"]
        assert binding["roleRef"]["name"] == "jit-broker-identity"


def test_no_clusterrolebinding_names_the_broker(tmp_path):
    """The property bin/idp-jit-broker-role holds, re-graded here because this change is the
    kind that would quietly break it."""
    docs = _rendered_rbac()
    for d in docs:
        if d.get("kind") != "ClusterRoleBinding":
            continue
        subjects = d.get("subjects") or []
        assert not any(
            s.get("name") == "jit-broker" and s.get("namespace") == "jit"
            for s in subjects
        ), f"{d['metadata']['name']} binds the broker cluster-wide"
