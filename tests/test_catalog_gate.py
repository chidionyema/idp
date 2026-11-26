"""platform/llm/catalog_gate.py: a live, cloud-runnable probe of every model+key lane
llm/config.yaml pins, with no dependency on litellm being installed to collect the test (a
fake module is injected the same way an unavailable harness is handled elsewhere in this
suite) and no dependency on any network call actually happening."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fake_litellm() -> types.ModuleType:
    mod = types.ModuleType("litellm")

    class AuthenticationError(Exception):
        pass

    class NotFoundError(Exception):
        pass

    class BadRequestError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class Timeout(Exception):
        pass

    class ServiceUnavailableError(Exception):
        pass

    mod.AuthenticationError = AuthenticationError
    mod.NotFoundError = NotFoundError
    mod.BadRequestError = BadRequestError
    mod.RateLimitError = RateLimitError
    mod.Timeout = Timeout
    mod.ServiceUnavailableError = ServiceUnavailableError
    mod.completion = lambda **_: None  # overridden per-test where needed
    return mod


sys.modules["litellm"] = _fake_litellm()

spec = importlib.util.spec_from_file_location(
    "catalog_gate", ROOT / "platform/llm/catalog_gate.py"
)
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)
litellm = sys.modules["litellm"]


def test_lanes_dedupes_by_model_and_key_and_skips_wildcards_and_keyless(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
model_list:
  - model_name: gemini
    litellm_params: {model: "gemini/gemini-2.5-flash", api_key: "os.environ/GEMINI_API_KEY"}
  - model_name: vision
    litellm_params: {model: "gemini/gemini-2.5-flash", api_key: "os.environ/GEMINI_API_KEY"}
  - model_name: "claude-*"
    litellm_params: {model: "anthropic/claude-*"}
  - model_name: default
    litellm_params: {model: "openai/gpt-oss-120b", api_key: "os.environ/GROQ_API_KEY"}
"""
    )
    lanes = cg._lanes(cfg)
    assert [l["lane"] for l in lanes] == ["gemini", "default"]
    assert lanes[0]["key_var"] == "GEMINI_API_KEY"


def test_a_rejected_key_is_red():
    exc = litellm.AuthenticationError("401 invalid api key ****c966")
    status, reason = cg._classify(exc)
    assert status == "RED"
    assert "invalid" in reason


def test_a_retired_model_is_red():
    exc = litellm.BadRequestError(
        "models/gemini-2.5-flash is no longer available to new users"
    )
    status, _ = cg._classify(exc)
    assert status == "RED"


def test_a_generic_bad_request_is_unknown_not_red():
    exc = litellm.BadRequestError("max_tokens must be a positive integer")
    status, _ = cg._classify(exc)
    assert status == "UNKNOWN"


def test_a_timeout_or_rate_limit_is_unknown_never_red():
    assert cg._classify(litellm.Timeout("deadline exceeded"))[0] == "UNKNOWN"
    assert cg._classify(litellm.RateLimitError("429"))[0] == "UNKNOWN"
    assert cg._classify(litellm.ServiceUnavailableError("503"))[0] == "UNKNOWN"


