"""trust.* configurable keys -- cp22 "everything configurable".

Shape agreed with builder A: TRUST_KEYS: {key: (default, type, env_name,
help)}. sovereign/config.py imports this module and merges TRUST_KEYS into
its own KEYS table (see sovereign/trust/README.md for the two lines A adds).
"trust.backend" itself is already in A's KEYS table (CONTRACT.md's Config
section lists it); this module only adds the knobs sovereign/trust/ needs
beyond that one key, so a re-declare here would be silently skipped by
config.py's _merge_external_keys (first writer wins) -- listing it again
would be misleading, so it is deliberately absent from this table.

Standalone by design, like sovereign/otto/config_keys.py: get() resolves
env-or-default on its own and never imports sovereign.config, because
sovereign.config imports *this* module while it is still mid-definition
(see README.md, "why this file cannot import sovereign.config").
"""
from __future__ import annotations

import os
from typing import Any

# {key: (default, type, env_name, help)}
TRUST_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "trust.default_estate_home_dirname": (
        ".estate", str, "TRUST_DEFAULT_ESTATE_HOME_DIRNAME",
        "Fallback $ESTATE_HOME dirname under $HOME, used before sovereign.config is importable"),
    "trust.bin_dirname": (
        "bin", str, "SB_TRUST_BIN_DIRNAME",
        "Dirname under $ESTATE_HOME holding compiled trust helpers"),
    "trust.swift_helper_binname": (
        "estate-presence", str, "SB_TRUST_HELPER_BINNAME",
        "Compiled swift helper binary name"),
    "trust.swift_source_filename": (
        "presence_helper.swift", str, "SB_TRUST_SWIFT_SOURCE_FILENAME",
        "Swift source filename bundled alongside sovereign/trust/anchor.py"),
    "trust.compile_timeout_s": (
        60, float, "SB_TRUST_COMPILE_TIMEOUT_S",
        "swiftc compile timeout, first use only (binary is cached after)"),
    "trust.detect_timeout_s": (
        5, float, "SB_TRUST_DETECT_TIMEOUT_S",
        "Timeout for the capability-detect subprocess call (no prompt)"),
    "trust.presence_timeout_s": (
        30, float, "SB_TRUST_PRESENCE_TIMEOUT_S",
        "Timeout for a founder-presence verification prompt"),
    "trust.hmac_key_bytes": (
        32, int, "SB_TRUST_HMAC_KEY_BYTES",
        "software_key fallback signing key length"),
    "trust.software_key_filename": (
        "trust.key", str, "SB_TRUST_SOFTWARE_KEY_FILENAME",
        "software_key fallback key filename under $ESTATE_HOME/sovereign"),
    "trust.reason_default": (
        "estate action", str, "SB_TRUST_REASON_DEFAULT",
        "Default reason string shown in the presence prompt"),
    "trust.sovereign_dirname": (
        "sovereign", str, "SB_TRUST_SOVEREIGN_DIRNAME",
        "Dirname under $ESTATE_HOME holding the software_key fallback file"),
    "trust.helper_file_mode": (
        0o700, int, "SB_TRUST_HELPER_FILE_MODE",
        "chmod applied to the compiled swift helper binary"),
    "trust.software_key_file_mode": (
        0o600, int, "SB_TRUST_SOFTWARE_KEY_FILE_MODE",
        "chmod applied to the software_key fallback key file"),
    "trust.posix_separator": (
        "/", str, "SB_TRUST_POSIX_SEPARATOR",
        "The separator canonical_relpath normalizes every path to"),
    "trust.windows_separator": (
        "\\", str, "SB_TRUST_WINDOWS_SEPARATOR",
        "The separator canonical_relpath treats as equivalent to the POSIX one"),

    # ---- R11/R22: a signed approval, and the enrolment it is checked against ----
    "trust.enrolled_pubkey_filename": (
        "enrolled.pub", str, "SB_TRUST_ENROLLED_PUBKEY_FILENAME",
        "Enrolled Secure Enclave public key (base64) under $ESTATE_HOME/sovereign"),
    "trust.approval_nonce_bytes": (
        16, int, "SB_TRUST_APPROVAL_NONCE_BYTES",
        "Random bytes in an approval challenge, so two approvals never share a digest"),
    "trust.approval_ttl_s": (
        300, float, "SB_TRUST_APPROVAL_TTL_S",
        "How long a signed approval envelope stays valid after it was challenged"),
    "trust.used_counters_filename": (
        "approvals.used", str, "SB_TRUST_USED_COUNTERS_FILENAME",
        "Replay ledger: one used approval counter per line, under $ESTATE_HOME/sovereign"),
    "trust.attestation_hardware_label": (
        "hardware", str, "SB_TRUST_ATTESTATION_HARDWARE_LABEL",
        "Value of a receipt's `attestation` field when the enclave itself signed -- the pair reads attestation:hardware"),
    "trust.attestation_fallback_label": (
        "fallback", str, "SB_TRUST_ATTESTATION_FALLBACK_LABEL",
        "Value of a receipt's `attestation` field when the multi-signature set signed instead -- the pair cp29 names, attestation:fallback"),

    # ---- R24: 2-of-3 multi-signature fallback ----
    "trust.multisig_threshold": (
        2, int, "SB_TRUST_MULTISIG_THRESHOLD",
        "How many distinct enrolled signers must sign when the enclave is unavailable"),
    "trust.multisig_signers": (
        "founder,token_a,token_b", str, "SB_TRUST_MULTISIG_SIGNERS",
        "Comma-separated ids of the enrolled fallback signer set (the 3 of 2-of-3)"),
    "trust.signers_dirname": (
        "signers", str, "SB_TRUST_SIGNERS_DIRNAME",
        "Dirname under $ESTATE_HOME/sovereign holding one enrolled signer key per file"),
    "trust.signer_key_suffix": (
        ".key", str, "SB_TRUST_SIGNER_KEY_SUFFIX",
        "Filename suffix of an enrolled fallback signer key"),

    # ---- R31: SPIFFE identity ----
    "spiffe.trust_domain": (
        "estate.internal", str, "SB_SPIFFE_TRUST_DOMAIN",
        "Trust domain, matching platform/spire/values.yaml global.spire.trustDomain"),
    "spiffe.scheme": (
        "spiffe", str, "SB_SPIFFE_SCHEME",
        "URI scheme of a SPIFFE ID"),
    "spiffe.socket_env": (
        "SPIFFE_ENDPOINT_SOCKET", str, "SB_SPIFFE_SOCKET_ENV",
        "Env var naming the SPIFFE Workload API socket (the SPIFFE standard name)"),
    "spiffe.default_socket_path": (
        "unix:///tmp/spire-agent/public/api.sock", str, "SB_SPIFFE_DEFAULT_SOCKET",
        "Workload API endpoint used when the standard env var is unset"),
    "spiffe.scheme_suffix": (
        "://", str, "SB_SPIFFE_SCHEME_SUFFIX",
        "What separates a SPIFFE ID's scheme from its trust domain"),
    "spiffe.dev_fallback_label": (
        "dev-fallback", str, "SB_SPIFFE_DEV_FALLBACK_LABEL",
        "source= value marking an identity that no SPIRE agent attested (never trusted)"),
    "spiffe.attested_label": (
        "workload-api", str, "SB_SPIFFE_ATTESTED_LABEL",
        "source= value marking an SVID fetched from the SPIRE Workload API"),
    "spiffe.dev_path_prefix": (
        "dev", str, "SB_SPIFFE_DEV_PATH_PREFIX",
        "First path segment of a dev-fallback SPIFFE ID, so it can never collide with a real one"),
    "spiffe.max_missed_heartbeats": (
        3, int, "SB_SPIFFE_MAX_MISSED_HEARTBEATS",
        "Missed heartbeats before an SVID is revoked and the agent isolated (spec 4.4)"),
    "spiffe.heartbeat_interval_s": (
        30, float, "SB_SPIFFE_HEARTBEAT_INTERVAL_S",
        "Expected seconds between agent heartbeats"),
    "spiffe.registry_filename": (
        "spiffe-heartbeats.json", str, "SB_SPIFFE_REGISTRY_FILENAME",
        "Heartbeat/revocation registry filename under $ESTATE_HOME/sovereign"),
}


def get(key: str) -> Any:
    """Resolve one trust.* key: env override, else the default. Standalone
    by design -- see module docstring."""
    default, typ, env_name, _help = TRUST_KEYS[key]
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default
