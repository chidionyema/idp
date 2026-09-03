"""crew#716 CP2: verify the clocks table matches its sources."""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BIN = str(ROOT / "bin" / "estate-clocks")

# Load the bin script using the same pattern as other tests
spec = importlib.util.spec_from_file_location(
    "estate_clocks", BIN, loader=SourceFileLoader("estate_clocks", BIN)
)
estate_clocks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(estate_clocks)


def test_render_matches_file():
    """The rendered output must match the file on disk."""
    output = estate_clocks.render(ROOT)
    clocks_md = ROOT / "docs" / "scheduling" / "CLOCKS.md"
    actual = clocks_md.read_text()
    assert output == actual, "run bin/estate-clocks"
