"""The falsifier for the instruction ledger: a prompt that cannot be linked is
refused, a linked prompt is normalized to BDD and queryable, and yield is tracked
back to the instruction that produced it -- never a prompt lost in the void.

These tests fail before the fix and pass after it (AGENTS.md section 9: a gate needs
a two-way falsifier). They exercise only the pure contract in
``catalog/census/instruction.py`` -- no database, no network -- so they run exactly
the same in CI and on a laptop.
"""

from __future__ import annotations

import pytest

from catalog.census.instruction import (
    UnlinkedPromptError,
    STATUS_OPEN,
    STATUS_STRUCTURED,
    STATUS_DONE,
    ORIGIN_FOUNDER,
    ingest_prompt,
    link_or_new,
    structure_bdd,
    record_yield,
    upsert_sql,
    new_id,
)


def test_unlinked_prompt_is_refused():
    """The founding law: a prompt with no instruction id and no link is refused."""
    with pytest.raises(UnlinkedPromptError):
        link_or_new(
            "build the ledger", ORIGIN_FOUNDER, instruction_id=None, linked_to=""
        )


def test_prompt_with_id_becomes_instruction():
    instr = link_or_new("build the ledger", ORIGIN_FOUNDER, instruction_id="instr-1")
    assert instr.id == "instr-1"
    assert instr.status == STATUS_OPEN
    assert instr.prompt == "build the ledger"


def test_prompt_links_to_existing_instruction():
    instr = link_or_new("actually make it BDD", ORIGIN_FOUNDER, linked_to="instr-1")
    assert instr.linked_to == "instr-1"
    assert instr.id.startswith("instr-")
    assert instr.id != "instr-1"


def test_structure_bdd_normalizes_prompt():
    instr = link_or_new("build the ledger", ORIGIN_FOUNDER, instruction_id="instr-1")
    structured = structure_bdd(
        instr,
        given="a founder prompt",
        when="an agent ingests it",
        then="it is bound to an instruction id and queryable",
    )
    assert structured.status == STATUS_STRUCTURED
    assert structured.bdd_given == "a founder prompt"
    assert structured.bdd_when == "an agent ingests it"
    assert structured.bdd_then and structured.structured_at


def test_structure_bdd_refuses_empty_legs():
    instr = link_or_new("build it", ORIGIN_FOUNDER, instruction_id="instr-1")
    with pytest.raises(ValueError):
        structure_bdd(instr, "given", "", "then")


def test_yield_tracks_done_and_proven_separately():
    instr = link_or_new("build it", ORIGIN_FOUNDER, instruction_id="instr-1")
    structured = structure_bdd(instr, "g", "w", "t")
    yielded = record_yield(
        structured, done=True, proven=True, outcome="landed", evidence="log line"
    )
    assert yielded.status == STATUS_DONE
    assert yielded.yield_json["done"] is True
    assert yielded.yield_json["proven"] is True
    assert yielded.yield_json["evidence"] == "log line"
    assert yielded.closed_at


def test_done_but_not_proven_is_not_closed():
    instr = link_or_new("build it", ORIGIN_FOUNDER, instruction_id="instr-1")
    structured = structure_bdd(instr, "g", "w", "t")
    yielded = record_yield(
        structured, done=True, proven=False, outcome="merged", evidence=""
    )
    # done but unproven must not read as DONE: proof and done are different facts.
    assert yielded.status == STATUS_STRUCTURED
    assert yielded.closed_at is None
    assert yielded.yield_json["done"] is True
    assert yielded.yield_json["proven"] is False


def test_ingest_prompt_end_to_end():
    instr = ingest_prompt(
        "build the ledger",
        ORIGIN_FOUNDER,
        instruction_id="instr-1",
        bdd=("a founder prompt", "an agent ingests it", "it is queryable"),
    )
    assert instr.status == STATUS_STRUCTURED
    assert instr.id == "instr-1"


def test_upsert_sql_is_idempotent_and_scoped():
    instr = ingest_prompt("x", ORIGIN_FOUNDER, instruction_id="instr-1")
    sql = upsert_sql(instr)
    assert "insert into catalog.instructions" in sql
    assert "on conflict (id) do update" in sql


def test_new_id_is_unique_and_prefixed():
    a, b = new_id(), new_id()
    assert a != b
    assert a.startswith("instr-") and b.startswith("instr-")
