"""Sovereign Bus configuration -- the one table (cp22). Every number, path,
model alias, timeout, threshold and toggle the engine uses is a named key
here, in KEYS, with a default. Nothing outside this file is a literal
(LAW 46 + cp22); `sb config --lint` (see lint() below) checks that on every
other file under sovereign/.

Resolution order per key: default < $ESTATE_HOME/estate.toml < environment
< CLI flag. `get()` and `resolve_all()` are what every subcommand and every
other module should call; the module-level constants below them are a
resolved snapshot for convenience (recomputed at import time only).
"""
from __future__ import annotations

import ast
import fcntl
import json
import os
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib  # py311+
except ImportError:  # pragma: no cover - py310 on this machine
    import tomli as tomllib  # type: ignore


# ---------------------------------------------------------------------------
# estate.home is the one value resolved outside the KEYS table, because the
# table itself, and estate.toml's location, both depend on it.
# ---------------------------------------------------------------------------


def _estate_home() -> Path:
    return Path(os.environ.get("ESTATE_HOME", str(Path.home() / ".estate")))


def _env_file_path() -> Path:
    return Path(os.environ.get("ESTATE_ENV", str(Path.home() / ".config" / "estate" / "estate.env")))


def _load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text()
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def _loopback() -> str:
    try:
        return socket.gethostbyname("localhost")
    except OSError:
        return socket.inet_ntoa(bytes([127, 0, 0, 1]))


ESTATE_HOME: Path = _estate_home()
SOVEREIGN_HOME: Path = ESTATE_HOME / "sovereign"
ESTATE_TOML: Path = ESTATE_HOME / "estate.toml"
_ENV_FILE_VALUES = _load_env_file(_env_file_path())


# ---------------------------------------------------------------------------
# The KEYS table.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeySpec:
    default: Any
    type: str  # "str" | "int" | "float" | "bool" | "list" | "path"
    env: str | None = None
    help: str = ""
    secret: bool = False


def _default_temporal_address() -> str:
    return f"{os.environ.get('TEMPORAL_HOST', 'localhost')}:{os.environ.get('TEMPORAL_PORT', '7233')}"


def _default_sidecar_target() -> str:
    """cp8: names the one legacy DB and write path this estate's sidecar
    mirrors. Mirrors maestro.py's own Config.DB_PATH resolution exactly
    (same env var, same fallback) rather than a second hardcoded copy of
    that default -- maestro is the only live experience-graph database on
    this estate (crew note, 2026-08-24: "two maestros share one database,
    only the maestro checkout is live"). `episodes` is maestro's
    highest-write-volume table and the one _connect() in maestro.py calls
    "the one place a connection ... is opened" writes through."""
    db = os.path.expanduser(os.environ.get("MAESTRO_DB", "~/.maestro/experience_graph.db"))
    return f"{db}#episodes"


