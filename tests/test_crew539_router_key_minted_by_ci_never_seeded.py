"""crew#539 CP7: K8sGPT's router key is minted by CI from the vault's master key, never pasted.

Before: vault-seed.yml expected a repository secret SEED_K8SGPT_KEY that a person would mint in
the LiteLLM console and paste (measured 2026-08-27: `gh secret list` had no such secret, so
entry=k8sgpt could never run). bin/idp-router-key reads litellm-upstream, calls /key/generate,
writes vault entry <consumer> field `key`. Proved both ways here with fakes on PATH and via
IDP_CLOUD / IDP_VAULT_PUT (no socket is opened): a router-accepted key is kept, a refused or
missing one is minted and written, no value reaches stdout.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-router-key"
FAKE_KEY = "sk-fake-" + "minted-0123456789"
MASTER = "sk-fake-" + "master-9876543210"


def _fakes(tmp: Path, *, vault_key: str | None, info_code: str) -> dict:
    """A PATH with a fake curl, plus fake idp-cloud / idp-vault-put that log what they saw."""
    b = tmp / "bin"; b.mkdir()
    log = tmp / "log.txt"; log.write_text("")
    real = {t: subprocess.run(["which", t], capture_output=True, text=True).stdout.strip() for t in ("bash", "jq", "python3", "awk", "head", "mktemp", "date", "rm", "cat", "sh", "dirname", "cut", "sed", "tr")}
    for t, p in real.items():
        (b / t).symlink_to(p)
    cloud = b / "idp-cloud"
    cloud.write_text(
        "#!/bin/bash\n"
        f"echo \"cloud $*\" >> {log}\n"
        "case \"$3\" in\n"
        f"  litellm-upstream) printf '%s' '{{\"LITELLM_MASTER_KEY\":\"{MASTER}\"}}';;\n"
        + (f"  k8sgpt) printf '%s' '{{\"key\":\"{vault_key}\"}}';;\n" if vault_key else "  k8sgpt) exit 1;;\n")
        + "  *) exit 1;;\n"
        "esac\n")
    put = b / "idp-vault-put"
    put.write_text(
        "#!/bin/bash\n"
        f"echo \"put $* env=$(cut -d= -f1 \"$ESTATE_ENV_FILE\")\" >> {log}\n")
    curl = b / "curl"
    curl.write_text(
        "#!/bin/bash\n"
        f"echo \"curl $*\" >> {log}\n"
        "case \"$*\" in\n"
        f"  *key/info*) printf '{info_code}';;\n"
        f"  *key/generate*) printf '%s' '{{\"key\":\"{FAKE_KEY}\",\"key_alias\":\"x\"}}';;\n"
        "  *) exit 22;;\n"
        "esac\n")
    for f in (cloud, put, curl):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {"PATH": str(b), "HOME": str(tmp), "TMPDIR": str(tmp), "IDP_CLOUD": str(cloud), "IDP_VAULT_PUT": str(put), "ROUTER_URL": "https://router.test"}
    return {"env": env, "log": log}


def _run(fk: dict) -> subprocess.CompletedProcess:
    return subprocess.run([str(TOOL), "k8sgpt", "minimax"], capture_output=True, text=True, env=fk["env"], cwd=ROOT)


def test_missing_key_is_minted_from_the_master_key_and_written_to_the_vault(tmp_path: Path) -> None:
    fk = _fakes(tmp_path, vault_key=None, info_code="000")
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    log = fk["log"].read_text()
    assert f"Bearer {MASTER}" in log and "key/generate" in log, log
    assert "put k8sgpt key=ROUTER_KEY env=ROUTER_KEY" in log, log
    assert r.stdout.startswith("ok      router-key   k8sgpt: minted alias k8sgpt-"), r.stdout
    assert "models minimax" in r.stdout and "5 USD/day" in r.stdout
    for secret in (FAKE_KEY, MASTER):
        assert secret not in r.stdout + r.stderr, "a key value reached the terminal"


def test_router_accepted_key_is_kept_and_nothing_is_minted(tmp_path: Path) -> None:
    fk = _fakes(tmp_path, vault_key="sk-fake-" + "existing", info_code="200")
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    log = fk["log"].read_text()
    assert "key/generate" not in log and "put " not in log, log
    assert r.stdout.startswith("ok      router-key   k8sgpt: the vault key (k8sgpt.key) is accepted by https://router.test (kept)"), r.stdout


def test_router_refused_key_is_replaced(tmp_path: Path) -> None:
    fk = _fakes(tmp_path, vault_key="sk-fake-" + "revoked", info_code="401")
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "answered 401" in r.stdout and "minting a new one" in r.stdout, r.stdout
    assert "put k8sgpt key=ROUTER_KEY" in fk["log"].read_text()


def test_vault_seed_mints_k8sgpt_and_carries_no_hand_seeded_secret() -> None:
    wf = (ROOT / ".github" / "workflows" / "vault-seed.yml").read_text()
    assert "bin/idp-router-key k8sgpt minimax" in wf
    assert "SEED_K8SGPT_KEY" not in wf, "a person would have to mint and paste the key again"
    model = yaml.safe_load((ROOT / "platform" / "healing" / "analyzer" / "k8sgpt.yaml").read_text())["spec"]["ai"]["model"]
    assert model == "minimax", "the key is minted for a model the K8sGPT CR does not call"


def test_budget_is_a_config_row_not_a_literal_in_the_script() -> None:
    d = yaml.safe_load((ROOT / "estate-defaults.yaml").read_text())
    assert isinstance(d["llm"]["virtual_key_daily_usd"], (int, float))
    src = TOOL.read_text()
    assert "virtual_key_daily_usd" in src
    assert not re.search(r"max_budget:\s*\d", src), "budget typed in the script (LAW 46)"
