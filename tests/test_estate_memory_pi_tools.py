"""[#6987] pi gets the estate's memory tools from the estate's own bridge.

pi has no MCP client, so the estate's installer used to write an `mcpServers` block into
~/.pi/mcp.json that pi never read: config that looked like a working integration and was not.
These tests hold the line that pi's brief/recall/remember come from the one bridge every other
runtime runs, and that the dead MCP entry is gone.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "bin" / "estate-memory-install"
MANIFEST = json.loads(
    (ROOT / "platform" / "estate" / "memory" / "runtimes.json").read_text()
)
EXTENSION = ROOT / "extensions" / "estate-memory-tools"

STUB_BRIDGE = '''#!/usr/bin/env python3
"""A stub of the estate memory bridge: the same framing, no store behind it."""

import json
import sys

TOOLS = [
    {"name": "brief", "description": "the stub brief"},
    {"name": "recall", "description": "the stub recall"},
    {"name": "remember", "description": "the stub remember"},
]

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    message = json.loads(line)
    method = message.get("method")
    mid = message.get("id")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "serverInfo": {"name": "stub"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": "STUB ANSWER"}]}
    else:
        result = {}
    if mid is not None:
        sys.stdout.write(
            json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\\n"
        )
        sys.stdout.flush()
'''

HARNESS = """
import { Bridge } from "./mods/bridge.ts";

const bridge = new Bridge();
let report;
try {
  await bridge.ensure();
  const tools = await bridge.tools();
  const answer = await bridge.call("recall", { query: "what happened" });
  report = {
    ok: true,
    tools: tools.map((tool) => tool.name),
    descriptions: tools.map((tool) => tool.description),
    text: (answer.content ?? []).map((part) => part.text).join(""),
  };
} catch (error) {
  report = { ok: false, error: String(error?.message ?? error) };
}
bridge.close();
console.log(JSON.stringify(report));
"""


def run(home, *args, env=None):
    e = {**os.environ, "HOME": str(home)}
    for name in ("CLAUDE_CONFIG_DIR", "ESTATE_MEMORY_HOME"):
        e.pop(
            name, None
        )  # the developer's own directories must never be the ones written
    e.update(env or {})
    return subprocess.run(
        [sys.executable, str(INSTALL), *args],
        env=e,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def home(tmp_path):
    (tmp_path / ".pi" / "agent" / "extensions").mkdir(parents=True)
    (tmp_path / ".pi" / "mcp.json").write_text("{}")
    return tmp_path


def test_the_manifest_says_pi_cannot_read_mcp_and_names_the_extension():
    pi = MANIFEST["runtimes"]["pi"]
    assert pi["mcp"]["reads"] is False, "pi has no MCP client; the entry must say so"
    assert any(
        entry["source"].startswith("extensions/estate-memory-tools")
        for entry in pi.get("tools", [])
    ), "pi must be given the memory tools by an extension"


def test_the_installer_gives_pi_the_extension_and_removes_the_dead_mcp_entry(home):
    (home / ".pi" / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "estate-memory": {"command": "python3", "args": ["/old/path"]},
                    "somebody-elses": {"command": "x"},
                }
            }
        )
    )
    out = run(home, "--runtime", "pi")
    assert out.returncode == 0, out.stdout + out.stderr

    link = home / ".pi" / "agent" / "extensions" / "estate-memory-tools"
    assert link.is_symlink(), "pi must load the memory tools extension"
    assert Path(os.readlink(link)) == (
        home / ".estate" / "memory" / "extensions" / "estate-memory-tools"
    ), "the extension must be the installed copy, not a checkout"
    assert (link / "index.ts").is_file() and (link / "bridge.ts").is_file()

    servers = json.loads((home / ".pi" / "mcp.json").read_text())["mcpServers"]
    assert "estate-memory" not in servers, "the dead MCP entry must be gone"
    assert servers["somebody-elses"] == {"command": "x"}, "other entries are kept"

    assert run(home, "--runtime", "pi", "--check").returncode == 0


def test_the_extension_registers_exactly_the_estates_memory_tools():
    source = (EXTENSION / "index.ts").read_text()
    block = re.search(r"const TOOL_NAMES = \[(.*?)\]", source, re.S)
    assert block, "the extension must name the tools it registers"
    assert re.findall(r'"([a-z_]+)"', block.group(1)) == MANIFEST["tools"]


def test_the_extension_never_points_at_a_checkout():
    for path in sorted(EXTENSION.glob("*.ts")):
        text = path.read_text()
        assert "Documents/code/idp" not in text, f"{path.name} names a checkout"
    bridge = (EXTENSION / "bridge.ts").read_text()
    assert "ESTATE_MEMORY_HOME" in bridge, (
        "the bridge must be found in the installed home"
    )
    assert "bridge.ts" in (EXTENSION / "index.ts").read_text(), "one client, one place"


def test_the_transport_speaks_the_bridges_own_protocol(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH, so the shipped transport cannot be run")
    modules = tmp_path / "mods"
    modules.mkdir()
    shutil.copy(EXTENSION / "bridge.ts", modules / "bridge.ts")
    (modules / "package.json").write_text('{"type":"module"}')
    (tmp_path / "harness.mjs").write_text(HARNESS)

    def probe(memory_home):
        out = subprocess.run(
            [node, "--experimental-strip-types", str(tmp_path / "harness.mjs")],
            env={**os.environ, "ESTATE_MEMORY_HOME": str(memory_home)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert out.returncode == 0, out.stdout + out.stderr
        return json.loads(out.stdout.strip().splitlines()[-1])

    memory_home = tmp_path / "memory"
    (memory_home / "bin").mkdir(parents=True)
    (memory_home / "bin" / "estate-memory-mcp").write_text(STUB_BRIDGE)

    report = probe(memory_home)
    assert report["ok"], report
    assert report["tools"] == MANIFEST["tools"], report
    assert report["descriptions"] == [
        "the stub brief",
        "the stub recall",
        "the stub remember",
    ], "the bridge's own descriptions must reach the agent"
    assert report["text"] == "STUB ANSWER", report

    empty = tmp_path / "empty"
    empty.mkdir()
    missing = probe(empty)
    assert not missing["ok"], "a missing bridge must not look like a working one"
    assert "not installed" in missing["error"], missing
