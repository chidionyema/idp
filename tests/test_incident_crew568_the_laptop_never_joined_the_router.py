"""crew#568: the sessions that built the model router never joined it.

Measured 2026-08-29: ~/.pi/models.json pointed at three vendor hosts with keys on the laptop,
~/.config/llm/secrets.sh and ~/.config/wave/secrets.sh held seven more, consultd ran its own
cascade. The router had one wired consumer (k8sgpt). This test holds the path that replaces all
of it: vault-seed mints ONE virtual key for the laptop and delivers it through estate-secrets
(sops, encrypted to the repo's age recipient), and bin/litellm-status fails on any vendor key
left on the Mac.
"""
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "vault-seed.yml"
LANES = ROOT / "platform" / "github-app" / "lanes.json"
STATUS = ROOT / "bin" / "litellm-status"


def _seed_step():
    doc = yaml.safe_load(WF.read_text())
    steps = doc["jobs"]["seed"]["steps"]
    return doc, "\n".join(s.get("run", "") for s in steps), steps


def test_laptop_is_a_seedable_entry_and_all_covers_it():
    doc, run, _ = _seed_step()
    assert "laptop" in doc[True]["workflow_dispatch"]["inputs"]["entry"]["options"]
    assert '[ "$ENTRY" = all ] || [ "$ENTRY" = laptop ]' in run


def test_the_laptop_key_is_a_router_key_for_every_lane():
    _, run, _ = _seed_step()
    line = next(l for l in run.splitlines() if "idp-router-key laptop" in l)
    lanes = set(line.split()[-1].split(","))
    cfg = yaml.safe_load((ROOT / "platform" / "llm" / "config.yaml").read_text())
    assert lanes == {m["model_name"] for m in cfg["model_list"]}


def test_delivery_is_sops_to_estate_secrets_and_the_runner_decrypts_nothing():
    _, run, steps = _seed_step()
    assert any("nhedger/setup-sops@" in s.get("uses", "") for s in steps), "sops is not on the runner"
    assert 'secret-add" dev LITELLM_LAPTOP_KEY LITELLM_API_KEY' in run
    assert "idp-github-app token vault-writer" in run
    assert "SOPS_AGE_KEY" not in run, "the runner must never hold the age identity"
    lanes = json.loads(LANES.read_text())
    assert lanes["vault-writer"] == {"metadata": "read", "contents": "write"}


def test_the_value_never_lands_on_disk_or_in_the_log():
    _, run, _ = _seed_step()
    line = next(l for l in run.splitlines() if "secret get laptop" in l)
    assert "| jq -r .key |" in line and ">" not in line.split("secret-add")[0]


def test_litellm_status_fails_on_a_vendor_key_left_on_the_mac(tmp_path):
    home = tmp_path
    (home / ".pi").mkdir()
    (home / ".pi" / "models.json").write_text(json.dumps({"providers": {"minimax": {"baseUrl": "https://api.minimax.io/v1"}}}))
    out = subprocess.run(["bash", str(STATUS)], capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})
    assert "FAIL" in out.stdout and "minimax" in out.stdout and out.returncode == 1
    (home / ".pi" / "models.json").write_text(json.dumps({"providers": {"estate": {"baseUrl": "https://llm.example/v1"}}}))
    out = subprocess.run(["bash", str(STATUS)], capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})
    assert "ok     none" in out.stdout
