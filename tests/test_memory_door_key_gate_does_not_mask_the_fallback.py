"""A missing MCP_GATEWAY_KEY must not refuse a write the local origin can serve.

Measured 2026-11-12: `remember` was refused twice under two different messages -- the pi
transport reported `URLError: EOF occurred in violation of protocol` and the bridge reported
`no MCP_GATEWAY_KEY`. Both were the same outage. The cloud origin was genuinely dead
(Cloudflare 1033 / TLS EOF, documented 2026-11-09), and a local-primary store was answering
writes the whole time -- but `Bridge.forward` resolved the credential and refused BEFORE
calling `door.post()`, which is the function that asks the local store first and needs no key.

That is R6 recurring in a new place: the recovery path was gated behind the thing that failed.

These tests read the SHIPPED bridge and fail if the gate is ever moved back in front of the
local origin, or if the fix ever weakens the remote path instead of widening recognition of the
local one (AGENTS.md section 9, R14).
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bin" / "estate-memory-mcp"


def _bridge():
    loader = importlib.machinery.SourceFileLoader("shipped_bridge", str(BRIDGE))
    spec = importlib.util.spec_from_loader("shipped_bridge", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _call_without_key(name: str, arguments: dict) -> dict:
    """Run the shipped bridge as a subprocess with the key unset -- the failing condition."""
    env = {k: v for k, v in os.environ.items() if k != "MCP_GATEWAY_KEY"}
    payload = "\n".join(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }
            ),
        ]
    )
    out = subprocess.run(
        ["python3", str(BRIDGE)],
        input=payload + "\n",
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(ROOT),
    )
    lines = [ln for ln in out.stdout.splitlines() if ln.strip().startswith("{")]
    assert lines, f"the bridge printed no reply at all:\n{out.stdout}\n{out.stderr}"
    return json.loads(lines[-1])["result"]


def test_a_write_with_no_key_is_served_by_the_local_origin():
    """THE FALSIFIER. Unset MCP_GATEWAY_KEY, ask for a write, and it must be a write."""
    result = _call_without_key(
        "remember",
        {
            "content": "test: the keyless local origin served this write",
            "subject": "test-memory-door-key-gate",
            "kind": "fact",
        },
    )
    assert result.get("isError") is False, (
        "remember was refused with no MCP_GATEWAY_KEY. The local-primary origin needs no "
        f"credential, so the key gate is in front of it again: {result}"
    )
    body = json.loads(result["content"][0]["text"])
    assert body["written"] is True
    assert body["storage"] == "local-primary", body


def test_the_write_is_readable_back():
    """A write nobody can read is not a write. Recall must return the probe text."""
    result = _call_without_key("recall", {"query": "keyless local origin served this write"})
    assert result.get("isError") is False, result
    texts = [m["text"] for m in json.loads(result["content"][0]["text"])["memories"]]
    assert any("keyless local origin served this write" in t for t in texts), texts


def test_the_missing_key_still_refuses_when_the_local_origin_declines():
    """R14: widen recognition, never weaken the check.

    When the local store would not answer either, a missing key is the true reason and the
    true message, and it must still be said out loud.
    """
    module = _bridge()
    bridge = module.Bridge.__new__(module.Bridge)
    bridge.key = lambda: ""  # no credential at all
    declined = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {"name": "__no_such_tool__", "arguments": {}},
    }
    assert bridge._local_answers(declined) is False, (
        "the local store claims it would answer a tool it does not have; a missing key would "
        "then be hidden behind a local answer that does not exist"
    )


def test_the_key_gate_is_not_ahead_of_the_local_origin():
    """Read the decision out of the shipped source, not out of this file's belief about it.

    Parse to CODE, not to prose: `_local_answers` also appears in forward()'s docstring, and a
    substring search that hits the docstring measures the explanation instead of the logic.
    """
    import ast

    tree = ast.parse(BRIDGE.read_text())
    forward = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "forward"
    )
    # Every name and attribute forward() actually touches, in source order, excluding comments
    # and docstrings by construction -- ast nodes do not include either.
    local_lines = [
        n.lineno
        for n in ast.walk(forward)
        if (isinstance(n, ast.Name) and n.id == "_local_answers")
        or (isinstance(n, ast.Attribute) and n.attr == "_local_answers")
    ]
    post_lines = [
        n.lineno
        for n in ast.walk(forward)
        if isinstance(n, ast.Attribute) and n.attr == "post"
    ]
    assert local_lines, "forward() no longer consults the local origin before refusing"
    assert post_lines, "forward() no longer calls door.post()"
    assert min(local_lines) < min(post_lines), (
        "forward() reaches door.post() (line %d) before establishing whether the keyless "
        "local origin would answer (line %d), which is the 2026-11-12 defect"
        % (min(post_lines), min(local_lines))
    )
