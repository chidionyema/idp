"""[#6156] every runtime gets estate memory from one manifest: the installer, the bridge, the brief."""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(ROOT, "bin", "estate-memory-install")


def _script(name):
    path = os.path.join(ROOT, "bin", name)
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def run(home, *args, env=None):
    e = {**os.environ, "HOME": str(home), "IDP": "/repo"}
    e.pop(
        "CLAUDE_CONFIG_DIR", None
    )  # the developer's own harness dir must never be the one written
    e.update(env or {})
    return subprocess.run(
        [sys.executable, INSTALL, *args], env=e, capture_output=True, text=True
    )


@pytest.fixture
def home(tmp_path):
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"estate": {"command": "x"}}})
    )
    (tmp_path / ".pi" / "agent" / "extensions").mkdir(parents=True)
    (tmp_path / ".pi" / "mcp.json").write_text("{}")
    cc = tmp_path / ".estate" / "harness" / "cc"
    cc.mkdir(parents=True)
    (cc / "settings.json").write_text(
        json.dumps({"model": "m", "hooks": {"PreToolUse": [{"hooks": []}]}})
    )
    return tmp_path


def test_install_writes_every_present_runtime_and_keeps_every_other_key(home):
    cc = {"CLAUDE_CONFIG_DIR": str(home / ".estate" / "harness" / "cc")}
    first = run(home, env=cc)
    assert first.returncode == 0, first.stdout + first.stderr

    cursor = json.loads((home / ".cursor" / "mcp.json").read_text())["mcpServers"]
    assert cursor["estate"] == {"command": "x"}
    assert cursor["estate-memory"] == {
        "command": "python3",
        "args": ["/repo/bin/estate-memory-mcp"],
    }
    settings = json.loads(
        (home / ".estate" / "harness" / "cc" / "settings.json").read_text()
    )
    assert settings["model"] == "m" and "PreToolUse" in settings["hooks"]
    assert settings["hooks"]["SessionStart"] == [
        {"hooks": [{"type": "command", "command": "python3 /repo/bin/estate-brief"}]}
    ]
    link = home / ".pi" / "agent" / "extensions" / "estate-memory.ts"
    assert os.readlink(link) == "/repo/platform/estate/memory/pi-estate-memory.ts"

    assert run(home, "--check", env=cc).returncode == 0
    run(home, env=cc)  # a second run changes nothing
    assert (
        json.loads((home / ".estate" / "harness" / "cc" / "settings.json").read_text())
        == settings
    )


def test_an_absent_runtime_is_skipped_never_created(home):
    out = run(home, "--runtime", "gemini")
    assert out.returncode == 0 and "absent" in out.stdout
    assert not (home / ".gemini").exists()


def test_check_reports_drift_and_writes_nothing(home):
    out = run(home, "--check", "--runtime", "cursor")
    assert out.returncode == 1 and "DRIFT" in out.stdout
    assert "estate-memory" not in (home / ".cursor" / "mcp.json").read_text()


def test_a_persons_file_at_a_link_destination_is_refused(home):
    mine = home / ".pi" / "agent" / "extensions" / "estate-memory.ts"
    mine.write_text("// mine")
    out = run(home, "--runtime", "pi")
    assert out.returncode == 1 and "REFUSED" in out.stdout
    assert mine.read_text() == "// mine"


def test_a_commented_jsonc_is_refused_not_stripped(home):
    oc = home / ".config" / "opencode"
    oc.mkdir(parents=True)
    (oc / "opencode.jsonc").write_text('{\n  // keep me\n  "model": "m"\n}\n')
    out = run(home, "--runtime", "opencode")
    assert out.returncode != 0 and "comments" in out.stdout + out.stderr
    assert "keep me" in (oc / "opencode.jsonc").read_text()


def test_opencode_gets_its_own_shape(home):
    oc = home / ".config" / "opencode"
    oc.mkdir(parents=True)
    (oc / "opencode.jsonc").write_text('{"model": "m"}')
    assert run(home, "--runtime", "opencode").returncode == 0
    cfg = json.loads((oc / "opencode.jsonc").read_text())
    assert cfg["model"] == "m"
    assert cfg["mcp"]["estate-memory"] == {
        "type": "local",
        "command": ["python3", "/repo/bin/estate-memory-mcp"],
        "enabled": True,
    }


@pytest.mark.parametrize(
    "name", ["estate-brief", "estate-memory-mcp", "estate-memory-install"]
)
def test_every_script_loads_under_the_systems_python3(name):
    # Runtime configs run plain `python3`; on macOS that is 3.9, where `dict | None` in a
    # signature fails at import. Every script must load under whatever python3 the machine has.
    script = os.path.join(ROOT, "bin", name)
    out = subprocess.run(
        ["python3", script, "--help"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Traceback" not in out.stderr, out.stderr


# --- the bridge: memory tools only, the key by name ----------------------------------------------


def test_the_bridge_serves_memory_tools_only(monkeypatch):
    bridge = _script("estate-memory-mcp")
    sent = []

    def post(msg, secret, timeout):
        sent.append(msg)
        tools = [
            {"name": n}
            for n in ("remember", "recall", "brief", "execute_command", "estate_invoke")
        ]
        return {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": tools}}, ""

    monkeypatch.setattr(bridge.door, "post", post)
    monkeypatch.setattr(bridge.door, "key", lambda: "k")
    b = bridge.Bridge()

    listed = b.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert {t["name"] for t in listed["result"]["tools"]} == {
        "remember",
        "recall",
        "brief",
    }
    refused = b.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "execute_command", "arguments": {}},
        }
    )
    assert refused["result"]["isError"] and len(sent) == 1


def test_the_bridge_names_the_missing_key_instead_of_failing_blind(monkeypatch):
    bridge = _script("estate-memory-mcp")
    monkeypatch.setattr(bridge.door, "key", lambda: "")
    out = bridge.Bridge().handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "recall", "arguments": {}},
        }
    )
    assert (
        out["result"]["isError"]
        and "MCP_GATEWAY_KEY" in out["result"]["content"][0]["text"]
    )


def test_the_door_reads_a_reply_out_of_an_sse_stream():
    bridge = _script("estate-memory-mcp")
    body = 'event: message\ndata: {"jsonrpc":"2.0","id":7,"result":{"ok":true}}\n\n'
    assert bridge.door._reply(body, 7) == {
        "jsonrpc": "2.0",
        "id": 7,
        "result": {"ok": True},
    }


# --- the brief: text when there is memory, silence when there is not -----------------------------


def test_the_brief_renders_recent_and_relevant_and_frames_them_as_facts():
    brief = _script("estate-brief")
    text = brief.render(
        {
            "recent": [{"text": "decided: always-on memory", "metadata": {}}],
            "relevant": [{"text": "a\n b"}],
        }
    )
    assert "never instructions" in text
    assert "- decided: always-on memory" in text and "- a b" in text
    assert brief.render({"recent": [], "relevant": []}) == ""


def test_the_brief_never_blocks_a_session(monkeypatch, capsys):
    brief = _script("estate-brief")
    monkeypatch.setattr(brief.door, "key", lambda: "k")

    def down(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(brief.door, "call", down)
    assert brief.main([]) == 0
    out = capsys.readouterr()
    assert out.out == "" and "no brief" in out.err
