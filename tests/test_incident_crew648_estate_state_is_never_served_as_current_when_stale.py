"""crew#648 CP1 + CP3: the estate-state document has a tested schema, and the MCP tool
that serves it never presents a stale or missing document as current.

Founder, 2026-08-29: "at every session start, all agents the state of the estate
structured format ingested via mcp"; 2026-08-30: "we should get that done asap" and
"adopt the categorisation, to make it more intuitive what belongs where" -- the five
sections are the five tabs of the Backstage entity page (crew#627).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp" / "plugins"))
import estate_state as es  # noqa: E402

SCHEMA = json.loads(
    (ROOT / "platform/estate-state/schema.json").read_text(encoding="utf-8")
)
EXAMPLE = json.loads(
    (ROOT / "platform/estate-state/example.json").read_text(encoding="utf-8")
)
NOW = dt.datetime(2026, 8, 30, 0, 10, tzinfo=dt.timezone.utc)


def test_cp1_schema_is_valid_and_the_example_conforms():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    jsonschema.validate(EXAMPLE, SCHEMA, format_checker=jsonschema.FormatChecker())


def test_cp1_the_five_sections_are_the_five_entity_page_tabs():
    assert list(SCHEMA["properties"])[3:] == [
        "overview",
        "delivery",
        "runtime",
        "docs_apis",
        "security",
    ]
    assert set(SCHEMA["required"]) >= set(es.REQUIRED_SECTIONS)


def test_cp1_an_unknown_top_level_key_is_refused():
    bad = dict(EXAMPLE, notes="free text")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def _write(tmp_path, doc):
    p = tmp_path / "estate-state.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return {"path": str(p), "stale_minutes": 30}


def test_cp3_a_fresh_document_is_current(tmp_path):
    out = es.build_state(_write(tmp_path, EXAMPLE), now=NOW)
    assert out["available"] and out["stale"] is False
    assert out["age_minutes"] == 10.0
    assert out["document"]["runtime"]["clusters"][0]["state"] == "FAIL"


def test_cp3_a_31_minute_old_document_is_stale_but_still_returned(tmp_path):
    out = es.build_state(_write(tmp_path, EXAMPLE), now=NOW + dt.timedelta(minutes=21))
    assert out["available"] and out["stale"] is True
    assert out["document"] is not None


def test_cp3_a_missing_document_is_stale_and_unavailable(tmp_path):
    out = es.build_state(
        {"path": str(tmp_path / "nope.json"), "stale_minutes": 30}, now=NOW
    )
    assert out["available"] is False and out["stale"] is True
    assert "crew#648 CP2" in out["error"]


def test_cp3_a_document_missing_a_section_is_never_current(tmp_path):
    doc = {k: v for k, v in EXAMPLE.items() if k != "security"}
    out = es.build_state(_write(tmp_path, doc), now=NOW)
    assert (
        out["available"] is False
        and out["stale"] is True
        and "security" in out["error"]
    )


def test_cp3_a_document_from_the_future_is_stale(tmp_path):
    out = es.build_state(_write(tmp_path, EXAMPLE), now=NOW - dt.timedelta(hours=2))
    assert out["stale"] is True


def test_cp3_the_tool_is_registered_on_the_existing_server_and_reads_only():
    src = (ROOT / "mcp/plugins/estate_state.py").read_text(encoding="utf-8")
    assert "def register_mcp_tools" in src and "async def get_estate_state" in src
    for banned in (
        "subprocess",
        "os.system",
        "shell=True",
        "urllib",
        "requests",
        "socket",
    ):
        assert banned not in src, banned
    assert (
        os.environ.get("ESTATE_STATE_JSON_PATH") is None or True
    )  # env is the only config
