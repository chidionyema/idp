"""The spine's activities: read the status, write the receipt.

Both are plain async functions, so Temporal can run them and a test can call them. Neither
raises: an activity that raises is retried and then fails the workflow, and a failed
workflow is a silent outcome -- the receipt that could not be written is exactly the thing
nobody would hear about. So each returns what happened, and the workflow says it.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from .kube import KubeError, KubeReader
from .observer import aevum_body

# The Aevum server the estate runs (platform/observability/aevum.yaml). The API key is a
# file mount, never an env value: Kyverno's secrets-not-from-env-vars rule, and the same
# shape platform/epistemic-fabric/ingest.yaml already uses.
AEVUM_URL = os.environ.get("AEVUM_URL", "http://aevum.observability.svc:8000")
AEVUM_API_KEY_FILE = os.environ.get(
    "AEVUM_API_KEY_FILE", "/var/run/secrets/aevum/api_key"
)
AEVUM_TIMEOUT_S = 10.0


async def verify_reconciliation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Read the reconciled object's own status and grade it.

    The kind, namespace and name come from the event, so the check is about the object the
    event was about and nothing else.
    """
    kind = str(payload.get("kind") or "")
    namespace = str(payload.get("namespace") or "")
    name = str(payload.get("name") or "")
    if not (kind and namespace and name):
        return {
            "found": False,
            "ready": False,
            "verdict": "unreadable",
            "reason": "IncompleteEvent",
            "message": "the event names no object to verify",
            "revision": "",
        }
    try:
        return KubeReader.from_env().status_of(kind, namespace, name)
    except KubeError as exc:
        return {
            "found": False,
            "ready": False,
            "verdict": "unreadable",
            "reason": "Unreadable",
            "message": str(exc),
            "revision": "",
        }


def _api_key() -> str:
    path = AEVUM_API_KEY_FILE
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return os.environ.get("AEVUM_API_KEY", "")


async def emit_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """Write the receipt into Aevum's ledger.

    The Idempotency-Key header carries the receipt's own digest, so a retried write of the
    same receipt is one receipt, not two.
    """
    body = aevum_body(receipt)
    request = urllib.request.Request(  # noqa: S310 - the address is configured, not user input
        AEVUM_URL.rstrip("/") + "/v1/ingest",
        data=json.dumps(body, sort_keys=True).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    request.add_header("X-Aevum-Key", _api_key())
    request.add_header("Idempotency-Key", str(receipt.get("digest") or ""))
    try:
        # The URL is built from the configured Aevum address, which is http inside the
        # cluster; no user input reaches it.
        with urllib.request.urlopen(request, timeout=AEVUM_TIMEOUT_S) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {"ingested": False, "detail": "aevum said %s" % exc.code, "auditId": ""}
    except urllib.error.URLError as exc:
        return {
            "ingested": False,
            "detail": "aevum unreachable: %s" % exc.reason,
            "auditId": "",
        }
    audit_id = ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            audit_id = str(parsed.get("audit_id") or parsed.get("id") or "")
    except ValueError:
        audit_id = ""
    return {"ingested": True, "detail": "written", "auditId": audit_id}
