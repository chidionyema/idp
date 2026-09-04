"""Proving a vendor API key (decision 0020, part B).

One function, and every road into the estate ends at it: `prove(vendor, key)` asks the
vendor itself whether the key works, using that vendor's own row in
`platform/vendors/consoles.yaml`. A 2xx returns a `Proof`; anything else raises. There is
no code path that stores an unproved key and no flag that turns the check off.

The key value never leaves this module. It goes into the request and nowhere else: not
into a log line, not into an exception message, not into the summary the operator reads.
Two vendors make that harder than it looks -- Gemini carries the key in the query string,
so a network error's own message contains it -- so every string that escapes this module
passes through `redact()` first.

A credential is not always one string. Two rows in the registry are pairs -- a Telegram
bot token with the chat it must reach, a Google OAuth client id with its secret -- and
their verify templates name those fields rather than `{key}`. `prove()` takes either a
string or a mapping of field name to value, and both are redacted the same way.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests
import yaml

VENDORS_PATH = Path(__file__).resolve().parent.parent / "vendors" / "consoles.yaml"

REDACTED = "[redacted]"
_TIMEOUT_SECONDS = 30
_MESSAGE_LIMIT = 500


@dataclasses.dataclass(frozen=True)
class Proof:
    """A vendor's own confirmation that a key works. Carries no key."""

    vendor: str
    store: str
    status_code: int
    vendor_message: str
    verified_at: datetime.datetime


class ProofFailed(Exception):
    """The vendor refused the key, or could not be reached to ask."""

    def __init__(self, vendor: str, store: str, status_code: int, vendor_message: str):
        self.vendor = vendor
        self.store = store
        self.status_code = status_code
        self.vendor_message = vendor_message
        where = f"HTTP {status_code}" if status_code else "no answer"
        super().__init__(f"{vendor} refused the key: {where} - {vendor_message}")


def redact(text: str, key: str | Mapping[str, str]) -> str:
    """Remove every form of the credential from a string about to escape this module.

    A vendor's error body can echo the key, and a requests exception carries the URL --
    which for Gemini is the key. Both the raw value and its percent-encoded form are
    replaced, for every field of a paired credential. A value shorter than eight
    characters is not a secret worth trusting, and substituting it would mangle
    unrelated text, so it is left alone.
    """
    out = text
    for value in _credential(key).values():
        if not value or len(value) < 8:
            continue
        out = out.replace(value, REDACTED)
        encoded = requests.utils.quote(value, safe="")
        if encoded != value:
            out = out.replace(encoded, REDACTED)
    return out


def _credential(key: str | Mapping[str, str]) -> dict[str, str]:
    """One string is the field `key`; a mapping is already the fields."""
    if isinstance(key, Mapping):
        return {str(name): str(value) for name, value in key.items()}
    return {"key": str(key)}


def required_fields(config: dict[str, Any]) -> list[str]:
    """The credential fields this vendor's own verify templates ask for.

    Read from the row, not from a list kept beside it, so a registry row that adds a
    field cannot get out of step with the code that fills it.
    """
    verify = config.get("verify") or {}
    text = " ".join(
        [str(verify.get("url", "")), str(verify.get("body") or "")]
        + [str(v) for v in (verify.get("headers") or {}).values()]
    )
    seen: list[str] = []
    for name in re.findall(r"{([A-Za-z_][A-Za-z0-9_]*)}", text):
        if name != "base" and name not in seen:
            seen.append(name)
    return seen


def _fill(template: str, fields: Mapping[str, str]) -> str:
    for name, value in fields.items():
        template = template.replace("{" + name + "}", value)
    # The Google row's redirect URI carries ${ESTATE_ZONE}; the environment owns it.
    return os.path.expandvars(template)


def load_vendors() -> dict[str, Any]:
    with open(VENDORS_PATH) as handle:
        return yaml.safe_load(handle).get("vendors", {})


def vendor_config(vendor: str) -> dict[str, Any]:
    vendors = load_vendors()
    if vendor not in vendors:
        raise ValueError(f"Unknown vendor: {vendor}")
    return vendors[vendor]


def resolve_store(config: dict[str, Any], store: str | None = None) -> str:
    """The operator's choice wins, then the vendor's default, then the human store."""
    return store or config.get("store_default") or "human-vault"


