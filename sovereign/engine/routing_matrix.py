"""The routing matrix: independent config axes for the working method (idp#3525 CP3, ROUTE-02,
ROUTE-05).

ROUTE-02: "The working-method axes SHALL be independent config dimensions: resource tier
(Rung 0-3) x candidate volume N x selection method x escalation pattern. Changing any cell SHALL
be a config edit only, and every cell SHALL be individually enable/disable-able at runtime
without a redeploy." ACCEPT: matrix run against >= 4 config cells, no code change between cells;
toggling a cell off mid-run reroutes new requests within one poll interval.

The matrix itself lives in platform/llm/routing-matrix.yaml, alongside the cost ladder COST-03
already versions. dispatch_cell() reads a cell's fields and looks them up in a small registry --
it never branches on a cell's config_id, which is the concrete meaning of "config edit only": a
fifth cell in the YAML dispatches correctly with zero lines changed here.

MatrixWatcher is the "without a redeploy" half: it re-reads the file at most once per
poll_interval_s, so a cell disabled on disk stops being returned within one poll, not
immediately and not never -- matching the ACCEPT line's own wording, "within one poll interval."

ROUTE-05: filter_depth is a NAMED GAP axis (semantic intent routing), present and toggleable in
this schema, default off. validate_schema() is the config-schema-review ACCEPT: it fails if the
gap axis is missing or has drifted to enabled by default.

CFG-01 (idp#3525 CP7, spec section 5c): this file is the single config document every axis the
spec names lives in -- resource tier, candidate volume, selection method, escalation pattern,
filter_depth, and the three not-yet-built Pillar 2/3/4 toggles (pillar2_execute_python,
pillar3_grind_tool, pillar4_darwin_machines). content_version() gives the "visible as a version
bump" signal CFG-01 asks for: a hash of the file's own bytes, so any edit to any axis or cell
changes it mechanically, never by someone remembering to bump a hand-maintained counter.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

DEFAULT_MATRIX_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "platform"
    / "llm"
    / "routing-matrix.yaml"
)

# selection_method / escalation_pattern -> a strategy tag. A cell's fields are looked up here,
# never matched by config_id, so a new cell needs no new branch.
_SELECTION_METHODS = {"gate", "weighted_vote", "multi_verifier"}
_ESCALATION_PATTERNS = {"route", "cascade", "hybrid"}

# Pillar 2/3/4 (CFG-01): each is still a NAMED GAP (OFF-02, GRIND-01, DARWIN-01 -- CP5
# evidence), so each is only a toggle here, floored off until the capability it names exists.
_PILLAR_GAP_AXES = {
    "pillar2_execute_python": "OFF-02",
    "pillar3_grind_tool": "GRIND-01",
    "pillar4_darwin_machines": "DARWIN-01",
}


class RoutingMatrixError(ValueError):
    """The matrix file is missing, unparsable, or a cell names a value off no known axis."""


def load_matrix(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_MATRIX_PATH
    try:
        text = path.read_text()
    except OSError as exc:
        raise RoutingMatrixError(f"cannot read {path}: {exc}") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("cells"), list):
        raise RoutingMatrixError(f"{path}: not a routing matrix (need version + cells)")
    return data


def validate_schema(matrix: dict[str, Any]) -> None:
    """ROUTE-05's ACCEPT: the filter_depth axis exists, is toggleable, and defaults off."""
    axes = matrix.get("axes") or {}
    filter_depth = axes.get("filter_depth")
    if not isinstance(filter_depth, dict) or "enabled" not in filter_depth:
        raise RoutingMatrixError(
            "routing matrix has no toggleable filter_depth axis (ROUTE-05)"
        )
    if filter_depth["enabled"] is not False:
        raise RoutingMatrixError(
            "filter_depth (ROUTE-05, a named gap) must default to disabled: "
            "misclassification ships a wrong answer on the cheap path"
        )
    for axis_key, req_id in _PILLAR_GAP_AXES.items():
        axis = axes.get(axis_key)
        if not isinstance(axis, dict) or "enabled" not in axis:
            raise RoutingMatrixError(
                f"routing matrix has no toggleable {axis_key} axis ({req_id}, idp#3525 CFG-01)"
            )
        if axis["enabled"] is not False:
            raise RoutingMatrixError(
                f"{axis_key} ({req_id}, a named gap not yet built) must default to disabled"
            )
    for row in matrix["cells"]:
        for field, known in (
            ("selection_method", _SELECTION_METHODS),
            ("escalation_pattern", _ESCALATION_PATTERNS),
        ):
            if row.get(field) not in known:
                raise RoutingMatrixError(
                    f"cell {row.get('config_id')!r}: {field}={row.get(field)!r} is off no known axis"
                )


def active_cells(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in matrix["cells"] if row.get("enabled", True)]


def content_version(path: Path | None = None) -> str:
    """CFG-01's version-bump signal: a hash of the file's raw bytes, so it changes iff the
    file's content changes, whether that edit is a cell field, an axis, or anything else --
    never a separately hand-maintained counter someone can forget to bump."""
    path = path or DEFAULT_MATRIX_PATH
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def dispatch_cell(cell: dict[str, Any]) -> str:
    """The one thing every cell dispatches through: a pure lookup on its own declared fields,
    never on config_id. This is what "config edit only" means in code: this function does not
    change when platform/llm/routing-matrix.yaml grows a fifth cell."""
    if cell["selection_method"] not in _SELECTION_METHODS:
        raise RoutingMatrixError(
            f"unknown selection_method {cell['selection_method']!r}"
        )
    if cell["escalation_pattern"] not in _ESCALATION_PATTERNS:
        raise RoutingMatrixError(
            f"unknown escalation_pattern {cell['escalation_pattern']!r}"
        )
    return f"{cell['selection_method']}/{cell['escalation_pattern']}"


@dataclass
class MatrixWatcher:
    """Re-reads the matrix file at most once per poll_interval_s. A cell toggled off on disk
    stops being returned to a caller within one poll interval -- ROUTE-02's own wording -- never
    on the very next call and never only after a redeploy."""

    path: Path | None = None
    poll_interval_s: float = 5.0
    clock: Callable[[], float] = time.monotonic
    _matrix: dict[str, Any] | None = None
    _loaded_at: float = -1.0

    def _refresh(self) -> None:
        now = self.clock()
        if self._matrix is None or (now - self._loaded_at) >= self.poll_interval_s:
            self._matrix = load_matrix(self.path)
            self._loaded_at = now

    def is_enabled(self, config_id: str) -> bool:
        self._refresh()
        for row in self._matrix["cells"]:
            if row.get("config_id") == config_id:
                return bool(row.get("enabled", True))
        raise RoutingMatrixError(f"routing matrix has no cell {config_id!r}")

    def get_cell(self, config_id: str) -> dict[str, Any]:
        """CFG-01's own ACCEPT case: a cell whose selection_method (or any other field) changed
        on disk since the last poll comes back with its new fields, not its stale ones."""
        self._refresh()
        for row in self._matrix["cells"]:
            if row.get("config_id") == config_id:
                return row
        raise RoutingMatrixError(f"routing matrix has no cell {config_id!r}")
