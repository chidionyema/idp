"""Negative provider-routing tests; no Anthropic account or network needed."""

import importlib.util
import json
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "claude_direct", ROOT / "bin" / "claude-anthropic"
)
# SourceFileLoader works for extension-less executable.
from importlib.machinery import SourceFileLoader

loader = SourceFileLoader("claude_direct", str(ROOT / "bin" / "claude-anthropic"))
spec = importlib.util.spec_from_loader("claude_direct", loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


def test_zai_gateway_is_not_forwarded_to_anthropic():
    polluted = {
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        "ANTHROPIC_AUTH_TOKEN": "SECRET",
        "ANTHROPIC_API_KEY": "ZAI_CODING_PLAN_SECRET",
        "ANTHROPIC_MODEL": "glm-5",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5",
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "PATH": "/usr/bin",
    }
    clean = module.direct_env(polluted)
    assert clean["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
    assert set(clean) == {"PATH", "ANTHROPIC_BASE_URL"}
    assert "SECRET" not in repr(clean)


def test_provider_override_is_strict_and_uses_real_claude_alias():
    cfg = json.loads(module.settings_override())
    assert cfg["model"] == "sonnet"
    assert cfg["env"]["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
    assert "glm" not in module.settings_override().lower()
    for args in (
        ["--model", "glm-5"],
        ["--settings", "{}"],
        ["--model=glm-5"],
        ["--api-key", "x"],
    ):
        with pytest.raises(ValueError, match="PROVIDER_OVERRIDE_REFUSED"):
            module.validate_args(args)


def test_default_invocation_replaces_claude_process_with_direct_provider_only():
    with (
        mock.patch.object(
            module, "effective_binary", return_value="/usr/local/bin/claude"
        ),
        mock.patch.dict(
            module.os.environ,
            {
                "ANTHROPIC_BASE_URL": "https://api.z.ai",
                "ANTHROPIC_API_KEY": "leak",
                "ANTHROPIC_MODEL": "glm-5",
            },
        ),
        mock.patch.object(module.os, "execvpe") as execve,
    ):
        module.main(["--verbose"])
    binary, args, env = execve.call_args.args
    assert binary == "/usr/local/bin/claude"
    assert args[:2] == [binary, "--settings"]
    assert args[3:5] == ["--model", "sonnet"]
    assert args[-1] == "--verbose"
    assert env["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
    assert "ANTHROPIC_API_KEY" not in env


def test_live_probe_does_not_certify_unproven_or_glm_model():
    with mock.patch.object(module.subprocess, "run") as run:
        run.return_value.returncode = 0
        for models in ({}, {"glm-5": {}}, {"claude-sonnet-4": {}, "glm-5": {}}):
            run.return_value.stdout = json.dumps({"modelUsage": models})
            assert module.live_probe("claude", module.direct_env({})) == 2
        run.return_value.stdout = json.dumps(
            {"modelUsage": {"claude-sonnet-5-5-20261101": {}}}
        )
        assert module.live_probe("claude", module.direct_env({})) == 0
