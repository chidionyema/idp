"""The broker mints write access on a cluster where nothing else holds any, so these tests
are the ones that matter: each names a way an agent could try to turn ten minutes into
forever, and proves the broker refuses it.

They grade behaviour, never prose (R76). Nothing here asserts that a sentence appears in a
file; every case drives the real object and checks what it did.
"""

from __future__ import annotations

import base64
import http.client
import io
import json
import pathlib
import sys
import threading
import time
import urllib.error
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "jit"))

from broker.broker import Broker, Refused, ttl_seconds  # noqa: E402
from broker.telegram import Phone, ask_text, digest  # noqa: E402

CATALOGUE = str(ROOT / "platform" / "jit" / "grants.yaml")
KEY = b"a key the agent identity cannot read"
NS = "backstage"


def _token(exp: float) -> str:
    """A JWT shaped like the one the API server signs, so the expiry the agent is told is
    read out of the token rather than guessed from the ask."""
    body = (
        base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode())
        .rstrip(b"=")
        .decode()
    )
    return f"header.{body}.signature"


class FakeCluster:
    """Stands in for bin/idp-kube. Records the argv it was handed, which is how the tests
    below check that the broker asked the cluster for exactly what the founder approved."""

    def __init__(
        self, *, history: str = "backstage:v1 backstage:v2", fail_on: str = ""
    ):
        self.calls: list[list[str]] = []
        self.history, self.fail_on = history, fail_on

    def __call__(self, args: list[str], stdin: str | None = None) -> tuple[int, str]:
        self.calls.append(args)
        joined = " ".join(args)
        if self.fail_on and self.fail_on in joined:
            return 1, f"Error from server: {self.fail_on} refused"
        if args[:2] == ["get", "replicaset"]:
            return 0, self.history
        if args[:2] == ["create", "token"]:
            return 0, _token(time.time() + 300)
        if args[:2] == ["get", "deployment"]:
            return 0, "registry.example/backstage:v2"
        return 0, "patched"


class FakeProvider:
    """Stands in for one of the layers below Kubernetes -- the OCI CLI, the DNS CLI, gh.
    Records the argv, so the tests can read exactly what the broker would have run on a real
    tenancy without one being anywhere near this suite (WJ.15)."""

    def __init__(self, rc: int = 0, out: str = "done"):
        self.calls: list[list[str]] = []
        self.rc, self.out = rc, out

    def __call__(self, args: list[str]) -> tuple[int, str]:
        self.calls.append(args)
        return self.rc, self.out


def make(
    tmp_path,
    cluster=None,
    stopped: str | None = None,
    now=None,
    providers=None,
    agent_key: bytes = b"",
) -> Broker:
    return Broker(
        catalogue=CATALOGUE,
        key=KEY,
        ledger_path=str(tmp_path / "ledger.jsonl"),
        kube=cluster or FakeCluster(),
        killswitch=lambda: stopped,
        now=now or time.time,
        providers=providers,
        agent_key=agent_key,
    )


def approve(broker: Broker, req):
    return broker.decide_callback(broker.callback_data(req.id, "approve"))


# --- the ask is bounded before the founder is ever woken -----------------------------


def test_a_grant_that_is_not_in_the_catalogue_cannot_be_asked_for(tmp_path):
    with pytest.raises(Refused):
        make(tmp_path).ask(
            "cluster-admin-for-a-minute", {"namespace": NS}, "why", "10m", "a"
        )


def test_a_namespace_the_grant_does_not_name_is_refused(tmp_path):
    with pytest.raises(Refused):
        make(tmp_path).ask(
            "restart-workload",
            {"namespace": "kube-system", "pod": "p"},
            "why",
            "5m",
            "a",
        )


def test_a_parameter_the_grant_does_not_declare_is_refused(tmp_path):
    """The parameters are the only thing the agent fills in, so an undeclared one is the
    obvious place to smuggle something the founder will not read on his phone."""
    with pytest.raises(Refused):
        make(tmp_path).ask(
            "restart-workload",
            {"namespace": NS, "pod": "p", "serviceAccountName": "admin"},
            "why",
            "5m",
            "a",
        )


def test_a_quantity_above_the_grants_ceiling_is_refused(tmp_path):
    with pytest.raises(Refused):
        make(tmp_path).ask(
            "raise-memory-limit",
            {"namespace": NS, "workload": "backstage", "memory": "64Gi"},
            "why",
            "10m",
            "a",
        )


def test_a_ttl_longer_than_the_grant_allows_is_refused(tmp_path):
    with pytest.raises(Refused):
        make(tmp_path).ask(
            "restart-workload", {"namespace": NS, "pod": "p"}, "why", "12h", "a"
        )


def test_an_ask_with_no_reason_is_refused(tmp_path):
    """WJ.2: he reads this on a lock screen. An ask with no why is a tap he cannot judge."""
    with pytest.raises(Refused):
        make(tmp_path).ask(
            "restart-workload", {"namespace": NS, "pod": "p"}, "  ", "5m", "a"
        )


def test_a_rollback_to_a_tag_this_cluster_never_ran_is_refused(tmp_path):
    """It would arrive on his phone under the word rollback while actually being a deploy."""
    cluster = FakeCluster(history="registry.example/backstage:v1")
    with pytest.raises(Refused):
        make(tmp_path, cluster).ask(
            "rollback-image",
            {"namespace": NS, "workload": "backstage", "tag": "v99"},
            "why",
            "10m",
            "a",
        )


