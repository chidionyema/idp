"""WJ.7: the signed record leaves the pod.

The founder's item is one sentence -- the ledger belongs on the collector -- and the reason is
one sentence too. Until now every line the broker wrote lived in `/var/lib/jit/ledger.jsonl` on
a 1Gi ReadWriteOnce volume attached to one node. Lose that node and the only account of who was
granted write access to this estate, and when, and for what reason, goes with it. An audit
trail with a single point of failure is a trail somebody can end by choosing the right afternoon.

So each record is now also shipped to the collector every other workload in this estate already
reports to (LAW 50, LAW 43: no second sink, no second store). The file stays -- it is what
`/healthz` verifies the hash chain of, and it is the write-ahead copy that survives the
collector being down -- but it is no longer the only place the record exists.

Stdlib only, and deliberately: the same shape as platform/otto-gateway's reconciler and
platform/observability/telemetry-coverage.yaml. One POST of OTLP/HTTP JSON, no SDK, no pip
install, no extra layer on an image whose whole point is that it is small and auditable.

The sink never raises into the broker. A collector that is down must not stop the founder
approving a restart at 3am -- the record is already durable in the file by the time this runs,
and undelivered records are held and retried on the next append, so the chain that arrives is
complete or visibly gapped, never quietly short.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

#: OTLP/HTTP wants nanoseconds since the epoch, as a string, because the field is a uint64 and
#: JSON numbers are doubles -- a float would lose the last three digits of a timestamp.
_NANOS = 1_000_000_000

#: How many undelivered records to hold. The broker writes a handful of lines a day; anything
#: past this is an outage long enough that the file, not this buffer, is the answer.
SPOOL_MAX = 256


def _attr(key: str, value: object) -> dict:
    """One OTLP attribute. Everything is carried as a string: the values here are hashes,
    signatures, request ids and grant names, and a query that has to know whether `at` was
    ingested as a double is a query nobody writes correctly the first time."""
    return {"key": key, "value": {"stringValue": str(value)}}


class OTLPSink:
    """Ships one signed ledger record to the estate collector as an OTLP log record.

    The whole record travels twice on purpose: as the body, verbatim, so a reader can re-run
    `Ledger.verify()`'s arithmetic over what arrived; and as attributes, so the record is
    queryable in SigNoz without parsing the body. `this` and `sig` are what make the copy
    self-defending -- a record altered between here and the collector fails the same HMAC check
    the file's copy does.
    """

    def __init__(
        self, endpoint: str, service: str = "jit-broker", timeout: float = 5.0
    ):
        # SigNoz's collector takes OTLP/HTTP on 4318 and the estate passes the base URL in
        # OTEL_EXPORTER_OTLP_ENDPOINT, the same variable litellm, the MCP servers and the
        # k8s-infra chart all read. The signal path is appended here rather than configured,
        # because a base URL that already ends in /v1/logs is the misconfiguration that makes
        # a collector answer 404 to everything and look like a fence problem.
        self.url = endpoint.rstrip("/") + "/v1/logs"
        self.service = service
        self.timeout = timeout
        self._spool: list[dict] = []

    def _envelope(self, records: list[dict]) -> dict:
        return {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": [
                            _attr("service.name", self.service),
                            # The namespace is what tells SigNoz's own views this belongs to
                            # the estate's platform rather than a product workload.
                            _attr(
                                "k8s.namespace.name",
                                os.environ.get("POD_NAMESPACE", "jit"),
                            ),
                        ]
                    },
                    "scopeLogs": [
                        {
                            "scope": {"name": "jit.ledger"},
                            "logRecords": [self._record(r) for r in records],
                        }
                    ],
                }
            ]
        }

    def _record(self, body: dict) -> dict:
        at = float(body.get("at", 0.0))
        # Every key of the record becomes an attribute, so a grant name, a request id or the
        # chain hash is a column in SigNoz rather than something to grep the body for.
        attributes = [
            _attr(k, v)
            for k, v in sorted(body.items())
            if not isinstance(v, (dict, list))
        ]
        return {
            "timeUnixNano": str(int(at * _NANOS)),
            # An access-control decision is never debug, and never an error either: it is the
            # thing that happened. INFO is what a retention policy keeps.
            "severityNumber": 9,
            "severityText": "INFO",
            "body": {"stringValue": json.dumps(body, sort_keys=True)},
            "attributes": attributes,
        }

    def __call__(self, record: dict) -> bool:
        """Deliver `record`, and any earlier record that has not been delivered yet.

        Returns whether the collector took them. Never raises: the caller has already made the
        record durable, and a broker that refuses to grant access because a metrics pipeline is
        unreachable has turned an observability outage into an access outage.
        """
        self._spool.append(record)
        # Oldest first: the chain only reads correctly in order, and dropping from the front
        # keeps the newest records -- the ones an incident is about -- when a long outage
        # overflows the buffer.
        if len(self._spool) > SPOOL_MAX:
            self._spool = self._spool[-SPOOL_MAX:]
        try:
            payload = json.dumps(self._envelope(self._spool)).encode()
            request = urllib.request.Request(  # noqa: S310 - the endpoint is the cluster's own collector
                self.url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as answer:  # noqa: S310
                if answer.status >= 300:
                    return False
        except (urllib.error.URLError, OSError, ValueError):
            return False
        self._spool.clear()
        return True

    @property
    def undelivered(self) -> int:
        return len(self._spool)


def sink_from_env() -> OTLPSink | None:
    """None when the estate has not told this pod where the collector is, which is how the
    unit tests and a laptop run get a broker that writes its file and nothing else."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    return OTLPSink(endpoint) if endpoint else None
