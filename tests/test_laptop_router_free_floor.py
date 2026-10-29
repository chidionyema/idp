"""The laptop router's free floor and its brain lane must survive the render.

The render in bin/litellm-local drops every model whose key this process does not hold, so a
vendor whose key is absent takes its whole deployment with it. Two things went missing because
of that and both cost the estate a working route (measured 2026-10-28):

  * `voice` -- the estate's brain lane -- had no deployment left at all, so a caller asking for
    it got "no healthy deployments for this model".
  * the free floor -- Ollama -- was not a lane, so when Groq's daily token allowance ran out
    (Limit 200000, Used 199348) the laptop had no paid-independent route left.

These tests run the render block out of bin/litellm-local itself, so they prove the repo's
bytes and not a copy of them.
"""

import json
import os
import sys
import types

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPER = os.path.join(REPO, "bin", "litellm-local")

# The render prints what it served; the last run's lines are kept so a test can read them.
_stdout_of_last_render = ""


def _render_block():
    text = open(WRAPPER).read()
    start = text.index('"$VENV/bin/python" - "$CFG" "$RUNCFG" <<\'PY\'')
    body_start = text.index("\n", start) + 1
    body_end = text.index("\nPY\n", body_start)
    return text[body_start:body_end]


def _render(tmp_path, model_list, fallbacks=None, env=None):
    """Run the wrapper's own render block over a config and return (kept, router_settings)."""
    import yaml

    cfg = {
        "model_list": model_list,
        "router_settings": {"fallbacks": fallbacks or []},
        "litellm_settings": {"callbacks": []},
        "general_settings": {},
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    out_path = tmp_path / "config.runtime.yaml"

    # The render imports litellm only for its provider table. Stub it: the tests here are about
    # the lane arithmetic, not about which vendors LiteLLM knows.
    stub = types.ModuleType("litellm")
    stub.provider_list = ["groq", "openai", "anthropic"]
    sys.modules.setdefault("litellm", stub)

    saved_argv, saved_env = list(sys.argv), dict(os.environ)
    saved_modules = {k: v for k, v in sys.modules.items() if k == "litellm"}
    printed = []

    class _Capture:
        def write(self, s):
            printed.append(s)

        def flush(self):
            pass

    try:
        sys.argv = ["render", str(cfg_path), str(out_path)]
        for key in list(os.environ):
            if key.endswith("_API_KEY"):
                del os.environ[key]
        os.environ.update(env or {})
        scope = {"os": os, "sys": sys, "yaml": yaml, "__name__": "__render__"}
        real_stdout = sys.stdout
        sys.stdout = _Capture()
        try:
            # noqa: S102 -- executing the repo's own render block IS the test: the block is
            # extracted from bin/litellm-local, so this proves the shipped bytes.
            exec(compile(_render_block(), "render", "exec"), scope)  # noqa: S102
        finally:
            sys.stdout = real_stdout
    finally:
        sys.argv = saved_argv
        os.environ.clear()
        os.environ.update(saved_env)
        for key, mod in saved_modules.items():
            sys.modules[key] = mod
    global _stdout_of_last_render
    _stdout_of_last_render = "".join(printed)
    return scope["kept"], scope["cfg"]["router_settings"]


def _groq_model():
    return {
        "model_name": "groq",
        "litellm_params": {
            "model": "groq/openai/gpt-oss-120b",
            "api_key": "os.environ/GROQ_API_KEY",
        },
    }


def _default_model():
    """The estate's standard tier, as the live laptop render serves it (a Groq deployment)."""
    return {
        "model_name": "default",
        "litellm_params": {
            "model": "openai/openai/gpt-oss-120b",
            "api_key": "os.environ/GROQ_API_KEY",
        },
    }


def test_the_render_refuses_a_model_whose_key_is_absent(tmp_path):
    """The refusal rule itself: a model whose key this process does not hold is not served."""
    model = {
        "model_name": "deepseek",
        "litellm_params": {
            "model": "deepseek/deepseek-chat",
            "api_key": "os.environ/DEEPSEEK_API_KEY",
        },
    }
    kept, _ = _render(tmp_path, [model], env={})
    assert "deepseek" not in [m["model_name"] for m in kept]
    assert "lanes  refused" in _stdout_of_last_render


def test_a_refused_lane_is_named_with_its_missing_credential(tmp_path):
    """A declared capability whose credential is absent is refused WITH a reason.

    Measured 2026-10-29: the `voice` lane vanished from the laptop because the process that
    happened to be running held no key for it, and nothing said so -- the served set was a
    function of one unsupervised process's environment, not of the repository. A lane that
    cannot be served must be visible to whoever depends on it, with the credential named.
    """
    model = {
        "model_name": "deepseek",
        "litellm_params": {
            "model": "deepseek/deepseek-chat",
            "api_key": "os.environ/DEEPSEEK_API_KEY",
        },
    }
    _render(tmp_path, [model], env={})
    ledger = json.loads((tmp_path / "lanes.json").read_text())
    assert "deepseek" in ledger["declared"], (
        "the declared lane is not recorded: %s" % ledger
    )
    refused = {r["lane"]: r for r in ledger["refused"]}
    assert "deepseek" in refused, (
        "a declared lane with no credential vanished: %s" % ledger
    )
    assert "DEEPSEEK_API_KEY" in refused["deepseek"]["reason"], (
        "the refusal does not name the credential that is missing: %s"
        % refused["deepseek"]
    )
    assert refused["deepseek"]["verdict"] == "MEASURED_FAIL"


def test_a_refused_lane_is_alarmed(tmp_path):
    """Silence is how a lane disappears for hours: the refusal must reach the alert inbox."""
    model = {
        "model_name": "deepseek",
        "litellm_params": {
            "model": "deepseek/deepseek-chat",
            "api_key": "os.environ/DEEPSEEK_API_KEY",
        },
    }
    inbox = tmp_path / "alerts.jsonl"
    _render(tmp_path, [model], env={"ESTATE_ALERTS_INBOX": str(inbox)})
    lines = [json.loads(ln) for ln in inbox.read_text().splitlines() if ln.strip()]
    assert lines, "a refused lane was not alarmed"
    assert any("deepseek" in ln.get("text", "") for ln in lines), lines


def test_every_declared_lane_is_accounted_for(tmp_path):
    """Declared == served + refused. No lane may fall between the two, ever.

    This is the invariant that makes the served set a function of the repository: a lane is
    either served (and therefore proven) or refused (and therefore visible). There is no third
    state in which a declared capability simply is not there.
    """
    _render(
        tmp_path, [_default_model(), _groq_model()], env={"GROQ_API_KEY": "sk-present"}
    )
    ledger = json.loads((tmp_path / "lanes.json").read_text())
    accounted = set(ledger["served"]) | {r["lane"] for r in ledger["refused"]}
    missing = set(ledger["declared"]) - accounted
    assert not missing, "declared lanes with no verdict: %s" % missing
    assert set(ledger["declared"]) <= accounted


def test_voice_is_served_from_a_surviving_deployment(tmp_path):
    """The brain lane must not vanish with the vendor that named it."""
    kept, _ = _render(
        tmp_path,
        [_groq_model()],
        env={"GROQ_API_KEY": "sk-present"},
    )
    names = [m["model_name"] for m in kept]
    assert "voice" in names, "the render dropped the voice lane: %s" % names


def test_the_free_floor_is_a_lane_when_ollama_answers(tmp_path, monkeypatch):
    """Ollama is the floor: free, local, and it answers when every paid vendor refuses."""
    import socket
    import urllib.request

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: _Ctx())
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **k: _Resp(b'{"models":[{"name":"qwen2.5:0.5b"}]}'),
    )

    kept, rs = _render(
        tmp_path,
        [_groq_model()],
        fallbacks=[{"groq": ["default"]}],
        env={"GROQ_API_KEY": "sk-present"},
    )
    names = [m["model_name"] for m in kept]
    assert "ollama" in names, "the free floor is not a lane: %s" % names
    row = next(m for m in kept if m["model_name"] == "ollama")
    assert row["litellm_params"]["api_base"] == "http://127.0.0.1:11434"
    assert row["litellm_params"]["model"] == "ollama/qwen2.5:0.5b"


