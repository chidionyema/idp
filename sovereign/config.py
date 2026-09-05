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
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def _vault_dir() -> Path:
    """The estate secret store: the sops+age directory vault (crew#119 ruling,
    STANDARDS "Secrets" row). Located the way bin/idp-vault-put locates it:
    $ESTATE_SECRETS, else $ESTATE_CODE/estate-secrets, else the sibling
    checkout of this one. Never a literal path (LAW 46)."""
    if os.environ.get("ESTATE_SECRETS"):
        return Path(os.environ["ESTATE_SECRETS"])
    code = os.environ.get("ESTATE_CODE") or str(Path(__file__).resolve().parents[2])
    return Path(code) / "estate-secrets"


def _vault_env_name() -> str:
    """Which secrets/<env>/ directory this host reads: ESTATE_HOME/env, the
    same file bin/catalog-gen resolves the lifecycle label from; dev otherwise."""
    try:
        name = (ESTATE_HOME / "env").read_text().strip().lower()
    except OSError:
        name = ""
    return name or "dev"


def _vault_get(key: str) -> str | None:
    """One value from the secret store through its one egress,
    scripts/secret-load, or None when the vault, the file or the age identity
    is absent. Never raises: no vault is the CI case, and the key then reads
    unset exactly as it did before the vault existed."""
    loader = _vault_dir() / "scripts" / "secret-load"
    if not loader.is_file():
        return None
    try:
        run = subprocess.run(
            [str(loader), _vault_env_name(), key, key],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return run.stdout if run.returncode == 0 and run.stdout else None


def _secret(key: str) -> str | None:
    """Default for a credential KeySpec: the secret store first, the
    operator's estate.env second. The store wins so a stale copy in the env
    file cannot outlive a rotation (crew#284 CP2: LITELLM_BASE_URL "set from
    the secret store"). Skipped entirely when the process env already
    carries the key, because KeySpec lets the env var win and the sops
    decrypt would be a wasted subprocess."""
    if os.environ.get(key):
        return None
    return _vault_get(key) or _ENV_FILE_VALUES.get(key)


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

    # crew#396 step 3: KiniFinishWorkflow. One activity per KINI checkpoint (crew#284 CP1-CP7);
    # each runs the bdd files bound to that checkpoint and returns pass / fail / unbound /
    # platform-fault. Paths are relative to kini.sovereign_dir; an empty list is "unbound".
    "kini.checkpoint_count": KeySpec(7, "int", "KINI_CHECKPOINT_COUNT", "CP1..CPn"),
    "kini.cp1_tests": KeySpec("tests/bdd/test_self_aware_cp1.py", "str", "KINI_CP1_TESTS", "space-separated pytest paths"),
    "kini.cp2_tests": KeySpec("tests/bdd/test_self_aware_cp2.py tests/bdd/test_cp2_litellm_real.py", "str", "KINI_CP2_TESTS", ""),
    "kini.cp3_tests": KeySpec("tests/bdd/test_self_aware_cp3.py tests/bdd/test_cp3_worker_registry.py", "str", "KINI_CP3_TESTS", ""),
    "kini.cp4_tests": KeySpec("", "str", "KINI_CP4_TESTS", "presence UI: unbound until its feature lands"),
    "kini.cp5_tests": KeySpec("", "str", "KINI_CP5_TESTS", "daily digest: unbound until its feature lands"),
    "kini.cp6_tests": KeySpec("", "str", "KINI_CP6_TESTS", "auto-termination: unbound until its feature lands"),
    "kini.cp7_tests": KeySpec("", "str", "KINI_CP7_TESTS", "identity: unbound until its feature lands"),
    "kini.sovereign_dir": KeySpec(str(Path(__file__).resolve().parent), "path", "KINI_SOVEREIGN_DIR", "pytest cwd; bdd_features_base_dir=.. resolves from here"),
    "kini.pytest_args": KeySpec(["-q", "-p", "no:cacheprovider"], "list", "KINI_PYTEST_ARGS", "the worker's rootfs is read-only"),
    "kini.pytest_exit_no_tests": KeySpec(5, "int", None, "pytest exit code for 'no tests collected'"),
    "kini.output_tail_lines": KeySpec(40, "int", "KINI_OUTPUT_TAIL_LINES", "lines of pytest output kept in the result"),
    "kini.cp_timeout_s": KeySpec(900, "int", "KINI_CP_TIMEOUT_S", "start_to_close per checkpoint activity"),
    "kini.cp_heartbeat_s": KeySpec(60, "int", "KINI_CP_HEARTBEAT_S", "heartbeat interval while pytest runs"),
    "kini.heartbeat_timeout_s": KeySpec(120, "int", "KINI_HEARTBEAT_TIMEOUT_S", "Temporal heartbeat_timeout on both activities"),
    "kini.cp_attempts": KeySpec(3, "int", "KINI_CP_ATTEMPTS", "RetryPolicy maximum_attempts per checkpoint activity"),
    "kini.heal_attempts": KeySpec(3, "int", "KINI_HEAL_ATTEMPTS", "RetryPolicy maximum_attempts for the heal activity"),
    "kini.heal_timeout_s": KeySpec(600, "int", "KINI_HEAL_TIMEOUT_S", "how long the heal activity waits for the cluster to report ready"),
    "kini.heal_poll_s": KeySpec(30, "int", "KINI_HEAL_POLL_S", "pause between a platform-fault and the re-run"),
    "kini.heal_max_rounds": KeySpec(5, "int", "KINI_HEAL_MAX_ROUNDS", "platform-fault -> heal -> re-run rounds per checkpoint before giving up"),
    "kini.workflow_id": KeySpec("kini-finish", "str", "KINI_WORKFLOW_ID", "one run at a time: Temporal refuses a second start while it runs"),
    "kini.k8s_host_env": KeySpec("KUBERNETES_SERVICE_HOST", "str", None, "set only inside a pod"),
    "kini.k8s_port_env": KeySpec("KUBERNETES_SERVICE_PORT", "str", None, ""),
    "kini.k8s_token_file": KeySpec("/var/run/secrets/kubernetes.io/serviceaccount/token", "path", "KINI_K8S_TOKEN_FILE", ""),
    "kini.k8s_ca_file": KeySpec("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt", "path", "KINI_K8S_CA_FILE", ""),
    "kini.k8s_nodes_path": KeySpec("/api/v1/nodes", "str", None, "the same probe platform/state reads for the cluster-state receipt"),
    "kini.k8s_request_timeout_s": KeySpec(15, "int", "KINI_K8S_REQUEST_TIMEOUT_S", ""),

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

    "shadow.heads_dir": KeySpec(str(_estate_home() / "heads"), "path", "SB_SHADOW_HEADS_DIR", "cp9/R15: dir holding every branch-pointer file; spec 3.1 topology is <estate.home>/heads, one level under estate.home and never a second .estate under it"),
    "shadow.head_filename": KeySpec("shadow_main", "str", None, "cp9: shadow_main -- the head that always names the DAG root equal to the legacy DB's current state"),
    "shadow.legacy_heads_dirs": KeySpec([str(_estate_home() / ".estate" / "heads")], "list", "SB_SHADOW_LEGACY_HEADS_DIRS", "R15: extra dirs the sweep also reads. The default is where the pre-fix doubled-.estate default wrote heads on this Mac; the sweep must be able to see an instance it no longer creates"),
    "dag.main_head_filename": KeySpec("main", "str", "SB_DAG_MAIN_HEAD", "R15: the head every rewind/recover moves; sits beside shadow_main in shadow.heads_dir"),
    "dag.node_suffix": KeySpec(".json", "str", None, "R15: filename suffix of one content-addressed DAG node"),
    "dag.max_walk_nodes": KeySpec(1000000, "int", "SB_DAG_MAX_WALK_NODES", "R15: hard stop on a DAG walk, so a corrupt chain can never spin forever"),

    "ops.fs_commit_tokens": KeySpec(200, "int", "SB_OPS_FS_COMMIT_TOKENS", "R9: tokens charged for one fs_commit (spec 3.1 checkpoint example: added_tokens 200)"),
    "ops.default_tokens": KeySpec(100, "int", "SB_OPS_DEFAULT_TOKENS", "R9: tokens charged for an op with no entry of its own"),
    "ops.nondestructive": KeySpec(["fs_commit", "fs_read", "git_status", "tool_result", "doc_commit", "budget_refill"], "list", "SB_OPS_NONDESTRUCTIVE", "R9: ops that need budget only -- no quorum, no hardware signature (spec 2.3 step 3)"),
    "ops.destructive": KeySpec(["fs_delete", "git_push_force", "db_drop", "service_destroy", "rewind"], "list", "SB_OPS_DESTRUCTIVE", "R9: ops that need quorum and a hardware signature on top of budget"),

    "budget.db_filename": KeySpec(str(_estate_home() / "sovereign" / "budget.db"), "path", "SB_BUDGET_DB", "R29: sqlite file holding one versioned budget row per session, the optimistic lock"),
    "budget.max_cas_retries": KeySpec(50, "int", "SB_BUDGET_MAX_CAS_RETRIES", "R29: compare-and-swap attempts before a spend gives up rather than spinning"),
    "budget.busy_timeout_ms": KeySpec(5000, "int", "SB_BUDGET_BUSY_TIMEOUT_MS", "R29: sqlite busy_timeout for the budget connection"),

    "fsm.cycle_path": KeySpec(["planning", "tool_use", "synthesis"], "list", "SB_FSM_CYCLE_PATH", "R30: the repeating loop counted against fsm.max_cycles (spec 4.3)"),
    "fsm.initial_state": KeySpec("init", "str", None, "R28: the state every session starts in"),
    "fsm.terminal_state": KeySpec("terminal", "str", None, "R28: the state no transition leaves"),

    "interventions.dir": KeySpec(str(_estate_home() / "interventions"), "path", "SB_INTERVENTIONS_DIR", "R17: append-only transparency log dir, spec 3.1 topology <estate.home>/interventions"),
    "interventions.filename_sep": KeySpec("_", "str", None, "R17: separator in <counter><sep><hash>.json"),
    "interventions.kinds": KeySpec(["stop", "approve", "deny", "steer", "refill", "undo", "rewind", "recover", "halt"], "list", "SB_INTERVENTIONS_KINDS", "R17: receipt kinds mirrored into the intervention log"),

    "receipts.counter_filename": KeySpec("receipts.counter", "str", "SB_RECEIPTS_COUNTER_FILENAME", "R23: signed monotonic-counter watermark; survives deletion of the log itself"),

    "undo.git_timeout_s": KeySpec(30, "int", "SB_UNDO_GIT_TIMEOUT_S", "R7: timeout on one git subprocess call made by undo/rewind"),
    "undo.parent_suffix": KeySpec("^", "str", None, "R7: git revision suffix naming a commit's first parent"),
    "recover.start_services": KeySpec(True, "bool", "SB_RECOVER_START_SERVICES", "cp35: whether `sb recover` also brings the worker and Temporal back up"),
    "views.dir": KeySpec(str(_estate_home() / "sovereign" / "views"), "path", "SB_VIEWS_DIR", "cp33/cp35: dir holding the projection views rebuilt from the DAG by rewind and recover"),
    "views.main_filename": KeySpec("main.json", "str", None, "cp33/cp35: the projection view of heads/main, materialized state plus the root it came from"),

    "dualread.max_overhead_ms": KeySpec(15, "int", "SB_DUALREAD_MAX_OVERHEAD_MS", "cp10: p95 budget for the dual-read router's added cost (DAG walk + receipt) over the legacy-only read, measured over 1000 reads"),
    "dualread.latency_round_ndigits": KeySpec(4, "int", None, "cp10: decimal places dual-read latencies are rounded to before entering a receipt"),
    "time.ms_per_second": KeySpec(1000, "int", None, "milliseconds per second, for every perf_counter() duration reported in ms"),

    "fork.dir": KeySpec(str(_estate_home() / "sovereign" / "forks"), "path", "SB_FORK_DIR", "cp12: disk-backed fork state/dag/receipts root, used once fork.max_parallel is exceeded"),
    "fork.max_ms": KeySpec(1000, "int", "SB_FORK_MAX_MS", "cp12: budget for `sb fork`'s elapsed_ms -- a fork is one pointer-file copy, never a data copy, so this is a correctness bound, not a target to tune toward"),
    "fork.max_parallel": KeySpec(3, "int", "SB_FORK_MAX_PARALLEL", "cp12: in-memory forks allowed open at once before a new fork spills to fork.dir on disk"),
    "fork.working_pointer_filename": KeySpec("working_branch", "str", None, "cp12: file under sovereign/ naming the branch `sb switch` last pointed at"),
    "fork.memory_dsn": KeySpec(":memory:", "str", None, "cp12: sqlite3.connect() DSN for an in-memory fork, below fork.max_parallel"),

    "telegram.bot_token": KeySpec(_ENV_FILE_VALUES.get("TELEGRAM_BOT_TOKEN"), "str", "TELEGRAM_BOT_TOKEN", "", secret=True),
    "telegram.home_channel": KeySpec(_ENV_FILE_VALUES.get("TELEGRAM_HOME_CHANNEL"), "str", "TELEGRAM_HOME_CHANNEL", ""),

    "cockpit.port": KeySpec(8788, "int", "COCKPIT_PORT", ""),
    "cockpit.bind": KeySpec(_loopback(), "str", "COCKPIT_BIND", ""),

    "langfuse.host": KeySpec(_ENV_FILE_VALUES.get("LANGFUSE_HOST"), "str", "LANGFUSE_HOST", ""),
    "langfuse.public_key": KeySpec(_ENV_FILE_VALUES.get("LANGFUSE_PUBLIC_KEY"), "str", "LANGFUSE_PUBLIC_KEY", "", secret=True),
    "langfuse.secret_key": KeySpec(_ENV_FILE_VALUES.get("LANGFUSE_SECRET_KEY"), "str", "LANGFUSE_SECRET_KEY", "", secret=True),

    "litellm.base_url": KeySpec(_secret("LITELLM_BASE_URL"), "str", "LITELLM_BASE_URL", "from the estate secret store (secrets/<env>/LITELLM_BASE_URL.yaml), estate.env as the fallback"),
    "litellm.api_key": KeySpec(_secret("LITELLM_API_KEY"), "str", "LITELLM_API_KEY", "a budgeted LiteLLM virtual key (alias sovereign-kernel), never the proxy master key; from the secret store", secret=True),
    "litellm.chat_completions_path": KeySpec("/chat/completions", "str", "LITELLM_CHAT_COMPLETIONS_PATH", ""),

    "budget.default": KeySpec(None, "int", "SB_DEFAULT_BUDGET", "tokens; None means budget is required at start"),
    "runner.default": KeySpec("echo", "str", "SB_DEFAULT_RUNNER", ""),
    "model.default": KeySpec("deepseek", "str", "SB_MODEL", "LiteLLM alias for the llm runner"),
    "model.vision": KeySpec("vision", "str", "SB_MODEL_VISION", "LiteLLM alias, vision-capable"),
    "model.consensus": KeySpec(["deepseek", "minimax", "gemini"], "list", "SB_MODEL_CONSENSUS", "comma-separated aliases; three different models (spec 4.2): one local, two hosted, because a second local voter on a 16 GB laptop misses the 30 s deadline (measured 2026-08-26: 3-4B models 60-75 s per answer)"),

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
    "approval.timeout_min": KeySpec(15, "int", "SB_APPROVAL_TIMEOUT_MIN", "R12 default-deny: minutes an approval request may go unanswered before the workflow halts itself. Silence is not consent, so this halts rather than denies -- a denial would end the session and lose the work, and the founder who was in a meeting can still refill/approve"),
    "trust.require_signed_approval": KeySpec(True, "bool", "SB_REQUIRE_SIGNED_APPROVAL", "R11/R22: refuse `sb approve` without a verified signature. Off only for a host with no trust anchor at all, and the receipt records which"),
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
    "flip.readonly_mode": KeySpec(0o444, "int", None, "cp13: filesystem mode `sb flip` chmods the legacy DB file to"),
    "flip.writable_mode": KeySpec(0o644, "int", None, "cp13: filesystem mode `sb flip --rollback` restores"),
    "flip.max_downtime_ms": KeySpec(250, "int", "SB_FLIP_MAX_DOWNTIME_MS", "cp13: budget for the chmod + one shadow-root verify() a flip takes; reads are never blocked, this bounds the window before the flip is durable"),
    "flip.receipt_template": KeySpec("[✓] FLIP | root:{root} | legacy:readonly", "str", "SB_FLIP_RECEIPT_TEMPLATE", "cp13 receipt line, exact format"),
    "flip.rollback_receipt_template": KeySpec("[✓] FLIP_ROLLBACK | root:{root} | legacy:writable", "str", "SB_FLIP_ROLLBACK_RECEIPT_TEMPLATE", "cp13 receipt line, exact format"),
    "flip.hash_chunk_bytes": KeySpec(65536, "int", None, "cp13: read chunk size for the legacy DB's sha256 in flip.py -- a lint-exempt literal would trip config.py's own numeric-literal rule"),
    "projection.store_path": KeySpec(str(_estate_home() / "sovereign" / "projection.json"), "path", "SB_PROJECTION_STORE_PATH", "cp14: the hot store rebuilt from the DAG, one JSON file keyed by table then rowid"),
    "rebuild.receipt_template": KeySpec("[✓] REBUILD | root:{root}", "str", "SB_REBUILD_RECEIPT_TEMPLATE", "cp14 receipt line, exact format from features/sovereign-bus/cp14_projection_views.feature"),
    "cross_stack.git_timeout_s": KeySpec(5, "int", "SB_CROSS_STACK_GIT_TIMEOUT_S", "cp15: timeout for the `git rev-parse HEAD` subprocess call that produces code_root"),
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

try:
    from sovereign.consensus.config_keys import CONSENSUS_KEYS

    _merge_external_keys(CONSENSUS_KEYS)
except ImportError:
    pass

try:
    from sovereign.engine.config_keys import TERMINATION_KEYS

    _merge_external_keys(TERMINATION_KEYS)
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Presence block (W3, master spec 2.1, 2.2, 2.5, 2.6). Every presence.* key
# -- the state file the menu bar dot reads, the digest hour and line cap,
# the receipt format, the haptic switch, the Spatial colours, the Siri
# sentence -- is defined once in sovereign/presence/config_keys.py and
# merged here. Nothing under sovereign/presence/ types a literal.
# ---------------------------------------------------------------------------
try:
    from sovereign.presence.config_keys import PRESENCE_KEYS

    _merge_external_keys(PRESENCE_KEYS)
except ImportError:
    pass

try:
    from sovereign.shadow.config_keys import SHADOW_KEYS

    _merge_external_keys(SHADOW_KEYS)
except ImportError:
    pass

try:
    from sovereign.intake.config_keys import INTAKE_KEYS

    _merge_external_keys(INTAKE_KEYS)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# crew#219 R38/R40: the living policy. AGENTS.md at the repository root is the
# one place the per-day budgets, the cost contract, the routing table and the
# merge criteria are written; sovereign/policy.py parses its toml block and
# the keys below are built from it, so the doc cannot drift from the code.
# A missing or unparseable block raises here, on import, rather than
# defaulting: config with no policy behind it is the thing R38 exists to end.
# ---------------------------------------------------------------------------

from sovereign.policy import load as _load_policy  # noqa: E402

POLICY = _load_policy()


def _env_name(prefix: str, name: str) -> str:
    return prefix + name.upper().replace(".", "_").replace("-", "_")


for _name, _usd in POLICY.budget_usd_per_day.items():
    KEYS[f"budget.usd_per_day.{_name}"] = KeySpec(
        float(_usd), "float", _env_name("SB_BUDGET_USD_PER_DAY_", _name),
        f"R40: default USD per day {_name} may spend; the sum over cost.days_per_month sits inside the cost contract (AGENTS.md)")
KEYS["cost.contract_min_usd_month"] = KeySpec(float(POLICY.cost["contract_min_usd_month"]), "float", "SB_COST_CONTRACT_MIN_USD_MONTH", "R40: spec section 8 floor of direct monthly cost (AGENTS.md)")
KEYS["cost.contract_max_usd_month"] = KeySpec(float(POLICY.cost["contract_max_usd_month"]), "float", "SB_COST_CONTRACT_MAX_USD_MONTH", "R40: spec section 8 ceiling of direct monthly cost (AGENTS.md)")
KEYS["cost.days_per_month"] = KeySpec(int(POLICY.cost["days_per_month"]), "int", "SB_COST_DAYS_PER_MONTH", "R40: days the per-day budgets are summed over (AGENTS.md)")
for _purpose, _alias in POLICY.routing.items():
    KEYS[f"routing.{_purpose}"] = KeySpec(
        list(_alias) if isinstance(_alias, list) else str(_alias), "list" if isinstance(_alias, list) else "str",
        _env_name("SB_ROUTING_", _purpose), f"R38: LiteLLM alias(es) used for {_purpose} (AGENTS.md routing table)")
KEYS["merge.strict_branches"] = KeySpec(list(POLICY.merge["strict_branches"]), "list", "SB_MERGE_STRICT_BRANCHES", "R41: branches whose PRs fail on any pending feature (AGENTS.md)")
KEYS["merge.require_bdd_green"] = KeySpec(bool(POLICY.merge["require_bdd_green"]), "bool", "SB_MERGE_REQUIRE_BDD_GREEN", "R41: a PR needs sovereign/tests/bdd green (AGENTS.md)")
KEYS["merge.pending_owner_required_on"] = KeySpec(list(POLICY.merge["pending_owner_required_on"]), "list", "SB_MERGE_PENDING_OWNER_REQUIRED_ON", "R39: branches where a pending mark must name a real owner (AGENTS.md)")


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

KINI_CHECKPOINT_COUNT: int = _R["kini.checkpoint_count"].value
KINI_CP_TESTS: dict[int, list[str]] = {
    n: str(_R[f"kini.cp{n}_tests"].value or "").split() for n in range(1, KINI_CHECKPOINT_COUNT + 1)
}
KINI_SOVEREIGN_DIR: Path = Path(_R["kini.sovereign_dir"].value)
KINI_PYTEST_ARGS: list[str] = _R["kini.pytest_args"].value
KINI_PYTEST_EXIT_NO_TESTS: int = _R["kini.pytest_exit_no_tests"].value
KINI_OUTPUT_TAIL_LINES: int = _R["kini.output_tail_lines"].value
KINI_CP_TIMEOUT_S: int = _R["kini.cp_timeout_s"].value
KINI_CP_HEARTBEAT_S: int = _R["kini.cp_heartbeat_s"].value
KINI_HEARTBEAT_TIMEOUT_S: int = _R["kini.heartbeat_timeout_s"].value
KINI_CP_ATTEMPTS: int = _R["kini.cp_attempts"].value
KINI_HEAL_ATTEMPTS: int = _R["kini.heal_attempts"].value
KINI_HEAL_TIMEOUT_S: int = _R["kini.heal_timeout_s"].value
KINI_HEAL_POLL_S: int = _R["kini.heal_poll_s"].value
KINI_HEAL_MAX_ROUNDS: int = _R["kini.heal_max_rounds"].value
KINI_WORKFLOW_ID: str = _R["kini.workflow_id"].value
KINI_K8S_HOST_ENV: str = _R["kini.k8s_host_env"].value
KINI_K8S_PORT_ENV: str = _R["kini.k8s_port_env"].value
KINI_K8S_TOKEN_FILE: Path = Path(_R["kini.k8s_token_file"].value)
KINI_K8S_CA_FILE: Path = Path(_R["kini.k8s_ca_file"].value)
KINI_K8S_NODES_PATH: str = _R["kini.k8s_nodes_path"].value
KINI_K8S_REQUEST_TIMEOUT_S: int = _R["kini.k8s_request_timeout_s"].value


def kini_workflow_params() -> dict[str, Any]:
    """Everything KiniFinishWorkflow needs, carried in params: a workflow never imports
    sovereign.config (see sovereign/engine/workflow.py), so the trigger hands it these."""
    return {
        "checkpoints": list(range(1, KINI_CHECKPOINT_COUNT + 1)),
        "cp_timeout_s": KINI_CP_TIMEOUT_S,
        "cp_heartbeat_s": KINI_CP_HEARTBEAT_S,
        "heartbeat_timeout_s": KINI_HEARTBEAT_TIMEOUT_S,
        "cp_attempts": KINI_CP_ATTEMPTS,
        "heal_attempts": KINI_HEAL_ATTEMPTS,
        "heal_timeout_s": KINI_HEAL_TIMEOUT_S,
        "heal_poll_s": KINI_HEAL_POLL_S,
        "heal_max_rounds": KINI_HEAL_MAX_ROUNDS,
    }

SB_RECEIPTS: Path = Path(_R["receipts.path"].value)
RECEIPTS_HEAD: Path = Path(_R["receipts.head_dir"].value) / _R["receipts.head_filename"].value
SIDECAR_TARGET: str = _R["sidecar.target"].value
SIDECAR_DAG_DIR: Path = Path(_R["sidecar.dag_dir"].value)
SIDECAR_HEAD_FILENAME: str = _R["sidecar.head_filename"].value
SHADOW_HEADS_DIR: Path = Path(_R["shadow.heads_dir"].value)
SHADOW_HEAD_FILENAME: str = _R["shadow.head_filename"].value
DAG_MAIN_HEAD_FILENAME: str = _R["dag.main_head_filename"].value
DAG_NODE_SUFFIX: str = _R["dag.node_suffix"].value
DAG_MAX_WALK_NODES: int = _R["dag.max_walk_nodes"].value
OPS_FS_COMMIT_TOKENS: int = _R["ops.fs_commit_tokens"].value
OPS_DEFAULT_TOKENS: int = _R["ops.default_tokens"].value
SHADOW_LEGACY_HEADS_DIRS: list[str] = _R["shadow.legacy_heads_dirs"].value
OPS_NONDESTRUCTIVE: list[str] = _R["ops.nondestructive"].value
OPS_DESTRUCTIVE: list[str] = _R["ops.destructive"].value
BUDGET_DB: Path = Path(_R["budget.db_filename"].value)
BUDGET_MAX_CAS_RETRIES: int = _R["budget.max_cas_retries"].value
BUDGET_BUSY_TIMEOUT_MS: int = _R["budget.busy_timeout_ms"].value
FSM_CYCLE_PATH: list[str] = _R["fsm.cycle_path"].value
FSM_INITIAL_STATE: str = _R["fsm.initial_state"].value
FSM_TERMINAL_STATE: str = _R["fsm.terminal_state"].value
FSM_MAX_CYCLES: int = _R["fsm.max_cycles"].value
INTERVENTIONS_DIR: Path = Path(_R["interventions.dir"].value)
INTERVENTIONS_FILENAME_SEP: str = _R["interventions.filename_sep"].value
INTERVENTIONS_KINDS: list[str] = _R["interventions.kinds"].value
RECEIPTS_COUNTER: Path = Path(_R["receipts.head_dir"].value) / _R["receipts.counter_filename"].value
UNDO_GIT_TIMEOUT_S: int = _R["undo.git_timeout_s"].value
UNDO_PARENT_SUFFIX: str = _R["undo.parent_suffix"].value
RECOVER_START_SERVICES: bool = _R["recover.start_services"].value
VIEWS_DIR: Path = Path(_R["views.dir"].value)
VIEWS_MAIN_FILENAME: str = _R["views.main_filename"].value
DUALREAD_MAX_OVERHEAD_MS: int = _R["dualread.max_overhead_ms"].value
DUALREAD_LATENCY_ROUND_NDIGITS: int = _R["dualread.latency_round_ndigits"].value
MS_PER_SECOND: int = _R["time.ms_per_second"].value
FORK_DIR: Path = Path(_R["fork.dir"].value)
FORK_MAX_MS: int = _R["fork.max_ms"].value
FORK_MAX_PARALLEL: int = _R["fork.max_parallel"].value
FORK_WORKING_POINTER: Path = SOVEREIGN_HOME / _R["fork.working_pointer_filename"].value
FORK_MEMORY_DSN: str = _R["fork.memory_dsn"].value
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
APPROVAL_TIMEOUT_MIN: int = _R["approval.timeout_min"].value
REQUIRE_SIGNED_APPROVAL: bool = _R["trust.require_signed_approval"].value
CLI_EXIT_USAGE_ERROR: int = _R["cli.exit_usage_error"].value
CLIENT_QUERY_TIMEOUT_S: float = _R["client.query_timeout_s"].value
LOG_BOT_TOKEN_REDACT_PATTERN: str = _R["log.bot_token_redact_pattern"].value
FLIP_READONLY_MODE: int = _R["flip.readonly_mode"].value
FLIP_WRITABLE_MODE: int = _R["flip.writable_mode"].value
FLIP_MAX_DOWNTIME_MS: int = _R["flip.max_downtime_ms"].value
FLIP_RECEIPT_TEMPLATE: str = _R["flip.receipt_template"].value
FLIP_ROLLBACK_RECEIPT_TEMPLATE: str = _R["flip.rollback_receipt_template"].value
FLIP_HASH_CHUNK_BYTES: int = _R["flip.hash_chunk_bytes"].value
PROJECTION_STORE_PATH: Path = Path(_R["projection.store_path"].value)
REBUILD_RECEIPT_TEMPLATE: str = _R["rebuild.receipt_template"].value,
CROSS_STACK_GIT_TIMEOUT_S: int = _R["cross_stack.git_timeout_s"].value

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
