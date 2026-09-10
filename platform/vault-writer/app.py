#!/usr/bin/env python3
"""The key ingest door's writer (docs/specs/key-ingest-door-part4.md, part B).

The portal does not talk to OCI. It posts here, and this is the only thing in the estate holding
a vault WRITE grant. Why that indirection exists is in the spec: per-pod workload identity needs
an Enhanced cluster, so a portal pod would inherit the node's dynamic group and get read on every
Operator secret -- decision 0021 says the operator road never widens the customer road.

The rules this file holds, each one a thing the estate has paid for before:

  * The value is read from the body into a local and handed to the writer as one argument. It is
    never logged, never echoed, never returned, never in an error message.
  * The only thing returned about a value is the first 8 hex of its SHA-256, so the person who
    pasted can confirm they pasted the right thing and no reader learns it.
  * `entry` and `key` are matched against the register at REQUEST time (scoping.py), not a list
    baked in at build time, so a row added in a pull request takes effect without a redeploy.
  * The write goes through `bin/idp-vault-put --merge <entry> <key>=<value>` with the value on
    STDIN -- never argv, which is visible to any process on the node.
  * An entry whose register Owner is not `Customer` is a 403. That is the tenant plane refusing
    to reach the control plane, which is the isolation decision 0021 exists to enforce.
  * The failure a caller sees is a 502, never a false success. An unwired or refused write must
    never read as a key that landed.

Standard library only: this runs in the cluster on a slim image and adding a framework to reach
one endpoint would be more surface than the endpoint.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scoping  # noqa: E402  (sibling module; the path insert above is what makes it importable)

logger = logging.getLogger("vault_writer")

REGISTER = pathlib.Path(
    os.environ.get("VAULT_WRITER_REGISTER", "/app/docs/reference/policy/root-trust.md")
)
VAULT_PUT = os.environ.get("VAULT_WRITER_VAULT_PUT", "bin/idp-vault-put")
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
PORT = int(os.environ.get("VAULT_WRITER_PORT", "8080"))

# A JSON body's ceiling. A key is a key; a megabyte of body is not one, and reading it would be
# a memory-cost hole in a process that holds no privilege worth having.
MAX_BODY_BYTES = 64 * 1024


def _sha_prefix(value: str) -> str:
    """The first 8 hex characters of the value's SHA-256. The only fact about a value we return."""
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def _emit_span(entry: str, key: str, store: str, sha_prefix: str, tenant: str) -> None:
    """One span per submission to the central collector (LAW 50), carrying no value.

    An unreachable collector is not allowed to fail a write that already happened: the same rule
    the rest of the estate follows, and it is why this is best-effort and logs only.
    """
    if not OTLP_ENDPOINT:
        return
    try:
        body = json.dumps(
            {
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": "vault-writer"}}
                            ]
                        },
                        "scopeSpans": [
                            {
                                "scope": {"name": "vault-writer"},
                                "spans": [
                                    {
                                        "name": "credential.ingest",
                                        "kind": 1,
                                        # nanoseconds as a decimal string, per OTLP JSON
                                        "startTimeUnixNano": str(int(_now_ns())),
                                        "endTimeUnixNano": str(int(_now_ns())),
                                        "attributes": [
                                            {"key": "entry", "value": {"stringValue": entry}},
                                            {"key": "key", "value": {"stringValue": key}},
                                            {"key": "store", "value": {"stringValue": store}},
                                            {
                                                "key": "sha256_prefix",
                                                "value": {"stringValue": sha_prefix},
                                            },
                                            {"key": "tenant", "value": {"stringValue": tenant}},
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ).encode()
        req = urllib.request.Request(  # noqa: S310  (scheme is built from our own env)
            OTLP_ENDPOINT.rstrip("/") + "/v1/traces",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5):  # noqa: S310
            pass
    except Exception as e:  # a collector outage is not a failed write
        logger.warning("span not delivered: %s", type(e).__name__)


def _now_ns() -> int:
    import time

    return int(time.time() * 1_000_000_000)


def write_to_vault(entry: str, key: str, value: str) -> None:
    """One write, value on stdin, never argv.

    Raises on any failure so the caller answers 502. The alternative -- swallowing it and
    answering 200 -- is the false success this whole door exists inside an estate that keeps
    paying for exactly that kind of quiet.
    """
    argv = [VAULT_PUT, "--merge", entry, f"{key}=-"]
    proc = subprocess.run(  # noqa: S603  (fixed argv; the value is not in it)
        argv,
        input=value.encode(),
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        # stderr may name the entry or the vault's own words, never the value: idp-vault-put
        # prints key names only (its own contract). Truncated so a wall of text cannot become
        # the response body.
        detail = proc.stderr.decode(errors="replace").strip()[:200]
        raise RuntimeError(f"vault write refused ({proc.returncode}): {detail}")


class Handler(BaseHTTPRequestHandler):
    server_version = "vault-writer"

    def log_message(self, fmt: str, *args) -> None:
        # The default logging writes the request line, which for this endpoint carries no value
        # because the value is in the body -- but the body is never read into a log either way.
        logger.info("%s", fmt % args)

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802  (BaseHTTPRequestHandler's own naming)
        if self.path.rstrip("/") != "/write":
            self._send(404, {"error": "no such endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._send(400, {"error": "bad content-length"})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(400, {"error": "body missing or too large"})
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode())
        except Exception:
            self._send(400, {"error": "body is not JSON"})
            return
        if not isinstance(payload, dict):
            self._send(400, {"error": "body is not an object"})
            return

        entry = str(payload.get("entry") or "").strip()
        key = str(payload.get("key") or "").strip()
        value = payload.get("value")
        store = str(payload.get("store") or "estate-vault").strip()

        if not entry or not key:
            self._send(400, {"error": "entry and key are required"})
            return
        if not isinstance(value, str) or not value:
            self._send(400, {"error": "value is required"})
            return

        # The allow-list. A non-Customer Owner is 403, not 400: the caller is understood and
        # refused, which is a different statement from a malformed request.
        try:
            allowed = scoping.entry_is_customer_owned(REGISTER, entry)
        except Exception as e:
            # A register we cannot read is blindness, and blindness is never a pass.
            logger.error("register unreadable: %s", type(e).__name__)
            self._send(502, {"error": "register unreadable"})
            return
        if not allowed:
            logger.warning("refused entry=%s key=%s (not Customer-owned)", entry, key)
            self._send(403, {"error": "entry is not owned by a customer"})
            return

        sha_prefix = _sha_prefix(value)
        try:
            write_to_vault(entry, key, value)
        except Exception as e:
            logger.error("write failed entry=%s key=%s: %s", entry, key, e)
            self._send(502, {"error": "write to the vault store failed"})
            return
        finally:
            # Drop the reference as early as the language allows. Not a guarantee, and not
            # claimed as one: it is the cheapest thing that reduces the window.
            value = ""

        _emit_span(entry, key, store, sha_prefix, "estate")
        logger.info("wrote entry=%s key=%s sha=%s", entry, key, sha_prefix)
        self._send(200, {"entry": entry, "key": key, "sha256_prefix": sha_prefix, "store": store})


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logger.info("vault-writer listening on :%d (register=%s)", PORT, REGISTER)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())
