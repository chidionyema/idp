"""shadow-side config keys (W5: spec 2.4, 3.2, 3.3, 3.4) -- cp22.

Same {key: (default, type, env_name, help)} shape as the otto, cockpit,
trust, attach, consensus and termination tables; config.py merges it into
KEYS. Standalone get() with no import of sovereign.config, for the same
reason those are standalone (config.py imports this file, not the other
way round).

Keys config.py already owns are NOT redeclared here, because
_merge_external_keys is first-writer-wins and a copy would be ignored
while looking authoritative: shadow.min_confidence (0.95), branch.count
(3) and branch.budget_pct (10) live in config.py's own table and are read
through sovereign.config.get() at the call site.
"""
from __future__ import annotations

import os
from typing import Any

SHADOW_KEYS: dict[str, tuple[Any, type, str, str]] = {
    # -- 2.4 / 3.4 predictive pre-authorization ------------------------------
    "shadow.horizon_steps": (
        3, int, "SB_SHADOW_HORIZON_STEPS",
        "How many steps ahead the shadow planning loop simulates spend (spec 2.4: 'within the next 3 steps')"),
    "shadow.min_samples": (
        20, int, "SB_SHADOW_MIN_SAMPLES",
        "Founder decisions of one boundary kind the shadow-founder needs before its confidence is trusted at all; below this it reports 0"),
    "shadow.refill_round_to": (
        1000, int, "SB_SHADOW_REFILL_ROUND_TO",
        "A predicted refill is rounded up to a multiple of this many tokens so the card asks a round number"),
    "shadow.refill_boundary_kind": (
        "budget_refill", str, "SB_SHADOW_REFILL_BOUNDARY_KIND",
        "The boundary kind a budget prediction is recorded and looked up under (spec 3.4's receipt: boundary:budget_refill)"),
    "shadow.auth_receipt_kind": (
        "shadow_auth", str, "SB_SHADOW_AUTH_RECEIPT_KIND",
        "Receipt kind written when the shadow-founder authorizes on the founder's behalf"),
    "shadow.approve_kind": (
        "approve", str, "SB_SHADOW_APPROVE_KIND",
        "Receipt kind counted as a founder approval when the shadow-founder measures its confidence"),
    "shadow.deny_kind": (
        "deny", str, "SB_SHADOW_DENY_KIND",
        "Receipt kind counted as a founder denial"),
    "shadow.founder": (
        "founder", str, "SB_SHADOW_FOUNDER",
        "The `by` value that marks a receipt as the founder's own decision; other actors do not train the shadow-founder"),
    "shadow.receipt_line_format": (
        "[✓] SHADOW_AUTH | boundary:{boundary} | confidence:{confidence:.2f} | founder_notified:false", str,
        "SB_SHADOW_RECEIPT_LINE_FORMAT",
        "One-line text of a shadow_auth receipt (spec 3.4)"),

    # -- 3.2 temporal branching ---------------------------------------------
    "branch.name_prefix": (
        "experiment", str, "SB_BRANCH_NAME_PREFIX",
        "Git branch name prefix for a forked micro-session; the branch is <prefix>-<n>"),
    "branch.steps": (
        1, int, "SB_BRANCH_STEPS",
        "Steps each branch runs before the kernel evaluates it (spec 3.2 step 4: 'after N steps')"),
    "branch.step_timeout_s": (
        120, int, "SB_BRANCH_STEP_TIMEOUT_S",
        "start-to-close timeout of one branch step activity"),
    "branch.merge_timeout_s": (
        60, int, "SB_BRANCH_MERGE_TIMEOUT_S",
        "start-to-close timeout of the merge/receipt activities"),
    "branch.retry_max_attempts": (
        1, int, "SB_BRANCH_RETRY_MAX_ATTEMPTS",
        "Activity retry attempts inside a branch; 1 means a failed step fails that branch and the others still race"),
    "branch.git_timeout_s": (
        30, int, "SB_BRANCH_GIT_TIMEOUT_S",
        "Timeout on one git subprocess call made by a branch activity"),
    "branch.child_id_sep": (
        "-b", str, None,
        "Separator between the parent session id and the branch number in a child workflow id"),
    "branch.merge_receipt_kind": (
        "branch_merge", str, "SB_BRANCH_MERGE_RECEIPT_KIND",
        "Receipt kind of the ONE receipt a branch run emits"),
    "branch.halt_receipt_kind": (
        "halt", str, "SB_BRANCH_HALT_RECEIPT_KIND",
        "Receipt kind written when a branch hits its 10% budget cap (crew#213)"),
    "branch.halt_reason": (
        "branch_budget_cap", str, "SB_BRANCH_HALT_REASON",
        "Reason text on the halt receipt"),
    "branch.merge_line_format": (
        "[✓] BRANCH_MERGE | main←{winner} | hash:{hash} | savings:{savings:+d} tokens", str,
        "SB_BRANCH_MERGE_LINE_FORMAT",
        "One-line text of the merge receipt (spec 3.2 step 6)"),
    "branch.main_branch": (
        "main", str, "SB_BRANCH_MAIN_BRANCH",
        "The git branch the winner is fast-forwarded into"),
    "branch.marker_filename": (
        "BRANCH.md", str, "SB_BRANCH_MARKER_FILENAME",
        "File a branch step writes and commits so the branch has a commit to fast-forward"),
    "branch.commit_hash_len": (
        7, int, "SB_BRANCH_COMMIT_HASH_LEN",
        "Short hash length in the merge receipt line"),
    "branch.worktree_dir": (
        None, str, "SB_BRANCH_WORKTREE_DIR",
        "Directory holding one git worktree per running branch; None means <sovereign_home>/branches"),
    "branch.stop_within_s": (
        10, int, "SB_BRANCH_STOP_WITHIN_S",
        "Seconds every child must report stopped in after a stop on the parent (cp27 scenario 2)"),
    "temporal.cli_binary": (
        "temporal", str, "SB_TEMPORAL_CLI_BINARY",
        "Name or path of the Temporal CLI; the acceptance suite starts its dev server from it instead of downloading one"),

    # -- 3.3 auto-distillation ----------------------------------------------
    "distill.dir": (
        None, str, "SB_DISTILL_DIR",
        "Directory under $ESTATE_HOME/sovereign holding the queue, the dataset mirror and the routes; None means <sovereign_home>/distill"),
    "distill.queue_filename": (
        "queue.jsonl", str, "SB_DISTILL_QUEUE_FILENAME",
        "Append-only queue of successful frontier steps waiting to become training rows"),
    "distill.dataset_filename": (
        "dataset.jsonl", str, "SB_DISTILL_DATASET_FILENAME",
        "Local mirror of the Langfuse dataset, one item per line; written even when Langfuse is not configured so a grade never depends on network"),
    "distill.routes_filename": (
        "routes.json", str, "SB_DISTILL_ROUTES_FILENAME",
        "task class -> model map that the LiteLLM router reads; changed only by `sb distill` on a measured number"),
    "distill.dataset_name_format": (
        "distill-{task_class}", str, "SB_DISTILL_DATASET_NAME_FORMAT",
        "Langfuse dataset name for one task class"),
    "distill.min_items": (
        20, int, "SB_DISTILL_MIN_ITEMS",
        "Dataset items a task class needs before its local accuracy is measured at all"),
    "distill.route_accuracy": (
        0.9, float, "SB_DISTILL_ROUTE_ACCURACY",
        "Measured local accuracy at or above which the LiteLLM route for a task class flips to the local model (spec 3.3 step 4)"),
    "distill.local_model": (
        "ollama", str, "SB_DISTILL_LOCAL_MODEL",
        "LiteLLM alias of the local model the route flips to"),
    "distill.frontier_models": (
        ["claude", "anthropic", "openai", "gpt", "gemini", "deepseek", "minimax", "openrouter"], list,
        "SB_DISTILL_FRONTIER_MODELS",
        "Runner/model names whose successful steps are captured as training rows; a local model's own success is not distilled from"),
    "distill.trainer": (
        "ollama", str, "SB_DISTILL_TRAINER",
        "Which local fine-tuning tool runs the LoRA job: ollama or axolotl"),
    "distill.ollama_command": (
        "ollama create {model} -f {modelfile}", str, "SB_DISTILL_OLLAMA_COMMAND",
        "Command template for the ollama trainer; {model} {modelfile} {dataset} {task_class} are filled in"),
    "distill.axolotl_command": (
        "axolotl train {config}", str, "SB_DISTILL_AXOLOTL_COMMAND",
        "Command template for the axolotl trainer; {config} {dataset} {model} {task_class} are filled in"),
    "distill.train_timeout_s": (
        3600, int, "SB_DISTILL_TRAIN_TIMEOUT_S",
        "Timeout on the fine-tuning subprocess"),
    "distill.grade_timeout_s": (
        60, int, "SB_DISTILL_GRADE_TIMEOUT_S",
        "httpx timeout on one grading completion against the local model"),
    "distill.grade_max_tokens": (
        256, int, "SB_DISTILL_GRADE_MAX_TOKENS",
        "max_tokens on a grading completion"),
    "distill.receipt_kind": (
        "distill", str, "SB_DISTILL_RECEIPT_KIND",
        "Receipt kind of the routing decision"),
    "distill.receipt_line_format": (
        "[✓] DISTILL | task:{task_class} | local_accuracy:{accuracy:.2f} | routing:{model}", str,
        "SB_DISTILL_RECEIPT_LINE_FORMAT",
        "One-line text of the distill receipt (spec 3.3 step 5)"),
    "distill.done_status": (
        "done", str, "SB_DISTILL_DONE_STATUS",
        "Session status that counts as a success worth capturing"),
}


def get(key: str) -> Any:
    default, typ, env_name, _help = SHADOW_KEYS[key]
    raw = os.environ.get(env_name) if env_name else None
    if raw is None or raw == "":
        return default
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if typ is list:
        return [part.strip() for part in raw.split(",") if part.strip()]
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default
