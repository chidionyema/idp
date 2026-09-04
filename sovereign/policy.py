"""The living policy, read from AGENTS.md (crew#219 R38, spec v1.0 section 6
"File 5: AGENTS.md -- living policy").

AGENTS.md at the repository root carries one fenced ```toml block. That block
is the only place the budget defaults, the model routing table, the merge
criteria, the FSM rules and the agent capability declarations are written
down. This module parses it, and sovereign/config.py builds its
`budget.usd_per_day.*`, `cost.*`, `routing.*` and `merge.*` keys from the
result. The doc is the code's input, so the two cannot say different things.

Some numbers config.py has to declare on its own (fsm.max_cycles,
consensus.quorum, consensus.timeout_s ...) because older modules read them
as module constants. For those, AGENTS.md repeats the value under
[invariants] and drift() compares the two tables. A mismatch is a failing
test (sovereign/tests/bdd/test_policy.py), which is what "cannot drift"
means in practice.

Standalone by design, like every config_keys.py under sovereign/: this
module never imports sovereign.config, because sovereign.config imports it
while its own KEYS table is still being built. The one path it needs is
computed from its own location, with an environment override (LAW 46).

The parser is tomllib, which ships with Python 3.11+ (tomli before that,
already in sovereign/requirements.txt). PyYAML was rejected: it would be a
second config syntax next to estate.toml and a dependency the runtime
does not otherwise carry.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

try:
    import tomllib  # py311+
except ImportError:  # pragma: no cover - py310 on this machine
    import tomli as tomllib  # type: ignore

AGENTS_MD_ENV = "SB_POLICY_AGENTS_MD"
AGENTS_MD_FILENAME = "AGENTS.md"
FENCE = "```"
FENCE_LANG = "toml"


class PolicyError(RuntimeError):
    """AGENTS.md is missing, has no toml block, or the block will not parse.
    Raised rather than defaulted: a policy that silently falls back to
    built-in numbers is no policy at all."""


def agents_md_path() -> Path:
    """The AGENTS.md this checkout runs under. Two parents up from this
    file (sovereign/policy.py sits directly under the repository root),
    never a literal path."""
    override = os.environ.get(AGENTS_MD_ENV)
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / AGENTS_MD_FILENAME


def console_lanes(repo_root: Path | None = None) -> set[str]:
    """Model groups the LiteLLM console serves that the rendered config does not.

    A model row declared in `llm/config.yaml` is read-only in the LiteLLM admin
    console -- it shows as "defined in config" and its key cannot be replaced
    there. The founder rotates the vendor keys himself (2026-09-04: "i can
    change the keys nyself, i eed to be ble to delete the esting keys set in
    config"), so a lane whose key he owns is declared in
    `platform/vendors/consoles.yaml` under `router.console_lanes` and is
    rendered into no config file. The router serves it all the same, so the
    question "does this alias exist" is answered by the union of the two files.

    Read as text, like the config check beside it: this carries no yaml parser.
    """
    root = repo_root or agents_md_path().parent
    consoles = root / "platform" / "vendors" / "consoles.yaml"
    if not consoles.is_file():
        return set()
    names: set[str] = set()
    for line in consoles.read_text().splitlines():
        head, sep, tail = line.partition("console_lanes:")
        if not sep or head.strip().startswith("#"):
            continue
        names |= {n.strip() for n in tail.strip().strip("[]").split(",") if n.strip()}
    return names


def fenced_toml(text: str) -> str:
    """The body of the first ```toml fence in a Markdown document."""
    inside = False
    body: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not inside and stripped.startswith(FENCE) and stripped[len(FENCE):].strip().split() [:1] == [FENCE_LANG]:
            inside = True
            continue
        if inside and stripped == FENCE:
            return "\n".join(body) + "\n"
        if inside:
            body.append(line)
    raise PolicyError(f"no closed {FENCE}{FENCE_LANG} block found")


@dataclass(frozen=True)
class Policy:
    """One parsed AGENTS.md policy block. Every field is a plain mapping
    or list so config.py can turn it into KeySpecs without knowing more
    than the section names."""

    path: Path
    capabilities: Mapping[str, list[str]] = field(default_factory=dict)
    fsm: Mapping[str, Any] = field(default_factory=dict)
    budget_usd_per_day: Mapping[str, float] = field(default_factory=dict)
    cost: Mapping[str, Any] = field(default_factory=dict)
    routing: Mapping[str, Any] = field(default_factory=dict)
    merge: Mapping[str, Any] = field(default_factory=dict)
    invariants: Mapping[str, Any] = field(default_factory=dict)

    def monthly_spend_usd(self) -> float:
        """What the per-day defaults add up to over the contract month."""
        return float(sum(float(v) for v in self.budget_usd_per_day.values())) * float(self.cost["days_per_month"])

    def within_cost_contract(self) -> bool:
        """Spec section 8: direct costs $0 to $150 a month."""
        spend = self.monthly_spend_usd()
        return float(self.cost["contract_min_usd_month"]) <= spend <= float(self.cost["contract_max_usd_month"])


REQUIRED_SECTIONS = ("capabilities", "fsm", "budget", "cost", "routing", "merge", "invariants")


def load(path: Path | None = None) -> Policy:
    path = path or agents_md_path()
    try:
        text = path.read_text()
    except OSError as exc:
        raise PolicyError(f"cannot read {path}: {exc}") from exc
    try:
        data = tomllib.loads(fenced_toml(text))
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"{path}: policy block is not valid toml: {exc}") from exc
    missing = [s for s in REQUIRED_SECTIONS if s not in data]
    if missing:
        raise PolicyError(f"{path}: policy block lacks sections {missing}")
    budget = data["budget"].get("usd_per_day")
    if not isinstance(budget, dict) or not budget:
        raise PolicyError(f"{path}: [budget.usd_per_day] is missing or empty")
    return Policy(
        path=path,
        capabilities=dict(data["capabilities"]),
        fsm=dict(data["fsm"]),
        budget_usd_per_day={str(k): float(v) for k, v in budget.items()},
        cost=dict(data["cost"]),
        routing=dict(data["routing"]),
        merge=dict(data["merge"]),
        invariants=dict(data["invariants"]),
    )


# Config keys config.py declares on its own, and the policy section and
# field that must agree with each. [invariants] covers the plain numbers
# and is compared key by key on top of this table.
BOUND: dict[str, tuple[str, str]] = {
    "fsm.max_cycles": ("fsm", "max_cycles"),
    "fsm.cycle_path": ("fsm", "cycle_path"),
    "fsm.initial_state": ("fsm", "initial_state"),
    "fsm.terminal_state": ("fsm", "terminal_state"),
    "model.default": ("routing", "default"),
    "model.vision": ("routing", "vision"),
    "model.consensus": ("routing", "consensus"),
    "consensus.cheap_model": ("routing", "cheap"),
    "ops.destructive": ("capabilities", "destructive"),
    "ops.nondestructive": ("capabilities", "nondestructive"),
}


def drift(defaults: Mapping[str, Any], policy: Policy | None = None) -> list[str]:
    """Every place the code's default and AGENTS.md disagree, as one line
    each. Empty means the doc and the code say the same thing.

    `defaults` is {config key: default value}; the caller passes
    sovereign.config's KEYS defaults so this module never imports it."""
    policy = policy or load()
    expected: dict[str, Any] = {}
    for key, (section, name) in BOUND.items():
        table = getattr(policy, section)
        if name in table:
            expected[key] = table[name]
    expected.update(policy.invariants)
    out: list[str] = []
    for key, doc_value in sorted(expected.items()):
        if key not in defaults:
            out.append(f"{key}: AGENTS.md names it, config.py has no such key")
            continue
        if _normalize(defaults[key]) != _normalize(doc_value):
            out.append(f"{key}: config.py default {defaults[key]!r} != AGENTS.md {doc_value!r}")
    return out


def _normalize(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)
