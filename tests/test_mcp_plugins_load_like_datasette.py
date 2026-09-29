"""Every estate MCP plugin must load the way datasette loads it.

datasette.utils.module_from_path execs a plugin into a module it never puts in sys.modules.
On Python 3.13 (estate-mcp.Dockerfile), `@dataclass` under `from __future__ import annotations`
looks the class's module up in sys.modules and gets None, so the import raised AttributeError
and estate-mcp crashlooped (oke-check break-glass 36514295848: jev.py line 79). The other
plugin tests register their module in sys.modules first, which hides exactly this failure.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PLUGINS = sorted((Path(__file__).resolve().parents[1] / "mcp" / "plugins").glob("*.py"))


@pytest.mark.parametrize("path", PLUGINS, ids=lambda p: p.name)
def test_plugin_loads_without_sys_modules_entry(path: Path) -> None:
    spec = importlib.util.spec_from_file_location(path.name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Deliberately never registered in sys.modules: that is datasette's shape.
    assert path.name not in sys.modules
    spec.loader.exec_module(mod)