def test_a_missing_key_in_this_run_is_unknown_not_red(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = cg.probe(
        {
            "lane": "gemini",
            "model": "gemini/gemini-2.5-flash",
            "key_var": "GEMINI_API_KEY",
        }
    )
    assert result["status"] == "UNKNOWN"
    assert "not set" in result["reason"]


def test_probe_reports_green_when_the_provider_answers(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr(litellm, "completion", lambda **_: {"ok": True})
    result = cg.probe(
        {
            "lane": "gemini",
            "model": "gemini/gemini-2.5-flash",
            "key_var": "GEMINI_API_KEY",
        }
    )
    assert result["status"] == "GREEN"


def test_probe_reports_red_when_the_provider_rejects_it(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "bad")

    def boom(**_):
        raise litellm.AuthenticationError("401 invalid api key")

    monkeypatch.setattr(litellm, "completion", boom)
    result = cg.probe(
        {
            "lane": "deepseek-v4-flash",
            "model": "deepseek/deepseek-v4-flash",
            "key_var": "DEEPSEEK_API_KEY",
        }
    )
    assert result["status"] == "RED"


def test_main_exit_code_is_the_red_count(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
model_list:
  - model_name: ok
    litellm_params: {model: "openai/good", api_key: "os.environ/OK_KEY"}
  - model_name: broken
    litellm_params: {model: "openai/dead", api_key: "os.environ/BROKEN_KEY"}
"""
    )
    monkeypatch.setenv("OK_KEY", "x")
    monkeypatch.setenv("BROKEN_KEY", "x")

    def fake_completion(model, **_):
        if model == "openai/dead":
            raise litellm.AuthenticationError("401 invalid api key")
        return {"ok": True}

    monkeypatch.setattr(litellm, "completion", fake_completion)
    rc = cg.main(["catalog_gate.py", str(cfg)])
    assert rc == 1
    out = capsys.readouterr().out
    assert '"lanes_checked": 2' in out


def test_catalogue_preserves_exact_provider_endpoint_and_dedupes_by_endpoint(
    tmp_path, monkeypatch
):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
model_list:
  - model_name: first
    litellm_params: {model: "openai/model", api_key: "os.environ/TEST_KEY", api_base: "https://one.example/v1"}
  - model_name: duplicate
    litellm_params: {model: "openai/model", api_key: "os.environ/TEST_KEY", api_base: "https://one.example/v1"}
  - model_name: second
    litellm_params: {model: "openai/model", api_key: "os.environ/TEST_KEY", api_base: "https://two.example/v1"}
  - model_name: default
    litellm_params: {model: "openai/model", api_key: "os.environ/TEST_KEY"}
"""
    )
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    calls = []
    monkeypatch.setattr(litellm, "completion", lambda **kw: calls.append(kw))
    lanes = cg._lanes(cfg)
    assert [lane["lane"] for lane in lanes] == ["first", "second", "default"]
    assert all(cg.probe(lane)["status"] == "GREEN" for lane in lanes)
    assert [call.get("api_base") for call in calls] == [
        "https://one.example/v1",
        "https://two.example/v1",
        None,
    ]
    assert "api_base" not in calls[2]
    assert all(call["max_tokens"] == 1 for call in calls)


def test_invalid_explicit_base_never_falls_back_or_exposes_url(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
model_list:
  - model_name: invalid
    litellm_params: {model: "openai/model", api_key: "os.environ/TEST_KEY", api_base: "https://user:secret@example.com/v1"}
"""
    )
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    calls = []
    monkeypatch.setattr(litellm, "completion", lambda **kw: calls.append(kw))
    result = cg.probe(cg._lanes(cfg)[0])
    assert result["status"] == "UNKNOWN"
    assert "secret" not in str(result)
    for base in ("", "http://example.com", "https://example.com/?key=secret", {}):
        result = cg.probe(
            {"model": "openai/model", "key_var": "TEST_KEY", "api_base": base}
        )
        assert result["status"] == "UNKNOWN"
        assert "api_base" not in result
    assert not calls


def test_provider_exception_does_not_echo_exact_key(monkeypatch):
    key = "fixture-sensitive-key" * 30
    monkeypatch.setenv("TEST_KEY", key)

    def boom(**kw):
        raise litellm.AuthenticationError("invalid key " + kw["api_key"])

    monkeypatch.setattr(litellm, "completion", boom)
    result = cg.probe({"model": "openai/model", "key_var": "TEST_KEY"})
    assert result["status"] == "RED"
    assert "fixture-sensitive-key" not in str(result)


def test_cli_emits_only_json_when_provider_library_prints(
    tmp_path, monkeypatch, capsys
):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """model_list:
  - model_name: broken
    litellm_params: {model: "openai/dead", api_key: "os.environ/TEST_KEY"}
"""
    )
    key = "fixture-noise-secret"
    monkeypatch.setenv("TEST_KEY", key)

    def noisy_completion(**kw):
        print("provider diagnostic " + kw["api_key"])
        raise litellm.AuthenticationError("invalid api key")

    monkeypatch.setattr(litellm, "completion", noisy_completion)
    assert cg.main(["catalog_gate.py", str(cfg)]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert len(report["red"]) == 1
    assert key not in captured.out + captured.err
