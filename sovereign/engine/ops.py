"""Op classification and the budget check that gates it (R9, spec 2.3).

Spec 2.3 step 3, verbatim: "Governance Kernel checks budget, classifies op
as `fs_commit` (non-destructive, no quorum needed), executes write." Three
things happen there in a fixed order, and this module is the first two.
Nothing in the estate named `fs_commit` before this file existed
(`rg fs_commit` returned 0 rows in the crew#200 gap table).

Two axes, both read from config so neither is a literal (LAW 46):

  * destructive or not -- ops.destructive / ops.nondestructive. A
    destructive op needs cross-model quorum (spec 4.2) and a hardware
    signature (spec 3.4's safety invariant: the shadow-founder may NEVER
    auto-authorize one). This module reports that requirement; the trust
    boundary enforces it.
  * cost in tokens -- ops.fs_commit_tokens for fs_commit, else
    ops.default_tokens.

`check()` returns a Decision, never a bool. A bool loses the reason, and
the reason is what a receipt has to carry.
"""
from __future__ import annotations

from dataclasses import dataclass

from sovereign import config

ALLOW = "allow"
REFUSE_BUDGET = "refuse_budget"

UNKNOWN_CLASS = "unknown"
NONDESTRUCTIVE = "nondestructive"
DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class OpSpec:
    name: str
    classification: str
    destructive: bool
    needs_quorum: bool
    needs_hardware_signature: bool
    tokens: int


@dataclass(frozen=True)
class Decision:
    op: str
    allowed: bool
    verdict: str
    tokens: int
    remaining_after: int
    reason: str


def _tokens_for(name: str) -> int:
    if name == "fs_commit":
        return config.OPS_FS_COMMIT_TOKENS
    return config.OPS_DEFAULT_TOKENS


def classify(name: str) -> OpSpec:
    """An op the tables do not name is classified `unknown` and treated as
    destructive. Fail closed: an op nobody has classified is exactly the
    one that should not run unattended (spec 4.2, "Policy is a hard safety
    invariant above consensus")."""
    key = str(name).strip().lower()
    if key in {o.lower() for o in config.OPS_NONDESTRUCTIVE}:
        return OpSpec(key, NONDESTRUCTIVE, False, False, False, _tokens_for(key))
    if key in {o.lower() for o in config.OPS_DESTRUCTIVE}:
        return OpSpec(key, DESTRUCTIVE, True, True, True, _tokens_for(key))
    return OpSpec(key, UNKNOWN_CLASS, True, True, True, _tokens_for(key))


def check(name: str, budget_remaining: int) -> Decision:
    """The budget half of spec 2.3 step 3. At or below zero remaining, or
    a cost the remaining budget cannot cover, the op is refused -- there
    is no partial spend and no "ask for more" (spec 4.3: "At zero, hard
    halt")."""
    spec = classify(name)
    remaining = int(budget_remaining)
    if remaining <= 0:
        return Decision(spec.name, False, REFUSE_BUDGET, spec.tokens, remaining, "budget")
    if spec.tokens > remaining:
        return Decision(spec.name, False, REFUSE_BUDGET, spec.tokens, remaining, "budget")
    return Decision(spec.name, True, ALLOW, spec.tokens, remaining - spec.tokens, "")


def as_dict(spec: OpSpec) -> dict:
    return {
        "op": spec.name,
        "classification": spec.classification,
        "destructive": spec.destructive,
        "needs_quorum": spec.needs_quorum,
        "needs_hardware_signature": spec.needs_hardware_signature,
        "tokens": spec.tokens,
    }
