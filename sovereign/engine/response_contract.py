"""UX-01 (idp#3525 CP9, spec section 10): "Every tier/model/axis switch inside the Battalion
(COST-03 ladder, ROUTE-02 matrix, CFG-01 toggles) SHALL be invisible to the requester in the
success path -- same call shape in, same response shape out, regardless of which config cell
served it. Only the trace (ORCH-03) shows which cell ran."
ACCEPT: client-side integration test issuing identical requests across 5 different config cells
receives schema-identical responses; only the Langfuse trace differs. METHOD: contract test.

sovereign.engine.routing_matrix.dispatch_cell() already proves a cell resolves on its own
declared fields, never on config_id (its own docstring: "this function does not change when
platform/llm/routing-matrix.yaml grows a fifth cell"). build_response() below is the same
property one hop further out: the one function every cell's answer passes through on its way to
the requester. It calls dispatch_cell(cell) only to prove the cell resolves at all -- an
unrecognized cell raises here, before any envelope is built -- and never carries the cell's own
fields (resource_tier, selection_method, escalation_pattern, config_id) into the envelope body.
Those belong to the trace ORCH-03 already tags (sovereign.engine.tracing.trace_session's own
config_id parameter), not to the response shape a requester sees.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sovereign.engine.routing_matrix import dispatch_cell

SCHEMA_VERSION = 1

# The complete, closed set of keys a success-path response carries. UX-01's own "same response
# shape out" as a literal, checkable set -- a contract test compares this set (and each field's
# type) across cells, never the cells' own config fields, which never appear here.
RESPONSE_KEYS = frozenset({"schema_version", "status", "answer"})


@dataclass(frozen=True)
class ResponseEnvelope:
    schema_version: int
    status: str
    answer: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "answer": self.answer,
        }


def build_response(cell: dict[str, Any], answer: Any) -> ResponseEnvelope:
    """The one function a cell's answer passes through on the way out. dispatch_cell(cell) is
    called for its side effect only -- proving the cell resolves -- and its return value never
    enters the envelope: the envelope's shape does not vary with which cell built it."""
    dispatch_cell(cell)
    return ResponseEnvelope(schema_version=SCHEMA_VERSION, status="done", answer=answer)
