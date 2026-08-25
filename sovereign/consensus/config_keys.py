"""consensus.* configurable keys -- cp22 "everything configurable".

Same shape as sovereign/otto/config_keys.py and sovereign/trust/config_keys.py:
{key: (default, type, env_name, help)}, merged into config.py's KEYS table.
Standalone get(), no import of sovereign.config, for the same reason those
two are standalone.

Note what is NOT redeclared here. consensus.timeout_s, consensus.quorum and
model.consensus are already in config.py's own KEYS table; config.py's
_merge_external_keys is first-writer-wins, so repeating them here would be
silently ignored and would read as if this file controlled them.
"""
from __future__ import annotations

import os
from typing import Any

CONSENSUS_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "consensus.cheap_model": (
        "ollama", str, "SB_CONSENSUS_CHEAP_MODEL",
        "Single model used for a non-destructive op: the last entry of every fallback "
        "chain in llm/config.yaml, and the only local (zero marginal cost) one"),
    "consensus.request_timeout_s": (
        30, float, "SB_CONSENSUS_REQUEST_TIMEOUT_S",
        "Per-model HTTP timeout for one vote through the LiteLLM proxy"),
    "consensus.temperature": (
        0, float, "SB_CONSENSUS_TEMPERATURE",
        "Sampling temperature for a vote -- 0, because a vote is a proposal to be "
        "compared, not prose"),
    "consensus.max_tokens": (
        256, int, "SB_CONSENSUS_MAX_TOKENS",
        "Per-vote completion cap; a tool call is short and the budget is $5/day"),
    "consensus.system_prompt": (
        "Reply with exactly one shell command and nothing else. No explanation, "
        "no code fences, no prose.", str, "SB_CONSENSUS_SYSTEM_PROMPT",
        "System message every voting model receives, so votes are comparable"),
    "consensus.quorum_separator": (
        "/", str, "SB_CONSENSUS_QUORUM_SEPARATOR",
        "What splits config key consensus.quorum, e.g. the 2 and the 3 of \"2/3\""),
    "consensus.policy_dirname": (
        "policy", str, "SB_CONSENSUS_POLICY_DIRNAME",
        "Directory of .rego policy under the idp checkout root"),
    "consensus.policy_namespace": (
        "sovereign.command", str, "SB_CONSENSUS_POLICY_NAMESPACE",
        "conftest --namespace for the command allowlist policy; deliberately not "
        "`main`, so it cannot collide with licences.rego and placement.rego"),
    "consensus.policy_binary": (
        "conftest", str, "SB_CONSENSUS_POLICY_BINARY",
        "The policy engine bin/policy-test already uses"),
    "consensus.policy_timeout_s": (
        30, float, "SB_CONSENSUS_POLICY_TIMEOUT_S",
        "Timeout for one conftest evaluation"),
    "consensus.destructive_markers": (
        "rm -rf,--force,--hard,drop table,truncate table,delete from,kubectl delete,"
        "terraform destroy,fly apps destroy,git push --force,mkfs,dd if",
        str, "SB_CONSENSUS_DESTRUCTIVE_MARKERS",
        "Comma-separated substrings that classify an op as destructive when the "
        "caller does not say. A marker list over-classifies by design: a "
        "non-destructive op wrongly sent to three models costs one Ollama call, a "
        "destructive one wrongly sent to one model costs the estate"),
}


def get(key: str) -> Any:
    default, typ, env_name, _help = CONSENSUS_KEYS[key]
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default