# --- WJ.6: the approval is signed, and spending one is not the same as forging one ----


def test_a_forged_approval_is_refused_and_recorded(tmp_path):
    broker = make(tmp_path)
    req = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    forged = f"j:{req.id[:12]}:a:{'0' * 24}"
    with pytest.raises(Refused):
        broker.decide_callback(forged)
    assert req.state == "pending", "a forged tap must move nothing"
    events = [json.loads(x)["event"] for x in open(broker.ledger.path) if x.strip()]
    assert "forged" in events, (
        "an attempt to forge an approval is the thing he most needs to see"
    )


def test_an_approval_cannot_be_spent_twice(tmp_path):
    """A captured callback is one grant, not a renewable one."""
    broker = make(tmp_path)
    req = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    approve(broker, req)
    with pytest.raises(Refused):
        approve(broker, req)


def test_a_button_press_fits_inside_what_telegram_will_carry(tmp_path):
    """Telegram truncates callback_data past 64 bytes without saying so, and a truncated
    signature that still verified would be a hole. It must fit whole."""
    broker = make(tmp_path)
    req = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    assert len(broker.callback_data(req.id, "approve").encode()) <= 64


def test_the_ask_is_pinned_while_it_waits_and_unpinned_the_moment_it_is_answered(
    tmp_path, monkeypatch
):
    """The tap has to be findable, and this broker shares a chat with every alert.

    platform/jit/deployment.yaml gives the broker the alerts row's bot and channel, so the
    approval button lands in the same chat as Robusta's crash reports and the Flux reds.
    Founder, 2026-09-08: "welli dnt see it cos its a fucking ness of alerts ... inpossible to
    se naything". A pinned message sits in the chat header above everything that arrives after
    it; unpinning on the decision is what stops the header from lying about what is waiting.
    """
    import broker.telegram as tg

    calls = []

    def fake(token, method, payload, timeout=20):
        calls.append((method, payload))
        return {"result": {"message_id": 4242}}

    monkeypatch.setattr(tg, "_call", fake)

    broker = make(tmp_path)
    req = broker.ask("restart-workload", {"namespace": NS, "pod": "p"}, "w", "5m", "a")
    phone = tg.Phone("t", "111", broker)
    phone.send_ask(req, broker._load_grant(req.grant_id))

    assert [m for m, _ in calls] == ["sendMessage", "pinChatMessage"]
    assert calls[1][1]["message_id"] == 4242
    # Silent: the message it pins has already made the noise.
    assert calls[1][1]["disable_notification"] is True

    phone.handle(
        {
            "callback_query": {
                "data": broker.callback_data(req.id, "deny"),
                "message": {"chat": {"id": "111"}},
            }
        }
    )
    # Denied, not granted -- and it still comes off the header. An answered ask left pinned is
    # a header that lies about what is waiting on him.
    assert req.state == "denied"
    assert calls[-1][0] == "unpinChatMessage"
    assert calls[-1][1]["message_id"] == 4242


def test_an_ask_still_reaches_him_when_the_bot_cannot_pin(tmp_path, monkeypatch):
    """A bot without pin rights in the chat has still sent the ask. Refusing the whole ask
    because the header could not be written would be the worse failure, so the pin is
    best-effort and the ledger records that it could not."""
    import broker.telegram as tg

    def fake(token, method, payload, timeout=20):
        if method == "pinChatMessage":
            raise RuntimeError("not enough rights to pin a message")
        return {"result": {"message_id": 7}}

    monkeypatch.setattr(tg, "_call", fake)

    broker = make(tmp_path)
    req = broker.ask("restart-workload", {"namespace": NS, "pod": "p"}, "w", "5m", "a")
    tg.Phone("t", "111", broker).send_ask(req, broker._load_grant(req.grant_id))

    with open(broker.ledger.path) as fh:
        events = [json.loads(line)["event"] for line in fh if line.strip()]
    assert "pin-failed" in events


def test_a_tap_from_a_chat_that_is_not_his_is_refused(tmp_path):
    broker = make(tmp_path)
    req = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    phone = Phone("t", "111", broker)
    update = {
        "callback_query": {
            "data": broker.callback_data(req.id, "approve"),
            "message": {"chat": {"id": "222"}},
        }
    }
    assert phone.handle(update).startswith("refused")
    assert req.state == "pending"


# --- WJ.4 and the two modes ----------------------------------------------------------


def test_a_token_grant_mints_a_token_that_carries_its_own_expiry(tmp_path):
    cluster = FakeCluster()
    broker = make(tmp_path, cluster)
    req = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    approve(broker, req)
    assert req.state == "granted"
    minted = [c for c in cluster.calls if c[:2] == ["create", "token"]][0]
    assert "--duration=300s" in minted, (
        "the TTL the founder saw is the TTL that is minted"
    )
    assert req.result["expires_at"] <= time.time() + 300 + 5


def test_a_grant_that_could_rewrite_a_pod_spec_never_hands_over_a_token(tmp_path):
    """The whole reason two modes exist: `patch deployment` would let its holder rewrite
    serviceAccountName and keep access after the token died."""
    cluster = FakeCluster()
    broker = make(tmp_path, cluster)
    req = broker.ask(
        "raise-memory-limit",
        {"namespace": NS, "workload": "backstage", "memory": "2Gi"},
        "OOM",
        "10m",
        "a",
    )
    approve(broker, req)
    assert req.state == "granted"
    assert "token" not in req.result
    assert not [c for c in cluster.calls if c[:2] == ["create", "token"]]
    patched = [c for c in cluster.calls if c[0] == "patch"][0]
    assert "2Gi" in " ".join(patched), (
        "the broker applies the change the founder approved"
    )


