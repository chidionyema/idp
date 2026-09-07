"""The broker mints write access on a cluster where nothing else holds any, so these tests
are the ones that matter: each names a way an agent could try to turn ten minutes into
forever, and proves the broker refuses it.

They grade behaviour, never prose (R76). Nothing here asserts that a sentence appears in a
file; every case drives the real object and checks what it did.
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "jit"))

from broker.broker import Broker, Refused, ttl_seconds  # noqa: E402
from broker.telegram import Phone, digest  # noqa: E402

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


def make(tmp_path, cluster=None, stopped: str | None = None, now=None) -> Broker:
    return Broker(
        catalogue=CATALOGUE,
        key=KEY,
        ledger_path=str(tmp_path / "ledger.jsonl"),
        kube=cluster or FakeCluster(),
        killswitch=lambda: stopped,
        now=now or time.time,
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
