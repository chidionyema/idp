"""Tests for bin/idp-voice — the conversation loop.

Cover:
  - clause splitting at every boundary character
  - a clause is spoken before the stream ends (order asserted)
  - Ollama unreachable is BLIND exit 2 and does NOT hang
  - --ask works with no `sound` command available
  - the system prompt carries the no-claims rule
  - every HTTP call passes a timeout
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import io
import json
import sys
import time
import urllib.error
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# Load bin/idp-voice as a module (it has a dash in the name).
# --------------------------------------------------------------------------

BIN = Path(__file__).resolve().parent.parent / "bin" / "idp-voice"


@pytest.fixture()
def no_faster_whisper(monkeypatch):
    """Force the pre-faster-whisper path, so the fallback tests test the fallback.

    Measured 2026-09-19: installing faster-whisper (pip, no compile -- whisper-cpp has no bottle
    on this Intel Mac) made four cases fail, because they asserted the WHISPER_CMD and sibling
    .txt behaviour while the first-choice engine was silently answering first. The engine order is
    a product decision, so each test now names the engine it means.
    """
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper" or name.startswith("faster_whisper."):
            raise ImportError("forced off by the test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.delenv("WHISPER_CMD", raising=False)
    return None


def _load_module():
    """Load bin/idp-voice, which has no .py suffix.

    `spec_from_file_location` returns None for an extensionless file, so the loader has to be
    NAMED -- `importlib.machinery.SourceFileLoader` -- and the spec built with
    `spec_from_loader`. The estate already has this trap written down for bin/idp-jit
    (tests/test_the_agent_reaches_the_cluster_without_the_oci_cli.py:53):
    "bin/idp-jit has no .py suffix, so the loader has to be named: spec_from_file_location
     returns None for an extensionless file and the import fails with an unhelpful
     AttributeError on spec.loader."
    """
    loader = importlib.machinery.SourceFileLoader("idp_voice", str(BIN))
    spec = importlib.util.spec_from_loader("idp_voice", loader, origin=str(BIN))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["idp_voice"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def idp():
    return _load_module()


# --------------------------------------------------------------------------
# Clause splitting at every boundary character
# --------------------------------------------------------------------------


@pytest.mark.parametrize("boundary", [",", ".", "?", "!", ";"])
def test_split_clauses_at_every_boundary(idp, boundary):
    clauses, remainder = idp.split_clauses(f"hello{boundary} world")
    assert clauses == [f"hello{boundary}"]
    assert remainder == " world"


def test_split_clauses_multiple(idp):
    clauses, remainder = idp.split_clauses("one, two. three? four!")
    assert clauses == ["one,", "two.", "three?", "four!"]
    assert remainder == ""


def test_split_clauses_no_boundary(idp):
    clauses, remainder = idp.split_clauses("no boundary here")
    assert clauses == []
    assert remainder == "no boundary here"


def test_split_clauses_keeps_boundary_char(idp):
    clauses, _ = idp.split_clauses("a;b")
    assert clauses == ["a;"]


# --------------------------------------------------------------------------
# A clause is spoken before the stream ends (order asserted)
# --------------------------------------------------------------------------


def test_clause_spoken_before_stream_ends(idp, monkeypatch):
    """The speaker must receive a clause while the model is still generating."""
    events: list[str] = []

    async def fake_stream(prompt):
        events.append("stream:start")
        yield "Hello, "
        events.append("stream:mid")
        # give the speaker a chance to run before the stream finishes
        await asyncio.sleep(0.05)
        yield "world."
        events.append("stream:end")

    spoken: list[str] = []

    def fake_speak(text):
        spoken.append(text)
        events.append(f"speak:{text}")

    monkeypatch.setattr(idp, "think_stream", fake_stream)
    monkeypatch.setattr(idp, "speak", fake_speak)

    loop = idp.VoiceLoop(speak_enabled=True)
    answer = asyncio.run(loop.think_and_speak("hi"))

    assert answer == "Hello, world."
    assert spoken == ["Hello,", "world."]
    # the first clause was spoken before the stream ended
    assert events.index("speak:Hello,") < events.index("stream:end")


def test_clause_spoken_order_multiple(idp, monkeypatch):
    async def fake_stream(prompt):
        for piece in ["a, ", "b. ", "c? ", "d! ", "e; ", "tail"]:
            yield piece

    spoken: list[str] = []
    monkeypatch.setattr(idp, "think_stream", fake_stream)
    monkeypatch.setattr(idp, "speak", lambda t: spoken.append(t))

    loop = idp.VoiceLoop(speak_enabled=True)
    asyncio.run(loop.think_and_speak("x"))
    assert spoken == ["a,", "b.", "c?", "d!", "e;", "tail"]


# --------------------------------------------------------------------------
# Ollama unreachable is BLIND exit 2 and does NOT hang
# --------------------------------------------------------------------------


def test_ollama_unreachable_is_blind_exit_2(idp, monkeypatch, capsys):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")

    def boom(url, payload, timeout=idp.HTTP_TIMEOUT):
        raise idp.blind(f"cannot reach {url}: connection refused")

    monkeypatch.setattr(idp, "_post", boom)

    start = time.monotonic()
    code = idp.mode_ask("what is stuck")
    elapsed = time.monotonic() - start

    assert code == 2
    assert elapsed < 5.0
    err = capsys.readouterr().err
    assert "BLIND voice" in err


def test_ollama_unreachable_does_not_hang(idp, monkeypatch):
    """A real connection to a dead port must fail fast, not hang."""
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
    start = time.monotonic()
    with pytest.raises(idp.Blind):
        idp.think("hello")
    elapsed = time.monotonic() - start
    assert elapsed < 10.0


# --------------------------------------------------------------------------
# --ask works with no `sound` command available
# --------------------------------------------------------------------------


def test_ask_works_without_say(idp, monkeypatch, capsys):
    monkeypatch.setattr(idp, "_say_available", lambda: False)
    monkeypatch.setattr(idp, "think", lambda prompt: "nothing is stuck")

    code = idp.mode_ask("what is stuck")
    out = capsys.readouterr().out

    assert code == 0
    assert "USER  what is stuck" in out
    assert "AGENT nothing is stuck" in out


def test_ask_does_not_call_speak(idp, monkeypatch):
    called = {"speak": False}

    def fake_speak(text):
        called["speak"] = True

    monkeypatch.setattr(idp, "speak", fake_speak)
    monkeypatch.setattr(idp, "think", lambda prompt: "answer")
    idp.mode_ask("q")
    assert called["speak"] is False


def test_text_mode_blind_when_no_say(idp, monkeypatch, capsys):
    monkeypatch.setattr(idp, "think", lambda prompt: "answer")
    monkeypatch.setattr(idp, "_say_available", lambda: False)

    code = idp.mode_text("q")
    err = capsys.readouterr().err
    assert code == 2
    assert "BLIND voice no speech synthesis" in err


# --------------------------------------------------------------------------
# The system prompt carries the no-claims rule
# --------------------------------------------------------------------------


def test_system_prompt_no_claims(idp):
    prompt = idp.voice_system()
    assert "never claim" in prompt.lower()
    assert "fleet operator" in prompt.lower()


def test_system_prompt_used_in_payload(idp):
    payload = idp._build_chat_payload("hi", stream=False)
    system = payload["messages"][0]
    assert system["role"] == "system"
    assert "never claim" in system["content"].lower()


def test_system_prompt_configurable(idp, monkeypatch):
    monkeypatch.setenv("VOICE_SYSTEM", "custom system")
    assert idp.voice_system() == "custom system"


# --------------------------------------------------------------------------
# Every HTTP call passes a timeout
# --------------------------------------------------------------------------


def test_post_passes_timeout(idp, monkeypatch):
    captured = {}

    class FakeResp:
        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(idp.urllib.request, "urlopen", fake_urlopen)
    idp._post("http://example.invalid/api/chat", {"x": 1})
    assert captured["timeout"] is not None
    assert captured["timeout"] > 0


def test_get_passes_timeout(idp, monkeypatch):
    captured = {}

    class FakeResp:
        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(idp.urllib.request, "urlopen", fake_urlopen)
    idp._get("http://example.invalid/api/tags")
    assert captured["timeout"] is not None
    assert captured["timeout"] > 0


def test_http_timeout_constant_positive(idp):
    assert idp.HTTP_TIMEOUT > 0


# --------------------------------------------------------------------------
# Transcribe: sibling .txt fallback, BLIND otherwise
# --------------------------------------------------------------------------


def test_transcribe_reads_sibling_txt(idp, tmp_path, no_faster_whisper):
    wav = tmp_path / "utterance.wav"
    wav.write_bytes(b"")
    (tmp_path / "utterance.txt").write_text("hello there", encoding="utf-8")
    assert idp.transcribe(str(wav)) == "hello there"


def test_transcribe_blind_without_whisper_or_txt(idp, tmp_path, monkeypatch, no_faster_whisper):
    monkeypatch.delenv("WHISPER_CMD", raising=False)
    wav = tmp_path / "utterance.wav"
    wav.write_bytes(b"")
    with pytest.raises(idp.Blind) as exc:
        idp.transcribe(str(wav))
    assert "no transcriber" in exc.value.message


def test_transcribe_uses_whisper_cmd(idp, tmp_path, monkeypatch, no_faster_whisper):
    wav = tmp_path / "utterance.wav"
    wav.write_bytes(b"")
    # The path is always appended (see transcribe()'s docstring), so a fake that echoes its
    # arguments emits "transcribed <path>". `sh -c` with $0 discarded prints the literal and
    # ignores everything passed to it: a transcriber that answers the same for any file.
    monkeypatch.setenv("WHISPER_CMD", "sh -c 'printf transcribed' ignored")
    assert idp.transcribe(str(wav)) == "transcribed"


# --------------------------------------------------------------------------
# Config (LAW 46)
# --------------------------------------------------------------------------


def test_config_defaults(idp, monkeypatch):
    for var in ("OLLAMA_HOST", "VOICE_MODEL", "VOICE_MAX_TOKENS", "VOICE_SYSTEM"):
        monkeypatch.delenv(var, raising=False)
    assert idp.ollama_host() == idp.DEFAULT_HOST
    assert idp.voice_model() == idp.DEFAULT_MODEL
    assert idp.voice_max_tokens() == idp.DEFAULT_MAX_TOKENS
    assert idp.voice_system() == idp.SYSTEM_PROMPT


def test_config_overrides(idp, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://example:1234/")
    monkeypatch.setenv("VOICE_MODEL", "llama3")
    monkeypatch.setenv("VOICE_MAX_TOKENS", "42")
    assert idp.ollama_host() == "http://example:1234"
    assert idp.voice_model() == "llama3"
    assert idp.voice_max_tokens() == 42


# --------------------------------------------------------------------------
# --check exits non-zero when nothing is reachable
# --------------------------------------------------------------------------


def test_check_exit_nonzero_when_nothing(idp, monkeypatch, capsys, no_faster_whisper):
    # Every engine must be absent for this to mean anything. `no_faster_whisper` is what makes
    # "nothing" true on a machine where the package IS installed -- without it this case asserted
    # a BLIND state that the box no longer has, and the correct exit 0 looked like a failure.
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
    monkeypatch.setattr(idp, "_say_available", lambda: False)
    code = idp.mode_check()
    assert code == 2


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------


def test_cli_ask(idp, monkeypatch, capsys):
    monkeypatch.setattr(idp, "think", lambda prompt: "the answer")
    code = idp.main(["--ask", "what is stuck"])
    out = capsys.readouterr().out
    assert code == 0
    assert "USER  what is stuck" in out
    assert "AGENT the answer" in out


def test_cli_requires_a_mode(idp):
    with pytest.raises(SystemExit):
        idp.main([])

