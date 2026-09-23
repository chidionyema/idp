#!/usr/bin/env python3
"""The warden job: proves every vendor key and publishes metrics.

For every vendor in platform/vendors/consoles.yaml that has a verify: block and is provable
with a single credential (required_fields(config) == ["key"]; a paired credential such as
Telegram's bot+chat or Google's client id+secret needs a Mapping this job does not build),
this script proves every field the vendor's own targets: list names -- not just the seed
field -- so a pool with several independent keys (groq, cerebras, sambanova) gets a result
per key, not one result for the pool.

The key is never read from an environment variable: Kyverno's secrets-not-from-env-vars
policy (platform/edge/kyverno-secrets-policy.yaml) exists because an env var secret ends up
in log output and forwarding tools. Instead, each field is read from a mounted file at
WARDEN_SECRETS_DIR/<vendor>/<field> -- the vendor-bridge chart (platform/vendors/templates)
generates a human-<vendor> Secret with exactly those files, from consoles.yaml's own
`targets: [{ns: dagster, field, bw}]` rows, and scheduler/estate_scheduler/definitions.py
mounts it into the launched run for this one job only.

For every proved field this script publishes Prometheus gauges:
  - estate_vendor_key_valid{vendor, field, store} = 1|0
  - estate_vendor_key_age_days{vendor, field, store} = days since rotation started
  - estate_vendor_key_checked_timestamp{vendor, field} = unix time of the check

A ProofFailed is recorded as 0, never a crash. The key value never reaches stdout --
use prove.summary() and prove.redact() for any output.

Metrics are pushed to the Prometheus pushgateway. The address is configured via the
PUSH_GATEWAY_URL environment variable (defaults to the in-cluster address) -- a URL is
config, not a credential, so it is not subject to the same rule.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

# No sys.path insert here: the only real invocation is `python -m warden.warden` with
# PYTHONPATH=/app (warden.Dockerfile), which already makes `warden` importable. A prior
# self-insert of platform/ onto sys.path had no matching removal, so any test process that
# imported this module (even via the try/finally-guarded import in tests/test_warden_job.py)
# leaked platform/ onto sys.path for the rest of that process -- `import dagster` then
# resolved to the empty PEP 420 namespace package platform/dagster/ instead of the real
# pip-installed dagster (or ModuleNotFoundError, wherever dagster isn't installed at all, as
# in the bdd-suites CI job), breaking TestSchedulerRow.

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from warden import prove as warden

# Default in-cluster pushgateway address
DEFAULT_PUSH_GATEWAY = "http://prometheus-pushgateway.monitoring.svc.cluster.local:9091"
PUSH_GATEWAY_URL = os.environ.get("PUSH_GATEWAY_URL", DEFAULT_PUSH_GATEWAY)
JOB_NAME = "api-key-warden"

# Where the mounted human-<vendor> Secrets land (crew#832 CP3, kyverno secrets-not-from-env-vars).
# A directory path is config, like PUSH_GATEWAY_URL above -- it names where to look, not a secret.
DEFAULT_SECRETS_DIR = "/run/secrets/human"
WARDEN_SECRETS_DIR = os.environ.get("WARDEN_SECRETS_DIR", DEFAULT_SECRETS_DIR)


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


def read_key_file(vendor: str, field: str, base_dir: str | None = None) -> str | None:
    """Read one credential field from its mounted file, or None if not mounted.

    The mount is optional (a vendor whose key has not reached Bitwarden yet mounts nothing),
    so a missing file is a normal, expected state -- not an error.
    """
    path = Path(base_dir or WARDEN_SECRETS_DIR) / vendor / field
    try:
        value = path.read_text().strip()
    except OSError:
        return None
    return value or None


def provable_fields(config: dict) -> list[str]:
    """The credential fields this vendor can be proved on, one per independent key.

    Only vendors provable with a single plain string (required_fields == ["key"]) are
    covered here -- a paired credential (Telegram's bot+chat, Google's client id+secret)
    needs a Mapping of several named fields for ONE proof, which is a different shape from
    a pool of several INDEPENDENT single-key targets (groq/cerebras/sambanova) and is not
    covered by this job (crew#832 CP3 is the pools, not paired credentials).
    """
    if warden.required_fields(config) != ["key"]:
        return []
    seen: list[str] = []
    for target in config.get("targets") or []:
        field = target.get("field")
        if field and field not in seen:
            seen.append(field)
    return seen


def publish_metrics(results: list[dict]) -> None:
    """Push metrics to Prometheus pushgateway."""
    registry = CollectorRegistry()

    valid_gauge = Gauge(
        "estate_vendor_key_valid",
        "Whether the vendor key is currently valid (1) or not (0)",
        ["vendor", "field", "store"],
        registry=registry,
    )

    age_gauge = Gauge(
        "estate_vendor_key_age_days",
        "Days since the key was last rotated",
        ["vendor", "field", "store"],
        registry=registry,
    )

    checked_gauge = Gauge(
        "estate_vendor_key_checked_timestamp",
        "Unix timestamp when the key was last checked",
        ["vendor", "field"],
        registry=registry,
    )

    now = datetime.datetime.now(datetime.timezone.utc).timestamp()

    for result in results:
        vendor = result["vendor"]
        field = result["field"]
        store = result["store"]
        is_valid = 1 if result["valid"] else 0

        valid_gauge.labels(vendor=vendor, field=field, store=store).set(is_valid)
        checked_gauge.labels(vendor=vendor, field=field).set(now)

        age_days = result.get("age_days")
        if age_days is not None:
            age_gauge.labels(vendor=vendor, field=field, store=store).set(age_days)

    # Push to gateway
    try:
        push_to_gateway(PUSH_GATEWAY_URL, job=JOB_NAME, registry=registry)
    except Exception as e:
        # Log the error but don't crash - metrics are secondary to the run completing
        print(f"WARNING: failed to push metrics: {e}", file=sys.stderr)


def run_warden() -> int:
    """Run the warden job for every provable field of every vendor.

    Returns exit code 0 even if some keys fail - we record failure as gauge=0.
    """
    vendors = load_vendors()
    results = []

    for vendor_name, config in vendors.items():
        verify = config.get("verify")
        if not verify:
            continue  # Skip vendors without verification

        fields = provable_fields(config)
        if not fields:
            continue  # Paired credential, or no target names a field we can prove

        for field in fields:
            key = read_key_file(vendor_name, field)
            if not key:
                # Not mounted yet - record as invalid, same as a proof failure
                results.append(
                    {
                        "vendor": vendor_name,
                        "field": field,
                        "store": config.get("store_default", "unknown"),
                        "valid": False,
                        "age_days": None,
                        "error": "no key mounted",
                    }
                )
                continue

            try:
                proof = warden.prove(vendor_name, key)
                results.append(
                    {
                        "vendor": vendor_name,
                        "field": field,
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
                        "field": field,
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
                        "field": field,
                        "store": config.get("store_default", "unknown"),
                        "valid": False,
                        "age_days": None,
                        "error": warden.redact(str(e), key),
                    }
                )

    # Push metrics
    publish_metrics(results)

    # Print summary (no key values)
    print(f"Warden run complete: {len(results)} keys checked")
    valid_count = sum(1 for r in results if r["valid"])
    print(f"Valid: {valid_count}, Invalid: {len(results) - valid_count}")

    for result in results:
        status = "VALID" if result["valid"] else "INVALID"
        print(f"  {result['vendor']}/{result['field']}: {status}")
        if "summary" in result:
            print(f"    {result['summary']}")
        if "error" in result:
            print(f"    {result['error']}")

    # Exit 0 regardless of results - we recorded failures as gauge=0
    return 0


if __name__ == "__main__":
    sys.exit(run_warden())
