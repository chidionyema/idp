"""A caller asks the router for `kimi`, never for the vendor's own path.

The Kimi lane is console-owned: the founder brought its key through the LiteLLM
console on 2026-09-04 and the proxy serves it under the vendor's name,
`moonshot/kimi-k3`. Probed from inside the litellm pod that day, that name
answered HTTP 200 in 30.5s while `kimi` answered HTTP 400 "Invalid model name".

Making every caller carry the vendor path is how a rename to k4 becomes a change
in several repositories. `router_settings.model_group_alias` resolves the short
name at the router, and unlike a `model_list` row it declares no model and holds
no credential, so it cannot lock the name against the console (R75).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RENDERED = ("llm/config.yaml", "platform/llm/config.yaml")


def test_both_rendered_configs_alias_kimi_to_the_console_lane() -> None:
    for rel in RENDERED:
        settings = yaml.safe_load((ROOT / rel).read_text())["router_settings"]
        assert settings["model_group_alias"]["kimi"] == "moonshot/kimi-k3", rel


def test_the_alias_is_not_a_model_row() -> None:
    """A `kimi` row would lock the name and the console would refuse the key."""
    for rel in RENDERED:
        parsed = yaml.safe_load((ROOT / rel).read_text())
        names = {m["model_name"] for m in parsed["model_list"]}
        assert "kimi" not in names, rel