KEYS: dict[str, KeySpec] = {
    "estate.home": KeySpec(str(_estate_home()), "path", "ESTATE_HOME", "estate state root"),
    "estate.env_file": KeySpec(str(_env_file_path()), "path", "ESTATE_ENV", "estate.env location"),
    "estate.public_url": KeySpec(None, "str", "ESTATE_PUBLIC_URL", "cloudflared tunnel URL for the Mini App"),
    "estate.alert_inbox": KeySpec(str(_estate_home() / "alerts" / "inbox.jsonl"), "path", "ESTATE_ALERT_INBOX", ""),

    "temporal.host": KeySpec("localhost", "str", "TEMPORAL_HOST", "Temporal frontend host"),
    "temporal.port": KeySpec(7233, "int", "TEMPORAL_PORT", "Temporal frontend port"),
    "temporal.address": KeySpec(None, "str", "TEMPORAL_ADDRESS", "overrides host:port together"),
    "temporal.namespace": KeySpec("estate", "str", "TEMPORAL_NAMESPACE", ""),
    "temporal.task_queue": KeySpec("sovereign", "str", "TEMPORAL_TASK_QUEUE", ""),
    "temporal.db_filename": KeySpec(str(_estate_home() / "temporal" / "dev.db"), "path", "TEMPORAL_DB", ""),

    "receipts.path": KeySpec(str(_estate_home() / "sovereign" / "receipts.jsonl"), "path", "SB_RECEIPTS", ""),
    "receipts.keychain_service": KeySpec("sovereign-receipts", "str", None, "macOS Keychain -s"),
    "receipts.keychain_account": KeySpec("estate", "str", None, "macOS Keychain -a"),
    "receipts.keychain_timeout_s": KeySpec(10, "int", "SB_RECEIPTS_KEYCHAIN_TIMEOUT_S", ""),
    "receipts.key_bytes": KeySpec(32, "int", "SB_RECEIPTS_KEY_BYTES", "signing key length"),
    "receipts.key_file_mode": KeySpec(0o600, "int", None, "software_file key permissions"),
    "receipts.lock_timeout_s": KeySpec(10, "int", "SB_RECEIPTS_LOCK_TIMEOUT_S", ""),
    "receipts.hash_hex_len": KeySpec(64, "int", None, "sha256 hexdigest length, the genesis prev_hash"),
    "receipts.json_field_sep": KeySpec(",", "str", None, "canonical json.dumps separators[0]"),
    "receipts.json_kv_sep": KeySpec(":", "str", None, "canonical json.dumps separators[1]"),
    "receipts.head_dir": KeySpec(str(_estate_home() / "sovereign"), "path", None, "dir for the signed head anchor (cp19 tail-truncation defense)"),
    "receipts.head_filename": KeySpec("receipts.head", "str", "SB_RECEIPTS_HEAD_FILENAME", "signed head-anchor filename, rewritten after every append"),

    "sidecar.target": KeySpec(_default_sidecar_target(), "str", "SB_SIDECAR_TARGET", "cp8: '<db path>#<table>' this sidecar mirrors, DB logic never changed"),
    "sidecar.dag_dir": KeySpec(str(_estate_home() / "sovereign" / "dag"), "path", "SB_SIDECAR_DAG_DIR", "cp8: Merkle DAG node directory, one JSON file per observed write"),
    "sidecar.head_filename": KeySpec("HEAD.json", "str", None, "cp8: current DAG head marker filename inside sidecar.dag_dir"),

    "shadow.heads_dir": KeySpec(str(_estate_home() / ".estate" / "heads"), "path", "SB_SHADOW_HEADS_DIR", "cp9: dir holding the shadow branch-pointer files"),
    "shadow.head_filename": KeySpec("shadow_main", "str", None, "cp9: shadow_main -- the head that always names the DAG root equal to the legacy DB's current state"),

    "dualread.max_overhead_ms": KeySpec(15, "int", "SB_DUALREAD_MAX_OVERHEAD_MS", "cp10: p95 budget for the dual-read router's added cost (DAG walk + receipt) over the legacy-only read, measured over 1000 reads"),
    "dualread.latency_round_ndigits": KeySpec(4, "int", None, "cp10: decimal places dual-read latencies are rounded to before entering a receipt"),
    "time.ms_per_second": KeySpec(1000, "int", None, "milliseconds per second, for every perf_counter() duration reported in ms"),

    "telegram.bot_token": KeySpec(_ENV_FILE_VALUES.get("TELEGRAM_BOT_TOKEN"), "str", "TELEGRAM_BOT_TOKEN", "", secret=True),
    "telegram.home_channel": KeySpec(_ENV_FILE_VALUES.get("TELEGRAM_HOME_CHANNEL"), "str", "TELEGRAM_HOME_CHANNEL", ""),

    "cockpit.port": KeySpec(8788, "int", "COCKPIT_PORT", ""),
    "cockpit.bind": KeySpec(_loopback(), "str", "COCKPIT_BIND", ""),

    "langfuse.host": KeySpec(_ENV_FILE_VALUES.get("LANGFUSE_HOST"), "str", "LANGFUSE_HOST", ""),
    "langfuse.public_key": KeySpec(_ENV_FILE_VALUES.get("LANGFUSE_PUBLIC_KEY"), "str", "LANGFUSE_PUBLIC_KEY", "", secret=True),
    "langfuse.secret_key": KeySpec(_ENV_FILE_VALUES.get("LANGFUSE_SECRET_KEY"), "str", "LANGFUSE_SECRET_KEY", "", secret=True),

    "litellm.base_url": KeySpec(_ENV_FILE_VALUES.get("LITELLM_BASE_URL"), "str", "LITELLM_BASE_URL", ""),
    "litellm.api_key": KeySpec(_ENV_FILE_VALUES.get("LITELLM_API_KEY"), "str", "LITELLM_API_KEY", "", secret=True),
    "litellm.chat_completions_path": KeySpec("/chat/completions", "str", "LITELLM_CHAT_COMPLETIONS_PATH", ""),

    "budget.default": KeySpec(None, "int", "SB_DEFAULT_BUDGET", "tokens; None means budget is required at start"),
    "runner.default": KeySpec("echo", "str", "SB_DEFAULT_RUNNER", ""),
    "model.default": KeySpec("ollama", "str", "SB_MODEL", "LiteLLM alias for the llm runner"),
    "model.vision": KeySpec("ollama-vision", "str", "SB_MODEL_VISION", "LiteLLM alias, vision-capable"),
    "model.consensus": KeySpec(["ollama", "ollama", "ollama"], "list", "SB_MODEL_CONSENSUS", "comma-separated aliases"),

    "step.start_to_close_min": KeySpec(30, "int", "SB_STEP_TIMEOUT_MIN", "activity start-to-close timeout"),
    "step.heartbeat_s": KeySpec(10, "int", "SB_HEARTBEAT_S", "activity heartbeat timeout"),
    "burn.tokens_per_step": KeySpec(100, "int", "SB_BURN_TOKENS", "the burn runner's tokens per step"),

    "consensus.timeout_s": KeySpec(30, "int", "SB_CONSENSUS_TIMEOUT_S", ""),
    "consensus.quorum": KeySpec("2/3", "str", "SB_CONSENSUS_QUORUM", ""),
    "fsm.max_cycles": KeySpec(5, "int", "SB_FSM_MAX_CYCLES", ""),
    "shadow.min_confidence": KeySpec(0.95, "float", "SB_SHADOW_MIN_CONFIDENCE", ""),
    "digest.max_lines": KeySpec(6, "int", "SB_DIGEST_MAX_LINES", ""),
    "digest.time": KeySpec("09:00", "str", "SB_DIGEST_TIME", ""),
    "branch.count": KeySpec(3, "int", "SB_BRANCH_COUNT", ""),
    "branch.budget_pct": KeySpec(10, "int", "SB_BRANCH_BUDGET_PCT", ""),
    "blind.halt_after_min": KeySpec(5, "int", "SB_BLIND_HALT_AFTER_MIN", ""),
    "alerts.digest_over_per_hour": KeySpec(50, "int", "SB_ALERTS_DIGEST_OVER_PER_HOUR", ""),
    "card.poll_s": KeySpec(3, "int", "SB_CARD_POLL_S", ""),
    "trust.backend": KeySpec("auto", "str", "SB_TRUST_BACKEND", ""),
    "presence.default": KeySpec("ghost", "str", "SB_PRESENCE_DEFAULT", ""),

    "cli.port_probe_timeout_s": KeySpec(0.3, "float", "SB_PORT_PROBE_TIMEOUT_S", "socket connect_ex timeout when probing a port"),
    "cli.up_wait_deadline_s": KeySpec(20, "int", "SB_UP_WAIT_DEADLINE_S", "seconds `sb up` waits for temporal's port to open"),
    "cli.up_poll_interval_s": KeySpec(0.5, "float", "SB_UP_POLL_INTERVAL_S", "poll interval while `sb up` waits"),
    "cli.down_wait_deadline_s": KeySpec(10, "int", "SB_DOWN_WAIT_DEADLINE_S", "seconds `sb down` waits for a SIGTERM'd pid to exit before SIGKILL"),
    "net.host_port_sep": KeySpec(":", "str", None, "separator between host and port in an address string"),
    "session.id_hex_len": KeySpec(8, "int", "SB_SESSION_ID_HEX_LEN", "hex chars from uuid4 used for a session id"),
    "session.last_output_max_chars": KeySpec(500, "int", "SB_LAST_OUTPUT_MAX_CHARS", "last_output truncation length"),
    "runner.token_estimate_divisor": KeySpec(4, "int", "SB_TOKEN_ESTIMATE_DIVISOR", "len(output)//N token estimate"),
    "runner.ask_prefix": KeySpec("needs", "str", "SB_ASK_PREFIX", "prefix the ask runner recognizes in a task, before the separator"),
    "runner.ask_prefix_sep": KeySpec(":", "str", None, "separator between the ask prefix and the rest of the task"),
    "runner.llm_timeout_s": KeySpec(120, "int", "SB_LLM_TIMEOUT_S", "httpx timeout for the llm runner"),
    "runner.claude_heartbeat_interval_s": KeySpec(3, "int", "SB_CLAUDE_HEARTBEAT_INTERVAL_S", "activity.heartbeat() interval while awaiting the claude subprocess"),
    "receipt.activity_timeout_s": KeySpec(30, "int", "SB_RECEIPT_ACTIVITY_TIMEOUT_S", "append_receipt start-to-close timeout"),
    "receipt.retry_max_attempts": KeySpec(5, "int", "SB_RECEIPT_RETRY_MAX_ATTEMPTS", ""),
    "notify.activity_timeout_s": KeySpec(10, "int", "SB_NOTIFY_ACTIVITY_TIMEOUT_S", "notify_change start-to-close timeout -- short: a stuck notify must never hold up the step loop"),
    "notify.retry_max_attempts": KeySpec(1, "int", "SB_NOTIFY_RETRY_MAX_ATTEMPTS", "1 == no retry; the next state change notifies again anyway"),
    "step.activity_retry_max_attempts": KeySpec(2, "int", "SB_STEP_RETRY_MAX_ATTEMPTS", "run_step activity retry attempts"),
    "cli.exit_usage_error": KeySpec(2, "int", "SB_EXIT_USAGE_ERROR", "exit code for a refused command, e.g. missing budget"),
    "client.query_timeout_s": KeySpec(5, "float", "SB_QUERY_TIMEOUT_S", "client-side timeout on a single workflow query, so one stuck session never hangs `sb list`"),
    "log.bot_token_redact_pattern": KeySpec(r"bot\d+:[A-Za-z0-9_-]+", "str", None, "regex matching a Telegram bot token as it appears in a URL (LAW 21)"),
}

