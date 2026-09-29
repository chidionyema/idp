"""AGENTS.md is the one instructions file; a root CLAUDE.md is a split brain.

Founder, 2026-09-29: "AGENTS.md, get rid of CLAUDE.md", "we don't want any split brain mess here".
Claude Code loads AGENTS.md as project instructions where the project has no CLAUDE.md, so every
agent reads the same file. `growmos integrate claude` (or `all`) would recreate CLAUDE.md with its
block; use `growmos integrate file --file AGENTS.md` instead.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_there_is_no_root_claude_md():
    assert not (ROOT / "CLAUDE.md").exists(), (
        "AGENTS.md is the one instructions file: move any content there and delete CLAUDE.md"
    )


def test_agents_md_carries_the_growmos_block_and_the_all_ways_rule():
    text = (ROOT / "AGENTS.md").read_text()
    assert (
        text.count("<!-- growmos:start") == 1
        and text.count("<!-- growmos:end -->") == 1
    )
    assert "## 12. All ways: no single point of failure" in text
