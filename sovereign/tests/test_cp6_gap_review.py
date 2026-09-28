"""idp#3525 CP6 -- code-review-record evidence for the free-lunch invariants
(spec section 5b, FL-01 and FL-02) that are pure config/code review, not a
runtime test of a capability that doesn't exist yet.

FL-03 and FL-04 are proved as running code, not review, and live in
sovereign/engine/test_tracing_zero_cost.py and sovereign/engine/test_weighted_vote.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = REPO_ROOT / "docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md"

FL_BLOCK_START = "## 5b. Free-lunch invariants"
FL_BLOCK_END = "## 5c. Configuration surface"


def _spec_text() -> str:
    return SPEC.read_text()


def _fl_block(text: str) -> str:
    return text.split(FL_BLOCK_START, 1)[1].split(FL_BLOCK_END, 1)[0]


def _fl_entry(block: str, req: str) -> str:
    """The REQ's own statement, spanning its wrapped lines up to the next
    FL-0N marker -- the spec wraps FL-02's "(... already real)" annotation
    onto its own line, so a single-line match would miss it."""
    marker = f"\n{req} "
    rest = block.split(marker, 1)[1]
    return rest.split("\nFL-0", 1)[0]


# ---------------------------------------------------------------------------
# FL-01 -- speculative decoding is a total NAMED GAP: no draft-model /
# rejection-sampling implementation exists anywhere in the repo, and unlike
# FL-02, the spec's own FL-01 line carries no "already real" annotation.
# ---------------------------------------------------------------------------


def test_fl_01_spec_line_is_not_marked_already_real() -> None:
    entry = _fl_entry(_fl_block(_spec_text()), "FL-01")
    status = "open" if "already real" not in entry else "already real"
    assert status == "open"


def test_fl_01_no_speculative_decoding_implementation_exists_yet() -> None:
    """Code review record (2026-09-15): grepped
    draft_model|rejection_sampling|speculative_decod across every .py file in
    the repo. No hits. If someone builds it, this test starts failing --
    that is the signal to move FL-01's spec line to "already real", not a
    defect in this test."""
    hits = []
    for path in REPO_ROOT.rglob("*.py"):
        if (
            "/tests/" in str(path)
            or path.name.startswith("test_")
            or path == Path(__file__)
        ):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(
            r"\b(draft_model|rejection_sampling|speculative_decod\w*)\b", text, re.I
        ):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], (
        f"speculative decoding now exists; FL-01 needs a real distribution-guarantee "
        f"review before the spec can call it already real: {hits}"
    )


# ---------------------------------------------------------------------------
# FL-02 -- the exact-match cache's TTL safeguard is real, parsed structure,
# checked against the actual keys LiteLLM reads (not the surrounding prose).
# The other two safeguards (per-call opt-out, reuse marked in trace) are
# LiteLLM's own built-in behaviour once cache/cache_params are set -- not a
# separate config key this repo could test in isolation.
# ---------------------------------------------------------------------------


def test_fl_02_spec_line_is_marked_already_real() -> None:
    entry = _fl_entry(_fl_block(_spec_text()), "FL-02")
    status = "already real" if "already real" in entry else "open"
    assert status == "already real"


def test_fl_02_cache_config_carries_its_ttl_safeguard() -> None:
    doc = yaml.safe_load((REPO_ROOT / "platform/llm/config.base.yaml").read_text())
    settings = doc["litellm_settings"]
    enabled = settings["cache"] is True
    ttl = settings["cache_params"]["ttl"]
    assert enabled
    assert ttl == 300


def test_fl_02_cache_ttl_matches_between_base_and_generated_config() -> None:
    """config.yaml is machine-generated from config.base.yaml
    (bin/idp-vendor-render); the two must never disagree on the TTL that
    makes the cache bounded."""
    base = yaml.safe_load((REPO_ROOT / "platform/llm/config.base.yaml").read_text())
    generated = yaml.safe_load((REPO_ROOT / "platform/llm/config.yaml").read_text())
    ttls = {
        base["litellm_settings"]["cache_params"]["ttl"],
        generated["litellm_settings"]["cache_params"]["ttl"],
    }
    assert ttls == {300}
