"""Incident test, crew#503 (rung 4).

https://llm.<zone>/ui answered 307 Location: http://llm.<zone>/ui/ because LiteLLM builds its
trailing-slash redirect from the plaintext hop behind Traefik (BerriAI/litellm#19663). The rule:
the Gateway answers the exact path /ui itself, on https, before any rule reaches the router.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _rules() -> list[dict]:
    doc = yaml.safe_load((ROOT / "platform/llm/httproute.yaml").read_text())
    return doc["spec"]["rules"]


def test_exact_ui_path_redirects_to_https_before_the_catch_all() -> None:
    rules = _rules()
    first = rules[0]
    assert first["matches"] == [{"path": {"type": "Exact", "value": "/ui"}}]
    redirect = first["filters"][0]["requestRedirect"]
    assert first["filters"][0]["type"] == "RequestRedirect"
    assert redirect["scheme"] == "https"
    assert redirect["path"] == {"type": "ReplaceFullPath", "replaceFullPath": "/ui/"}
    assert "backendRefs" not in first


def test_every_other_path_still_reaches_the_router() -> None:
    catch_all = [r for r in _rules() if "matches" not in r]
    assert len(catch_all) == 1
    assert catch_all[0]["backendRefs"][0]["name"] == "litellm"
