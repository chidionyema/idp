"""crew#631 CP9, third surface: SigNoz, the telemetry backend. Three layers, each a probe that can FAIL:

L1 liveness  GET /api/v2/dashboards answers at all (any status; the door is graded below).
L2 machine   the same read with the prover's service-account key (header SIGNOZ-API-KEY, role
             signoz-viewer, minted by bin/idp-signoz-key into vault entry signoz-prover) answers
             200 with a JSON object whose `data` is a list.
NEGATIVE     the same read with no key is refused (anything but a 200 JSON list).
L3 human     bin/idp-login-drill's front-door walk to signoz.<zone> (probes/front_door.py).

Vendor facts pinned from the SigNoz repository at the chart's version (v0.138.0,
tests/integration/tests/serviceaccount/02_keys.py and 03_auth.py, read 2026-08-31): a service-account
key rides in the SIGNOZ-API-KEY header and GET /api/v2/dashboards answers 200 to a viewer key.
Every function takes the http callable so tests run against a stub."""

from probes.langfuse import _json, http
from probes.verdict import assertion

DASHBOARDS = "/api/v2/dashboards"
KEY_HEADER = "SIGNOZ-API-KEY"


def _keyed(url, key, *, get):
    return get(url, headers={KEY_HEADER: key})


def _listing(body):
    doc = _json(body)
    return doc, isinstance(doc, dict) and isinstance(doc.get("data"), list)


def l1_liveness(host, get=http):
    status, body = get(f"{host}{DASHBOARDS}")
    return [assertion("l1.signoz.answers", "any status", status, status != 0)]


def l2_machine(host, key, get=http):
    status, body = _keyed(f"{host}{DASHBOARDS}", key, get=get)
    doc, listing = _listing(body)
    return [
        assertion(
            "l2.dashboards.status_200_json",
            "200 and a JSON object",
            f"{status} {type(doc).__name__}",
            status == 200 and isinstance(doc, dict),
        ),
        assertion(
            "l2.dashboards.data_is_a_list",
            "a JSON object whose data is a list",
            f"{type(doc).__name__} {str(body)[:60]}",
            listing,
        ),
    ]


def negative_no_key(host, get=http):
    status, body = get(f"{host}{DASHBOARDS}")
    _, listing = _listing(body)
    return [
        assertion(
            "l2.NEGATIVE.no_key_is_refused",
            "not a 200 JSON list",
            f"{status} {str(body)[:60]}",
            not (status == 200 and listing),
        )
    ]


def probe(host, key, get=http):
    """All three; with no key only L1 and the negative control (the prover marks that BLOCKED)."""
    l2 = l2_machine(host, key, get) if key else []
    return l1_liveness(host, get) + l2 + negative_no_key(host, get)
