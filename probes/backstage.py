"""crew#631 CP9, first surface: the catalogue. Three layers, each a probe that can FAIL:

L1 liveness  GET /api/catalog/entities?limit=1 answers at all (any status; the door is graded below).
L2 machine   the same read with the prover's Bearer token (backend.auth.externalAccess static,
             backstage/app-config.container.yaml) returns a JSON list whose first row has a `kind`.
NEGATIVE     the same read with no token is refused (401/403 or a non-JSON sign-in page).
L3 human     the login drill's entities stage (bin/idp-login-drill) already grades the signed-in read.

Every function takes the http callable so tests run against a stub and mutations
(probes/mutations.py) can break each door."""

from probes.langfuse import _json, http
from probes.verdict import assertion

ENTITIES = "/api/catalog/entities?limit=1"


def _bearer(url, token, *, get):
    return get(url, bearer=token)


def l1_liveness(host, get=http):
    status, body = get(f"{host}{ENTITIES}")
    return [assertion("l1.catalogue.answers", "any status", status, status != 0)]


def l2_machine(host, token, get=http):
    status, body = _bearer(f"{host}{ENTITIES}", token, get=get)
    doc = _json(body)
    first = doc[0] if isinstance(doc, list) and doc else None
    return [
        assertion("l2.entities.status", 200, status, status == 200),
        assertion(
            "l2.entities.first_row_has_kind",
            "a JSON list whose first row names a kind",
            f"{type(doc).__name__} {str(body)[:60]}",
            isinstance(first, dict) and bool(first.get("kind")),
        ),
    ]


def negative_no_token(host, get=http):
    status, body = get(f"{host}{ENTITIES}")
    doc = _json(body)
    open_door = status == 200 and isinstance(doc, list)
    return [
        assertion(
            "l2.NEGATIVE.no_token_is_refused",
            "not a 200 JSON list",
            f"{status} {str(body)[:60]}",
            not open_door,
        )
    ]


def probe(host, token, get=http):
    return (
        l1_liveness(host, get)
        + l2_machine(host, token, get)
        + negative_no_token(host, get)
    )