# ---------------------------------------------------------------------------
# Merge builder B's OTTO_KEYS and builder C's COCKPIT_KEYS into the one
# table (cp22, coordinator 2026-08-25): "shape {key: (default, type,
# env_name, help)} is agreed with both". Their tables use a real Python
# `type` object; this file's KeySpec.type is the short string _coerce()
# switches on. A key this table already defines locally wins -- it may
# carry a non-literal-computed default (e.g. cockpit.bind's DNS lookup)
# that the standalone table's sentinel value cannot express.
# ---------------------------------------------------------------------------

_TYPE_TO_SPEC_TYPE: dict[type, str] = {str: "str", int: "int", float: "float", bool: "bool", list: "list"}


def _merge_external_keys(table: dict[str, tuple[Any, type, str, str]]) -> None:
    for key, (default, typ, env_name, help_text) in table.items():
        if key in KEYS:
            continue
        KEYS[key] = KeySpec(default, _TYPE_TO_SPEC_TYPE.get(typ, "str"), env_name, help_text)


try:
    from sovereign.otto.config_keys import OTTO_KEYS

    _merge_external_keys(OTTO_KEYS)
except ImportError:
    pass

try:
    from sovereign.cockpit.config_keys import COCKPIT_KEYS

    _merge_external_keys(COCKPIT_KEYS)
