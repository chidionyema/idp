"""R53 (founder 2026-08-29): "should come with working instructions or fully automated, either way
zero friction." bin/idp-set-root <provider> is the founder's whole part: page, steps, hidden input,
gh secret set, apply dispatch, in one command. Every root on the life-cycle page that the founder
sets is a provider it knows; no value is ever echoed."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "bin/idp-set-root").read_text()


def test_every_founder_set_root_has_a_provider_road():
    for name in ("SEED_TAILSCALE_CLIENT_ID", "SEED_TAILSCALE_CLIENT_SECRET", "SEED_CLOUDFLARE_ROOT_TOKEN",
                 "SEED_TELEGRAM_HERMES_BOT_TOKEN", "SEED_TELEGRAM_ALERTS_BOT_TOKEN"):
        assert name in SCRIPT, name
    for vendor in ("anthropic", "openrouter", "deepseek", "minimax", "groq", "gemini", "exa", "stripe"):
        assert re.search(rf"\b{vendor}\b", SCRIPT), vendor


def test_the_value_is_read_hidden_and_never_echoed_and_apply_is_dispatched():
    assert "read -rs v" in SCRIPT and 'gh secret set "$name"' in SCRIPT
    assert "echo \"$v\"" not in SCRIPT and "printf '%s\\n' \"$v\"" not in SCRIPT
    assert "gh workflow run oke-check.yml" in SCRIPT and "mode=apply" in SCRIPT
    assert subprocess.run(["bash", "-n", str(ROOT / "bin/idp-set-root")]).returncode == 0


def test_an_unknown_provider_is_refused_before_anything_opens(tmp_path):
    gh = tmp_path / "gh"; gh.write_text("#!/bin/sh\nexit 0\n"); gh.chmod(0o755)
    r = subprocess.run([str(ROOT / "bin/idp-set-root"), "nope"], capture_output=True, text=True, env={"PATH": f"{tmp_path}:/usr/bin:/bin"})
    assert r.returncode == 2 and "unknown provider" in r.stdout
