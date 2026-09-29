"""The laptop router must forward the caller's own Max OAuth bearer to Anthropic.

Measured 2026-09-28: LiteLLM's `clean_headers` dropped `Authorization: Bearer sk-ant-oat…`
whenever no `x-litellm-api-key` header was present, so every Claude Code request through
127.0.0.1:4000 came back "401 x-api-key header is required" and the founder's sessions stopped.
`anthropic_beta_passthrough` patches that; these cases hold it.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

pytest.importorskip("litellm.proxy.litellm_pre_call_utils")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "platform", "llm", "anthropic_beta_passthrough.py")
MAX = "Bearer sk-ant-oat01-" + "x" * 40


def _load():
    spec = importlib.util.spec_from_file_location(
        "anthropic_beta_passthrough", MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from litellm.proxy import litellm_pre_call_utils

    return litellm_pre_call_utils.clean_headers


def test_max_bearer_survives_when_it_is_the_only_credential():
    clean = _load()
    out = clean(
        {"authorization": MAX, "anthropic-version": "2023-06-01"},
        authenticated_with_header="authorization",
    )
    assert out.get("authorization") == MAX


def test_non_oauth_bearer_is_still_stripped():
    clean = _load()
    out = clean(
        {"authorization": "Bearer sk-some-proxy-key"},
        authenticated_with_header="authorization",
    )
    assert "authorization" not in {k.lower() for k in out}


def test_loading_twice_does_not_stack_wrappers():
    _load()
    clean = _load()
    assert clean.__wrapped__.__name__ == "clean_headers"
    assert not hasattr(clean.__wrapped__, "__wrapped__")
