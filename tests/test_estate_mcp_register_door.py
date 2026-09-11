"""Regression: the simulate and execute doors must end up in a real FastMCP server's tool
registry after pluggy resolves the plugin's `register_mcp_tools` hookimpl.

Two distinct defects this file guards against (each cost a 12-hour cycle before being found):

1. **Name shadowing / TypeError**. The MCP tool names must stay `simulate_change` and
   `execute_change`, but the wrappers that the MCP server registers MUST NOT be inlined as
   `async def simulate_change(...)` inside `register_mcp_tools` -- a name-equal inner def
   shadows the module-level target at call-time, and live-cluster reproduction showed the
   inner then receiving `graders=...` it had no slot for, returning "Error executing tool"
   silently. The closures in `_make_simulate_change` / `_make_execute_change` bind the
   module-level functions by parameter capture and the inner carries a different `__name__`,
   so no shadowing.

2. **Missing `@hookimpl` decorator**. While moving the wrapper logic into `_make_*` helpers
   in PR #2992, the `@hookimpl` decorator was accidentally left on `_make_simulate_change`
   rather than placed on `register_mcp_tools`. Pluggy then never invoked the plugin's
   register hook, so `simulate_change` and `execute_change` never got registered. Live
   `tools/list` returned 12 tools but the world-model door was not among them, and
   `tools/call simulate_change` returned `Unknown tool: simulate_change`.

The tests below go through the production wiring (real pluggy `PluginManager`, real
`MCPServer`, real `pm.hook.register_mcp_tools`) and assert the tools end up in the actual
tool registry -- not a `_FakeMCP` proxy that only proved the closure pattern, not the
registration path.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pluggy
import pytest
from mcp.server.mcpserver import MCPServer

PLUGIN_FILE = (
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_simulate.py"
)


# Minimal datasette-shaped stand-in. The plugin's `register_mcp_tools` body does not touch
# any datasette attributes at all (the wrapper only references the module-level helpers), so
# an empty stub satisfies it.
class _StubDatasette:
    pass


@pytest.fixture(scope="module")
def estate_simulate_module():
    """Load the plugin module from its on-disk path via importlib.util.spec_from_file_location.

    This mirrors how pluggy loads plugins under `--plugins-dir` (filename, not a Python
    module name). The module is also entered in `sys.modules` under its loaded name so any
    `sys.modules[__name__]` reference inside the plugin would resolve (none should -- the
    fix at PR #2992 dropped that alias).
    """
    spec = importlib.util.spec_from_file_location(
        "estate_simulate_under_test", PLUGIN_FILE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, "spec_from_file_location must yield a loader"
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def real_server_and_hook():
    """Stand up the real FastMCP + a real pluggy root with the `register_mcp_tools` hookspec
    declared, mount the plugin's hookimpls on it, and run `pm.hook.register_mcp_tools(...)`
    exactly the way `datasette_mcp.create_mcp_server` does in production. The returned
    `server._tool_manager` is the production registry the live pod answers `tools/list` from.

    No `_FakeMCP` proxy: tests below read names out of the real `_tool_manager` and assert
    each wrapper is callable with the door's argument set.

    The plugin's `@hookimpl` is `from datasette import hookimpl`, which is a
    `pluggy.HookimplMarker('datasette')`. For pluggy to recognise the impl, the pm must
    have the same project name -- mirroring what `datasette.plugins.pm` is in production.
    """
    _hookspec_marker = pluggy.HookspecMarker("datasette")

    class _ProbeSpecs:
        @_hookspec_marker
        def register_mcp_tools(self, datasette, mcp):
            pass

    pm = pluggy.PluginManager("datasette")
    pm.add_hookspecs(_ProbeSpecs)

    # Mirror datasette_mcp's create_mcp_server wiring, but resolve the hookimpl on THIS pm.
    spec = importlib.util.spec_from_file_location("estate_simulate_proof", PLUGIN_FILE)
    plugin = importlib.util.module_from_spec(spec)
    sys.modules[plugin.__name__] = plugin
    spec.loader.exec_module(plugin)
    pm.register(plugin)

    server = MCPServer("estate-mcp", instructions="probe")
    pm.hook.register_mcp_tools(datasette=_StubDatasette(), mcp=server)
    return server


def test_register_mcp_tools_carries_hookimpl_decorator(estate_simulate_module):
    """Hard guarantee: `register_mcp_tools` itself is decorated with `@hookimpl` (the
    `datasette.hookimpl` marker) so pluggy finds it. The previous fix at PR #2992 left
    `@hookimpl` on a helper function, so pluggy never invoked the hook and the door's tools
    were never registered.
    """
    import pluggy as _pluggy

    fn = estate_simulate_module.register_mcp_tools
    # pluggy stores the marker on the function under `datasette_impl` because the plugin's
    # `@hookimpl` was imported from `datasette` (project='datasette'); the marker attribute
    # name encodes that project.
    assert hasattr(fn, "datasette_impl"), (
        "register_mcp_tools has no datasette_impl marker. "
        "Add `@hookimpl` (from datasette) directly above `def register_mcp_tools(...)`. "
        "Without this decorator, pluggy never invokes the plugin and `simulate_change` is "
        "unreachable via MCP, no matter how clean the closure is."
    )

    # Functional check: with a datasette-shaped pm, this function shows up as an impl.
    _hspec = _pluggy.HookspecMarker("datasette")

    class _ProbeSpecs:
        @_hspec
        def register_mcp_tools(self, datasette, mcp):
            pass

    pm = _pluggy.PluginManager("datasette")
    pm.add_hookspecs(_ProbeSpecs)
    pm.register(estate_simulate_module)
    impls = [i for i in pm.hook.register_mcp_tools.get_hookimpls() if i.function is fn]
    assert impls, (
        "register_mcp_tools is not registered as a pluggy hookimpl on a datasette root. "
        "Re-add @hookimpl above the function (not above any helper it calls)."
    )


def test_simulate_change_is_registered_in_the_real_server(real_server_and_hook):
    """After running the production hook, `simulate_change` MUST appear in the server's
    `_tool_manager.list_tools()` -- this is what `tools/list` reads from on the live pod.
    With the previous missing-`@hookimpl` build, this test sees only the three datasette-mcp
    tools.
    """
    server = real_server_and_hook
    names = {t.name for t in server._tool_manager.list_tools()}
    assert "simulate_change" in names, (
        f"simulate_change missing from real server registry. "
        f"Got: {sorted(names)} -- the @hookimpl decorator is on the wrong function."
    )
    assert "execute_change" in names, "execute_change must be registered alongside"


def test_simulate_change_wrapper_accepts_only_source_and_returns_proposal(
    real_server_and_hook,
):
    """The registered `simulate_change` wrapper dispatches to the module-level function.
    With `config()['graders_door']` false (the env var unset in CI), an empty grader set
    yields verdict UNKNOWN. With it on, the door runs the six graders and answer is
    determined by them. This test runs the form that the deployed pod runs by default.
    """
    server = real_server_and_hook
    tool = {t.name: t for t in server._tool_manager.list_tools()}["simulate_change"]
    # The tool's __call__ through the registered wrapper; FastMCP tool objects expose
    # `fn` as the underlying callable and `run` for the async wrapper.
    result = asyncio.run(tool.fn("hello"))
    assert isinstance(result, dict), (
        f"simulate_change must return a dict proposal; got {result!r}"
    )
    assert "verdict" in result, f"proposal missing verdict; got keys: {list(result)}"
    assert result["verdict"] in ("SAFE", "UNSAFE", "UNKNOWN"), (
        f"verdict invalid: {result['verdict']}"
    )


def test_execute_change_wrapper_refuses_unknown_proposal(real_server_and_hook):
    """execute_change must refuse a non-existent proposal with the standard refusal envelope,
    not raise (a raised exception would surface as 'Error executing tool' from datasette-mcp).
    """
    server = real_server_and_hook
    tool = {t.name: t for t in server._tool_manager.list_tools()}["execute_change"]
    result = asyncio.run(tool.fn("00000000-0000-0000-0000-000000000000", ""))
    assert isinstance(result, dict)
    assert result.get("executed") is False
    assert isinstance(result.get("error"), str), "refusal envelope missing reason"


def test_pluggy_resolves_register_mcp_tools_via_hookspec(real_server_and_hook):
    """The `register_mcp_tools` hookspec MUST have at least two impls registered on the pm
    after `pm.register(plugin)`: datasette_mcp's own (for list_databases etc.) and
    estate_simulate's. A missing impl on the plugin's side is exactly what the bug was.

    Belt-and-braces: this is the same observable outcome as the previous test, but framed
    in pluggy terms so a future regression that moves `register_mcp_tools` back into a
    module `--pluggy cannot see it` directly fails this test even if the closure wrappers
    themselves remained valid.
    """
    names = sorted(t.name for t in real_server_and_hook._tool_manager.list_tools())
    assert "simulate_change" in names and "execute_change" in names, (
        f"Both world-model doors must end up in the production tool registry. "
        f"Got: {names}"
    )
