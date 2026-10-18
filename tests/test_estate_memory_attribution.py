"""Per-agent attribution on the remember path (claim #6228).

`build_metadata` is what lands in memories.provenance, and provenance is stored verbatim
(Jsonb(payload.provenance) in platform/unified-memory-server/main.py), so the agent name
the plugin stamps here is exactly what /harness/stats groups on. `runtime` names the tool
(claude-code, otto); `agent` names who was driving it -- read from ESTATE_AGENT, the same
identity env bin/claim-open reads, so any agent that can claim work can attribute memory
with no new config.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "estate_memory",
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_memory.py",
)
estate_memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(estate_memory)


def test_agent_stamp_lands_in_provenance(monkeypatch):
    monkeypatch.setenv("ESTATE_AGENT", "estate-agent")
    meta = estate_memory.build_metadata(
        "deploy", "decision", [], "voice", "claude-code"
    )
    assert meta["agent"] == "estate-agent"
    assert meta["runtime"] == "claude-code"  # tool identity survives beside it


def test_no_agent_env_means_no_invented_identity(monkeypatch):
    monkeypatch.delenv("ESTATE_AGENT", raising=False)
    meta = estate_memory.build_metadata("deploy", "decision", [], "voice", "")
    assert "agent" not in meta  # never invented: unattributed stays unattributed
