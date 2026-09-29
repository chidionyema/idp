"""Every estate MCP plugin must load, and register its tools, the way estate-mcp does.

datasette.utils.module_from_path execs a plugin into a module it never puts in sys.modules.
On Python 3.13 (estate-mcp.Dockerfile), `@dataclass` under `from __future__ import annotations`
looks the class's module up in sys.modules and gets None, so the import raised AttributeError
and estate-mcp crashlooped (oke-check break-glass 36514295848: jev.py line 79). The other
plugin tests register their module in sys.modules first, which hides exactly this failure.

Loading is not enough: datasette-mcp then calls each plugin's register_mcp_tools, and FastMCP
builds a pydantic schema for every tool's return there. An async-generator tool has no schema,
so the server died at boot on the image that fixed jev.py (voice.py voice_intent_stream,
2026-09-29), taking remember and recall down with it.
"""

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

PLUGINS = sorted((Path(__file__).resolve().parents[1] / "mcp" / "plugins").glob("*.py"))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Deliberately never registered in sys.modules: that is datasette's shape.
    assert path.name not in sys.modules
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("path", PLUGINS, ids=lambda p: p.name)
def test_plugin_loads_without_sys_modules_entry(path: Path) -> None:
    _load(path)


class _ToolRegistry:
    """Stands in for FastMCP: records tools and rejects the shape FastMCP cannot serve."""

    def __init__(self) -> None:
        self.tools: dict = {}

    def add_tool(self, fn, *args, **kwargs):
        assert not (
            inspect.isasyncgenfunction(fn) or inspect.isgeneratorfunction(fn)
        ), f"MCP tool {fn.__name__} is a generator; an MCP tool must return a value"
        self.tools[fn.__name__] = fn
        return fn

    def tool(self, *args, **kwargs):
        return self.add_tool


@pytest.mark.parametrize("path", PLUGINS, ids=lambda p: p.name)
def test_plugin_tools_register_like_fastmcp(path: Path) -> None:
    register = getattr(_load(path), "register_mcp_tools", None)
    if register is None:
        pytest.skip("no MCP tools in this plugin")
    register(datasette=None, mcp=_ToolRegistry())
