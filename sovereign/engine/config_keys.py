"""engine-side self-termination keys (R32, spec v1.0 section 5) -- cp22.

Same {key: (default, type, env_name, help)} shape as the otto, cockpit,
trust and attach tables, merged into config.py's KEYS. Standalone get(),
no import of sovereign.config, for the same reason those are standalone.

The three thresholds spec section 5 states as numbers are here as
defaults, so the sentence in the spec and the number in the code are the
same number and a change is a config line rather than a patch.
blind.halt_after_min and alerts.digest_over_per_hour are NOT redeclared:
they already exist in config.py's own table, and _merge_external_keys is
first-writer-wins, so a copy here would be silently ignored while looking
authoritative.
"""
from __future__ import annotations

import os
from typing import Any

TERMINATION_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "terminate.min_confidence": (
        0.4, float, "SB_TERMINATE_MIN_CONFIDENCE",
        "Confidence below which a reasoning step counts as low-confidence (spec 5)"),
    "terminate.low_confidence_steps": (
        3, int, "SB_TERMINATE_LOW_CONFIDENCE_STEPS",
        "Consecutive low-confidence steps that trigger a soft halt"),
    "terminate.latency_baseline_s": (
        2.0, float, "SB_TERMINATE_LATENCY_BASELINE_S",
        "Expected step latency; recorded so a breach can be reported against it"),
    "terminate.latency_max_s": (
        30.0, float, "SB_TERMINATE_LATENCY_MAX_S",
        "Step latency above which the engine retries once via the fallback, then halts"),
    "terminate.latency_retries": (
        1, int, "SB_TERMINATE_LATENCY_RETRIES",
        "Retries allowed after a latency breach before the halt is unconditional"),
    "tracing.last_ok_filename": (
        "langfuse-last-ok.json", str, "SB_TRACING_LAST_OK_FILENAME",
        "File under $ESTATE_HOME/sovereign recording when Langfuse last accepted a "
        "trace, so blind.halt_after_min can be measured rather than guessed"),
    "time.seconds_per_minute": (
        60, int, None, "Seconds in a minute -- a literal nowhere but a config table (cp22)"),
    "time.minutes_per_hour": (
        60, int, None, "Minutes in an hour"),
    "trace.signature_field": (
        "trace_sig", str, "SB_TRACE_SIGNATURE_FIELD",
        "Metadata field carrying a trace entry's signature over the session Merkle root"),
}


def get(key: str) -> Any:
    default, typ, env_name, _help = TERMINATION_KEYS[key]
    raw = os.environ.get(env_name) if env_name else None
    if raw is None:
        return default
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default
