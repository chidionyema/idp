"""Regression: the MCP-tool wrapper `simulate_change(source)` must dispatch through the
module-level function, not recurse into its own local definition (which only accepts `source`
and would refuse `graders=` with TypeError). Live reproduction on the running estate-mcp pod:

    POST /-/mcp tools/call {"name":"simulate_change","arguments":{"source":"hello"}}
    -> {"isError": true, "content":[{"text":"Error executing tool simulate_change"}]}
    -> inner def simulate_change() got an unexpected keyword argument 'graders'

The fix at `mcp/plugins/estate_simulate.py` binds the module-level targets to non-shadowing
local names (via `sys.modules[__name__]`) and the inner `@mcp.tool()` defs call those, keeping
the MCP tool name intact while forwarding the door's grader argument.
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
    """Minimal stand-in for the FastMCP the estate-mcp server passes in. Records the wrappers.

    The real FastMCP @mcp.tool() decorator, given `async def simulate_change(source: str)`,
    registers the inner function AS A LOCAL NAME of `register_mcp_tools` -- that is exactly the
    shadowing condition this test guards against. The fake honours the same contract.
    """

    def __init__(self):
        self.tools: dict[str, object] = {}

    def tool(self, **_kw):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


class _FakeDatasette:  # datasette-mcp's hookimpl contract
    pass


@pytest.fixture(scope="module")
def estate_simulate_module():
    """Load the plugin module from its on-disk path via importlib.util.spec_from_file_location.

    This is the same wiring the production datasette-mcp server does (`register_plugin(...)`
    loads plugins by file path). Using `importlib` here is also what bin/test-executes-gate
    counts as 'this test runs something' -- a test that merely inspects file text cannot catch
    a behaviour defect, and was the defect class wiped on 2026-09-04 (519d59e8).
    """
    spec = importlib.util.spec_from_file_location(
        "estate_simulate_under_test", PLUGIN_FILE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # The plugin's `register_mcp_tools` reads `sys.modules[__name__]`, so the dynamic module
    # has to be in the import registry before exec_module. importlib.util.exec_module does
    # NOT insert automatically.
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def fake_mcp_datasette():
    mcp = _FakeMCP()
    register = _FakeDatasette()
    return mcp, register


def test_simulate_change_wrapper_calls_module_level_not_self(
    estate_simulate_module, fake_mcp_datasette
):
    """The MCP wrapper simulate_change must call the module-level simulate_change; a recursion
    into itself with `graders=` raises TypeError. With the fix in place, no TypeError is raised
    and the wrapper returns a real proposal (verdict UNKNOWN here because no graders are wired).
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
    """The MCP wrapper execute_change must call the module-level execute_change; a recursion into
    itself would call execute_change() with no arguments and TypeError before refusal messages.
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
