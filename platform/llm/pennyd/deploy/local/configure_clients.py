#!/usr/bin/env python3
"""Point local model clients at pennyd without changing their stored credentials."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
NOW = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup(path: Path) -> None:
    if path.exists():
        shutil.copy2(path, path.with_name(f"{path.name}.bak-pennyd-{NOW}"))


def write_json(path: Path, data) -> None:
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def configure_opencode(path: Path, base_url: str) -> bool:
    if not path.is_file():
        return False
    data = json.loads(path.read_text())
    provider = data.setdefault("provider", {}).setdefault("litellm", {})
    provider.setdefault("options", {})["baseURL"] = f"{base_url}/v1"
    models = provider.setdefault("models", {})
    models["glm"] = {"name": "GLM 5.3 via pennyd"}
    models["reliable-chat"] = {"name": "MiniMax failover via pennyd"}
    data["model"] = "litellm/glm"
    write_json(path, data)
    return True


def configure_pi(path: Path, base_url: str) -> bool:
    if not path.is_file():
        return False
    data = json.loads(path.read_text())
    provider = data.setdefault("providers", {}).setdefault("estate", {})
    provider["baseUrl"] = f"{base_url}/v1"
    models = provider.setdefault("models", [])
    ids = {model.get("id") for model in models}
    if "glm" not in ids:
        models.insert(0, {"id": "glm", "contextWindow": 200000})
    if "reliable-chat" not in ids:
        models.insert(1, {"id": "reliable-chat", "contextWindow": 1000000})
    write_json(path, data)
    return True


def configure_dsh(path: Path, base_url: str) -> bool:
    if not path.is_file():
        return False
    rows = json.loads(path.read_text())
    for row in rows:
        ident = row.get("id")
        config = row.get("config", {})
        if ident == "llm-pi-ai":
            provider = config.setdefault("providers", {}).setdefault("estate", {})
            provider["baseURL"] = f"{base_url}/v1"
            models = provider.setdefault("models", [])
            ids = {model.get("id") for model in models}
            if "glm" not in ids:
                models.insert(0, {"id": "glm", "name": "glm", "contextWindow": 200000})
        elif ident == "agent-default-model":
            config["provider"] = "estate"
            config["model"] = "glm"
    write_json(path, rows)
    return True


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: configure_clients.py BASE_URL")
    base_url = sys.argv[1].rstrip("/")
    targets = [
        configure_opencode(HOME / ".config" / "opencode" / "opencode.jsonc", base_url),
        configure_pi(HOME / ".pi" / "agent" / "models.json", base_url),
        configure_dsh(HOME / ".dsh" / "profiles" / "web" / "cordis.patch.yml", base_url),
    ]
    print(f"configured local clients: {sum(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
