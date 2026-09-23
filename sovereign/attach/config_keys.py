"""attach.* configurable keys -- cp22 "everything configurable".

Shape agreed with builder A: ATTACH_KEYS: {key: (default, type, env_name,
help)}. sovereign/config.py imports this module and merges ATTACH_KEYS
into its own KEYS table (see sovereign/attach/README.md for the two lines
A adds). Standalone by design, like otto/config_keys.py and
trust/config_keys.py: get() resolves env-or-default on its own.
"""
from __future__ import annotations

import os
from typing import Any

# {key: (default, type, env_name, help)}
ATTACH_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "attach.mode": (
        "local", str, "SB_ATTACH_MODE",
        "'local': state under <path>/.estate/; 'global': under $ESTATE_HOME/estates/<hash>/"),
    "attach.dirname": (
        ".estate", str, "SB_ATTACH_DIRNAME",
        "Dirname created at the attach root (local mode) holding policy + receipts"),
    "attach.global_estates_dirname": (
        "estates", str, "SB_ATTACH_GLOBAL_ESTATES_DIRNAME",
        "Dirname under $ESTATE_HOME holding global-mode estate state, keyed by path hash"),
    "attach.path_hash_hex_len": (
        12, int, "SB_ATTACH_PATH_HASH_HEX_LEN",
        "Chars of sha256(path) used as the global-mode estate key"),
    "attach.registry_filename": (
        "registry.jsonl", str, "SB_ATTACH_REGISTRY_FILENAME",
        "Filename under $ESTATE_HOME holding the list of attached estates"),
    "attach.policy_filename": (
        "AGENTS.md", str, "SB_ATTACH_POLICY_FILENAME",
        "Policy filename read at the attach root and scaffolded under .estate/ if absent"),
    "attach.receipts_filename": (
        "receipts.jsonl", str, "SB_ATTACH_RECEIPTS_FILENAME",
        "Receipts filename under the estate's .estate/ dir"),
    "attach.destructive_patterns": (
        ["rm -rf", "git push --force", "git reset --hard", "DROP TABLE"], list,
        "SB_ATTACH_DESTRUCTIVE_PATTERNS",
        "Substrings that mark a command destructive: quorum + hardware signature required"),
    "attach.quorum": (
        "2/3", str, "SB_ATTACH_QUORUM",
        "Approvals required for a destructive command, same shape as consensus.quorum"),
    "attach.mounted_receipt_template": (
        "[✓] ESTATE_MOUNTED | root:{root} | nodes:{nodes} | hash:{hash}", str,
        "SB_ATTACH_MOUNTED_RECEIPT_TEMPLATE", "cp21 receipt line, exact format"),
    "attach.policy_inherited_receipt_template": (
        "[✓] POLICY_INHERITED | policy:{policy} | mode:{mode}", str,
        "SB_ATTACH_POLICY_INHERITED_RECEIPT_TEMPLATE", "cp21 receipt line, exact format"),
    "attach.policy_scaffolded_label": (
        "AGENTS.md (auto-scaffolded)", str, "SB_ATTACH_POLICY_SCAFFOLDED_LABEL", ""),
    "attach.policy_existing_label": (
        "AGENTS.md", str, "SB_ATTACH_POLICY_EXISTING_LABEL", ""),
    "attach.policy_mode": (
        "Ghost", str, "SB_ATTACH_POLICY_MODE",
        "The conservative default mode named in the POLICY_INHERITED receipt"),
    "attach.git_ls_files_timeout_s": (
        30, float, "SB_ATTACH_GIT_LS_FILES_TIMEOUT_S", "Timeout for `git ls-files` when counting nodes"),
    "attach.ignored_dirnames": (
        [".git", ".estate", "node_modules", "__pycache__", ".venv"], list,
        "SB_ATTACH_IGNORED_DIRNAMES", "Dirnames skipped when walking a non-git target"),
    "attach.write_verbs": (
        ["write", "edit", "create", "delete", "mv", "mkdir", "chmod"], list,
        "SB_ATTACH_WRITE_VERBS", "Prefixes/verbs classified as a write operation"),
    "attach.git_write_verbs": (
        ["add", "commit", "push", "merge", "rebase", "checkout", "reset", "branch", "tag"], list,
        "SB_ATTACH_GIT_WRITE_VERBS", "`git <verb>` subcommands classified as a git write"),
    "attach.default_runner": (
        "echo", str, "SB_ATTACH_START_RUNNER",
        "Default --runner when `sb start --estate` omits one (mirrors runner.default)"),
    "attach.status_max_sessions_per_estate": (
        50, int, "SB_ATTACH_STATUS_MAX_SESSIONS_PER_ESTATE",
        "Sessions listed per estate in `sb status` before truncation"),
    "attach.cli_attach_help": (
        "mount a repo, directory or workspace as an estate", str,
        "SB_ATTACH_CLI_ATTACH_HELP", "argparse help for `sb attach`"),
    "attach.cli_write_policy_help": (
        "also write a scaffolded AGENTS.md into the repo root; default is .estate/ only", str,
        "SB_ATTACH_CLI_WRITE_POLICY_HELP", "argparse help for `sb attach --write-policy`"),
    "attach.cli_status_help": (
        "list every attached estate and its running sessions", str,
        "SB_ATTACH_CLI_STATUS_HELP", "argparse help for `sb status`"),
    "attach.cli_halt_help": (
        "stop every running session across every attached estate", str,
        "SB_ATTACH_CLI_HALT_HELP", "argparse help for `sb halt`"),
    "attach.cli_halt_all_help": (
        "required; halt has no single-session form here, use sb stop", str,
        "SB_ATTACH_CLI_HALT_ALL_HELP", "argparse help for `sb halt --all`"),
}


def get(key: str) -> Any:
    """Resolve one attach.* key: env override, else the default. Standalone
    by design -- see module docstring."""
    default, typ, env_name, _help = ATTACH_KEYS[key]
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    if typ is list:
        return default if raw is None else [x.strip() for x in raw.split(",") if x.strip()]
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default
