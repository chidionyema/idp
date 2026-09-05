"""crew#284 CP2 -- LiteLLM is real.

Live, on purpose. cp30 proves the consensus rules at the wire with a fake
proxy; this file proves the estate actually has a router: the secret store
holds where it is, the process on that address serves the voters, and a
real destructive op reaches quorum through it. Nothing here is mocked.
On a host with no vault or no router the scenarios skip with the reason in
the pytest line, so a skip is visible and a pass means the router answered.

Run:  cd sovereign && .venv/bin/python -m pytest tests/bdd/test_cp2_litellm_real.py -q -rs
"""
from __future__ import annotations

import asyncio
import importlib
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from pytest_bdd import given, scenarios, then, when

from sovereign import config as config_mod
from sovereign.engine import receipts as receipts_mod

scenarios("features/sovereign-bus/cp2_litellm_real.feature")

# Captured at import, before the estate_home fixture points HOME at a fake:
# the age identity secret-load reads lives under the real home.
_REAL_HOME = Path(os.environ.get("HOME", str(Path.home())))
_REAL_VAULT = Path(os.environ.get("ESTATE_SECRETS") or Path(__file__).resolve().parents[4] / "estate-secrets")
_AGE_KEY = Path(os.environ.get("SOPS_AGE_KEY_FILE") or _REAL_HOME / ".config" / "prospector" / "age-key.txt")
DESTRUCTIVE_OP = "delete the local git branch feature/old-experiment"


def _with_real_vault(monkeypatch: pytest.MonkeyPatch) -> Any:
    """config re-resolved against the real secret store and no estate.env."""
    if not (_REAL_VAULT / "scripts" / "secret-load").is_file() or not _AGE_KEY.is_file():
        pytest.skip(f"no estate secret store on this host ({_REAL_VAULT}); the vault lives on the estate machine")
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.setenv("ESTATE_SECRETS", str(_REAL_VAULT))
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(_AGE_KEY))
    return importlib.reload(config_mod)


def _master_key() -> str | None:
    env = _REAL_VAULT.parent / "idp" / "llm" / ".env"
    try:
        for line in env.read_text().splitlines():
            if line.startswith("LITELLM_MASTER_KEY="):
                return line.partition("=")[2].strip()
    except OSError:
        return None
    return None


# --- Scenario 1 ---------------------------------------------------------------


@given("this host has the estate secret store")
def _has_store(context: dict[str, Any]) -> None:
    if not (_REAL_VAULT / "scripts" / "secret-load").is_file() or not _AGE_KEY.is_file():
        pytest.skip(f"no estate secret store on this host ({_REAL_VAULT})")
    context["vault"] = _REAL_VAULT


@when("the kernel resolves its configuration with no estate.env at all")
def _resolve(estate_home: Path, monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]) -> None:
    assert not Path(os.environ["ESTATE_ENV"]).exists(), "the fixture must point ESTATE_ENV at nothing"
    context["config"] = _with_real_vault(monkeypatch)


@then("litellm.base_url and litellm.api_key come from the store")
def _from_store(context: dict[str, Any]) -> None:
    cfg = context["config"]
    loader = str(_REAL_VAULT / "scripts" / "secret-load")
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(_AGE_KEY)}
    stored_url = subprocess.run([loader, "dev", "LITELLM_BASE_URL", "LITELLM_BASE_URL"], capture_output=True, text=True, env=env, check=True).stdout
    stored_key = subprocess.run([loader, "dev", "LITELLM_API_KEY", "LITELLM_API_KEY"], capture_output=True, text=True, env=env, check=True).stdout
    assert cfg.LITELLM_BASE_URL and cfg.LITELLM_BASE_URL == stored_url, "base url did not come from the vault"
    assert cfg.LITELLM_API_KEY and cfg.LITELLM_API_KEY == stored_key, "api key did not come from the vault"
    context["api_key"] = cfg.LITELLM_API_KEY


@then("the api key is not the proxy master key")
def _not_master(context: dict[str, Any]) -> None:
    master = _master_key()
    if master is None:
        pytest.skip("llm/.env is not on this host, so the master key cannot be compared")
    assert context["api_key"] != master, "the kernel is holding the proxy master key; mint a virtual key"


# --- Scenarios 2 and 3 --------------------------------------------------------


@given("the live router answers")
def _router_up(estate_home: Path, monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]) -> None:
    cfg = _with_real_vault(monkeypatch)
    if not cfg.LITELLM_BASE_URL:
        pytest.skip("LITELLM_BASE_URL is not in the secret store")
    try:
        r = httpx.get(str(cfg.LITELLM_BASE_URL) + "/models", headers={"Authorization": f"Bearer {cfg.LITELLM_API_KEY}"}, timeout=5)
    except httpx.HTTPError as exc:
        pytest.skip(f"no router at {cfg.LITELLM_BASE_URL}: {exc.__class__.__name__} (bin/litellm-up)")
    assert r.status_code == 200, f"router answered {r.status_code}: {r.text[:200]}"
    context["config"] = cfg
    context["served"] = {m["id"] for m in r.json()["data"]}


@then("the consensus list names three different aliases")
def _three_distinct(context: dict[str, Any]) -> None:
    voters = list(context["config"].SB_MODEL_CONSENSUS)
    assert len(voters) == 3 and len(set(voters)) == 3, voters
    context["voters"] = voters


@then("GET /models on the live router lists every one of them")
def _all_served(context: dict[str, Any]) -> None:
    missing = [v for v in context["voters"] if v not in context["served"]]
    assert not missing, f"router does not serve {missing}; it serves {sorted(context['served'])}"


@when("the kernel decides a destructive op through the live router")
def _decide_live(context: dict[str, Any]) -> None:
    decide_mod = importlib.import_module("sovereign.consensus.decide")
    context["result"] = asyncio.run(decide_mod.decide_async(DESTRUCTIVE_OP, destructive=True))


@then("two different models agree before the deadline")
def _quorum(context: dict[str, Any]) -> None:
    result = context["result"]
    fresh = [v for v in result["votes"] if not v["stale"] and not v["error"] and v["proposal"] == result["quorum"]["proposal"]]
    names = {v["model"] for v in fresh}
    assert result["quorum"]["agreed"], result["quorum"]
    assert len(names) >= 2, f"quorum needs two different models, got {sorted(names)}: {result['votes']}"


@then("the model_consensus receipt names each voter and its elapsed time")
def _receipt(context: dict[str, Any]) -> None:
    rows = [r for r in receipts_mod.read_all() if r.get("kind") == "model_consensus"]
    assert rows, "decide() wrote no model_consensus receipt"
    receipt = rows[-1]
    voters = list(context["config"].SB_MODEL_CONSENSUS)
    text = str(receipt)
    for v in voters:
        assert v in text, f"receipt does not name voter {v}: {receipt}"
    assert all("elapsed_s" in vote for vote in context["result"]["votes"])
