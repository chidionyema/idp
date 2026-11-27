"""AGENTS.md is a kernel plus a route table, and every routed law is reachable (idp#8636).

Every harness (Claude Code, Codex, pi, Cline, Gemini) loads AGENTS.md before its first action,
so it carries only the laws that bind every task. Everything else lives verbatim under
docs/agents/ and is reached through the route table. These checks fail when a route dangles,
when a law file is orphaned (on disk but routed from nowhere, so no agent ever opens it), when
the substrate authority stops being line 1, or when the Turn-1 files grow past the cap.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTE = re.compile(r"^\| .+ \| `(docs/agents/[^`]+\.md)` \|$", re.MULTILINE)


def _routes() -> list:
    return ROUTE.findall((ROOT / "AGENTS.md").read_text(encoding="utf-8"))


def test_the_substrate_authority_is_line_one():
    first = (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()[0]
    assert first == "<!-- ESTATE_SUBSTRATE_AUTHORITY_START -->", first


def test_every_route_resolves_and_every_law_file_is_routed():
    routes = _routes()
    assert routes, "AGENTS.md has no route table: the moved law is unreachable"
    assert len(routes) == len(set(routes)), "a law file is routed twice"
    dangling = [r for r in routes if not (ROOT / r).is_file()]
    assert not dangling, f"routes to files that do not exist: {dangling}"
    on_disk = {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "docs" / "agents").glob("*.md")
    }
    orphans = sorted(on_disk - set(routes))
    assert not orphans, f"law files no agent is routed to: {orphans}"


def test_every_routed_file_is_current_law_not_history():
    for rel in _routes():
        first = (ROOT / rel).read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("<!-- estate:routed-from AGENTS.md"), (rel, first)
        assert "estate:historical" not in first, rel


def test_claude_md_imports_the_kernel():
    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()[
        0
    ] == "@AGENTS.md"


def test_the_turn1_files_fit_the_cap_on_the_gate_s_own_measure():
    cap = json.loads((ROOT / "policy" / "context-policy.v1.json").read_text())[
        "global_invariants"
    ]["max_auto_injected_rules_tokens"]
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "estate_context_fleet_sync.py"),
            "--optimus",
            "--repo-root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    got = int(
        re.fullmatch(r"optimus\.context\.turn1_rule_tokens=(\d+)\n", rc.stdout).group(1)
    )
    assert 0 < got <= cap, f"Turn-1 rule files read {got} tokens, cap {cap}"
