"""CFG-02 (idp#3525 CP7, spec section 5c): the routing matrix's config schema SHALL be
generated from this spec's own REQ list -- a REQ with a config-relevant axis and no matching
schema field is a CI failure, not a silent drift.

CFG-01 is the REQ that names the axis list, in one sentence, in its own text. That sentence is
parsed here rather than copied, so an edit to either side that isn't mirrored on the other
breaks this check instead of going unnoticed.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = REPO_ROOT / "docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md"
MATRIX = REPO_ROOT / "platform/llm/routing-matrix.yaml"

_CFG01_MARKER = "CFG-01 Every axis named in this spec ("

# The exact phrase CFG-01 names -> the schema key(s) it maps to. Any phrase the spec adds to
# CFG-01's own sentence with no entry here fails assert_schema_matches_spec(), by design.
SPEC_PHRASE_TO_SCHEMA_KEY: dict[str, str | tuple[str, ...]] = {
    "resource tier": "resource_tier",
    "candidate volume": "candidate_volume",
    "selection method": "selection_method",
    "escalation pattern": "escalation_pattern",
    "filter_depth/semantic-routing on/off": "filter_depth",
    "Pillar 2/3/4 on/off once built": (
        "pillar2_execute_python",
        "pillar3_grind_tool",
        "pillar4_darwin_machines",
    ),
}


class ConfigSchemaMismatch(ValueError):
    pass


def spec_named_axes() -> tuple[str, ...]:
    """The parenthetical phrase list straight out of CFG-01's own sentence in the live spec."""
    text = SPEC.read_text()
    rest = text.split(_CFG01_MARKER, 1)[1]
    inside_parens = rest.split(")", 1)[0]
    return tuple(p.strip() for p in inside_parens.split(","))


def schema_axis_keys() -> set[str]:
    doc = yaml.safe_load(MATRIX.read_text())
    return set(doc["axes"].keys())


def assert_schema_matches_spec() -> None:
    """CFG-02's ACCEPT: schema fields == REQs tagged config-relevant; mismatch fails CI."""
    expected: set[str] = set()
    for phrase in spec_named_axes():
        mapped = SPEC_PHRASE_TO_SCHEMA_KEY.get(phrase)
        if mapped is None:
            raise ConfigSchemaMismatch(
                f"spec names axis {phrase!r} in CFG-01 with no entry in "
                "SPEC_PHRASE_TO_SCHEMA_KEY -- add the mapping and the matching schema field"
            )
        expected.update(mapped if isinstance(mapped, tuple) else (mapped,))

    actual = schema_axis_keys()
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise ConfigSchemaMismatch(
            f"routing-matrix.yaml axes drifted from spec CFG-01: "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
