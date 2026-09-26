"""Claude Code on the Max subscription through the LOCAL router (bin/litellm-local).

Every assertion here is a way this path has already broken, not a hypothetical:

  - the cluster copy of the `claude-*` passthrough lane and its header forwarding were deleted
    by the 2026-09-23 consolidate (8f6298ad) without anyone noticing;
  - #4063 then aliased claude-opus / claude-opus-5-5 to deepseek, which outranks any lane and
    silently turned Claude Code sessions into another vendor's model;
  - llm/config.yaml named its callback `request_ceiling` without `.proxy_handler_instance`, and
    LiteLLM refused to start ("ValueError: Empty module name", measured 2026-09-26);
  - LiteLLM's beta allow-list dropped `inline-tools-2026-09-15` and Anthropic 400'd a real turn;
  - a lane with no api_key falls back to ANTHROPIC_API_KEY from the environment -- the
    "credit balance is too low" error -- so the launcher must never pass one through.
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "llm" / "config.yaml"
LAUNCHER = ROOT / "bin" / "litellm-local"
MODULE_DIR = ROOT / "platform" / "llm"
BUILTIN_CALLBACKS = {"otel", "langfuse", "prometheus"}


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load(CONFIG.read_text())


def _claude_rows(cfg):
    return [
        m
        for m in cfg["model_list"]
        if str(m.get("model_name", "")).startswith("claude")
    ]


def test_the_claude_wildcard_lane_exists_and_relays_to_anthropic(cfg):
    rows = {m["model_name"]: m["litellm_params"] for m in _claude_rows(cfg)}
    assert "claude-*" in rows, (
        "the claude-* passthrough lane is gone from llm/config.yaml"
    )
    assert rows["claude-*"]["model"] == "anthropic/claude-*"


def test_no_claude_lane_carries_a_credential(cfg):
    # The lane relays the client's own OAuth token; an api_key here is an Anthropic API key.
    for m in _claude_rows(cfg):
        assert "api_key" not in m["litellm_params"], (
            f"{m['model_name']} carries an api_key"
        )


def test_claude_lanes_are_priced_at_zero(cfg):
    # Without explicit zero, LiteLLM prices Opus from its own table and the $5/day max_budget
    # refuses every Claude call within minutes.
    for m in _claude_rows(cfg):
        p = m["litellm_params"]
        assert (
            p.get("input_cost_per_token") == 0 and p.get("output_cost_per_token") == 0
        ), m["model_name"]


def test_nothing_aliases_a_claude_name_to_another_model(cfg):
    aliases = (cfg.get("router_settings") or {}).get("model_group_alias") or {}
    claude_aliases = {k: v for k, v in aliases.items() if str(k).startswith("claude")}
    assert not claude_aliases, (
        f"claude names aliased away from the passthrough lane: {claude_aliases}"
    )


def test_client_headers_are_forwarded_but_provider_auth_headers_are_not(cfg):
    gs = cfg.get("general_settings") or {}
    assert gs.get("forward_client_headers_to_llm_api") is True
    # forward_llm_provider_auth_headers is the x-api-key BYOK path: an Anthropic API key.
    assert not gs.get("forward_llm_provider_auth_headers")


def test_every_custom_callback_is_importable_by_the_local_router(cfg):
    callbacks = (cfg.get("litellm_settings") or {}).get("callbacks") or []
    launcher = LAUNCHER.read_text()
    custom = [c for c in callbacks if c not in BUILTIN_CALLBACKS]
    assert "anthropic_beta_passthrough.proxy_handler_instance" in custom
    for cb in custom:
        module, sep, attr = cb.rpartition(".")
        assert sep and module and attr, (
            f"callback {cb!r} is not module.instance -- LiteLLM will not start"
        )
        assert (MODULE_DIR / f"{module}.py").is_file(), (
            f"{module}.py missing from platform/llm"
        )
        # `install` stages only the modules it lists; an unlisted one is absent under launchd.
        assert f"{module}.py" in launcher, (
            f"bin/litellm-local does not stage {module}.py"
        )


def test_the_launcher_never_hands_litellm_an_anthropic_key():
    text = LAUNCHER.read_text()
    assert "unset ANTHROPIC_API_KEY" in text
    assert "--host 127.0.0.1" in text


def test_beta_passthrough_forwards_unknown_betas_for_anthropic_only():
    pytest.importorskip("litellm")
    import sys

    sys.path.insert(0, str(MODULE_DIR))
    import anthropic_beta_passthrough  # noqa: F401  (import applies the patch)
    from litellm import anthropic_beta_headers_manager as mgr

    new_beta = "inline-tools-2026-09-15"
    assert mgr.filter_and_transform_beta_headers(
        [new_beta, " " + new_beta], "anthropic"
    ) == [new_beta]
    # other providers still go through LiteLLM's own translation map
    assert new_beta not in mgr.filter_and_transform_beta_headers([new_beta], "bedrock")
