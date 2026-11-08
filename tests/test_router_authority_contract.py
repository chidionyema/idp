"""The router authority contract has one and only one authoritative model router."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "catalog" / "router-authority.v1.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text())


def test_contract_and_release_are_versioned() -> None:
    contract = load_contract()
    assert SEMVER.match(contract["schemaVersion"])
    assert SEMVER.match(contract["release"]["version"])
    assert contract["release"]["id"]


def test_exactly_one_router_is_authoritative_for_models() -> None:
    contract = load_contract()
    authoritative = [
        router
        for router in contract["routers"]
        if router.get("authoritative") and router.get("role") == "model-inference"
    ]
    assert [router["id"] for router in authoritative] == [
        contract["canonicalModelRouter"]
    ]


def test_every_client_names_the_canonical_router() -> None:
    contract = load_contract()
    canonical = contract["canonicalModelRouter"]
    assert contract["clients"]
    assert {client["router"] for client in contract["clients"]} == {canonical}


def test_control_and_fallback_roles_cannot_claim_model_authority() -> None:
    contract = load_contract()
    by_id = {router["id"]: router for router in contract["routers"]}
    assert by_id["estate.control-router"]["authoritative"] is False
    assert by_id["estate.control-router"]["modelEndpoint"] is False
    assert by_id["estate.laptop-fallback"]["authoritative"] is False
