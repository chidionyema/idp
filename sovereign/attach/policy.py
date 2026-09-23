"""The conservative default policy scaffolded when an attached estate has
no AGENTS.md (cp21 "the scaffolded policy is conservative"): read
operations are allowed; write and git operations require a receipt
commit; a destructive pattern (attach.destructive_patterns) requires
quorum and a hardware signature.
"""
from __future__ import annotations

from typing import Literal

from sovereign.attach import config_keys as ck

Classification = Literal["read", "write", "git_write", "destructive"]


def scaffold_policy_text(mode: str | None = None) -> str:
    """The in-memory policy content written to <estate>/.estate/AGENTS.md
    when the target repo has none. Never written into the repo root
    unless the caller passes --write-policy (see cli.py)."""
    mode = mode or ck.get("attach.policy_mode")
    destructive = ", ".join(f"`{p}`" for p in ck.get("attach.destructive_patterns"))
    return (
        f"# AGENTS.md (auto-scaffolded, mode: {mode})\n\n"
        "No AGENTS.md was found at this estate's root, so sovereign-bus "
        "scaffolded this conservative default. Replace it with the real "
        "policy for this repo; until then, every session attached here "
        "runs under these rules:\n\n"
        "- Read operations (list, cat, grep, diff, log) are always allowed.\n"
        "- Write operations (edit, create, delete, mv, mkdir, chmod) and git "
        "write operations (add, commit, push, merge, rebase, checkout, "
        "reset, branch, tag) each require a receipt commit -- the action "
        "and its author are appended to this estate's signed receipt chain "
        "before it runs.\n"
        f"- Destructive commands ({destructive}) require quorum "
        f"({ck.get('attach.quorum')}) and a hardware signature (see "
        "sovereign/trust/README.md) before they run.\n"
    )


def classify(command: str) -> Classification:
    """Classify one shell command against the conservative default policy.
    Order matters: a destructive substring anywhere in the command outranks
    a write/git-write prefix match (e.g. "git push --force" is destructive,
    not merely a git write)."""
    stripped = command.strip()
    for pattern in ck.get("attach.destructive_patterns"):
        if pattern in stripped:
            return "destructive"
    first_word = stripped.split(" ", 1)[0] if stripped else ""
    if first_word == "git":
        rest = stripped[len("git"):].strip()
        verb = rest.split(" ", 1)[0] if rest else ""
        if verb in ck.get("attach.git_write_verbs"):
            return "git_write"
        return "read"
    if first_word in ck.get("attach.write_verbs"):
        return "write"
    return "read"


def requires_receipt_commit(classification: Classification) -> bool:
    return classification in ("write", "git_write", "destructive")


def requires_quorum_and_hardware_signature(classification: Classification) -> bool:
    return classification == "destructive"
