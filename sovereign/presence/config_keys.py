"""presence.* configurable keys (W3, master spec 2.1, 2.2, 2.5, 2.6).

Every literal sovereign/presence/ needs is named here once, in the
{key: (default, type, env_name, help)} shape sovereign.config merges under
its clearly marked presence block. resolve() below is what the presence
modules call, so a value has exactly one definition to change.

The estate root is never typed here (LAW 46): every path default is built
from the same ESTATE_HOME resolution sovereign.config uses.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _estate_home() -> Path:
    return Path(os.environ.get("ESTATE_HOME", str(Path.home() / ".estate")))


PRESENCE_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "presence.state_file": (
        str(_estate_home() / "sovereign" / "presence.json"), str, "SB_PRESENCE_STATE_FILE",
        "where the kernel writes the current presence state; the SwiftBar plugin reads it",
    ),
    "presence.digest_hour": (
        9, int, "SB_PRESENCE_DIGEST_HOUR",
        "local hour the daily digest is built (spec 2.5: one digest at 09:00)",
    ),
    "presence.digest_max_lines": (
        6, int, "SB_PRESENCE_DIGEST_MAX_LINES",
        "hard cap on digest lines, hash line included (spec 2.5: max 6 lines)",
    ),
    "presence.digest_label": (
        "estate.digest", str, "SB_PRESENCE_DIGEST_LABEL",
        "launchd label for the 09:00 digest job printed by `sb digest --launchd`",
    ),
    "presence.receipt_hash_chars": (
        8, int, "SB_PRESENCE_RECEIPT_HASH_CHARS",
        "hex chars of a hash shown in a one-line receipt (spec 2.2 example: 8)",
    ),
    "presence.receipt_state_chars": (
        6, int, "SB_PRESENCE_RECEIPT_STATE_CHARS",
        "hex chars of the state hash shown in a one-line receipt (spec 2.2 example: 6)",
    ),
    "presence.receipt_ok_mark": (
        "[✓]", str, "SB_PRESENCE_RECEIPT_OK_MARK",
        "prefix of a receipt whose op succeeded",
    ),
    "presence.receipt_fail_mark": (
        "[✗]", str, "SB_PRESENCE_RECEIPT_FAIL_MARK",
        "prefix of a receipt whose op failed or was halted",
    ),
    "presence.receipt_field_sep": (
        " | ", str, "SB_PRESENCE_RECEIPT_FIELD_SEP",
        "separator between receipt fields",
    ),
    "presence.budget_kilo": (
        1000, int, "SB_PRESENCE_BUDGET_KILO",
        "tokens per 'k' in a receipt's budget delta",
    ),
    "presence.haptic_enabled": (
        False, bool, "SB_PRESENCE_HAPTIC_ENABLED",
        "when true, state commits, boundary warnings and halts also emit a haptic pattern",
    ),
    "presence.haptic_kind": (
        "haptic", str, "SB_PRESENCE_HAPTIC_KIND",
        "the alert-inbox `kind` of a haptic pattern line (cockpit /api/inbox and the phone read it)",
    ),
    "presence.receipt_kind": (
        "receipt", str, "SB_PRESENCE_RECEIPT_KIND",
        "the alert-inbox `kind` of a one-line receipt",
    ),
    "presence.remediation_command": (
        "bin/sb audit --verify", str, "SB_PRESENCE_REMEDIATION_COMMAND",
        "the command a catastrophe message tells the founder to run",
    ),
    "presence.chat_channel": (
        "telegram", str, "SB_PRESENCE_CHAT_CHANNEL",
        "name of the founder chat surface (the emergency broadcast channel, spec 2.5)",
    ),
    "presence.route_api_status": (
        "/api/status", str, "SB_PRESENCE_ROUTE_API_STATUS",
        "cockpit GET path returning running/waiting/burn counts (the Siri shortcut reads it)",
    ),
    "presence.route_api_spatial": (
        "/api/spatial", str, "SB_PRESENCE_ROUTE_API_SPATIAL",
        "cockpit GET path returning the Spatial graph (nodes coloured by health, sized by burn)",
    ),
    "presence.dot_ghost": (
        "grey", str, "SB_PRESENCE_DOT_GHOST",
        "menu bar dot colour in Ghost and Haptic (spec 2.1: no pixels change)",
    ),
    "presence.dot_spatial": (
        "orange", str, "SB_PRESENCE_DOT_SPATIAL",
        "menu bar dot colour when Spatial was opened by the founder",
    ),
    "presence.dot_catastrophe": (
        "red", str, "SB_PRESENCE_DOT_CATASTROPHE",
        "menu bar dot colour when Spatial was raised by a catastrophe",
    ),
    "presence.dot_converse": (
        "green", str, "SB_PRESENCE_DOT_CONVERSE",
        "menu bar dot colour while the founder is in Converse",
    ),
    "presence.health_running": (
        "#2ecc71", str, "SB_PRESENCE_HEALTH_RUNNING",
        "Spatial node colour for a running session",
    ),
    "presence.health_waiting": (
        "#f1c40f", str, "SB_PRESENCE_HEALTH_WAITING",
        "Spatial node colour for a session waiting on the founder",
    ),
    "presence.health_halted": (
        "#e74c3c", str, "SB_PRESENCE_HEALTH_HALTED",
        "Spatial node colour for a halted, failed or denied session",
    ),
    "presence.health_done": (
        "#95a5a6", str, "SB_PRESENCE_HEALTH_DONE",
        "Spatial node colour for a finished session",
    ),
    "presence.node_min_size": (
        8, int, "SB_PRESENCE_NODE_MIN_SIZE",
        "Spatial node radius at zero burn rate",
    ),
    "presence.node_size_per_kilo": (
        4, int, "SB_PRESENCE_NODE_SIZE_PER_KILO",
        "extra Spatial node radius per 1k tokens burned per step",
    ),
    "presence.speak_template": (
        "{running} agents active. {waiting} waiting on you. Burn {burn_per_step} tokens per step.",
        str, "SB_PRESENCE_SPEAK_TEMPLATE",
        "what Siri says for 'estate status' (spec 2.6)",
    ),
}

_TRUE_WORDS = ("1", "true", "yes", "on")


def resolve(key: str, config_module: Any = None) -> Any:
    """key's effective value: the merged sovereign.config attribute if it is
    there, else this process's environment, else the table default."""
    default, typ, env_name, _help = PRESENCE_KEYS[key]
    raw: Any = None
    if config_module is not None and hasattr(config_module, env_name):
        raw = getattr(config_module, env_name)
    elif env_name in os.environ:
        raw = os.environ[env_name]
    if raw is None:
        return default
    if isinstance(raw, typ):
        return raw
    if typ is bool:
        return str(raw).strip().lower() in _TRUE_WORDS
    return typ(raw)
