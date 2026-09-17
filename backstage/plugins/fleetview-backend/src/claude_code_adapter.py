"""FleetView CP6: Claude Code ledger tail — bridges the prompt-ledger to the NATS event bus.

Tails all *.jsonl files under the prompt-ledger directory for new lines (poll every 2s).
Each new ledger row is mapped to the estate.agent.event contract and published via
nats_adapter.publish().

Row-to-kind mapping:
  source == "tool" or tool_name present  →  kind="tool",  phase="executing"
  source == "user"                        →  kind="phase", phase="planning"
  source == "assistant"                   →  kind="phase", phase="executing"

CONFIG (LAW 46):
  ESTATE_STATE_PATH_PREFIX  ledger directory (default ~/.claude/state/prompt-ledger/)
  NATS_URL                  NATS server (default nats://nats.event-bus.svc:4222)

A missing or unreadable ledger dir is the empty operation — no crash.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_PREFIX = "~/.claude/state/prompt-ledger/"
_POLL_INTERVAL_S = 2.0


def _ledger_dir(prefix: str | None) -> Path:
    raw = prefix or os.environ.get("ESTATE_STATE_PATH_PREFIX", _DEFAULT_PREFIX)
    return Path(os.path.expanduser(raw))


def _map_row(row: dict[str, Any]) -> tuple[str, str] | None:
    """Return (kind, phase) for a ledger row, or None to skip it."""
    source = row.get("source", "")
    tool_name = row.get("tool_name")
    if source == "tool" or tool_name:
        return "tool", "executing"
    if source == "user":
        return "phase", "planning"
    if source == "assistant":
        return "phase", "executing"
    return None


async def run_claude_code_adapter(nats_url: str, prefix: str | None = None) -> None:
    """Poll every *.jsonl file in the ledger directory for new rows and publish each
    to NATS. Runs forever; call via asyncio.create_task().

    A missing ledger dir is treated as the empty set — the adapter waits, does not crash.
    """
    directory = _ledger_dir(prefix)
    # byte_offsets tracks how far into each file we have already read, keyed by absolute path
    byte_offsets: dict[str, int] = {}

    # Load nats_adapter by path (same pattern as routes.py's _load helpers), not a relative
    # import — these modules are loaded by importlib path, not as a package, so relative
    # imports are unavailable.
    import importlib.util as _ilu

    _nats_module_path = Path(__file__).resolve().parent / "nats_adapter.py"
    _spec = _ilu.spec_from_file_location(
        "fleetview_nats_adapter_cc_impl", _nats_module_path
    )
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"cannot load nats_adapter at {_nats_module_path}")
    nats_adapter = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(nats_adapter)

    while True:
        if directory.is_dir():
            for path in sorted(directory.glob("*.jsonl")):
                key = str(path)
                offset = byte_offsets.get(key, 0)
                try:
                    with path.open("rb") as fh:
                        fh.seek(offset)
                        chunk = fh.read()
                    if not chunk:
                        continue
                    byte_offsets[key] = offset + len(chunk)
                    text = chunk.decode("utf-8", errors="replace")
                    for raw_line in text.splitlines():
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue
                        try:
                            row = json.loads(raw_line)
                        except ValueError:
                            continue
                        if not isinstance(row, dict):
                            continue
                        session_id = row.get("session")
                        if not isinstance(session_id, str) or not session_id:
                            continue
                        mapping = _map_row(row)
                        if mapping is None:
                            continue
                        kind, phase = mapping
                        extra: dict[str, Any] = {}
                        tool_name = row.get("tool_name")
                        if tool_name:
                            text_val = row.get("text") or ""
                            extra["tool"] = {
                                "name": tool_name,
                                "target": text_val[:500],
                            }
                        try:
                            await nats_adapter.publish(
                                nats_url=nats_url,
                                session_id=session_id,
                                runtime="claude-code",
                                kind=kind,
                                phase=phase,
                                **extra,
                            )
                        except Exception:  # noqa: BLE001, S110 — one bad publish must not stop the tail
                            pass
                except OSError:
                    continue
        await asyncio.sleep(_POLL_INTERVAL_S)