def test_a_change_that_fails_after_approval_comes_back_to_the_agent(tmp_path):
    """WJ.12: the agent that asked is told, so it does not ask for the same grant again."""
    broker = make(tmp_path, FakeCluster(fail_on="patch"))
    req = broker.ask(
        "raise-memory-limit",
        {"namespace": NS, "workload": "backstage", "memory": "2Gi"},
        "OOM",
        "10m",
        "a",
    )
    approve(broker, req)
    assert req.state == "failed"
    assert req.reason


# --- WJ.9, WJ.10, WJ.3 ---------------------------------------------------------------


def test_the_rate_limit_stops_a_loop(tmp_path):
    broker = make(tmp_path)
    for _ in range(4):
        req = broker.ask(
            "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
        )
        approve(broker, req)
    with pytest.raises(Refused):
        broker.ask("restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a")


def test_the_kill_switch_refuses_every_ask(tmp_path):
    with pytest.raises(Refused):
        make(tmp_path, stopped="the founder pressed stop").ask(
            "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
        )


def test_a_tap_that_never_comes_is_a_no(tmp_path):
    """WJ.3. A request that waits forever is a tap available at 3am to whoever holds his
    phone, which is not the same thing as his approval."""
    clock = {"t": 1000.0}
    broker = make(tmp_path, now=lambda: clock["t"])
    req = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    clock["t"] += 1000
    broker.expire_stale(after_s=900)
    assert req.state == "expired"
    with pytest.raises(Refused):
        approve(broker, req)


# --- WJ.7: the record proves it was not edited ---------------------------------------


def test_the_record_notices_a_line_that_was_edited(tmp_path):
    broker = make(tmp_path)
    for _ in range(2):
        req = broker.ask(
            "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
        )
        approve(broker, req)
    assert broker.ledger.verify()[0]

    lines = [x for x in open(broker.ledger.path).read().split("\n") if x.strip()]
    rec = json.loads(lines[0])
    rec["why"] = "something he would have approved"
    lines[0] = json.dumps(rec, sort_keys=True)
    pathlib.Path(broker.ledger.path).write_text("\n".join(lines) + "\n")

    ok, why = broker.ledger.verify()
    assert not ok and "line 1" in why


def test_the_record_notices_a_line_that_was_removed(tmp_path):
    """Deleting the grant you do not want seen is the more likely tampering than editing
    one, and a plain append-only file cannot tell."""
    broker = make(tmp_path)
    for _ in range(3):
        req = broker.ask(
            "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
        )
        approve(broker, req)
    lines = [x for x in open(broker.ledger.path).read().split("\n") if x.strip()]
    pathlib.Path(broker.ledger.path).write_text("\n".join(lines[:1] + lines[2:]) + "\n")
    assert not broker.ledger.verify()[0]


def test_the_morning_summary_counts_what_happened(tmp_path):
    broker = make(tmp_path)
    granted = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )
    approve(broker, granted)
    denied = broker.ask(
        "restart-workload", {"namespace": NS, "pod": "q"}, "why", "5m", "a"
    )
    broker.decide_callback(broker.callback_data(denied.id, "deny"))
    text = digest(broker.ledger.path, time.time() - 3600)
    assert "1 approved" in text and "1 denied" in text


def test_a_duration_is_read_the_way_a_person_writes_one():
    assert ttl_seconds("10m") == 600
    assert ttl_seconds("30s") == 30
    assert ttl_seconds("2h") == 7200
    assert ttl_seconds("forever") is None


# --- WJ.15: the layer below Kubernetes gets the same treatment -----------------------
#
# Zero standing privilege in one layer is not zero standing privilege. These prove the other
# three layers go through the same ask, the same tap and the same refusals, and that none of
# them can ever hand the agent a credential.


def test_the_layers_below_kubernetes_never_hand_over_a_credential(tmp_path):
    """The whole reason they are broker-applies: OCI's session token carries the minting
    principal's entire policy set, GitHub's needs the App key, and DNS has no request-scoped
    credential at all. Whatever comes back, it is an outcome and not something to hold."""
    oci, dns, gh = FakeProvider(), FakeProvider(), FakeProvider()
    b = make(tmp_path, providers={"oci": oci, "dns": dns, "github": gh})
    for grant, params in (
        ("oci-scale-node-pool", {"node_pool": "pool-a", "size": "4"}),
        (
            "dns-point-record",
            {"record": "signoz", "record_type": "A", "target": "1.2.3.4"},
        ),
        (
            "github-rerun-failed-checks",
            {"repository": "chidionyema/prospector", "run_id": "12"},
        ),
    ):
        req = b.ask(
            grant, params, "the estate needs this for ten minutes", "5m", "agent"
        )
        done = approve(b, req)
        assert done.result["mode"] == "broker-applies", grant
        assert "token" not in done.result, f"{grant} handed the agent a credential"


