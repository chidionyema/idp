"""Claude Code and Claude Desktop switch together between native Claude and Pennyd GLM."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "claude-surface"


def _run(home: Path, mode: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "CLAUDE_CONFIG_DIR": str(home / ".estate" / "harness" / "cc"),
        "CLAUDE_SURFACE_NO_RESTART": "1",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    }
    return subprocess.run(
        [str(SCRIPT), mode],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_both_surfaces_switch_atomically_and_keep_unrelated_settings(tmp_path):
    cc = tmp_path / ".estate" / "harness" / "cc" / "settings.json"
    cc.parent.mkdir(parents=True)
    cc.write_text(
        json.dumps(
            {
                "model": "sonnet",
                "theme": "dark",
                "env": {
                    "KEEP_ME": "yes",
                    "ANTHROPIC_BASE_URL": "https://old.example",
                },
            }
        )
    )
    desktop = (
        tmp_path
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json"
    )
    desktop.parent.mkdir(parents=True)
    desktop.write_text(json.dumps({"userThemeMode": "dark"}))

    glm = _run(tmp_path, "glm")
    assert glm.returncode == 0, glm.stdout + glm.stderr
    cc_data = json.loads(cc.read_text())
    assert cc_data["model"] == "glm"
    assert cc_data["theme"] == "dark"
    assert cc_data["env"]["KEEP_ME"] == "yes"
    assert cc_data["env"]["ANTHROPIC_BASE_URL"].endswith(":4200")
    assert cc_data["env"]["ANTHROPIC_CUSTOM_HEADERS"] == "x-estate-surface: claude-code"
    assert cc_data["apiKeyHelper"].endswith("/.estate/bin/pennyd-client-key")
    desktop_data = json.loads(desktop.read_text())
    assert desktop_data["userThemeMode"] == "dark"
    assert desktop_data["deploymentMode"] == "3p"
    library = (
        tmp_path
        / "Library"
        / "Application Support"
        / "Claude-3p"
        / "configLibrary"
    )
    meta = json.loads((library / "_meta.json").read_text())
    assert meta["appliedId"] in {entry["id"] for entry in meta["entries"]}
    active = json.loads((library / f"{meta['appliedId']}.json").read_text())
    assert active["inferenceProvider"] == "gateway"
    assert active["inferenceCredentialKind"] == "helper-script"
    assert active["inferenceGatewayBaseUrl"].endswith(":4200")
    assert len(active["inferenceModels"]) == 12
    assert active["inferenceModels"][0]["name"] == "claude-sonnet-primary"
    assert active["inferenceModels"][0]["labelOverride"] == "GLM 5.3"
    assert active["inferenceModels"][0]["behavesAs"] == "claude-sonnet-5"

    # Claude Desktop 4.23118.1 removes gateway IDs containing a known
    # non-Anthropic provider name (including GLM, DeepSeek, Gemini and Qwen).
    # The visible label carries that information instead.
    provider_words = re.compile(
        r"ark-code|astron|command-r|deepseek|doubao|gemini|gemma|glm|gpt|grok|"
        r"hermes|kimi|llama|minimax|mistral|mixtral|moonshot|nemotron|openai|"
        r"qwen|qianfan",
        re.IGNORECASE,
    )
    names = [model["name"] for model in active["inferenceModels"]]
    assert len(names) == len(set(names))
    assert all(name.startswith("claude-") for name in names)
    assert not any(provider_words.search(name) for name in names)
    assert {model["labelOverride"] for model in active["inferenceModels"]} >= {
        "GLM 5.3",
        "DeepSeek V4 Pro",
        "Gemini 3.5 Flash",
        "MiniMax M3",
    }

    claude = _run(tmp_path, "claude")
    assert claude.returncode == 0, claude.stdout + claude.stderr
    cc_data = json.loads(cc.read_text())
    assert cc_data["model"] == "sonnet"
    assert "ANTHROPIC_BASE_URL" not in cc_data["env"]
    assert "apiKeyHelper" not in cc_data
    assert cc_data["env"]["KEEP_ME"] == "yes"
    desktop_data = json.loads(desktop.read_text())
    assert desktop_data == {"userThemeMode": "dark"}
    assert (tmp_path / ".estate" / "claude-surfaces" / "cc-original.json").is_file()
    assert (
        tmp_path / ".estate" / "claude-surfaces" / "desktop-original.json"
    ).is_file()
