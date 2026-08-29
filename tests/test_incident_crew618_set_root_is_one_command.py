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


def test_all_walks_every_provider_once_and_skips_the_ones_already_set(tmp_path):
    """`bin/idp-set-root all`: one command for every root. gh is a shim: `secret list` says tailscale
    is set, so it is skipped; every other provider's road runs with no dispatch until the end."""
    gh = tmp_path / "gh"
    gh.write_text("#!/bin/sh\ncase \"$1 $2\" in\n  'auth status') exit 0;;\n  'secret list') printf 'SEED_TAILSCALE_CLIENT_ID\\nSEED_TAILSCALE_CLIENT_SECRET\\n';;\n"
                  "  'secret set') cat >/dev/null; echo \"set $3\" >> " + str(tmp_path / "set.log") + ";;\n  'workflow run') echo run >> " + str(tmp_path / "run.log") + ";;\nesac\n")
    gh.chmod(0o755)
    (tmp_path / "open").write_text("#!/bin/sh\nexit 0\n"); (tmp_path / "open").chmod(0o755)
    values = "\n".join(["x"] * 20) + "\n"
    r = subprocess.run([str(ROOT / "bin/idp-set-root"), "all"], input=values, capture_output=True, text=True,
                       env={"PATH": f"{tmp_path}:/usr/bin:/bin", "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "tailscale already set; skipped" in r.stdout
    names = [l.split()[1] for l in (tmp_path / "set.log").read_text().splitlines()]
    assert names == ["SEED_CLOUDFLARE_ROOT_TOKEN", "SEED_ANTHROPIC_API_KEY", "SEED_OPENROUTER_API_KEY", "SEED_DEEPSEEK_API_KEY",
                     "SEED_MINIMAX_API_KEY", "SEED_GROQ_API_KEY", "SEED_GEMINI_API_KEY", "SEED_EXA_API_KEY", "SEED_STRIPE_SECRET_KEY",
                     "SEED_TELEGRAM_HERMES_BOT_TOKEN", "SEED_TELEGRAM_ALERTS_BOT_TOKEN"], names
    assert (tmp_path / "run.log").read_text().count("run") == 1, "one apply run at the end, not one per provider"
    assert "x" not in "".join(l for l in r.stdout.splitlines() if "SEED_" in l and "set on" in l)
