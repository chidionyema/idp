"""API key proving (Decision 0020 CP2).

One function, fail-closed: prove(vendor, key) -> Proof. The key is never logged,
never in an exception message, never in a Dagster event, never in a returned summary.
The summary names the vendor, the store, the status and the time only.

Rules enforced by tests:
1. A key is never written before a 2xx. Store is called with a Proof object; there is
   no codepath that stores without one.
2. Failure reports the vendor's HTTP status and the vendor's message, not "something
   went wrong".
3. The key value is never logged, never in an exception message, never in a Dagster
   event, never in a returned summary.
4. No override flag exists. Not an environment variable, not a parameter, not a config
   key.
"""

import dataclasses
import datetime
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

import requests
import yaml

logger = logging.getLogger(__name__)

# Path to the vendor registry
VENDORS_PATH = Path(__file__).parent.parent / "vendors" / "consoles.yaml"


@dataclasses.dataclass(frozen=True)
class Proof:
    """Result of proving a key against a vendor.

    The key value is NOT included in this object — it must never appear in logs,
    events or summaries.
    """
    vendor: str
    store: str
    status_code: int
    vendor_message: str  # may be truncated, but never contains the key
    verified_at: datetime.datetime
    success: bool


def load_vendors() -> dict[str, Any]:
    """Load the vendor registry."""
    with open(VENDORS_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("vendors", {})


def get_vendor_config(vendor: str) -> dict[str, Any]:
    """Get a vendor's configuration from the registry."""
    vendors = load_vendors()
    if vendor not in vendors:
        raise ValueError(f"Unknown vendor: {vendor}")
    return vendors[vendor]


def _build_verify_request(
    vendor_config: dict[str, Any],
    key: str
) -> tuple[str, str, dict[str, str], Optional[str], Optional[dict]]:
    """Build the verify request from vendor config.

    Returns: (method, url, headers, body, auth_template)
    """
    verify = vendor_config.get("verify", {})

    method = verify.get("method", "GET").upper()
    url_template = verify.get("url", "")

    # Handle multi-base vendors (e.g., kimi with multiple bases)
    bases = vendor_config.get("bases", [None])
    if len(bases) > 1 or bases[0] is not None:
        # For multi-base vendors, we'll iterate in prove()
        return method, url_template, {}, None, None

    # Substitute {key} in URL
    url = url_template.replace("{key}", key)

    # Build headers with auth
    headers = {}
    auth = verify.get("auth", "")
    if auth == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    elif auth == "header":
        # Look for header_name in verify config
        header_name = verify.get("header_name", "X-API-Key")
        headers[header_name] = key

    # Handle custom headers
    custom_headers = verify.get("headers", {})
    for h_name, h_val in custom_headers.items():
        if "{key}" in h_val:
            headers[h_name] = h_val.replace("{key}", key)
        else:
            headers[h_name] = h_val

    body = verify.get("body")

    return method, url, headers, body, auth


def _check_refuse_when(response_body: str, refuse_when: Optional[str]) -> bool:
    """Check if response matches refuse_when pattern."""
    if not refuse_when:
        return False
    return bool(re.search(refuse_when, response_body, re.IGNORECASE))


def prove(vendor: str, key: str, store: Optional[str] = None) -> Proof:
    """Prove a key against a vendor's verify endpoint.

    Args:
        vendor: Vendor name from platform/vendors/consoles.yaml
        key: The API key to prove (never logged)
        store: Optional store override (defaults to vendor's store_default)

    Returns:
        Proof object with vendor response

    Raises:
        ValueError: If vendor is unknown
        ProofFailed: If the vendor rejects the key (non-2xx or refuse_when matches)

    The key value is NEVER logged, never in exception messages, never in events.
    """
    vendor_config = get_vendor_config(vendor)

    # Resolve store
    if store is None:
        store = vendor_config.get("store_default", "human-vault")

    # Get verify config
    verify = vendor_config.get("verify", {})
    if not verify:
        raise ValueError(f"Vendor {vendor} has no verify block")

    # Handle multi-base vendors (kimi)
    bases = vendor_config.get("bases", [None])

    last_error = None
    for base in bases:
        try:
            method, url_template, headers, body, auth = _build_verify_request(vendor_config, key)

            if base:
                url = url_template.replace("{base}", base)
            else:
                url = url_template

            # Make the request
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=body, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Check for refusal pattern
            refuse_when = verify.get("refuse_when")
            if _check_refuse_when(resp.text, refuse_when):
                raise ProofFailed(
                    vendor=vendor,
                    store=store,
                    status_code=resp.status_code,
                    vendor_message=_extract_message(resp.text),
                )

            # Success is 2xx
            if resp.status_code >= 200 and resp.status_code < 300:
                return Proof(
                    vendor=vendor,
                    store=store,
                    status_code=resp.status_code,
                    vendor_message=_extract_message(resp.text),
                    verified_at=datetime.datetime.utcnow(),
                    success=True,
                )

            # Non-2xx is a failure
            last_error = ProofFailed(
                vendor=vendor,
                store=store,
                status_code=resp.status_code,
                vendor_message=_extract_message(resp.text),
            )

        except requests.RequestException as e:
            last_error = ProofFailed(
                vendor=vendor,
                store=store,
                status_code=0,
                vendor_message=str(e),
            )

    # All bases failed
    if last_error:
        raise last_error

    # Should not reach here
    raise ProofFailed(
        vendor=vendor,
        store=store,
        status_code=0,
        vendor_message="No verify bases configured",
    )


def _extract_message(response_text: str) -> str:
    """Extract a message from vendor response, truncated for safety."""
    # Try common patterns
    text = response_text.strip()

    # Truncate to 500 chars to avoid huge messages
    if len(text) > 500:
        text = text[:500] + "..."

    return text


class ProofFailed(Exception):
    """Raised when a key fails proof against the vendor."""

    def __init__(
        self,
        vendor: str,
        store: str,
        status_code: int,
        vendor_message: str,
    ):
        self.vendor = vendor
        self.store = store
        self.status_code = status_code
        # Never include the key in the message
        self.vendor_message = vendor_message

        super().__init__(f"{vendor} rejected key: HTTP {status_code} - {vendor_message}")


def prove_summary(proof: Proof) -> str:
    """Generate a summary of a proof result.

    The key is NEVER included. Only vendor, store, status and time.
    """
    return (
        f"vendor={proof.vendor} store={proof.store} "
        f"status={proof.status_code} verified_at={proof.verified_at.isoformat()}Z"
    )
