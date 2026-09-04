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
    """Every lane the router serves, asked of the router at seed time rather than rendered
    from the config file. The list used to be derived from platform/llm/config.yaml, which
    froze it to the lanes git declares; a lane the founder brings through the router's own
    console lives only in litellm-db (kimi is one, console-owned on purpose -- see
    platform/vendors/consoles.yaml), so it was never on his key and never in his picker. On
    2026-09-04 moonshot/kimi-k3 answered in the console while /v1/models on the laptop key
    named thirteen lanes without it. Two angles: the seed line asks for @router, and the
    script resolves @router by asking the router."""
    _, run, _ = _seed_step()
    line = next(l for l in run.splitlines() if "idp-router-key laptop" in l)
    assert line.split()[-1] == "@router", line
    script = (ROOT / "bin" / "idp-router-key").read_text()
    assert '"$MODELS" = @router' in script, "the script does not resolve @router"
    assert "/v1/models" in script, (
        "@router does not ask the router which lanes it serves"
    )


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


def test_the_hermes_key_is_a_router_key_with_the_capable_lane_first():
    _, run, _ = _seed_step()
    line = next(l for l in run.splitlines() if "idp-router-key hermes" in l)
    lanes = line.split()[-1].split(",")
    cfg = yaml.safe_load((ROOT / "platform" / "llm" / "config.yaml").read_text())
    # `default` is the capable lane, first so hermes gets it before the cheaper ones. It was
    # `claude` until 2026-09-04; a key names lanes, never a vendor (LAW 34).
    assert lanes[0] == "default"
    assert set(lanes) <= {m["model_name"] for m in cfg["model_list"]}


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
