# ruff: noqa: S101, S105  (asserts test behaviour; S105 flags the broker forwarding a secret_name)

"""A below-Kubernetes grant lands on a dedicated executor, not on a binary the broker does
not ship (decision 0027). These tests pin the broker->executor hand-off: what the broker
signs and sends, and that it fails closed (refuses) when no executor is configured, rather
than pretending it ran the act itself.

They grade behaviour, never prose (R76). Every case drives the real Broker object.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "jit"))

from broker.broker import Broker  # noqa: E402

CATALOGUE = str(ROOT / "platform" / "jit" / "grants.yaml")
KEY = b"a broker signing key that only the broker and the executor share"


def _dummy_who(history: str = "backstage:v1") -> object:
    class _DummyCluster:
        def __init__(self) -> None:
            self.history = history

        def __call__(self, args, stdin=None):
            if args[:2] == ["get", "deployment"]:
                return 0, "registry.example/backstage:v2"
            if args[:2] == ["create", "token"]:
                return 0, "x.y.z"
            return 0, "ok"

    return _DummyCluster()


class FakeExecutor:
    """Stands in for the executor on the bridge machine. Records the payload the broker
    dispatched, so the test can assert exactly what the broker sent for the approved grant
    and params -- the grant id it approved and the values the founder saw, and nothing the
    broker invented."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, request_id: str, grant_id: str, params: dict) -> dict:
        self.calls.append(
            {"request_id": request_id, "grant_id": grant_id, "params": params}
        )
        return {
            "mode": "broker-applies",
            "executor": "bridge",
            "applied": f"{grant_id}:{','.join(sorted(params))}",
        }


def build(tmp_path, executor=None) -> Broker:
    return Broker(
        catalogue=CATALOGUE,
        key=KEY,
        ledger_path=str(tmp_path / "ledger.jsonl"),
        kube=_dummy_who(),
        killswitch=lambda: None,
        executor=executor,
    )


def approve(broker, req):
    return broker.decide_callback(broker.callback_data(req.id, "approve"))


def test_an_approved_below_kubernetes_grant_is_dispatched_to_the_executor(tmp_path):
    """When an oci grant is approved, the broker must not try to run an `oci` binary itself
    -- it does not ship one (decision 0027). It hands the exact approved grant and the exact
    parameters to the executor, and reports what the executor did, not what the broker did."""
    ex = FakeExecutor()
    b = build(tmp_path, executor=ex)
    req = b.ask(
        "oci-vault-write",
        {"secret_name": "agent_foundry_runner", "contents_b64": "c3R1ZmY="},
        "seed the runner credential",
        "10m",
        "agent",
    )
    done = approve(b, req)
    assert done.state == "granted", done.reason
    assert len(ex.calls) == 1
    sent = ex.calls[0]
    assert sent["grant_id"] == "oci-vault-write"
    # the broker forwards the secret name the founder approved, and never invents another
    assert sent["params"]["secret_name"] == "agent_foundry_runner"
    # the outcome the broker reports is the executor's, so the agent learns where it ran
    assert done.result["executor"] == "bridge"
    assert "token" not in done.result, (
        "a broker-applies grant never hands the agent a credential"
    )


def test_a_below_kubernetes_grant_with_nothing_to_run_it_is_failed_not_done(tmp_path):
    """Decision 0027's core refusal: a grant below Kubernetes must never be reported as
    done when nothing performed it. A broker with neither an executor nor a reachable
    provider fails the approved request -- the tap is not wasted on a lie."""
    b = build(tmp_path, executor=None)  # no executor
    # empty providers: no oci/dns/gh binary the broker can call
    b.providers = {}
    req = b.ask(
        "oci-scale-node-pool",
        {"node_pool": "pool-a", "size": "4"},
        "the pool is full",
        "10m",
        "agent",
    )
    done = approve(b, req)
    assert done.state == "failed", done.state
    assert done.result == {}, "nothing claimed to have run"


def test_a_kubernetes_grant_is_untouched_by_the_executor_path(tmp_path):
    """Decision 0027 only moves the below-Kubernetes layer. A Kubernetes grant still runs
    against the cluster exactly as before -- the executor must not become a second road for
    work that already has one."""
    ex = FakeExecutor()
    b = build(tmp_path, executor=ex)
    req = b.ask(
        "raise-memory-limit",
        {"namespace": "backstage", "workload": "backstage", "memory": "2Gi"},
        "the pod is OOM crashing",
        "10m",
        "agent",
    )
    done = approve(b, req)
    assert done.state == "granted", done.reason
    assert ex.calls == [], "a Kubernetes grant must not reach the executor"
    assert done.result["mode"] == "broker-applies"
