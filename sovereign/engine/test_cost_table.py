"""Tests for sovereign/engine/cost_table.py (idp#3525 CP1, COST-04).

COST-04's ACCEPT, verbatim: "cost table rows include grade column;
ungraded row fails schema." Both halves below, against the real
platform/llm/hosting-cost-table.yaml and
platform/llm/cost-table.schema.json this repo ships.
"""

from __future__ import annotations

import copy

from sovereign.engine import cost_table


def test_real_hosting_cost_table_passes_schema() -> None:
    errors = cost_table.validate(cost_table.load_table())
    assert errors == []


def test_every_row_grade_is_one_of_the_declared_grades() -> None:
    table = cost_table.load_table()
    for row in table["rows"]:
        assert row["grade"] in cost_table.GRADES, row


def test_a_row_with_no_grade_column_fails_schema() -> None:
    table = copy.deepcopy(cost_table.load_table())
    del table["rows"][0]["grade"]

    errors = cost_table.validate(table)

    assert errors != []
    assert any("grade" in message for message in errors), errors


def test_a_row_with_an_unrecognized_grade_fails_schema() -> None:
    table = copy.deepcopy(cost_table.load_table())
    table["rows"][0]["grade"] = "founder-vibes"

    errors = cost_table.validate(table)

    assert errors != []


def test_a_table_with_no_rows_fails_schema() -> None:
    errors = cost_table.validate({"version": 1, "rows": []})
    assert errors != []
