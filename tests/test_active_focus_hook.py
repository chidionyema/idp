"""Prove the SHIPPED Active Focus extension registers a context handler and injects once.

This reads the real file at ~/.pi/agent/extensions/active-focus-memory/index.ts, strips the
imports and the few TypeScript annotations it uses, and executes the module's own logic
against the real engine. If the extension never registers on("context"), if the marker guard
disappears so the header can stack, or if it calls an SDK method that does not exist, a test
here fires. That is the whole point: the hook is proven by running it, not by reading it.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EXT = Path("/Users/roseonyema/.pi/agent/extensions/active-focus-memory/index.ts")
ENGINE = Path("/Users/roseonyema/.estate/bin/estate-memory-engine")
# node is not on PATH inside the executor; resolve it explicitly or every probe fails on
# FileNotFoundError and the test grades a missing binary rather than the hook's logic.
NODE_CANDIDATES = (
    Path("/Users/roseonyema/.nvm/versions/node/v22.15.1/bin/node"),
    Path("/opt/homebrew/bin/node"),
    Path("/usr/local/bin/node"),
)


def _node() -> str:
    for candidate in NODE_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    raise AssertionError("node not found; the hook cannot be proven without it")


def _src() -> str:
    assert EXT.is_file(), f"extension not found at {EXT}"
    return EXT.read_text(encoding="utf-8")


def _body() -> str:
    """The module with imports removed and its annotations lowered to plain JavaScript."""
    src = re.sub(r"^import\s+type[^;]*;", "", _src(), flags=re.M)
    src = re.sub(r"^import\s+[^;]*from\s+[\"'][^\"']+[\"'];", "", src, flags=re.M)
    src = re.sub(r"^import\s+[\"'][^\"']+[\"'];", "", src, flags=re.M)
    # Lower the TypeScript the file actually uses, narrowly rather than globally.
    src = src.replace(": readonly unknown[]", "")
    src = src.replace(": string | null", "")
    src = src.replace("): boolean {", ") {")
    src = src.replace("(pi: ExtensionAPI)", "(pi)")
    src = src.replace("(messages: readonly unknown[])", "(messages)")
    src = re.sub(r"\b(content|part|message) as \{[^}]*\}", r"\1", src)
    src = src.replace(" as const", "")
    src = src.replace("export default function activeFocusMemory", "function activeFocusMemory")
    assert "function activeFocusMemory" in src, "extension entrypoint was not found"
    return src


def _run_js() -> str:
    script = (
        'import { execFileSync } from "node:child_process";\n'
        'import { existsSync } from "node:fs";\n'
        'import { homedir } from "node:os";\n'
        'import { join } from "node:path";\n'
        + _body()
        + """
let handler = null;
const pi = { on: (ev, h) => { if (ev === "context") handler = h; } };
activeFocusMemory(pi);
if (!handler) { console.log("NO_HANDLER"); }
else {
  const r1 = await handler({ type: "context", messages: [{ role: "user", content: "hi" }] });
  const injected = Array.isArray(r1 && r1.messages) && r1.messages.length === 2 &&
    String(r1.messages[0].content).includes("GENESIS ACTIVE FOCUS REGISTER");
  console.log(injected ? "INJECTS" : "NO_INJECT");
  if (injected) {
    const r2 = await handler({ type: "context", messages: r1.messages });
    console.log(r2 === undefined ? "ONCE" : "DUPLICATES");
  }
}
"""
    )
    proc = subprocess.run(
        [_node(), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=90,
    )
    return f"{proc.stdout}\n{proc.stderr}"


def test_engine_emits_the_marker_the_hook_keys_on() -> None:
    """The guard is only real if the engine truly prints the marker it searches for."""
    assert ENGINE.is_file(), f"engine missing at {ENGINE}"
    proc = subprocess.run([str(ENGINE), "render-focus"], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-600:]
    assert "GENESIS ACTIVE FOCUS REGISTER" in proc.stdout


def test_extension_registers_a_context_handler_and_injects() -> None:
    out = _run_js()
    assert "NO_HANDLER" not in out, f"extension never registered on('context'):\n{out[-900:]}"
    assert "INJECTS" in out, f"header was not injected into messages:\n{out[-900:]}"


def test_extension_injects_only_once() -> None:
    """Without the marker guard the register stacks and defeats its own token budget."""
    out = _run_js()
    assert "ONCE" in out, f"marker guard missing, header can duplicate:\n{out[-900:]}"


def test_extension_does_not_call_an_invented_sdk_method() -> None:
    """appendSystemContext is not in ExtensionAPI; calling it throws at session start.

    The check reads executable CODE, not prose: the file's own comment explains that the
    method does not exist, and a naive substring scan grades the explanation as the defect.
    """
    code = re.sub(r"/\*.*?\*/", "", _src(), flags=re.S)
    code = re.sub(r"//[^\n]*", "", code)
    assert "appendSystemContext" not in code, "the hook calls an SDK method that does not exist"


def test_extension_is_a_directory_not_a_loose_file() -> None:
    """Pi loads extensions as <name>/index.ts directories; a bare .ts file never loads."""
    assert EXT.name == "index.ts" and EXT.parent.name == "active-focus-memory"
    stray = Path("/Users/roseonyema/.pi/agent/extensions/active-focus-memory-hook.ts")
    assert not stray.exists(), f"a loose extension file also exists and will not load: {stray}"


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q", "-p", "no:warnings"]))
