"""The presence state file: what the menu bar dot reads (R2/R3).

The kernel writes `presence.state_file` after every transition. The
SwiftBar plugin (swiftbar/estate-presence.5s.sh) reads it and prints a
coloured dot. SwiftBar runs the script on its own schedule, so there is
no daemon here and no polling loop.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from sovereign.presence import config_keys
from sovereign.presence.fsm import Converse, Presence, Spatial, is_ghost_equivalent, name


def dot_colour(state: Presence) -> str:
    if is_ghost_equivalent(state):
        return str(config_keys.resolve("presence.dot_ghost"))
    if isinstance(state, Spatial):
        key = "presence.dot_catastrophe" if state.cause == "catastrophe" else "presence.dot_spatial"
        return str(config_keys.resolve(key))
    if isinstance(state, Converse):
        return str(config_keys.resolve("presence.dot_converse"))
    raise TypeError(f"not a presence state: {state!r}")


def state_path() -> Path:
    return Path(str(config_keys.resolve("presence.state_file")))


def as_dict(state: Presence) -> dict[str, Any]:
    detail: dict[str, Any] = {}
    if isinstance(state, Spatial):
        detail["cause"] = state.cause
    if isinstance(state, Converse):
        detail["initiated_by"] = {"kind": state.initiated_by.kind, "by": state.initiated_by.by}
    pattern = getattr(state, "pattern", None)
    if pattern is not None:
        detail["pattern"] = pattern.value
    return {"state": name(state), "dot": dot_colour(state), "ts": time.time(), **detail}


def write(state: Presence) -> Path:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(as_dict(state), sort_keys=True) + "\n")
    tmp.replace(path)
    return path


def read() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {"state": "ghost", "dot": str(config_keys.resolve("presence.dot_ghost")), "ts": None}
    return json.loads(path.read_text())


class FilePresence:
    """The live presence state as sovereign.intake's PresenceGate reads it:
    `current()` is the state name from the file the kernel writes."""

    def current(self) -> str:
        return str(read()["state"])