def build_request(
    config: dict[str, Any], key: str | Mapping[str, str], base: str | None = None
) -> dict[str, Any]:
    """Turn a vendor row plus a key into the request that asks the vendor about it.

    Every vendor takes the same path through here, including the multi-base ones: a
    vendor whose row lists bases still needs its authorization header, and an earlier
    version of this function returned an empty header map for exactly those vendors,
    which made a perfectly good Kimi key answer 401 forever.
    """
    verify = config.get("verify", {})
    method = verify.get("method", "GET").upper()
    fields = _credential(key)

    url = verify.get("url", "")
    if base:
        url = url.replace("{base}", base)
    url = _fill(url, fields)

    headers: dict[str, str] = {}
    auth = verify.get("auth")
    single = fields.get("key", "")
    if auth == "bearer":
        headers["Authorization"] = f"Bearer {single}"
    elif auth == "header":
        headers[verify.get("header_name", "X-API-Key")] = single
    for name, value in (verify.get("headers") or {}).items():
        headers[name] = _fill(str(value), fields)

    body = verify.get("body")
    if isinstance(body, str):
        body = _fill(body, fields)

    return {"method": method, "url": url, "headers": headers, "body": body}


def _send(request: dict[str, Any]) -> requests.Response:
    """Send it, respecting what the registry actually holds.

    A `body:` in the registry is a JSON *string*. Handing that to `requests(json=...)`
    posts a quoted string rather than an object, which every vendor rejects, so a string
    body is parsed when it is JSON and passed through as data when it is not.
    """
    method, url, headers = request["method"], request["url"], request["headers"]
    body = request["body"]

    if method == "GET":
        return requests.get(url, headers=headers, timeout=_TIMEOUT_SECONDS)
    if method != "POST":
        raise ValueError(f"Unsupported verify method: {method}")

    if body is None:
        return requests.post(url, headers=headers, timeout=_TIMEOUT_SECONDS)
    if isinstance(body, str):
        try:
            return requests.post(
                url, headers=headers, json=json.loads(body), timeout=_TIMEOUT_SECONDS
            )
        except json.JSONDecodeError:
            return requests.post(
                url, headers=headers, data=body, timeout=_TIMEOUT_SECONDS
            )
    return requests.post(url, headers=headers, json=body, timeout=_TIMEOUT_SECONDS)


def _message(text: str, key: str | Mapping[str, str]) -> str:
    text = redact(text.strip(), key)
    return text[:_MESSAGE_LIMIT] + "..." if len(text) > _MESSAGE_LIMIT else text


def prove(vendor: str, key: str | Mapping[str, str], store: str | None = None) -> Proof:
    """Ask the vendor whether this key works. Return a Proof, or raise.

    A vendor whose row lists several bases is tried at each in turn: the first 2xx is the
    proof, and if none answers, the last failure is raised. A vendor whose row asks for
    several fields takes a mapping, and is refused before any request goes out if a field
    is missing -- a half-filled template would ask the vendor a question about nothing and
    read its "no" as a bad credential.
    """
    config = vendor_config(vendor)
    resolved_store = resolve_store(config, store)
    verify = config.get("verify")
    if not verify:
        raise ValueError(
            f"Vendor {vendor} has no verify block, so no key can be proved"
        )

    fields = _credential(key)
    missing = [name for name in required_fields(config) if not fields.get(name)]
    if missing:
        raise ValueError(
            f"{vendor} is proved with {', '.join(required_fields(config))}; missing: {', '.join(missing)}"
        )

    refuse_when = verify.get("refuse_when")
    bases: list[str | None] = list(config.get("bases") or [None])
    failure: ProofFailed | None = None

    for base in bases:
        request = build_request(config, key, base)
        try:
            response = _send(request)
        except requests.RequestException as exc:
            # The exception text carries the URL, and for Gemini the URL carries the key.
            failure = ProofFailed(vendor, resolved_store, 0, _message(str(exc), key))
            continue

        message = _message(response.text or "", key)

        if refuse_when and re.search(refuse_when, response.text or "", re.IGNORECASE):
            failure = ProofFailed(vendor, resolved_store, response.status_code, message)
            continue

        if 200 <= response.status_code < 300:
            return Proof(
                vendor=vendor,
                store=resolved_store,
                status_code=response.status_code,
                vendor_message=message,
                verified_at=datetime.datetime.now(datetime.timezone.utc),
            )

        failure = ProofFailed(vendor, resolved_store, response.status_code, message)

    raise failure or ProofFailed(
        vendor, resolved_store, 0, "the vendor row lists nowhere to ask"
    )


def summary(proof: Proof) -> str:
    """What the operator reads. Names the vendor, the store, the status and the time."""
    return (
        f"{proof.vendor} confirmed the key at {proof.verified_at.isoformat()} "
        f"(HTTP {proof.status_code}); it is kept in {proof.store}"
    )
