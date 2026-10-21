"""The estate-mcp image's build-time search check names an intent that exists.

estate-mcp.Dockerfile asserts that searching the library for "ci status" finds a named intent.
#6590 renamed that intent from ci-status to ci.status and left the assertion on the old name, so
from 2026-10-19 16:47Z every estate-mcp image build failed at that RUN line and none shipped for
~40 hours; CI showed it only as a red build-multiarch job. This runs the same search against the
library in the repo, so a rename that breaks the build fails here first.
"""

import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "estate-mcp.Dockerfile"


def _checked_intent() -> str:
    m = re.search(r"assert '## intent ([^']+)' in hit", DOCKERFILE.read_text())
    assert m, "the build-time search check is gone from estate-mcp.Dockerfile"
    return m.group(1)


def test_the_intent_the_build_checks_for_exists():
    name = _checked_intent()
    assert (ROOT / "platform" / "estate" / "intents" / f"{name}.yaml").is_file(), name


def test_the_build_check_passes_against_the_library(monkeypatch):
    monkeypatch.setenv(
        "ESTATE_INTENTS_DIR", str(ROOT / "platform" / "estate" / "intents")
    )
    spec = importlib.util.spec_from_file_location(
        "estate_mcp_build_check", ROOT / "mcp" / "plugins" / "estate_mcp.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert len(m._load_intents()) >= 50
    assert f"## intent {_checked_intent()}" in m._estate_list({"query": "ci status"})
