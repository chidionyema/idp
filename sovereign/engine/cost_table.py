"""The hosting cost table's receipt-grade schema (idp#3525 CP1, COST-04).

"Every hosting tier SHALL carry a receipt grade (vendor-doc / survey /
founder-supplied-unverified). Founder-supplied figures SHALL NOT enter the
cost model until cross-checked."

The table itself is platform/llm/hosting-cost-table.yaml; the schema it
must satisfy is platform/llm/cost-table.schema.json. This module is the
one place that loads both and checks one against the other -- so a row
someone adds without a `grade` fails here, in a test, rather than
silently entering cost_ladder.py's arithmetic ungraded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TABLE_PATH = _ROOT / "platform" / "llm" / "hosting-cost-table.yaml"
DEFAULT_SCHEMA_PATH = _ROOT / "platform" / "llm" / "cost-table.schema.json"

GRADES = ("vendor-doc", "survey", "founder-supplied-unverified")


def load_table(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_TABLE_PATH
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a mapping")
    return data


def load_schema(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_SCHEMA_PATH
    return json.loads(path.read_text())


def validate(table: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    """Every jsonschema error, as one string each. Empty means every row
    carries a grade from GRADES and a receipt. Errors, not an exception,
    because a caller reporting "which rows" needs the whole list, not just
    the first ValidationError raised."""
    schema = schema or load_schema()
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(table), key=str)]
