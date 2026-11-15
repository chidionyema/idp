"""W0 baseline: FR-001, MEM-001-POS and MEM-001-NEG.

A planned memory path must resolve to its current owner and the named installed revision;
an obsolete OKE route, or a path with no current owner, must be refused. The inventory is
machine-generated (docs/specs/2026-11-15-one-estate-memory/baseline-inventory.json) and the
test reads the real files, so a drift between the pin and the disk fails here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import pytest

REPO = Path(__file__).resolve().parents[1]
INVENTORY = REPO / "docs/specs/2026-11-15-one-estate-memory/baseline-inventory.json"
OBSOLETE = REPO / "tests/fixtures/memory/baseline/obsolete-oke.json"

DOOR_SHA256 = "009dcf808982bd6793ef89c293cbb12b9e3ac945c6c919cb4993b5beca007100"


class ObsoleteRoute(RuntimeError):
    """A route that history names but current authority retires."""


class UnresolvedOwner(RuntimeError):
    """A path with no current owner; never silently admitted."""


def load_inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def load_obsolete() -> list[dict]:
    return json.loads(OBSOLETE.read_text(encoding="utf-8"))


def _obsolete_hit(path: str, rules: list[dict]) -> dict | None:
    parts = [p.lower() for p in PurePosixPath(path).parts]
    for rule in rules:
        match = rule["match"].lower()
        for part in parts:
            if (
                part == match
                or part.startswith(match + "-")
                or part.startswith(match + "_")
            ):
                return rule
    return None


def select_route(
    path: str, inventory: dict | None = None, obsolete: list[dict] | None = None
) -> dict:
    inv = inventory if inventory is not None else load_inventory()
    rules = obsolete if obsolete is not None else load_obsolete()
    hit = _obsolete_hit(path, rules)
    if hit:
        raise ObsoleteRoute(f"{path}: obsolete {hit['kind']}: {hit['reason']}")
    for component in inv["components"]:
        if component["path"] == path:
            if not component.get("owner") or component["owner"] == "UNRESOLVED":
                raise UnresolvedOwner(f"{path}: no current owner")
            return component
    raise UnresolvedOwner(f"{path}: not in the pinned inventory")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_mem_001_pos_route_matches_current_authority_and_installed_revision() -> None:
    inventory = load_inventory()
    route = select_route("platform/estate/memory/door.py")
    assert route["owner"] == "platform/estate/memory"
    assert route["sha256"] == DOOR_SHA256
    assert route["sha256"] == _sha256(REPO / route["path"])
    assert "chidionyema/idp#6164" in inventory["authority"]["canonical_issues"]
    assert inventory["authority"]["adr"].endswith(
        "0048-the-estate-runs-on-one-node-with-an-admission-list.md"
    )


def test_mem_001_pos_every_engine_component_matches_disk() -> None:
    for component in load_inventory()["components"]:
        if component["id"] == "brief":
            assert component.get("successor"), (
                "the brief must carry a successor pointer"
            )
            continue
        path = REPO / component["path"]
        assert path.is_file(), component["path"]
        assert _sha256(path) == component["sha256"], (
            f"drift from the pinned revision: {component['path']}"
        )


def test_mem_001_neg_obsolete_oke_route_is_refused() -> None:
    for path in (
        "docs/runbooks/oke-cluster-recovery.md",
        "rancher/oke/memory/deploy.yaml",
        "oke/bootstrap.sh",
    ):
        with pytest.raises(ObsoleteRoute):
            select_route(path)


def test_mem_001_neg_unknown_owner_is_refused() -> None:
    with pytest.raises(UnresolvedOwner):
        select_route("platform/estate/memory/not-inventoried.py")


def test_mem_001_neg_mutant_missing_owner_is_refused() -> None:
    inventory = load_inventory()
    for component in inventory["components"]:
        if component["path"] == "platform/estate/memory/door.py":
            component["owner"] = None
    with pytest.raises(UnresolvedOwner):
        select_route("platform/estate/memory/door.py", inventory=inventory)
