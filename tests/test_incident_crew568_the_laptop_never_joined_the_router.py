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
    """The lane list is derived from the rendered router config at seed time, never typed
    by hand: the line must name the config, and running its own derivation must emit
    exactly the lanes the cluster serves (two angles on the same claim)."""
    _, run, _ = _seed_step()
    line = next(l for l in run.splitlines() if "idp-router-key laptop" in l)
    assert "platform/llm/config.yaml" in line and "model_list" in line
    snippet = line.split("python3 -c '", 1)[1].rsplit("'", 1)[0]
    out = subprocess.run(
        ["python3", "-c", snippet], capture_output=True, text=True, cwd=ROOT, check=True
    )
    lanes = set(out.stdout.strip().split(","))
    cfg = yaml.safe_load((ROOT / "platform" / "llm" / "config.yaml").read_text())
    assert lanes == {m["model_name"] for m in cfg["model_list"]}


def test_delivery_is_sops_to_estate_secrets_and_the_runner_decrypts_nothing():
    _, run, steps = _seed_step()
    assert any("nhedger/setup-sops@" in s.get("uses", "") for s in steps), (
        "sops is not on the runner"
    )
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
    (home / ".pi" / "models.json").write_text(
        json.dumps({"providers": {"minimax": {"baseUrl": "https://api.minimax.io/v1"}}})
    )
    out = subprocess.run(
        ["bash", str(STATUS)],
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        },
    )
    assert "FAIL" in out.stdout and "minimax" in out.stdout and out.returncode == 1
    (home / ".pi" / "models.json").write_text(
        json.dumps({"providers": {"estate": {"baseUrl": "https://llm.example/v1"}}})
    )
    out = subprocess.run(
        ["bash", str(STATUS)],
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        },
    )
    assert "ok     none" in out.stdout


# crew#568 Phase 5: the first product joins the same road. Hermes (hermes-v2/config.yaml) ran its
# primary model on a vendor key; it now calls the router on its own virtual key, minted and
# delivered exactly the way the laptop's is, so a buyer's engineer reads one road, not two.
def test_hermes_is_a_seedable_entry_and_all_covers_it():
    doc, run, _ = _seed_step()
    assert "hermes" in doc[True]["workflow_dispatch"]["inputs"]["entry"]["options"]
    assert '[ "$ENTRY" = all ] || [ "$ENTRY" = hermes ]' in run


def test_the_hermes_key_is_a_router_key_with_claude_first():
    _, run, _ = _seed_step()
    line = next(l for l in run.splitlines() if "idp-router-key hermes" in l)
    lanes = line.split()[-1].split(",")
    cfg = yaml.safe_load((ROOT / "platform" / "llm" / "config.yaml").read_text())
    assert lanes[0] == "claude"
    assert set(lanes) <= {m["model_name"] for m in cfg["model_list"]}


def test_hermes_delivery_is_the_laptop_road():
    _, run, _ = _seed_step()
    assert 'secret-add" dev LITELLM_HERMES_KEY LITELLM_API_KEY' in run
    line = next(l for l in run.splitlines() if "secret get hermes" in l)
    assert "| jq -r .key |" in line and ">" not in line.split("secret-add")[0]


def test_a_new_key_file_is_added_by_name_before_the_commit():
    """Run 33257838162: `commit -am` skipped the untracked LITELLM_LAPTOP_KEY.yaml and printed
    "unchanged"; the key was minted and never delivered. Silent green is the defect class."""
    _, run, _ = _seed_step()
    for name in ("LAPTOP", "HERMES"):
        assert f"add secrets/dev/LITELLM_{name}_KEY.yaml" in run
    assert "commit -q -am" not in run


def test_a_refused_push_is_an_error_and_the_hook_can_see_the_token():
    """Run 33258762617: estate-secrets' pre-push hook refused (gh had no token) and the workflow said
    'unchanged' and exited 0. The push carries GH_TOKEN for the hook, and its failure is exit 1."""
    text = WF.read_text()
    for human in ("laptop", "hermes"):
        block = text.split(f'commit -q -m "{human} router key', 1)[1].split(
            "rm -rf", 1
        )[0]
        assert 'GH_TOKEN="$tok" git -C "$RUNNER_TEMP/estate-secrets" push' in block, (
            human
        )
        assert "exit 1" in block, human
        assert "push -q origin HEAD ||" not in block.replace("|| { echo", ""), human
