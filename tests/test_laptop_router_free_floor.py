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


def _render(tmp_path, model_list, fallbacks=None, env=None, block_litellm=False):
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

    saved_argv, saved_env = list(sys.argv), dict(os.environ)
    saved_modules = {k: v for k, v in sys.modules.items() if k == "litellm"}

    # The render imports litellm only for its provider table. Stub it: the tests here are about
    # the lane arithmetic, not about which vendors LiteLLM knows. With block_litellm the stub is
    # NOT injected and `import litellm` is made to fail, which proves the render reads the
    # provider names out of LiteLLM's source instead of paying for the import.
    if not block_litellm:
        stub = types.ModuleType("litellm")
        stub.provider_list = ["groq", "openai", "anthropic"]
        sys.modules.setdefault("litellm", stub)
    else:
        sys.modules["litellm"] = None
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


def test_the_ledger_says_whether_it_adds_up(tmp_path):
    """A ledger a reader can check: declared == declared_served + refused, and the lanes the
    render DERIVED are listed apart, because a derived lane is not a declared one.

    Measured 2026-10-29: the ledger said 26 served and 8 refused out of 22 declared, because
    the served set also held the derived lanes (the free floor, the Codex row, the provider
    rows, the restored `voice` alias). The counts did not add up for a reader, and the truth
    instrument's `declared_accounted` predicate could not be measured at all.
    """
    _render(
        tmp_path, [_default_model(), _groq_model()], env={"GROQ_API_KEY": "sk-present"}
    )
    ledger = json.loads((tmp_path / "lanes.json").read_text())
    declared = set(ledger["declared"])
    served = set(ledger["declared_served"])
    refused = {r["lane"] for r in ledger["refused"]}
    assert ledger["declared_accounted"] is True
    assert len(served) + len(refused) == len(declared)
    assert served | refused == declared
    assert not (set(ledger["added"]) & declared)
    assert set(ledger["served"]) == served | set(ledger["added"])


def test_the_ledger_counts_lanes_and_not_refusal_entries(tmp_path):
    """One lane can be refused more than once, and the ledger must count it once.

    Measured 2026-10-29 on the live laptop: three cerebras deployments were refused under one
    lane name with three different missing credentials, so the ledger held 8 refusal entries
    for 4 lanes and read 18 served + 8 refused = 26 out of 22 declared -- declared_accounted
    false for a ledger that accounted for every lane. The accounting is over lane NAMES.
    """
    models = [
        _default_model(),
        _groq_model(),
        {
            "model_name": "cerebras",
            "litellm_params": {
                "model": "cerebras/llama-3.3-70b",
                "api_key": "os.environ/CEREBRAS_API_KEY",
            },
        },
        {
            "model_name": "cerebras",
            "litellm_params": {
                "model": "cerebras/llama-3.1-8b",
                "api_key": "os.environ/CEREBRAS_API_KEY_2",
            },
        },
        {
            "model_name": "cerebras",
            "litellm_params": {
                "model": "cerebras/llama-3.1-70b",
                "api_key": "os.environ/CEREBRAS_API_KEY_3",
            },
        },
    ]
    _render(tmp_path, models, env={"GROQ_API_KEY": "sk-present"})
    ledger = json.loads((tmp_path / "lanes.json").read_text())
    declared = set(ledger["declared"])
    served = set(ledger["declared_served"])
    refused = {r["lane"] for r in ledger["refused"]}
    assert len(ledger["refused"]) == 3, (
        "the test wants three refusal entries for one lane"
    )
    assert len(refused) == 1, "the three refusals are one lane"
    assert ledger["declared_accounted"] is True, ledger.get("declared_unaccounted")
    assert served | refused == declared


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


