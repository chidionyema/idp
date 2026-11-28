"""A model id the vendor has retired must not stay named in a live router config.

WHY THIS EXISTS (2026-11-28). `deepseek/deepseek-chat` was still the upstream of two rows in
llm/config.yaml after DeepSeek's own pricing table dropped it, while the Worker's lane table
(platform/router-edge/scripts/role-pool.mjs) had already moved on. The ids were copied by hand
into several files and nothing compared them. The vendor table was read on 2026-11-28 at
https://api-docs.deepseek.com/quick_start/pricing.

Adding a model to a lane is one edit, in `CANDIDATES`. Retiring one is one entry in RETIRED
below, and this test then refuses every live config that still names it. Fixtures that use a
retired id as inert sample data live under tests/ and are not scanned.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# provider/id as LiteLLM spells it -> what replaced it.
RETIRED = {
    "deepseek/deepseek-chat": "deepseek/deepseek-flash",
}

LIVE_CONFIGS = [
    "llm/config.yaml",
    "platform/llm/config.yaml",
    "platform/llm/config.local.yaml",
    "platform/llm/pennyd/deploy/local/estate-cloud.toml",
]


def retired_ids_named(text: str) -> list[str]:
    """Retired ids named on a non-comment line of a LiteLLM config."""
    code = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    return [
        rid
        for rid in RETIRED
        if re.search(rf"(?<![\w/.-]){re.escape(rid)}(?![\w.-])", code)
    ]


def test_the_check_can_fail() -> None:
    """A gate that cannot fail is not a gate: a known-bad config is flagged, a known-good is not."""
    bad = "model_list:\n  - litellm_params:\n      model: deepseek/deepseek-chat\n"
    good = "  # deepseek/deepseek-chat was retired\n  - litellm_params:\n      model: deepseek/deepseek-flash\n"
    assert retired_ids_named(bad) == ["deepseek/deepseek-chat"]
    assert retired_ids_named(good) == []


def test_every_retired_id_has_a_live_replacement_in_the_lane_table() -> None:
    pool = (ROOT / "platform/router-edge/scripts/role-pool.mjs").read_text()
    upstream = set(re.findall(r'upstreamModel:\s*"([^"]+)"', pool))
    for replacement in RETIRED.values():
        assert replacement.split("/", 1)[1] in upstream, (
            f"{replacement} is not a lane in role-pool.mjs"
        )


def test_no_live_config_names_a_retired_model_id() -> None:
    offenders = {}
    for rel in LIVE_CONFIGS:
        path = ROOT / rel
        if path.exists():
            named = retired_ids_named(path.read_text())
            if named:
                offenders[rel] = named
    assert not offenders, (
        f"retired model ids still live (replace per RETIRED): {offenders}"
    )
