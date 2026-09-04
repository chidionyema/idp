#!/usr/bin/env python3
"""The warden job: proves every vendor key and publishes metrics.

For every vendor in platform/vendors/consoles.yaml that has a verify: block, this script:
1. Reads the key from the environment (using the secret name from the vendor row)
2. Calls prove() to ask the vendor whether the key works
3. Publishes two Prometheus gauges per vendor:
   - estate_vendor_key_valid{vendor} = 1|0
   - estate_vendor_key_age_days{vendor} = days since rotation_period started

A ProofFailed is recorded as 0, never a crash. The key value never reaches stdout —
use prove.summary() and prove.redact() for any output.

Metrics are pushed to the Prometheus pushgateway. The address is configured via
PUSH_GATEWAY_URL environment variable (defaults to the in-cluster address).
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

# Add platform to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from warden import prove as warden

# Default in-cluster pushgateway address
DEFAULT_PUSH_GATEWAY = "http://prometheus-pushgateway.monitoring.svc.cluster.local:9091"
PUSH_GATEWAY_URL = os.environ.get("PUSH_GATEWAY_URL", DEFAULT_PUSH_GATEWAY)
JOB_NAME = "api-key-warden"


def rotation_days(config: dict) -> int | None:
    """Days from the rotation period, or None if not set."""
    rotation = config.get("rotation")
    if not rotation:
        return None
    # rotation can be "programmatic" or "assisted" - both have rotation info
    # The rotation block in the row has rotation_period_days
    # For now, return None as rotation_period_days isn't in the row format yet
    return None


def key_age_days(config: dict) -> int | None:
    """Calculate key age from rotation period, or None if not applicable."""
    # TODO: This requires tracking when the key was last rotated/created
    # For now, return None - the gauge will not be emitted if None
    return None


def load_vendors() -> dict[str, dict]:
    """Load vendor configurations from the registry."""
    return warden.load_vendors()


def env_key(secret_name: str) -> str | None:
    """Read a secret from the environment, or None if not set."""
    return os.environ.get(secret_name)


def vendor_has_key(config: dict) -> bool:
    """Check if vendor has a key we can prove.

    A vendor has a key if it has either:
    - A top-level secret field
    - A pair: true (which means it needs multiple fields)
    """
    if config.get("secret"):
        return True
    if config.get("pair"):
        # Paired credentials need special handling - skip for now
        return False
    return False


def publish_metrics(results: list[dict]) -> None:
    """Push metrics to Prometheus pushgateway."""
    registry = CollectorRegistry()

    valid_gauge = Gauge(
        "estate_vendor_key_valid",
        "Whether the vendor key is currently valid (1) or not (0)",
        ["vendor", "store"],
        registry=registry,
    )

    age_gauge = Gauge(
        "estate_vendor_key_age_days",
        "Days since the key was last rotated",
        ["vendor", "store"],
        registry=registry,
    )

    checked_gauge = Gauge(
        "estate_vendor_key_checked_timestamp",
        "Unix timestamp when the key was last checked",
        ["vendor"],
        registry=registry,
    )

    now = datetime.datetime.now(datetime.timezone.utc).timestamp()

    for result in results:
        vendor = result["vendor"]
        store = result["store"]
        is_valid = 1 if result["valid"] else 0

        valid_gauge.labels(vendor=vendor, store=store).set(is_valid)
        checked_gauge.labels(vendor=vendor).set(now)

        age_days = result.get("age_days")
        if age_days is not None:
            age_gauge.labels(vendor=vendor, store=store).set(age_days)

    # Push to gateway
    try:
        push_to_gateway(PUSH_GATEWAY_URL, job=JOB_NAME, registry=registry)
    except Exception as e:
        # Log the error but don't crash - metrics are secondary to the run completing
        print(f"WARNING: failed to push metrics: {e}", file=sys.stderr)


def run_warden() -> int:
    """Run the warden job for all vendors.

    Returns exit code 0 even if some keys fail - we record failure as gauge=0.
    """
    vendors = load_vendors()
    results = []

    for vendor_name, config in vendors.items():
        verify = config.get("verify")
        if not verify:
            continue  # Skip vendors without verification

        # Skip vendors without a provable key (e.g., paired credentials)
        if not vendor_has_key(config):
            continue

        secret_name = config.get("secret")

        key = env_key(secret_name)
        if not key:
            # No key in environment - record as invalid
            results.append(
                {
                    "vendor": vendor_name,
                    "store": config.get("store_default", "unknown"),
                    "valid": False,
                    "age_days": None,
                    "error": "no key in environment",
                }
            )
            continue

        try:
            proof = warden.prove(vendor_name, key)
            results.append(
                {
                    "vendor": vendor_name,
                    "store": proof.store,
                    "valid": True,
                    "age_days": key_age_days(config),
                    "summary": warden.summary(proof),
                }
            )
        except warden.ProofFailed as e:
            # Record failure as invalid (gauge = 0), don't crash
            # Redact the key from the error message
            results.append(
                {
                    "vendor": vendor_name,
                    "store": e.store,
                    "valid": False,
                    "age_days": None,
                    "error": warden.redact(str(e), key),
                }
            )
        except Exception as e:
            # Other errors - still record as invalid
            results.append(
                {
                    "vendor": vendor_name,
                    "store": config.get("store_default", "unknown"),
                    "valid": False,
                    "age_days": None,
                    "error": warden.redact(str(e), key),
                }
            )

    # Push metrics
    publish_metrics(results)

    # Print summary (no key values)
    print(f"Warden run complete: {len(results)} vendors checked")
    valid_count = sum(1 for r in results if r["valid"])
    print(f"Valid: {valid_count}, Invalid: {len(results) - valid_count}")

    for result in results:
        status = "VALID" if result["valid"] else "INVALID"
        print(f"  {result['vendor']}: {status}")
        if "summary" in result:
            print(f"    {result['summary']}")
        if "error" in result:
            print(f"    {result['error']}")

    # Exit 0 regardless of results - we recorded failures as gauge=0
    return 0


if __name__ == "__main__":
    sys.exit(run_warden())