def test_each_layer_is_reached_through_its_own_tool_with_exactly_the_approved_values(
    tmp_path,
):
    """The founder approved a node pool and a size; the argv the broker runs has to be those
    values and no others, or what he tapped and what happened are two different things."""
    oci = FakeProvider()
    b = make(tmp_path, providers={"oci": oci})
    req = b.ask(
        "oci-scale-node-pool",
        {"node_pool": "ocid1.nodepool.oc1..aaa", "size": "5"},
        "the cluster has nowhere to schedule the collector",
        "10m",
        "agent",
    )
    approve(b, req)
    assert len(oci.calls) == 1
    argv = oci.calls[0]
    assert argv[:3] == ["ce", "node-pool", "update"]
    assert "ocid1.nodepool.oc1..aaa" in argv
    assert argv[argv.index("--size") + 1] == "5"


def test_a_node_pool_cannot_be_emptied_by_a_ten_minute_grant(tmp_path):
    """`size: 0` is not a scale, it is an eviction of every workload on the pool. The floor
    the grant declares is what stops the resize grant from being an outage button."""
    oci = FakeProvider()
    b = make(tmp_path, providers={"oci": oci})
    with pytest.raises(Refused):
        b.ask(
            "oci-scale-node-pool",
            {"node_pool": "pool-a", "size": "0"},
            "the pool is idle and costing money",
            "10m",
            "agent",
        )
    assert oci.calls == [], "a refused ask still reached the tenancy"


def test_a_record_the_grant_does_not_name_is_refused(tmp_path):
    """The DNS equivalent of asking for kube-system: the record the estate is reached on."""
    dns = FakeProvider()
    b = make(tmp_path, providers={"dns": dns})
    with pytest.raises(Refused):
        b.ask(
            "dns-point-record",
            {"record": "gw", "record_type": "A", "target": "1.2.3.4"},
            "the gateway moved and the record has to follow",
            "10m",
            "agent",
        )
    assert dns.calls == []


def test_a_record_type_the_grant_does_not_write_is_refused(tmp_path):
    """An NS record moves the zone rather than one name in it."""
    b = make(tmp_path, providers={"dns": FakeProvider()})
    with pytest.raises(Refused):
        b.ask(
            "dns-point-record",
            {"record": "signoz", "record_type": "NS", "target": "ns1.example"},
            "the zone should be delegated elsewhere",
            "10m",
            "agent",
        )


def test_a_repository_the_grant_does_not_name_is_refused(tmp_path):
    """WJ.8 in the GitHub layer: the repository that holds the broker is not reachable, so a
    re-run can never become a way back into the fence."""
    gh = FakeProvider()
    b = make(tmp_path, providers={"github": gh})
    with pytest.raises(Refused):
        b.ask(
            "github-rerun-failed-checks",
            {"repository": "chidionyema/idp", "run_id": "5"},
            "a check failed on infrastructure rather than the change",
            "5m",
            "agent",
        )
    assert gh.calls == []


def test_a_layer_the_broker_cannot_reach_is_refused_not_reported_as_done(tmp_path):
    """A grant whose provider has no runner must fail loudly. Reporting an approval as applied
    when nothing ran is the one outcome that teaches the founder to stop reading the tap."""
    b = make(tmp_path, providers={})
    req = b.ask(
        "oci-scale-node-pool",
        {"node_pool": "pool-a", "size": "4"},
        "the cluster has nowhere to schedule the collector",
        "10m",
        "agent",
    )
    done = approve(b, req)
    assert done.state == "failed", done.state


def test_a_failure_below_kubernetes_reaches_the_agent(tmp_path):
    """WJ.12, one layer down: the agent has to learn the tenancy refused it, or it asks for
    the same grant again."""
    b = make(
        tmp_path,
        providers={"oci": FakeProvider(rc=1, out="ServiceError: LimitExceeded")},
    )
    req = b.ask(
        "oci-scale-node-pool",
        {"node_pool": "pool-a", "size": "6"},
        "the cluster has nowhere to schedule the collector",
        "10m",
        "agent",
    )
    done = approve(b, req)
    assert done.state == "failed"
    assert "LimitExceeded" in (done.reason or ""), done.reason


def test_every_grant_in_the_catalogue_names_a_layer_the_broker_can_actually_reach(
    tmp_path,
):
    """The catalogue and the broker are two files, and a grant naming an act with no step is
    a 3am approval that does nothing. This is the check that keeps them in step.

    It used to ask a weaker question -- whether the grant's *provider* had a runner -- and that
    is how `oci-vault-write` (#2496) passed: OCI had a runner, the node pool resizer, and the
    vault write would have been handed to it. The set is keyed by the grant now, on both sides.
    """
    import yaml

    from broker.broker import APPLIES, KUBERNETES_APPLIES

    with open(CATALOGUE) as fh:
        grants = yaml.safe_load(fh)["grants"]
    unreachable = [
        g["id"]
        for g in grants
        if g.get("mode") == "broker-applies"
        and g["id"]
        not in (
            KUBERNETES_APPLIES
            if str(g.get("provider") or "kubernetes") == "kubernetes"
            else APPLIES
        )
    ]
    assert not unreachable, (
        f"the catalogue offers grants the broker cannot perform: {unreachable}"
    )


