"""platform/llm/router_catalog.py writes the router's catalog into every installed harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "router_catalog", ROOT / "platform/llm/router_catalog.py"
)
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

CATALOG = rc.build(
    {"served": ["deepseek", "default", "deepseek/*", "groq/*"]},
    {
        "deepseek": ["deepseek/deepseek-chat"],
        "groq": ["groq/qwen3-32b", "groq/llama-3.3-70b"],
    },
)
EXPECTED = [
    "deepseek",
    "default",
    "deepseek/deepseek-chat",
    "groq/qwen3-32b",
    "groq/llama-3.3-70b",
]


def test_catalog_is_aliases_then_every_discovered_model():
    assert rc.all_models(CATALOG) == EXPECTED


def test_opencode_gets_every_model_and_keeps_its_other_settings(tmp_path):
    cfg = tmp_path / ".config/opencode/opencode.jsonc"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"model": "litellm/deepseek", "theme": "x"}))
    assert rc.opencode(CATALOG, tmp_path) == "5 models"
    data = json.loads(cfg.read_text())
    assert (data["model"], data["theme"]) == ("litellm/deepseek", "x")
    assert list(data["provider"]["litellm"]["models"]) == EXPECTED
    assert data["provider"]["litellm"]["options"]["baseURL"] == rc.ROUTER


def test_pi_gets_an_estate_provider_and_keeps_others(tmp_path):
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"providers": {"ollama": {"baseUrl": "x"}}}))
    assert rc.pi(CATALOG, tmp_path) == "5 models"
    data = json.loads(cfg.read_text())
    assert data["providers"]["ollama"] == {"baseUrl": "x"}
    assert [m["id"] for m in data["providers"]["estate"]["models"]] == EXPECTED
    assert data["providers"]["estate"]["apiKey"] == "$LITELLM_API_KEY"


def test_a_config_with_comments_is_never_rewritten(tmp_path):
    cfg = tmp_path / ".config/opencode/opencode.jsonc"
    cfg.parent.mkdir(parents=True)
    original = '{\n  // mine\n  "model": "x"\n}\n'
    cfg.write_text(original)
    assert rc.opencode(CATALOG, tmp_path).startswith("skipped")
    assert cfg.read_text() == original


def test_an_absent_harness_is_not_created(tmp_path):
    assert rc.sync(CATALOG, tmp_path) == {"opencode": "absent", "pi": "absent"}
    assert list(tmp_path.iterdir()) == []