def test_every_fallback_chain_ends_in_the_free_floor(tmp_path, monkeypatch):
    """A chain that forgets the floor ends in a paid vendor that refuses."""
    import socket
    import urllib.request

    class _Resp:
        def read(self):
            return b'{"models":[{"name":"qwen2.5:0.5b"}]}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: _Ctx())
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())

    _, rs = _render(
        tmp_path,
        [_groq_model()],
        fallbacks=[{"groq": ["default"]}],
        env={"GROQ_API_KEY": "sk-present"},
    )
    chains = {k: v for entry in rs["fallbacks"] for k, v in entry.items()}
    assert chains, "the render dropped every fallback chain"
    for src, tgts in chains.items():
        assert "ollama" in tgts, "chain %s does not end in the free floor: %s" % (
            src,
            tgts,
        )


def test_the_kubectl_step_is_bounded():
    """A hung kubectl stalls every slot boot, so the render must kill it, not wait for it."""
    text = open(WRAPPER).read()
    assert "subprocess.run(sys.argv[1:], capture_output=True, timeout=25)" in text, (
        "the kubectl step is not bounded by a killable timeout"
    )


def test_codex_model_name_is_published(tmp_path):
    """Codex asks for `gpt-6.1-sol`, and the name has to be answerable here.

    Measured 2026-10-29: the cloud router published this model group from its DATABASE
    (`store_model_in_db: true`), not from YAML, so the name is in no config file and the
    laptop answered Codex with "There are no healthy deployments for this model". Until the
    database is restored, the laptop publishes the name onto the estate's standard tier.
    """
    kept, _ = _render(
        tmp_path, [_default_model(), _groq_model()], env={"GROQ_API_KEY": "sk-present"}
    )
    names = [m["model_name"] for m in kept]
    assert "gpt-6.1-sol" in names, (
        "the laptop does not publish Codex's model name: %s" % names
    )
    row = next(m for m in kept if m["model_name"] == "gpt-6.1-sol")
    default = next(m for m in kept if m["model_name"] == "default")
    assert row["litellm_params"] == default["litellm_params"], (
        "Codex's model name is not served on the estate's standard tier"
    )


