"""Langfuse probes (crew#631 CP1): L1 liveness, L2 machine plane, L3 human plane.

Each level proves strictly more than the one below, and says nothing about the one above:
  L1  the process answers; nothing about auth, ever.
  L2  the public API answers an API key. This is validated against the key table in the app and
      never touches the OIDC path, so a green L2 says nothing about whether a person can sign in.
      That gap is the eight hours of 2026-08-29 (crew#626).
  L4  a journey: one OTLP trace is emitted through the ingest door and read back through the
      authenticated API inside 60 s, asserted on `returned id == emitted id`, never on the ingest
      202 (an accepted span that never lands is the silent-green class). Negative control: the same
      span with no key is refused.
  L3  a cold browser handshake through the front door yields a session whose identity is the
      drill user. Asserted on the identity claim, never on a cookie or a 200 (next-auth
      GHSA-v64w-49xw-qq89: a session that exists is not a session that is someone). Paired with a
      negative control: a context holding nothing must get no user, or the gate is open and the
      positive probe is theatre. Every L3 check is these two assertions or it is not a check.
No test id, selector or layout word appears here (LAW 53 / R53).
"""

import base64
import json
import urllib.error
import urllib.request

from probes.verdict import assertion

TIMEOUT_S = 20


def http(url, auth=None, timeout=TIMEOUT_S, data=None, bearer=None):
    """(status, body_text). Redirects are followed; a redirect to the identity domain shows up
    as a 200 HTML sign-in page, which is why nothing below asserts on 200 alone. data (bytes)
    makes it a JSON POST."""
    if not url.startswith("https://"):
        return 0, "refused: only https targets"
    headers = {"Accept": "application/json", "User-Agent": "idp-prove/1"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=data)  # noqa: S310
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")
    if auth:
        req.add_header(
            "Authorization",
            "Basic " + base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode(),
        )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - https URLs built from estate-config, never user input
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # DNS, TLS, timeout: the assertion records the reason
        return 0, f"{type(e).__name__}: {e}"


def _json(body):
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


def l1_liveness(host, get=http):
    """Langfuse serves /api/public/health on the web container. By default it does not include
    the database; ?failIfDatabaseUnavailable=true makes it (vendor docs). Two assertions: the
    status, and that the body parses, so a proxy error page cannot pass as health."""
    status, body = get(f"{host}/api/public/health?failIfDatabaseUnavailable=true")
    doc = _json(body)
    return [
        assertion("l1.health.status", 200, status, status == 200),
        assertion(
            "l1.health.body_is_json",
            "object",
            type(doc).__name__ if doc is not None else body[:80],
            isinstance(doc, dict),
        ),
    ]


def l2_machine(host, public_key, secret_key, get=http):
    """Basic auth, public key as user, secret key as password (vendor docs). The negative control
    is the same call with no key: it must be refused, or L2 is green while the API is open."""
    status, body = get(f"{host}/api/public/projects", auth=(public_key, secret_key))
    doc = _json(body) or {}
    data = doc.get("data") if isinstance(doc, dict) else None
    ok_shape = (
        isinstance(data, list) and len(data) > 0 and isinstance(data[0].get("id"), str)
    )
    nstatus, nbody = get(f"{host}/api/public/projects")
    ndoc = _json(nbody)
    refused = nstatus in (401, 403) or (
        nstatus == 200 and not (isinstance(ndoc, dict) and ndoc.get("data"))
    )
    return [
        assertion("l2.projects.status", 200, status, status == 200),
        assertion(
            "l2.projects.has_project_id",
            "data[0].id is a string",
            f"data={str(data)[:80]}",
            ok_shape,
        ),
        assertion(
            "l2.NEGATIVE.no_key_is_refused",
            "401/403 or no data",
            f"{nstatus} {nbody[:60]}",
            refused,
        ),
    ]


def l3_from_sessions(authed, cold, expected_identity):
    """authed: the /api/auth/session document from the browser that completed the cold handshake.
    cold: the same document from a context holding nothing (None when the door answered no JSON,
    which is the front door refusing). expected_identity: the drill user's email."""
    user = (authed or {}).get("user") if isinstance(authed, dict) else None
    email = (user or {}).get("email") if isinstance(user, dict) else None
    ident_ok = (
        isinstance(email, str)
        and email.strip().lower() == expected_identity.strip().lower()
    )
    cold_user = (cold or {}).get("user") if isinstance(cold, dict) else None
    return [
        assertion(
            "l3.session.identity",
            expected_identity,
            email if email else f"no user in {str(authed)[:80]}",
            ident_ok,
        ),
        assertion(
            "l3.NEGATIVE.cold_context_has_no_user",
            "no user",
            f"user={str(cold_user)[:80]}" if cold_user else "no user",
            not cold_user,
        ),
    ]


def otlp_span_document(trace_id, span_id, name, start_ns, end_ns):
    """The smallest OTLP/JSON ExportTraceServiceRequest: one resource, one scope, one span."""
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "idp-prove"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "idp-prove"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": name,
                                "kind": 1,
                                "startTimeUnixNano": str(start_ns),
                                "endTimeUnixNano": str(end_ns),
                                "attributes": [
                                    {
                                        "key": "langfuse.trace.name",
                                        "value": {"stringValue": name},
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def l4_journey(
    host,
    public_key,
    secret_key,
    trace_id,
    span_id,
    name,
    *,
    http=http,
    sleep=None,
    clock=None,
    deadline_s=60,
    every_s=5,
):
    """Emit one span through the OTLP door (vendor: POST /api/public/otel/v1/traces, Basic auth
    pk:sk, HTTP/JSON), then poll the authenticated read API until the trace with the emitted id
    is returned, inside deadline_s. Three assertions: the ingest answered 2xx; the read-back id
    equals the emitted id (the journey); NEGATIVE: the same document with no key is refused."""
    import time as _t

    sleep = sleep or _t.sleep
    clock = clock or _t.time
    now_ns = int(clock() * 1e9)
    doc = json.dumps(
        otlp_span_document(trace_id, span_id, name, now_ns - 1_000_000, now_ns)
    ).encode()
    auth = (public_key, secret_key)
    istatus, ibody = http(f"{host}/api/public/otel/v1/traces", auth=auth, data=doc)
    found, last = None, ""
    t0 = clock()
    while clock() - t0 < deadline_s:
        rstatus, rbody = http(f"{host}/api/public/traces/{trace_id}", auth=auth)
        rdoc = _json(rbody)
        if rstatus == 200 and isinstance(rdoc, dict) and rdoc.get("id"):
            found = rdoc
            break
        last = f"{rstatus} {rbody[:60]}"
        sleep(every_s)
    returned = (found or {}).get("id")
    nstatus, nbody = http(f"{host}/api/public/otel/v1/traces", data=doc)
    return [
        assertion(
            "l4.otlp.ingest_accepted",
            "2xx",
            f"{istatus} {ibody[:60]}",
            200 <= istatus < 300,
        ),
        assertion(
            "l4.journey.returned_id_equals_emitted_id",
            trace_id,
            returned or f"not readable within {deadline_s}s: {last}",
            returned == trace_id,
        ),
        assertion(
            "l4.NEGATIVE.no_key_ingest_is_refused",
            "401/403",
            f"{nstatus} {nbody[:60]}",
            nstatus in (401, 403),
        ),
    ]
