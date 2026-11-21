"""The provider census must not prevent a healthy alternative from being discovered.

idp#8283: Gemini's intentionally empty model list was accidentally nested
under [auth], making auto_candidates() abort the entire census before probing
Groq/OpenRouter. These are source/parse falsifiers, NOT live capacity receipts.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PROVIDERS = ROOT / "platform" / "llm" / "pennyd" / "providers"


def legion_admit():
    loader = importlib.machinery.SourceFileLoader(
        "legion_admit_provider_census", str(ROOT / "bin" / "legion-admit")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_every_openai_provider_advertises_models_at_the_registry_root():
    checked = 0
    for path in sorted(PROVIDERS.glob("*.toml")):
        spec = tomllib.loads(path.read_text())
        if spec.get("dialect") != "openai":
            continue
        checked += 1
        assert spec["id"] == path.stem, path
        assert isinstance(spec.get("models"), list), (
            f"{path.name}: models missing at TOML root; "
            "a models entry inside [auth] disables discovery of ALL providers"
        )
        assert "models" not in spec.get("auth", {}), path
    assert checked >= 3, "provider catalogue unexpectedly missing"


def test_disabled_gemini_cannot_hide_healthy_free_provider_candidates():
    gemini = tomllib.loads((PROVIDERS / "gemini.toml").read_text())
    assert gemini["models"] == []  # I-8107: no Gemini authority or availability
    assert "models" not in gemini["auth"]

    # Non-secret synthetic keys only: tests registry discovery, not API capacity.
    env = {
        "GEMINI_API_KEY": "synthetic-only",
        "GROQ_API_KEY": "synthetic-only",
        "OPENROUTER_API_KEY": "synthetic-only",
    }
    candidates = legion_admit().auto_candidates(PROVIDERS, env)
    discovered = {route["provider"] for route in candidates}
    assert "gemini" not in discovered
    assert {"groq", "openrouter"} <= discovered
