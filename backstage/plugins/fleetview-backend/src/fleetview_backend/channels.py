"""Fleet channels: one per platform component, read from platform/<component>/channel.yaml.

The manifest is the source (bin/channel-gate refuses a component without one); this module only
serves it. Live activity for a channel is published on its `subject` over the estate bus.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _platform_dir() -> Path:
    env = os.environ.get("FLEETVIEW_PLATFORM_DIR")
    if env:
        return Path(env)
    for p in Path(__file__).resolve().parents:
        if (p / "platform").is_dir() and (p / "bin" / "channel-gate").is_file():
            return p / "platform"
    return Path.home() / "Documents/code/idp/platform"


def list_channels() -> tuple[dict[str, Any], int]:
    channels = []
    for f in sorted(_platform_dir().glob("*/channel.yaml")):
        try:
            d = yaml.safe_load(f.read_text()) or {}
        except yaml.YAMLError:
            continue
        if d.get("id") and d.get("subject"):
            channels.append(d)
    return {"channels": channels, "count": len(channels)}, 200
