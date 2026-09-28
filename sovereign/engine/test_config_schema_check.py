"""Tests for sovereign/engine/config_schema_check.py (idp#3525 CP7, CFG-02).

CFG-02's ACCEPT, verbatim: "schema fields == REQs tagged config-relevant; mismatch fails CI."
"""

from __future__ import annotations

from sovereign.engine import config_schema_check


def test_every_spec_named_axis_has_a_mapping_entry() -> None:
    unmapped = [
        phrase
        for phrase in config_schema_check.spec_named_axes()
        if phrase not in config_schema_check.SPEC_PHRASE_TO_SCHEMA_KEY
    ]
    assert unmapped == []


def test_schema_matches_spec_today() -> None:
    status = "ok"
    try:
        config_schema_check.assert_schema_matches_spec()
    except config_schema_check.ConfigSchemaMismatch:
        status = "mismatch"
    assert status == "ok"


def test_a_missing_schema_key_is_caught_as_a_mismatch(monkeypatch) -> None:
    """CFG-02: a REQ's axis with no matching schema field is a CI failure."""
    monkeypatch.setattr(
        config_schema_check, "schema_axis_keys", lambda: {"resource_tier"}
    )
    status = "ok"
    try:
        config_schema_check.assert_schema_matches_spec()
    except config_schema_check.ConfigSchemaMismatch:
        status = "mismatch"
    assert status == "mismatch"


def test_an_unmapped_spec_phrase_is_caught_as_a_mismatch(monkeypatch) -> None:
    """Simulates CFG-02's own scenario: a new REQ added to CFG-01's sentence without a
    matching schema field mapped yet."""
    monkeypatch.setattr(
        config_schema_check,
        "spec_named_axes",
        lambda: ("a brand new axis nobody mapped yet",),
    )
    status = "ok"
    try:
        config_schema_check.assert_schema_matches_spec()
    except config_schema_check.ConfigSchemaMismatch:
        status = "mismatch"
    assert status == "mismatch"


def test_an_extra_unmapped_schema_key_is_caught_as_a_mismatch(monkeypatch) -> None:
    """The other half of drift: a schema field with no REQ naming it at all."""
    real_keys = config_schema_check.schema_axis_keys()
    monkeypatch.setattr(
        config_schema_check,
        "schema_axis_keys",
        lambda: real_keys | {"an_orphan_field"},
    )
    status = "ok"
    try:
        config_schema_check.assert_schema_matches_spec()
    except config_schema_check.ConfigSchemaMismatch:
        status = "mismatch"
    assert status == "mismatch"
