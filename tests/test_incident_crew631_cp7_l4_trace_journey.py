"""crew#631 CP7: the L4 journey. A span accepted by the OTLP door that never lands is the
silent-green class, so the assertion is `returned id == emitted id` through the authenticated
read API, inside 60 s, with a no-key ingest as the negative control. Graded on a fake door that
can be set to accept-and-drop, accept-open, or work."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IDP = os.path.dirname(HERE)
sys.path.insert(0, IDP)
from probes import langfuse as LF  # noqa: E402

TID = "a" * 32


def _door(mode):
    store = {}
    calls = []

    def http(url, auth=None, timeout=20, data=None):
        calls.append((url, auth, data is not None))
        if url.endswith("/api/public/otel/v1/traces"):
            if auth != ("pk", "sk") and mode != "open":
                return 401, '{"message":"Unauthorized"}'
            if mode != "drop":
                span = json.loads(data)["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
                store[span["traceId"]] = span["name"]
            return 207, "{}"
        if "/api/public/traces/" in url:
            if auth != ("pk", "sk"):
                return 401, "{}"
            tid = url.rsplit("/", 1)[1]
            if tid in store:
                return 200, json.dumps({"id": tid, "name": store[tid]})
            return 404, '{"message":"Trace not found"}'
        return 404, ""

    return http, calls


def _clock():
    t = [1000.0]

    def clock():
        return t[0]

    def sleep(s):
        t[0] += s

    return clock, sleep


def test_a_working_door_passes_and_the_ids_match():
    http, calls = _door("ok")
    clock, sleep = _clock()
    out = LF.l4_journey(
        "https://lf",
        "pk",
        "sk",
        TID,
        TID[:16],
        "n",
        http=http,
        sleep=sleep,
        clock=clock,
    )
    assert all(a["ok"] for a in out), out
    assert out[1]["actual"] == TID
    assert any(
        u.endswith("/api/public/otel/v1/traces") and a == ("pk", "sk") and d
        for u, a, d in calls
    )


def test_an_accepted_span_that_never_lands_is_red_inside_the_deadline():
    http, _ = _door("drop")
    clock, sleep = _clock()
    out = LF.l4_journey(
        "https://lf",
        "pk",
        "sk",
        TID,
        TID[:16],
        "n",
        http=http,
        sleep=sleep,
        clock=clock,
    )
    assert out[0]["ok"], "ingest said yes"
    assert not out[1]["ok"] and "not readable within 60s" in out[1]["actual"]
    assert clock() - 1000.0 >= 60


def test_an_open_ingest_door_fails_the_negative_control_only():
    http, _ = _door("open")
    clock, sleep = _clock()
    out = LF.l4_journey(
        "https://lf",
        "pk",
        "sk",
        TID,
        TID[:16],
        "n",
        http=http,
        sleep=sleep,
        clock=clock,
    )
    assert [a["name"] for a in out if not a["ok"]] == [
        "l4.NEGATIVE.no_key_ingest_is_refused"
    ]


def test_the_prover_emits_l4_with_a_fresh_trace_id_per_run():
    src = open(os.path.join(IDP, "bin", "idp-prove")).read()
    assert "LF.l4_journey(" in src and "uuid.uuid4().hex" in src
    doc = LF.otlp_span_document(TID, TID[:16], "n", 1, 2)
    span = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span["traceId"] == TID and span["spanId"] == TID[:16]