def test_the_gate_refuses_a_grant_with_no_step_even_when_it_escalates_nothing(tmp_path):
    """The check bin/idp-jit-grants was missing.

    Every other check in that gate asks whether a grant can be turned into standing access.
    `oci-vault-write` (#2496) could not -- and it also could not be performed, because no code
    existed for it, and it passed. The catalogue below escalates nothing and still has to fail.
    """
    gate = _load_gate()
    clean_but_absent = tmp_path / "c.yaml"
    clean_but_absent.write_text(
        "apiVersion: idp.internal/v1\n"
        "kind: GrantCatalogue\n"
        "grants:\n"
        "  - id: oci-invent-a-thing\n"
        "    provider: oci\n"
        "    why: something plausible\n"
        "    mode: broker-applies\n"
        "    operations: [update-node-pool]\n"
        "    max_ttl: 10m\n"
        "    rate_per_hour: 2\n"
    )
    ok, why = gate.grade(clean_but_absent.read_text())
    assert ok is False, why
    assert "no step for it" in why

    ok, why = gate.grade(open(CATALOGUE).read())
    assert ok is True, why


def _load_gate():
    """Load bin/idp-jit-grants by path. It has no .py suffix and is not a package, which is
    how workspace.yaml loads code locations too (LAW 45)."""
    import importlib.machinery
    import importlib.util

    spec = importlib.util.spec_from_loader(
        "idp_jit_grants",
        importlib.machinery.SourceFileLoader(
            "idp_jit_grants", str(ROOT / "bin" / "idp-jit-grants")
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_grant_the_broker_cannot_perform_is_refused_before_the_phone_rings(tmp_path):
    """The founder is never woken to approve an act nothing performs.

    The catalogue this broker loads is the real one, so the refusal has to be provoked with a
    grant id it does not hold -- which is the same code path, and the same answer, as a grant
    that is in the catalogue with no step behind it. Before 2026-09-08 the equivalent ask
    reached the phone and failed on the far side of the tap.
    """
    b = make(tmp_path, providers={"oci": FakeProvider()})
    unimplemented = {
        "id": "oci-invent-a-thing",
        "provider": "oci",
        "mode": "broker-applies",
    }
    with pytest.raises(Refused) as e:
        b._check_implemented(unimplemented)
    assert "no step" in str(e.value)

    # And the guard is not simply refusing everything: the seven real grants pass it, which is
    # what makes the refusal above mean something.
    import yaml

    with open(CATALOGUE) as fh:
        for g in yaml.safe_load(fh)["grants"]:
            b._check_implemented(g)


def test_an_approved_vault_write_never_runs_another_grants_step(tmp_path):
    """The specific defect of #2496, pinned.

    Dispatching below-Kubernetes acts by provider meant every OCI grant ran the one OCI step
    that existed. This asserts the vault write builds a vault argv -- and, because the value is
    the secret, that the record of what happened does not contain it (LAW 21).
    """
    import os

    from broker.broker import APPLIES

    seen = []

    def run(args):
        seen.append(args)
        return 0, "{}"

    os.environ.update(
        {
            "JIT_OCI_COMPARTMENT_ID": "ocid1.compartment.oc1..test",
            "JIT_OCI_VAULT_ID": "ocid1.vault.oc1..test",
            "JIT_OCI_KEY_ID": "ocid1.key.oc1..test",
        }
    )
    req = SimpleNamespace(
        id="r1", params={"secret_name": "estate_seed_keys", "contents_b64": "c3Vw"}
    )
    out = APPLIES["oci-vault-write"]({"id": "oci-vault-write"}, req, run, "oci")

    assert [a[:3] for a in seen] == [
        ["vault", "secret", "list"],
        ["vault", "secret", "create-base64"],
    ], seen
    assert "node-pool" not in " ".join(" ".join(a) for a in seen)
    assert "c3Vw" not in json.dumps(out)


def test_the_lock_screen_names_the_layer_and_what_will_actually_happen(tmp_path):
    """WJ.2 and WJ.15 together. Ten minutes on the cluster and ten minutes on the tenancy are
    not the same risk, and a broker-applies grant hands nothing over -- both have to be on the
    message, because it is the only thing he reads before tapping."""
    b = make(tmp_path, providers={"oci": FakeProvider()})
    req = b.ask(
        "oci-scale-node-pool",
        {"node_pool": "pool-a", "size": "4"},
        "the cluster has nowhere to schedule the collector",
        "10m",
        "agent",
    )
    text = ask_text(req, b._load_grant("oci-scale-node-pool"))
    assert "oci" in text, text
    assert "update-node-pool" in text, text
    assert "nothing is handed over" in text, text

    k = b.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "it is wedged", "5m", "agent"
    )
    ktext = ask_text(k, b._load_grant("restart-workload"))
    assert "oci" not in ktext, ktext
    assert "Ends* by itself after 5m" in ktext, ktext


def test_the_agent_client_says_the_broker_is_unreachable_instead_of_raising(
    monkeypatch,
):
    """Found by running it: `idp-jit grants` with no broker up printed a urllib stack trace.
    An agent reading that learns nothing and cannot tell it apart from its own bug, so the
    client now answers in words and exits `refused` -- the founder was never woken, which is
    exactly what that code means."""
    import importlib.machinery
    import importlib.util

    spec = importlib.util.spec_from_loader(
        "idp_jit",
        importlib.machinery.SourceFileLoader("idp_jit", str(ROOT / "bin" / "idp-jit")),
    )
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("JIT_BROKER_URL", "http://127.0.0.1:9")
    spec.loader.exec_module(mod)

    for argv in (
        ["grants"],
        [
            "ask",
            "--grant",
            "restart-workload",
            "--namespace",
            NS,
            "--pod",
            "p",
            "--why",
            "the pod is wedged and a restart is the whole fix",
        ],
    ):
        assert mod.main(argv) == mod.CODES["refused"], argv


# --- the answer gets back to the broker (WJ.6 delivery) ------------------------------
#
# The broker registers no webhook and polls nothing. One Telegram bot has exactly one webhook
# URL and exactly one reader, this estate runs exactly one bot, and otto-gateway's door holds
# that URL -- so the broker is handed a mirrored copy of the same POST instead
# (platform/otto-gateway/telegram-mirror.yaml). What these grade is the door that copy lands
# on: it must refuse anything not carrying the secret token Telegram signs with, it must apply
# the approval it is handed, and a correct signature from a chat that is not his must still be
# refused. The 2026-09-07 regression they close is a broker that polled instead, took otto's
# webhook away at every start, and then answered 409 forever.

SECRET_TOKEN = "the-token-telegram-was-registered-with"


def _door(broker, phone, secret_token=SECRET_TOKEN, public_prefix=""):
    """The real HTTP door on a loopback port, not a stand-in: the check under test reads a
    header, and a fake handler would grade the test's own idea of the request."""
    from broker import serve as srv

    srv.Handler.broker, srv.Handler.phone = broker, phone
    srv.Handler.webhook_secret = secret_token
    srv.Handler.telegram_path = "/webhook/telegram"
    srv.Handler.public_prefix = public_prefix
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _deliver(httpd, update, token=SECRET_TOKEN, path="/webhook/telegram"):
    host, port = httpd.server_address[0], httpd.server_address[1]
    conn = http.client.HTTPConnection(host, port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Telegram-Bot-Api-Secret-Token"] = token
    conn.request("POST", path, json.dumps(update), headers)
    status = conn.getresponse()
    status.read()
    code = status.status
    conn.close()
    return code


def _tap(broker, req, chat_id):
    return {
        "update_id": 7,
        "callback_query": {
            "data": broker.callback_data(req.id, "approve"),
            "message": {"chat": {"id": chat_id}},
        },
    }


def _asked(broker):
    return broker.ask(
        "restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a"
    )


def test_an_accepted_delivery_leaves_a_line_a_human_can_read(tmp_path, capfd):
    """The broker silences its HTTP access log, so without this line a real tap completes
    and `kubectl logs` stays empty -- nothing to quote when asked to prove it works."""
    broker = make(tmp_path)
    req = _asked(broker)
    httpd = _door(broker, Phone("t", "42", broker))
    try:
        assert _deliver(httpd, _tap(broker, req, 42)) == 200
    finally:
        httpd.shutdown()
    assert "jit telegram: mirrored delivery handled" in capfd.readouterr().out


def test_his_tap_delivered_to_the_mirrored_path_grants_the_request(tmp_path):
    broker = make(tmp_path)
    req = _asked(broker)
    httpd = _door(broker, Phone("t", "42", broker))
    try:
        assert _deliver(httpd, _tap(broker, req, 42)) == 200
    finally:
        httpd.shutdown()
    assert req.state == "granted"


def test_a_delivery_with_no_secret_token_is_refused(tmp_path):
    broker = make(tmp_path)
    req = _asked(broker)
    httpd = _door(broker, Phone("t", "42", broker))
    try:
        assert _deliver(httpd, _tap(broker, req, 42), token=None) == 401
    finally:
        httpd.shutdown()
    assert req.state == "pending", (
        "the mirrored path is reachable from the public door; a delivery Telegram did not "
        "sign must not move a request"
    )


def test_a_delivery_with_the_wrong_secret_token_is_refused(tmp_path):
    broker = make(tmp_path)
    req = _asked(broker)
    httpd = _door(broker, Phone("t", "42", broker))
    try:
        assert _deliver(httpd, _tap(broker, req, 42), token="not-it") == 401
    finally:
        httpd.shutdown()
    assert req.state == "pending"


def test_a_broker_holding_no_webhook_secret_refuses_every_delivery(tmp_path):
    broker = make(tmp_path)
    req = _asked(broker)
    httpd = _door(broker, Phone("t", "42", broker), secret_token="")
    try:
        assert _deliver(httpd, _tap(broker, req, 42), token="") == 401, (
            "an empty configured secret must never compare equal to an empty header, or a "
            "broker whose Secret failed to sync would accept anything"
        )
    finally:
        httpd.shutdown()
    assert req.state == "pending"


def test_a_signed_tap_from_a_chat_that_is_not_his_is_still_refused(tmp_path):
    broker = make(tmp_path)
    req = _asked(broker)
    httpd = _door(broker, Phone("t", "42", broker))
    try:
        _deliver(httpd, _tap(broker, req, 999))
    finally:
        httpd.shutdown()
    assert req.state == "pending", (
        "Telegram's secret token proves Telegram sent it, never that he sent it"
    )


def test_the_broker_has_no_poller_to_take_the_webhook_away(tmp_path):
    from broker import telegram as tg

    assert not hasattr(tg, "poll_forever"), (
        "a getUpdates loop calls deleteWebhook on the estate's one bot at every start, which "
        "takes otto-gateway's inbound Telegram away and then 409s forever (2026-09-07)"
    )


def test_a_telegram_refusal_says_what_telegram_said(monkeypatch):
    """`HTTP Error 409: Conflict` is equally true of a registered webhook and of a second
    reader, and those want opposite repairs. The description is the only thing that tells
    them apart, and urlopen throws it away unless someone reads the body."""
    from broker import telegram as tg

    def refuse(req, timeout=20):
        raise urllib.error.HTTPError(
            url="https://api.telegram.org/botX/getUpdates",
            code=409,
            msg="Conflict",
            hdrs=None,
            fp=io.BytesIO(
                b'{"ok":false,"error_code":409,"description":'
                b'"can\'t use getUpdates while webhook is active"}'
            ),
        )

    monkeypatch.setattr(tg.urllib.request, "urlopen", refuse)
    with pytest.raises(RuntimeError) as caught:
        tg._call("X", "getUpdates", {})
    assert "webhook is active" in str(caught.value)


# --- the ask door will not take an ask from a stranger --------------------------------
#
# Before this, `/ask` read `asked_by` out of the request body and believed it. Anything that
# could open a socket to port 8080 -- any pod the fence let through, a sidecar, a stray
# port-forward -- could put a name on an ask and make the founder's phone buzz with it. He
# taps every one, so it was never standing access; it was provenance, and provenance is the
# whole design. He is being asked to read a name and decide, and a name nothing attests is a
# name that makes the next ask worth less than the last.

AGENT_KEY = b"the-agent-bootstrap-key"


def _idp_jit():
    """bin/idp-jit as a module. It has no .py suffix, so the loader has to be named:
    spec_from_file_location returns None for an extensionless file."""
    import importlib.machinery
    import importlib.util

    spec = importlib.util.spec_from_loader(
        "idp_jit_ask",
        importlib.machinery.SourceFileLoader(
            "idp_jit_ask", str(ROOT / "bin" / "idp-jit")
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ask_over_http(httpd, key: str | None, grant="restart-workload", path="/ask"):
    host, port = httpd.server_address[0], httpd.server_address[1]
    conn = http.client.HTTPConnection(host, port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"
    conn.request(
        "POST",
        path,
        json.dumps(
            {
                "grant": grant,
                "params": {"namespace": NS, "pod": "p"},
                "why": "the pod is wedged and a restart is the whole fix",
                "ttl": "5m",
                "asked_by": "someone-elses-name",
            }
        ),
        headers,
    )
    res = conn.getresponse()
    body = json.loads(res.read() or b"{}")
    code = res.status
    conn.close()
    return code, body


class SilentPhone:
    """The founder's phone, counting buzzes. What the door must not do is reach this at all
    for a caller that proved nothing."""

    def __init__(self):
        self.sent = []

    def send_ask(self, req, grant):
        self.sent.append(req.id)


def test_an_ask_carrying_no_key_never_reaches_the_founders_phone(tmp_path):
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone)
    try:
        code, body = _ask_over_http(httpd, None)
    finally:
        httpd.shutdown()
    assert code == 401, body
    assert phone.sent == [], "an unauthenticated ask must not buzz his phone"
    assert broker.pending == {}, "and must not leave a request behind either"


def test_an_ask_carrying_the_wrong_key_is_refused(tmp_path):
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone)
    try:
        code, body = _ask_over_http(httpd, "not-the-key")
    finally:
        httpd.shutdown()
    assert code == 401, body
    assert phone.sent == []


def test_a_broker_holding_no_agent_key_takes_an_ask_from_nobody(tmp_path):
    """Fail closed, and the same way `identity()` already does. The key arrives by
    ExternalSecret, so there is a window at start where it is absent; taking asks from
    anybody during that window is the one behaviour the window must not have."""
    broker = make(tmp_path, agent_key=b"")
    phone = SilentPhone()
    httpd = _door(broker, phone)
    try:
        code, _ = _ask_over_http(httpd, "")
        empty_header, _ = _ask_over_http(httpd, None)
    finally:
        httpd.shutdown()
    assert code == 401, (
        "an empty configured key must never compare equal to an empty header"
    )
    assert empty_header == 401
    assert phone.sent == []


def test_a_refused_ask_writes_no_ledger_line(tmp_path):
    """Same reasoning the Telegram path already carries: this door is reachable from outside
    the cluster, so one line per refusal is a way for a stranger to fill the ledger volume.
    The ledger records what the broker did, and it did nothing."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    httpd = _door(broker, SilentPhone())
    try:
        _ask_over_http(httpd, "not-the-key")
    finally:
        httpd.shutdown()
    ledger = tmp_path / "ledger.jsonl"
    lines = ledger.read_text().splitlines() if ledger.exists() else []
    assert lines == [], f"a refused ask left {len(lines)} line(s) on the ledger"


def test_an_ask_carrying_the_key_goes_through_and_is_recorded_as_attested(tmp_path):
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone)
    try:
        code, body = _ask_over_http(httpd, AGENT_KEY.decode())
    finally:
        httpd.shutdown()
    assert code == 200, body
    assert phone.sent == [body["request"]]
    line = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[0])
    assert line["event"] == "asked"
    assert line["attested"] is True, (
        "the name on an ask is still self-declared -- one key covers every agent -- so the "
        "ledger has to say whether anything attested the caller at all"
    )


def test_an_in_process_ask_is_recorded_as_unattested(tmp_path):
    """The flag is the door's word, not a decoration. A caller that did not come through the
    door says so, or the field means nothing wherever it appears."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    broker.ask("restart-workload", {"namespace": NS, "pod": "p"}, "why", "5m", "a")
    line = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[0])
    assert line["attested"] is False


def test_the_client_sends_the_same_key_it_identifies_with(tmp_path, monkeypatch):
    """bin/idp-jit's ask path, over a real socket. Without the header the broker refuses and
    the founder is never woken -- so a client that does not send it is a client that cannot
    ask for anything."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone)
    host, port = httpd.server_address[0], httpd.server_address[1]
    mod = _idp_jit()
    monkeypatch.setenv("JIT_BROKER_URL", f"http://{host}:{port}")
    monkeypatch.setenv("JIT_AGENT_KEY", AGENT_KEY.decode())
    monkeypatch.setenv("JIT_AGENT", "the-session-that-asked")
    try:
        rc = mod.main(
            [
                "ask",
                "--grant",
                "restart-workload",
                "--namespace",
                NS,
                "--pod",
                "p",
                "--why",
                "the pod is wedged and a restart is the whole fix",
                "--ttl",
                "5m",
                "--wait",
                "0",
            ]
        )
    finally:
        httpd.shutdown()
    # The founder never taps, so the ask times out unanswered. What is being graded is that
    # it reached him at all: an unauthenticated client is refused before this point.
    assert rc == mod.CODES["timeout"], rc
    assert len(phone.sent) == 1
    line = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[0])
    assert line["asked_by"] == "the-session-that-asked"
    assert line["attested"] is True


def test_a_client_holding_no_key_refuses_before_it_dials(tmp_path, monkeypatch):
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone)
    host, port = httpd.server_address[0], httpd.server_address[1]
    mod = _idp_jit()
    monkeypatch.setenv("JIT_BROKER_URL", f"http://{host}:{port}")
    monkeypatch.delenv("JIT_AGENT_KEY", raising=False)
    monkeypatch.setenv("IDP_KUBE_STATE", str(tmp_path / "no-key-here"))
    try:
        rc = mod.main(
            [
                "ask",
                "--grant",
                "restart-workload",
                "--namespace",
                NS,
                "--pod",
                "p",
                "--why",
                "the pod is wedged and a restart is the whole fix",
            ]
        )
    finally:
        httpd.shutdown()
    assert rc == mod.CODES["refused"]
    assert phone.sent == []


# --- the public door, and the prefix the edge puts in front of it ---------------------
#
# The shared Gateway listener carries one hostname and this broker does not get one of its own,
# so the public route is a path prefix on the host that already exists and the broker strips it
# back off (platform/jit/public-door.yaml). Stripping it here rather than rewriting it at the
# edge is one branch with a test around it, instead of a URLRewrite filter whose behaviour
# belongs to whichever ingress happens to be installed.


def test_a_prefixed_path_reaches_the_same_door_as_a_bare_one(tmp_path):
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone, public_prefix="/jit")
    try:
        code, body = _ask_over_http(httpd, AGENT_KEY.decode(), path="/jit/ask")
    finally:
        httpd.shutdown()
    assert code == 200, body
    assert phone.sent == [body["request"]]


def test_the_prefixed_path_is_behind_the_same_key(tmp_path):
    """The whole argument for a public door is that everything behind it refuses a stranger.
    A prefix that skipped the check would be a way in through the front."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    phone = SilentPhone()
    httpd = _door(broker, phone, public_prefix="/jit")
    try:
        code, _ = _ask_over_http(httpd, None, path="/jit/ask")
    finally:
        httpd.shutdown()
    assert code == 401
    assert phone.sent == []


def test_a_prefixed_path_is_not_a_door_when_no_prefix_is_configured(tmp_path):
    """A broker with no public door must not answer the public door's paths. Otherwise the
    prefix is a second name for every route, reachable wherever the pod is reachable."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    httpd = _door(broker, SilentPhone(), public_prefix="")
    try:
        code, _ = _ask_over_http(httpd, AGENT_KEY.decode(), path="/jit/ask")
    finally:
        httpd.shutdown()
    assert code == 404


def test_the_prefix_is_stripped_once_and_only_at_the_front(tmp_path):
    """`/jit/jit/ask` is not `/ask`. A repeated or embedded prefix has to stay a 404, or the
    exact-path rules in the route stop meaning what they say."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    httpd = _door(broker, SilentPhone(), public_prefix="/jit")
    try:
        doubled, _ = _ask_over_http(httpd, AGENT_KEY.decode(), path="/jit/jit/ask")
        embedded, _ = _ask_over_http(httpd, AGENT_KEY.decode(), path="/ask/jit")
    finally:
        httpd.shutdown()
    assert (doubled, embedded) == (404, 404)


def test_healthz_answers_on_the_prefix_and_is_not_on_the_public_route(tmp_path):
    """The kubelet's GET arrives bare, from the node. The prefixed form working is harmless;
    what matters is that platform/jit/public-door.yaml does not route it, and the manifest
    test in tests/test_the_broker_can_be_asked_from_outside_the_cluster.py grades that."""
    broker = make(tmp_path, agent_key=AGENT_KEY)
    httpd = _door(broker, SilentPhone(), public_prefix="/jit")
    host, port = httpd.server_address[0], httpd.server_address[1]
    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/healthz")
        bare = conn.getresponse()
        bare.read()
        code = bare.status
        conn.close()
    finally:
        httpd.shutdown()
    assert code == 200