def test_the_render_returns_without_the_interpreter_finalizer():
    """The render's work is done when the files are written; the shutdown is not part of it.

    Measured 2026-10-29: a render that had already written config.runtime.yaml and
    lanes.json sat in Python's interpreter shutdown for 4 h 33 m, garbage-collecting
    litellm's module graph (sampled: Py_FinalizeEx -> finalize_modules -> gc_collect_main).
    The slot waiting for it never bound its port, so the router could not be deployed at all.
    The fix is to leave the interpreter before the finalizer runs -- but only when the block
    runs as a script, because a test executes the same block in-process and os._exit would
    take the test runner with it.
    """
    text = open(WRAPPER).read()
    assert 'if __name__ == "__main__":' in text, (
        "the render has no guarded exit: the finalizer can still hold the slot"
    )
    block = _render_block()
    assert "os._exit(0)" in block, "the render does not skip the finalizer"
    guard = block.index('if __name__ == "__main__":')
    assert guard > block.index("yaml.safe_dump"), (
        "the exit is before the config is written"
    )
    assert block.index("os._exit(0)") > block.index("yaml.safe_dump"), (
        "the exit is before the config is written"
    )
    # And the guard must not fire in-process: the tests above execute this block.
    assert __name__ != "__main__"


def test_the_kubectl_step_is_bounded():
    """A hung kubectl stalls every slot boot, so the render must kill it, not wait for it."""
    text = open(WRAPPER).read()
    assert "subprocess.run(sys.argv[1:], capture_output=True, timeout=25)" in text, (
        "the kubectl step is not bounded by a killable timeout"
    )


def test_the_launcher_never_shells_out_to_a_bare_python3():
    """A bare `python3` is Apple's xcrun shim under launchd, and xcrun can hang.

    Measured 2026-10-29 on this machine: slot 4002 sat in `python3 -c <otel probe>` for ten
    minutes with 0.02s of CPU. The sample showed the process inside
    `xcrun_main2 -> xcinfocache_resolve_sdkroot -> cltools_lookup_boot_system_sdk`: under
    launchd the PATH is /usr/bin:/bin:/usr/sbin:/sbin, so `python3` is /usr/bin/python3, the
    shim that asks xcrun for an SDK. The render never started, the swap reported "slot 4002
    not live after 180s", and the slot stayed deaf. Every interpreter the launcher names must
    therefore be an absolute path to the venv's own python.
    """
    text = open(WRAPPER).read()
    bare = [
        line
        for line in text.splitlines()
        if "python3" in line
        and not line.strip().startswith("#")
        and '"$VENV/bin/python"' not in line
        and "python3.1" not in line
    ]
    assert bare == [], "the launcher still shells out to a bare python3: %r" % (bare,)


def test_the_otel_probe_is_bounded():
    """The probe that decides whether the router exports OTEL must not be able to hang."""
    text = open(WRAPPER).read()
    assert "signal.alarm(5)" in text, "the OTLP probe is not bounded by an alarm"


def test_the_render_does_not_need_litellm_imported(tmp_path):
    """The render must not import LiteLLM, because that import is what stops the router booting.

    Measured 2026-10-29 on this machine: `import litellm` alone ran past the executor's 100
    second ceiling, so the render could not finish inside the swap's 180 second window, slot
    4002 never came up and the estate's free floor stayed out of service. The render must get
    the provider names from LiteLLM's own source instead -- so a render run in a FRESH
    interpreter that has the real LiteLLM installed must finish without importing it.
    """
    import subprocess

    venv = os.path.expanduser("~/.cache/estate-tools/litellm-venv/bin/python")
    if not os.path.exists(venv):
        pytest.skip("the laptop router's venv is not on this machine")
    import yaml

    cfg = {
        "model_list": [_default_model(), _groq_model()],
        "router_settings": {"fallbacks": []},
        "litellm_settings": {"callbacks": []},
        "general_settings": {},
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    out_path = tmp_path / "config.runtime.yaml"
    block_path = tmp_path / "render.py"
    block_path.write_text(_render_block())
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import os, sys, yaml\n"
        "block = open(sys.argv[1]).read()\n"
        "sys.argv = ['render', sys.argv[2], sys.argv[3]]\n"
        "scope = {'os': os, 'sys': sys, 'yaml': yaml, '__name__': '__render__'}\n"
        "exec(compile(block, 'render', 'exec'), scope)\n"
        "print('LITELLM_IMPORTED', 'litellm' in sys.modules)\n"
    )
    env = dict(os.environ)
    env["GROQ_API_KEY"] = "sk-present"
    proc = subprocess.run(
        [venv, str(runner), str(block_path), str(cfg_path), str(out_path)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert proc.returncode == 0, (
        "the render failed without the litellm import: %s" % (proc.stderr[-400:])
    )
    assert "LITELLM_IMPORTED False" in proc.stdout, (
        "the render imported litellm: %s" % proc.stdout[-200:]
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
