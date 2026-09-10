"""Regression: the MCP-tool wrappers for `simulate_change` and `execute_change` must dispatch
through the module-level functions, not recurse into local @mcp.tool() defs of the same name
(which only accept the tool's public argument set and would reject `graders=`).

Live reproduction on the running estate-mcp pod, on a build that still inlines the wrapper:
    POST /-/mcp tools/call {\"name\": \"simulate_change\", \"arguments\": {\"source\": \"hello\"}}
      -> {\"isError\": true, \"content\": [{\"text\": \"Error executing tool simulate_change\"}]}
      -> exec inside the pod with the broken build:
         TypeError: register_mcp_tools.<locals>.simulate_change()
         got an unexpected keyword argument 'graders'

Live reproduction after the first fix (sys.modules[__name__] alias): the pod would not even
start because pluggy loads plugins by filename, so `__name__ == 'estate_simulate.py'` and
`sys.modules['estate_simulate.py']` does not exist.

This test guards the closed-over by-function wrapper that uses @wraps to keep the registered
tool name `simulate_change` while the inner function carries a different name.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

PLUGIN_FILE = (
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_simulate.py"
)


class _FakeMCP:
    """Minimal stand-in for the FastMCP the estate-mcp server passes in.

    Real FastMCP exposes `@mcp.tool()` as a decorator and registers by tool name. This fake
    matches the registration path (`add_tool` with explicit `name=`) since the production
    registration uses `mcp.add_tool(wrapper, name="simulate_change")` after the closed-over
    wrapper shadowing fix.
    """

    def __init__(self):
        self.tools: dict[str, object] = {}

    def add_tool(self, fn, *, name: str):
        self.tools[name] = fn
        return fn


class _FakeDatasette:  # datasette-mcp's hookimpl contract
    pass


@pytest.fixture(scope="module")
def estate_simulate_module():
    """Load the plugin module from its on-disk path via importlib.util.spec_from_file_location.

    This is the same wiring the production datasette-mcp server does (`--plugins-dir` loads
    plugins by file path through pluggy). Using `importlib` here is also what
    bin/test-executes-gate counts as 'this test runs something' -- a test that merely inspects
    file text cannot catch a behaviour defect, and was the defect class wiped on 2026-09-04 (519d59e8).

    The plugin's `__name__` after a pluggy load is the bare filename `estate_simulate.py`,
    which is intentionally NOT a Python module name; this fixture loads under a real module
    name so any `sys.modules[<name>]` access by the suite path is fine. The assertion below
    verifies that `register_mcp_tools` does NOT rely on `sys.modules[__name__]`, which would
    crash at startup.
    """
    spec = importlib.util.spec_from_file_location(
        "estate_simulate_under_test", PLUGIN_FILE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def fake_mcp_datasette():
    mcp = _FakeMCP()
    register = _FakeDatasette()
    return mcp, register


def test_register_does_not_touch_sys_modules_by_filename(estate_simulate_module):
    """register_mcp_tools must work even when sys.modules does not carry the plugin under the
    bare filename. Pluggy loads plugins by filename; `sys.modules['estate_simulate.py']` does
    not exist on the production path. A name miss at registration crashes the pod on startup
    (regression: estate-mcp CrashLoopBackOff after the first sys.modules-based fix).
    """
    # Make sure the filename is missing from sys.modules (it never is from a real pluggy load).
    assert "estate_simulate.py" not in sys.modules
    # Calling register_mcp_tools must complete without raising a KeyError on sys.modules lookups.
    estate_simulate_module.register_mcp_tools(_FakeDatasette(), _FakeMCP())


def test_simulate_change_wrapper_calls_module_level_not_self(
    estate_simulate_module, fake_mcp_datasette
):
    """The MCP wrapper for simulate_change must call the module-level simulate_change and not
    recurse into itself. The wrapper is exposed under the registered tool name `simulate_change`,
    but the inner function is named differently (so it does not shadow the target). With the
    fix in place, calling the wrapper returns the module-level proposal; with the recursion
    bug (a closed-over name of the same shape calling itself), TypeError.
    """
    mcp, register = fake_mcp_datasette
    estate_simulate_module.register_mcp_tools(register, mcp)
    assert "simulate_change" in mcp.tools, (
        "register_mcp_tools did not register `simulate_change`"
    )
    wrapper = mcp.tools["simulate_change"]

    result = asyncio.run(wrapper("hello"))
    assert isinstance(result, dict)
    assert "verdict" in result, (
        "module-level simulate_change should run; got a recursion TypeError"
    )
    assert result["verdict"] == "UNKNOWN", (
        "no graders wired -> verdict is UNKNOWN (fail-closed)"
    )


def test_execute_change_wrapper_calls_module_level_not_self(
    estate_simulate_module, fake_mcp_datasette
):
    """The MCP wrapper for execute_change must call the module-level execute_change and not
    recurse into itself.
    """
    mcp, register = fake_mcp_datasette
    estate_simulate_module.register_mcp_tools(register, mcp)
    wrapper = mcp.tools["execute_change"]

    # No proposal on the registry: the real execute_change returns `{"executed": False, "error": ...}`
    # not a TypeError raised from an unbound self-recursion.
    result = asyncio.run(wrapper("00000000-0000-0000-0000-000000000000", ""))
    assert isinstance(result, dict)
    assert "executed" in result
    assert result["executed"] is False
    # The refusal reason comes from the module-level execute_change, not a recursion traceback.
    assert isinstance(result.get("error"), str)


def test_simulate_change_wrapper_inherits_docstring(
    estate_simulate_module, fake_mcp_datasette
):
    """The closed-over wrapper's `__doc__` carries through (via functools.wraps) so the MCP
    tools/list description still names the door. Without this, tools/list description becomes
    a one-liner or None, and an agent calling simulate_change without first reading tools/list
    has no way to find out what the door accepts.
    """
    mcp, register = fake_mcp_datasette
    estate_simulate_module.register_mcp_tools(register, mcp)
    wrapper = mcp.tools["simulate_change"]
    assert isinstance(getattr(wrapper, "__doc__", None), str)
    assert "simulate-before-execute door" in (wrapper.__doc__ or "")
    assert "MUM-288" in (wrapper.__doc__ or ""), "docstring lost the spec reference"
