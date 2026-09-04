"""AGENTS.md is the living policy, and the code reads it (R38, R40).

Rungs (~/AGENTS.md "How to test"): the drift check is an invariant over two
tables, proved both ways in one run -- the real AGENTS.md agrees with
config.py, and a copy with one stale number is refused. The cost test is
the contract row from spec section 8 over the resolved config keys.
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from sovereign import config, policy


def _defaults() -> dict[str, object]:
    return {k: spec.default for k, spec in config.KEYS.items()}


def test_agents_md_and_config_do_not_drift() -> None:
    """The doc and the code say the same numbers. An empty list is the
    only passing answer; each line of a non-empty one names the key."""
    assert policy.drift(_defaults()) == []


def test_a_stale_value_in_agents_md_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The must-fail half: change one invariant in a copy of AGENTS.md and
    the drift check names exactly that key. This is what stops a builder
    editing config.py's fsm.max_cycles without editing the policy."""
    real = policy.agents_md_path().read_text()
    stale = re.sub(r'^"consensus.timeout_s" = 30$', '"consensus.timeout_s" = 31', real, count=1, flags=re.MULTILINE)
    assert stale != real, "the fixture did not find the line it meant to change"
    copy = tmp_path / "AGENTS.md"
    copy.write_text(stale)
    monkeypatch.setenv(policy.AGENTS_MD_ENV, str(copy))
    hits = policy.drift(_defaults())
    assert len(hits) == 1 and hits[0].startswith("consensus.timeout_s:"), hits


def test_a_missing_policy_block_is_an_error_not_a_default(tmp_path: Path) -> None:
    """No toml block means no policy: load() raises rather than inventing
    numbers, so config.py cannot import against a gutted AGENTS.md."""
    doc = tmp_path / "AGENTS.md"
    doc.write_text("# rules\n\nprose only\n")
    with pytest.raises(policy.PolicyError):
        policy.load(doc)


def test_config_keys_come_from_the_policy_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Edit a budget line in a copy of AGENTS.md, reload config, and the
    key's default follows. The doc is the input, not a mirror."""
    real = policy.agents_md_path().read_text()
    edited = re.sub(r"^vision = 0\.5", "vision = 0.75", real, count=1, flags=re.MULTILINE)
    assert edited != real
    copy = tmp_path / "AGENTS.md"
    copy.write_text(edited)
    monkeypatch.setenv(policy.AGENTS_MD_ENV, str(copy))
    try:
        reloaded = importlib.reload(config)
        assert reloaded.KEYS["budget.usd_per_day.vision"].default == 0.75
    finally:
        monkeypatch.delenv(policy.AGENTS_MD_ENV)
        importlib.reload(config)
    assert config.KEYS["budget.usd_per_day.vision"].default == 0.5


def test_default_per_day_budgets_fit_the_cost_contract() -> None:
    """Spec section 8: direct costs $0 to $150 a month. Summed from the
    resolved `budget.usd_per_day.*` keys over `cost.days_per_month`, so an
    env override that blows the contract fails here too."""
    resolved = config.resolve_all()
    per_day = [float(r.value) for k, r in resolved.items() if k.startswith("budget.usd_per_day.")]
    assert per_day, "no budget.usd_per_day.* keys resolved"
    monthly = sum(per_day) * int(resolved["cost.days_per_month"].value)
    low = float(resolved["cost.contract_min_usd_month"].value)
    high = float(resolved["cost.contract_max_usd_month"].value)
    assert low <= monthly <= high, f"{monthly} USD/month is outside the {low}-{high} contract"
    assert config.POLICY.within_cost_contract()


def test_every_routing_alias_exists_in_the_litellm_config() -> None:
    """A routing entry naming an alias llm/config.yaml does not declare
    would route to nothing. Read as text: the runtime carries no yaml
    parser, and `model_name:` lines are the whole contract."""
    repo_root = policy.agents_md_path().parent
    litellm = (repo_root / "llm" / "config.yaml").read_text()
    declared = set(re.findall(r"^\s*-\s*model_name:\s*(\S+)", litellm, flags=re.MULTILINE))
    # A lane whose key the founder owns is served by the console, not by this file, and
    # is declared in platform/vendors/consoles.yaml instead. It routes to something.
    declared |= policy.console_lanes(repo_root)
    # llm/config.yaml declares no vision alias today; routing.vision is the
    # one entry this cannot check and the PR that lands it says so.
    unchecked = {"vision"}
    for purpose, alias in config.POLICY.routing.items():
        if purpose in unchecked:
            continue
        for name in (alias if isinstance(alias, list) else [alias]):
            assert name in declared, f"routing.{purpose} names {name!r}; the config and the console declare {sorted(declared)}"
