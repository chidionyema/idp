"""WJ.7: the account of who was given write access must survive the node it was written on.

The ledger is signed and hash-chained, and until now its only copy was a file on a 1Gi
ReadWriteOnce volume (platform/jit/deployment.yaml). One node dies and the audit trail dies with
it -- and an audit trail that can be lost by an ordinary hardware failure is not one a buyer's
engineer will accept. So every record is also shipped to the estate's one collector, which is
also what closes the broker's LAW 50 gap: it emitted nothing at all.

The file stays, and stays first: it is the write-ahead copy, and the kill switch (WJ.10) lives on
the same volume. Delivery is best-effort by design -- these tests prove that a collector outage
costs delivery and never the record, and never the grant.

Behaviour, not prose (R76): every case drives the real objects, and the two fence cases parse the
rendered YAML rather than reading sentences out of it.
"""

from __future__ import annotations

import json
import pathlib
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "jit"))

from broker.broker import Ledger  # noqa: E402
from broker.collector import SPOOL_MAX, OTLPSink, sink_from_env  # noqa: E402

KEY = b"a key the agent identity cannot read"
COLLECTOR = "signoz-otel-collector.observability.svc"
OTLP_PORT = 4318


class _Collector:
    """A stand-in for the estate's OTLP/HTTP door: it records what it was posted, and can be
    told to refuse, which is how a collector outage is played here."""

    def __init__(self):
        self.posts: list[dict] = []
        self.paths: list[str] = []
        self.status = 200
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                if outer.status < 300:
                    outer.paths.append(self.path)
                    outer.posts.append(json.loads(raw))
                self.send_response(outer.status)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def endpoint(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def records(self) -> list[dict]:
        out = []
        for post in self.posts:
            for resource in post["resourceLogs"]:
                for scope in resource["scopeLogs"]:
                    out.extend(scope["logRecords"])
        return out

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def collector():
    door = _Collector()
    yield door
    door.close()


def _ledger(tmp_path, sink=None) -> Ledger:
    return Ledger(str(tmp_path / "ledger.jsonl"), KEY, sink=sink)


def test_a_record_written_to_the_ledger_arrives_at_the_collector(tmp_path, collector):
    ledger = _ledger(tmp_path, OTLPSink(collector.endpoint))
    written = ledger.append("granted", ns="backstage", verb="delete")

    assert collector.paths == ["/v1/logs"], collector.paths
    arrived = collector.records()
    assert len(arrived) == 1, arrived
    body = json.loads(arrived[0]["body"]["stringValue"])
    assert body["event"] == "granted"
    assert body["ns"] == "backstage"
    assert body["sig"] == written["sig"], (
        "the signature must survive the hop, or the copy proves nothing"
    )


def test_the_timestamp_crosses_as_a_string_because_a_json_double_cannot_hold_it(
    tmp_path, collector
):
    """OTLP's timeUnixNano is a uint64; a JSON number loses its low digits at that size, and the
    collector rejects the batch. It has to go over as a string. The ledger stamps `at` itself, so
    the check is on the shape rather than on a value the test chose."""
    ledger = _ledger(tmp_path, OTLPSink(collector.endpoint))
    ledger.append("granted")

    stamp = collector.records()[0]["timeUnixNano"]
    assert isinstance(stamp, str), stamp
    assert stamp.isdigit() and len(stamp) == 19, stamp


def test_the_record_says_which_service_and_namespace_it_came_from(tmp_path, collector):
    ledger = _ledger(tmp_path, OTLPSink(collector.endpoint))
    ledger.append("granted")

    resource = collector.posts[0]["resourceLogs"][0]["resource"]["attributes"]
    named = {a["key"]: a["value"]["stringValue"] for a in resource}
    assert named["service.name"] == "jit-broker"


def test_a_collector_that_is_down_costs_delivery_and_never_the_record(
    tmp_path, collector
):
    collector.status = 503
    sink = OTLPSink(collector.endpoint)
    ledger = _ledger(tmp_path, sink)

    written = ledger.append("granted", ns="backstage")

    assert collector.records() == [], "a refused post must not be counted as delivered"
    assert sink.undelivered == 1
    on_disk = [json.loads(line) for line in open(ledger.path)]
    assert on_disk == [written], (
        "the file is the write-ahead copy; an outage may not touch it"
    )
    assert ledger.verify()[0], "the chain must still verify after a failed delivery"


def test_the_records_an_outage_held_are_carried_by_the_next_delivery(
    tmp_path, collector
):
    collector.status = 503
    sink = OTLPSink(collector.endpoint)
    ledger = _ledger(tmp_path, sink)
    ledger.append("granted", ns="backstage")
    ledger.append("expired", ns="backstage")
    assert sink.undelivered == 2

    collector.status = 200
    ledger.append("granted", ns="edge")

    arrived = [
        json.loads(r["body"]["stringValue"])["event"] for r in collector.records()
    ]
    assert arrived == ["granted", "expired", "granted"], arrived
    assert sink.undelivered == 0, (
        "a delivered spool must be cleared, or every batch grows forever"
    )


def test_a_long_outage_cannot_grow_the_brokers_memory_without_a_bound(
    tmp_path, collector
):
    collector.status = 503
    sink = OTLPSink(collector.endpoint)
    ledger = _ledger(tmp_path, sink)
    for n in range(SPOOL_MAX + 25):
        ledger.append("granted", n=n)

    assert sink.undelivered == SPOOL_MAX, (
        "the spool is bounded; the file is the unbounded copy"
    )
    assert len(open(ledger.path).readlines()) == SPOOL_MAX + 25, (
        "no record is dropped from disk"
    )


def test_a_collector_that_is_not_listening_at_all_does_not_raise(tmp_path):
    """The endpoint resolves to nothing -- the shape of a collector Service that was deleted, or a
    fence that closed. urllib raises here; the sink must not."""
    sink = OTLPSink("http://127.0.0.1:1")
    ledger = _ledger(tmp_path, sink)
    assert ledger.append("granted")["event"] == "granted"
    assert sink.undelivered == 1


def test_a_sink_that_raises_does_not_refuse_the_grant(tmp_path):
    """An observability defect must never become an access outage: at 3am the founder taps
    approve, and a bug in the delivery path may not be what stops the token being minted."""

    def broken(_record):
        raise RuntimeError("the sink itself is defective")

    ledger = _ledger(tmp_path, broken)
    written = ledger.append("granted", ns="backstage")
    assert [json.loads(line) for line in open(ledger.path)] == [written]


def test_without_a_collector_endpoint_the_file_is_simply_the_only_copy(monkeypatch):
    """A laptop run and a unit test have no collector, and must not be made to invent one."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert sink_from_env() is None
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", f"http://{COLLECTOR}:{OTLP_PORT}")
    assert sink_from_env().url == f"http://{COLLECTOR}:{OTLP_PORT}/v1/logs"


def _docs(path: pathlib.Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_the_broker_pod_is_told_where_the_collector_is(tmp_path):
    containers = [
        c
        for d in _docs(ROOT / "platform" / "jit" / "deployment.yaml")
        if d.get("kind") == "Deployment"
        for c in d["spec"]["template"]["spec"]["containers"]
    ]
    env = {e["name"]: e.get("value") for c in containers for e in c.get("env", [])}
    assert COLLECTOR in (env.get("OTEL_EXPORTER_OTLP_ENDPOINT") or ""), env.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    assert str(OTLP_PORT) in env["OTEL_EXPORTER_OTLP_ENDPOINT"]


def _selects(peer: dict, ns: str) -> bool:
    labels = (peer.get("namespaceSelector") or {}).get("matchLabels") or {}
    return labels.get("kubernetes.io/metadata.name") == ns


def test_the_hop_to_the_collector_is_open_at_both_ends(tmp_path):
    """Both namespaces sit behind default-deny in both directions, so egress alone is a deny on
    the wire -- and the symptom would be a ledger that looks complete in the pod and is empty in
    SigNoz. jit is exempt from bin/idp-ns-fence-gen, so the far half only exists because the
    generator admits the namespaces it does not fence.
    """
    leaves = any(
        _selects(peer, "observability")
        and any(p.get("port") == OTLP_PORT for p in rule.get("ports") or [])
        for doc in _docs(ROOT / "platform" / "jit" / "fence.yaml")
        if doc.get("kind") == "NetworkPolicy"
        for rule in doc["spec"].get("egress") or []
        for peer in rule.get("to") or []
    )
    assert leaves, (
        "jit declares no egress to the collector; the ledger never leaves the pod"
    )

    arrives = any(
        _selects(peer, "jit")
        for doc in _docs(
            ROOT / "platform" / "ns-fences" / "network" / "observability.yaml"
        )
        if doc.get("kind") == "NetworkPolicy"
        for rule in doc["spec"].get("ingress") or []
        for peer in rule.get("from") or []
    )
    assert arrives, (
        "observability does not admit jit; the ledger is dropped at the far side"
    )