except ImportError:
    pass

try:
    from sovereign.trust.config_keys import TRUST_KEYS

    _merge_external_keys(TRUST_KEYS)
except ImportError:
    pass

try:
    from sovereign.attach.config_keys import ATTACH_KEYS

    _merge_external_keys(ATTACH_KEYS)
except ImportError:
    pass


_SECRET_LAST_SEGMENTS = ("token", "secret", "password", "api_key")


def is_secret(key: str) -> bool:
    """A key is secret when its own spec says so (langfuse.secret_key,
    litellm.api_key, ...) or when its last dotted segment names a secret
    kind exactly -- token|secret|password|api_key. Exact match on the last
    segment, not a bare string suffix: receipts.keychain_account is an
    account NAME (Keychain -a), not a credential, and must print."""
    spec = KEYS.get(key)
    if spec and spec.secret:
        return True
    return key.rsplit(".", 1)[-1].lower() in _SECRET_LAST_SEGMENTS


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _load_toml_flat() -> dict[str, Any]:
    if not ESTATE_TOML.exists():
        return {}
    try:
        with open(ESTATE_TOML, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return _flatten(data)


def _coerce(spec: KeySpec, raw: Any) -> Any:
    if raw is None:
        return None
    if spec.type == "int":
        return int(raw)
    if spec.type == "float":
        return float(raw)
    if spec.type == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if spec.type == "list":
        if isinstance(raw, list):
            return raw
        return [x.strip() for x in str(raw).split(",") if x.strip()]
    if spec.type == "path":
        return str(raw)
    return str(raw)


@dataclass(frozen=True)
class Resolved:
    key: str
    value: Any
    default: Any
    source: str  # default | file | env | flag


def get(key: str, cli_value: Any = None, *, _toml: dict[str, Any] | None = None) -> Resolved:
    spec = KEYS[key]
    value, source = spec.default, "default"
    toml_flat = _toml if _toml is not None else _load_toml_flat()
    if key in toml_flat and toml_flat[key] is not None:
        value, source = _coerce(spec, toml_flat[key]), "file"
    env_raw = os.environ.get(spec.env) if spec.env else None
    if env_raw is not None and env_raw != "":
        # SB_DEFAULT_BUDGET= (present, empty) is how a shell unsets a var
        # in-line without an explicit `unset`; coercing "" for an int/float
        # key raises ValueError deep inside _coerce, so treat empty exactly
        # like absent rather than a value of "".
        value, source = _coerce(spec, env_raw), "env"
    if cli_value is not None:
        value, source = _coerce(spec, cli_value), "flag"
    return Resolved(key=key, value=value, default=spec.default, source=source)


def resolve_all(cli_overrides: dict[str, Any] | None = None) -> dict[str, Resolved]:
    toml_flat = _load_toml_flat()
    cli_overrides = cli_overrides or {}
    return {k: get(k, cli_overrides.get(k), _toml=toml_flat) for k in KEYS}


def _toml_repr(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_repr(v) for v in value) + "]"
    return json.dumps(str(value))


def set_key(key: str, raw_value: str, by: str) -> Resolved:
    """Write one key to estate.toml (line-based, dotted keys -- TOML treats
    `a.b = 1` at top level as nested table a.b, so no [section] header is
    needed) and append a "config" receipt. Returns the new resolved value."""
    if key not in KEYS:
        raise KeyError(f"unknown config key: {key}")
    spec = KEYS[key]
    value = _coerce(spec, raw_value)
    line = f"{key} = {_toml_repr(value)}"
    ESTATE_TOML.parent.mkdir(parents=True, exist_ok=True)
    existing = ESTATE_TOML.read_text().splitlines() if ESTATE_TOML.exists() else []
    prefix = f"{key} = "
    replaced = False
    for i, existing_line in enumerate(existing):
        if existing_line.startswith(prefix):
            existing[i] = line
            replaced = True
            break
    if not replaced:
        existing.append(line)
    ESTATE_TOML.write_text("\n".join(existing) + "\n")

    from sovereign.engine import receipts as receipts_mod  # local import: avoid a cycle at module load

    receipts_mod.append(
        {
            "session_id": "-",
            "kind": "config",
            "by": by,
            "text": f"{key}={raw_value}",
            "step": 0,
            "status": "config",
            "task": "",
            "runner": "",
        }
    )
    return get(key)


# ---------------------------------------------------------------------------
# Resolved snapshot -- convenience attributes used by the rest of the
# engine, computed once at import time from the KEYS table above.
# ---------------------------------------------------------------------------

_R = resolve_all()

TEMPORAL_HOST: str = _R["temporal.host"].value
TEMPORAL_PORT: str = str(_R["temporal.port"].value)
TEMPORAL_ADDRESS: str = _R["temporal.address"].value or f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"
TEMPORAL_NAMESPACE: str = _R["temporal.namespace"].value
TEMPORAL_TASK_QUEUE: str = _R["temporal.task_queue"].value
TEMPORAL_DB: Path = Path(_R["temporal.db_filename"].value)

SB_RECEIPTS: Path = Path(_R["receipts.path"].value)
RECEIPTS_HEAD: Path = Path(_R["receipts.head_dir"].value) / _R["receipts.head_filename"].value
SIDECAR_TARGET: str = _R["sidecar.target"].value
SIDECAR_DAG_DIR: Path = Path(_R["sidecar.dag_dir"].value)
SIDECAR_HEAD_FILENAME: str = _R["sidecar.head_filename"].value
SHADOW_HEADS_DIR: Path = Path(_R["shadow.heads_dir"].value)
SHADOW_HEAD_FILENAME: str = _R["shadow.head_filename"].value
DUALREAD_MAX_OVERHEAD_MS: int = _R["dualread.max_overhead_ms"].value
DUALREAD_LATENCY_ROUND_NDIGITS: int = _R["dualread.latency_round_ndigits"].value
MS_PER_SECOND: int = _R["time.ms_per_second"].value
RECEIPTS_KEYCHAIN_SERVICE: str = _R["receipts.keychain_service"].value
RECEIPTS_KEYCHAIN_ACCOUNT: str = _R["receipts.keychain_account"].value
RECEIPTS_KEYCHAIN_TIMEOUT_S: int = _R["receipts.keychain_timeout_s"].value
RECEIPTS_KEY_BYTES: int = _R["receipts.key_bytes"].value
RECEIPTS_KEY_FILE_MODE: int = _R["receipts.key_file_mode"].value
RECEIPTS_LOCK_TIMEOUT_S: int = _R["receipts.lock_timeout_s"].value
RECEIPTS_HASH_HEX_LEN: int = _R["receipts.hash_hex_len"].value
RECEIPTS_JSON_SEPARATORS: tuple[str, str] = (_R["receipts.json_field_sep"].value, _R["receipts.json_kv_sep"].value)


def canonical_json(d: dict) -> bytes:
    """The exact serialization a receipt line is hashed over -- one place,
    so write-time and verify-time can never disagree (cp19)."""
    return json.dumps(d, sort_keys=True, separators=RECEIPTS_JSON_SEPARATORS).encode()
ESTATE_ALERT_INBOX: Path = Path(_R["estate.alert_inbox"].value)


def append_alert(obj: dict) -> None:
    """cp11: appends one JSON line to ESTATE_ALERT_INBOX, the file the
    cockpit's `/api/inbox` already tails (sovereign/cockpit/server.py).
    File-locked the same way sovereign.engine.receipts.append() locks the
    receipt file, since more than one process (worker, CLI) can append
    here. Alerts are informational, not the signed receipt chain -- no
    hash, no signature -- so a lost alert is a missed notification, never
    a broken audit trail."""
    ESTATE_ALERT_INBOX.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({**obj, "ts": time.time()}, sort_keys=True, default=str)
    with open(ESTATE_ALERT_INBOX, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

TELEGRAM_BOT_TOKEN: str | None = _R["telegram.bot_token"].value
TELEGRAM_HOME_CHANNEL: str | None = _R["telegram.home_channel"].value

ESTATE_PUBLIC_URL: str | None = _R["estate.public_url"].value

COCKPIT_PORT: int = _R["cockpit.port"].value
COCKPIT_BIND: str = _R["cockpit.bind"].value

LANGFUSE_HOST: str | None = _R["langfuse.host"].value
LANGFUSE_PUBLIC_KEY: str | None = _R["langfuse.public_key"].value
LANGFUSE_SECRET_KEY: str | None = _R["langfuse.secret_key"].value

LITELLM_BASE_URL: str | None = _R["litellm.base_url"].value
LITELLM_API_KEY: str | None = _R["litellm.api_key"].value
LITELLM_CHAT_COMPLETIONS_PATH: str = _R["litellm.chat_completions_path"].value
SB_MODEL: str = _R["model.default"].value
SB_MODEL_VISION: str = _R["model.vision"].value
SB_MODEL_CONSENSUS: list[str] = _R["model.consensus"].value

SB_DEFAULT_BUDGET: int | None = _R["budget.default"].value
SB_DEFAULT_RUNNER: str = _R["runner.default"].value
STEP_START_TO_CLOSE_MIN: int = _R["step.start_to_close_min"].value
STEP_HEARTBEAT_S: int = _R["step.heartbeat_s"].value
BURN_TOKENS_PER_STEP: int = _R["burn.tokens_per_step"].value

CLI_PORT_PROBE_TIMEOUT_S: float = _R["cli.port_probe_timeout_s"].value
CLI_UP_WAIT_DEADLINE_S: int = _R["cli.up_wait_deadline_s"].value
CLI_UP_POLL_INTERVAL_S: float = _R["cli.up_poll_interval_s"].value
CLI_DOWN_WAIT_DEADLINE_S: int = _R["cli.down_wait_deadline_s"].value
NET_HOST_PORT_SEP: str = _R["net.host_port_sep"].value
SESSION_ID_HEX_LEN: int = _R["session.id_hex_len"].value
SESSION_LAST_OUTPUT_MAX_CHARS: int = _R["session.last_output_max_chars"].value
RUNNER_TOKEN_ESTIMATE_DIVISOR: int = _R["runner.token_estimate_divisor"].value
RUNNER_ASK_PREFIX: str = _R["runner.ask_prefix"].value
RUNNER_ASK_PREFIX_SEP: str = _R["runner.ask_prefix_sep"].value
RUNNER_LLM_TIMEOUT_S: int = _R["runner.llm_timeout_s"].value
RUNNER_CLAUDE_HEARTBEAT_INTERVAL_S: int = _R["runner.claude_heartbeat_interval_s"].value
RECEIPT_ACTIVITY_TIMEOUT_S: int = _R["receipt.activity_timeout_s"].value
RECEIPT_RETRY_MAX_ATTEMPTS: int = _R["receipt.retry_max_attempts"].value
NOTIFY_ACTIVITY_TIMEOUT_S: int = _R["notify.activity_timeout_s"].value
NOTIFY_RETRY_MAX_ATTEMPTS: int = _R["notify.retry_max_attempts"].value
STEP_ACTIVITY_RETRY_MAX_ATTEMPTS: int = _R["step.activity_retry_max_attempts"].value
CLI_EXIT_USAGE_ERROR: int = _R["cli.exit_usage_error"].value
CLIENT_QUERY_TIMEOUT_S: float = _R["client.query_timeout_s"].value
LOG_BOT_TOKEN_REDACT_PATTERN: str = _R["log.bot_token_redact_pattern"].value

TEMPORAL_PID_FILE: Path = ESTATE_HOME / "temporal" / "dev-server.pid"
WORKER_PID_FILE: Path = SOVEREIGN_HOME / "worker.pid"
TEMPORAL_LOG_FILE: Path = ESTATE_HOME / "temporal" / "dev-server.log"
WORKER_LOG_FILE: Path = SOVEREIGN_HOME / "logs" / "worker.log"


def ensure_dirs() -> None:
    SOVEREIGN_HOME.mkdir(parents=True, exist_ok=True)
    (SOVEREIGN_HOME / "logs").mkdir(parents=True, exist_ok=True)
    (ESTATE_HOME / "temporal").mkdir(parents=True, exist_ok=True)
    ESTATE_ALERT_INBOX.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Lint: every numeric literal outside {0, 1, -1} and every string literal
# containing "/" or ":" in sovereign/**/*.py, excluding this file and
# test_*.py, that is not a docstring, an f-string literal segment, or a
# logging/print call argument.
# ---------------------------------------------------------------------------


@dataclass
class LintHit:
    path: str
    line: int
    kind: str
    snippet: str


def _is_docstring(node: ast.AST, parent_body: list[ast.stmt]) -> bool:
    return bool(parent_body) and parent_body[0] is node


_LOG_METHOD_NAMES = ("info", "warning", "warn", "error", "debug", "critical", "exception")


def _is_log_or_print_call_arg(node: ast.Constant, tree: ast.AST) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            func = n.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name == "print" or "log" in name.lower() or name.lower() in _LOG_METHOD_NAMES:
                if node in ast.walk(n):
                    return True
            if name == "basicConfig" and node in ast.walk(n):
                return True
    return False


def _in_joinedstr(node: ast.Constant, tree: ast.AST) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            if node in n.values:
                return True
    return False


def lint(root: Path | None = None) -> list[LintHit]:
    root = root or Path(__file__).parent
    hits: list[LintHit] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root.parent) if root.parent in path.parents else path
        if path.name in ("config.py", "config_keys.py") or path.name.startswith("test_") or ".venv" in path.parts:
            # config.py and every config_keys.py are the config -- their
            # literals are the KEYS defaults themselves, not code that
            # should be reading them from config.
            continue
        try:
            src = path.read_text()
            tree = ast.parse(src, filename=str(path))
        except (OSError, SyntaxError):
            continue

        docstring_nodes: set[int] = set()
        for n in ast.walk(tree):
            body = getattr(n, "body", None)
            if isinstance(body, list) and body:
                first = body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    docstring_nodes.add(id(first.value))

        for n in ast.walk(tree):
            if not isinstance(n, ast.Constant):
                continue
            v = n.value
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                if v in (0, 1, -1):
                    continue
                hits.append(LintHit(str(rel), n.lineno, "number", repr(v)))
            elif isinstance(v, str):
                if id(n) in docstring_nodes:
                    continue
                if "/" not in v and ":" not in v:
                    continue
                if _in_joinedstr(n, tree):
                    continue
                if _is_log_or_print_call_arg(n, tree):
                    continue
                hits.append(LintHit(str(rel), n.lineno, "string", repr(v)[:60]))
    return hits