def test_the_codex_row_is_a_keyed_lane(tmp_path):
    """A row, not an alias: the auth gate must still see a lane that spends the router's key.

    `local_caller_auth` decides whether a lane is keyed by matching the REQUESTED name against
    the lanes whose `api_key` is `os.environ/...`. An alias would resolve to a keyed lane
    AFTER that check, so every local caller would inherit the key. A row carries its own
    `api_key`, so the gate keeps asking for the laptop router key.
    """
    kept, _ = _render(
        tmp_path, [_default_model(), _groq_model()], env={"GROQ_API_KEY": "sk-present"}
    )
    row = next(m for m in kept if m["model_name"] == "gpt-6.1-sol")
    assert str(row["litellm_params"].get("api_key", "")).startswith("os.environ/"), (
        "the Codex row is not a keyed lane, so the auth gate would not see it: %s" % row
    )


def test_the_codex_row_falls_back_to_the_free_floor(tmp_path, monkeypatch):
    """A new row with no chain of its own ends at a paid vendor that refuses."""
    import socket
    import urllib.request

    class _Resp:
        def read(self):
            return b'{"models":[{"name":"qwen2.5:0.5b"}]}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: _Ctx())
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())

    _, rs = _render(
        tmp_path,
        [_default_model(), _groq_model()],
        fallbacks=[{"default": ["groq"]}],
        env={"GROQ_API_KEY": "sk-present"},
    )
    chains = {k: v for entry in rs["fallbacks"] for k, v in entry.items()}
    assert chains.get("gpt-6.1-sol"), "the Codex row has no fallback chain: %s" % chains
    assert "ollama" in chains["gpt-6.1-sol"]


def test_no_claude_alias_is_ever_published(tmp_path):
    """The law (#4063): a Claude Code session must never be silently turned into another model.

    So the alias table may carry a client's own model name, but never a `claude-*` one.
    """
    _, rs = _render(
        tmp_path, [_default_model(), _groq_model()], env={"GROQ_API_KEY": "sk-present"}
    )
    alias = rs.get("model_group_alias") or {}
    assert not [k for k in alias if k.startswith("claude")], (
        "a claude-* alias would outrank the claude-* lane: %s" % alias
    )


class _Ctx:
    def close(self):
        pass


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
