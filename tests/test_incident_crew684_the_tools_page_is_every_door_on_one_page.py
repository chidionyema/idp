"""Incident 2026-08-30 (crew#684): the founder saw red, could not tell who was looking, and had
no one place with every tool. Verbatim: "i am founder, i am CEO and i am also engineer ... so i
need all the tools one place ... another page in backstage just pure tools".

Rule (CP0): the portal publishes /tools; it is a founder surface in the catalogue (so the crew#401
gate carries it), it sits in the nav, and the login drill grades it like every other published
path. The page reads the catalogue, never a list typed into code. Reads files only."""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "backstage" / "packages" / "app" / "src" / "modules"
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"
DRILL = ROOT / "bin" / "idp-login-drill"


def _code(path: pathlib.Path) -> str:
    return "\n".join(
        l for l in path.read_text().splitlines() if not l.lstrip().startswith("//")
    )


def test_the_tools_page_is_mounted_at_tools_and_in_the_nav():
    assert "path: '/tools'" in _code(APP / "home" / "homeModule.tsx")
    assert "to: '/tools'" in _code(APP / "nav" / "EstateNav.tsx")


def test_the_page_names_no_tool_host_or_group_list_of_its_own():
    src = _code(APP / "home" / "Tools.tsx") + _code(APP / "home" / "toolGroups.ts")
    assert "founder-surface" not in src or "FOUNDER_SURFACE_TYPE" in _code(
        APP / "home" / "useDoors.ts"
    )
    assert not re.search(r"https?://", src), (
        "a URL in the page: the catalogue is the list (LAW 46)"
    )
    assert "estate/group" in src, "tiles are grouped by the catalogue's annotation"


def test_tools_is_a_founder_surface_the_gate_and_the_drill_carry():
    docs = [d for d in yaml.safe_load_all(FOUNDER.read_text()) if d]
    tools = [d for d in docs if d["metadata"]["name"] == "founder-tools"]
    assert len(tools) == 1
    assert any(l["url"].endswith("/tools") for l in tools[0]["metadata"]["links"])
    assert re.search(r'\(\s*"tools"\s*,\s*"text=', DRILL.read_text()), (
        "the login drill grades /tools on its own content"
    )


def test_no_two_source_files_differ_only_in_case():
    """2026-08-30: Tools.tsx beside tools.ts. On the Mac's case-insensitive disk `./tools`
    resolved to the page itself under jest, every import came back undefined, and tsc said
    TS1261. Linux CI would have passed. A name that only case tells apart is refused."""
    src = ROOT / "backstage" / "packages" / "app" / "src"
    seen: dict[str, str] = {}
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        key = str(f.relative_to(src).with_suffix("")).lower()
        if key in seen and seen[key] != f.name:
            raise AssertionError(
                f"{seen[key]} and {f.name} differ only in case (case-insensitive disks merge them)"
            )
        seen[key] = f.name
