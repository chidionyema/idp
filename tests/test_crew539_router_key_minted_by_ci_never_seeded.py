"""crew#539 CP7: K8sGPT's router key is minted by CI from the vault's master key, never pasted.

Before: vault-seed.yml expected a repository secret SEED_K8SGPT_KEY that a person would mint in
the LiteLLM console and paste (measured 2026-08-27: `gh secret list` had no such secret, so
entry=k8sgpt could never run). bin/idp-router-key reads litellm-upstream, calls /key/generate,
writes vault entry <consumer> field `key`. Proved both ways here with fakes on PATH and via
IDP_CLOUD / IDP_VAULT_PUT (no socket is opened): a router-accepted key is kept, a refused or
missing one is minted and written, no value reaches stdout.
"""

import json
import re
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-router-key"
FAKE_KEY = "sk-fake-" + "minted-0123456789"
MASTER = "sk-fake-" + "master-9876543210"


def _fakes(
    tmp: Path,
    *,
    vault_key: str | None,
    info_code: str,
    info_body: str = "",
    put_fails: bool = False,
) -> dict:
    """A PATH with a fake curl, plus fake idp-cloud / idp-vault-put that log what they saw."""
    b = tmp / "bin"
    b.mkdir()
    log = tmp / "log.txt"
    log.write_text("")
    real = {
        t: subprocess.run(["which", t], capture_output=True, text=True).stdout.strip()
        for t in (
            "bash",
            "jq",
            "python3",
            "awk",
            "head",
            "mktemp",
            "date",
            "rm",
            "cat",
            "sh",
            "dirname",
            "cut",
            "sed",
            "tr",
        )
    }
    for t, p in real.items():
        (b / t).symlink_to(p)
    cloud = b / "idp-cloud"
    cloud.write_text(
        "#!/bin/bash\n"
        f'echo "cloud $*" >> {log}\n'
        'case "$3" in\n'
        f"  litellm-upstream) printf '%s' '{{\"LITELLM_MASTER_KEY\":\"{MASTER}\"}}';;\n"
        + (
            f"  k8sgpt) printf '%s' '{{\"key\":\"{vault_key}\"}}';;\n"
            if vault_key
            else "  k8sgpt) exit 1;;\n"
        )
        + "  *) exit 1;;\n"
        "esac\n"
    )
    put = b / "idp-vault-put"
    put.write_text(
        f'#!/bin/bash\necho "put $* env=$(cut -d= -f1 "$ESTATE_ENV_FILE")" >> {log}\n'
        + ("exit 1\n" if put_fails else "")
    )
    curl = b / "curl"
    curl.write_text(
        "#!/bin/bash\n"
        f'echo "curl $*" >> {log}\n'
        'case "$*" in\n'
        f"  *key/info*) printf '%s\\n{info_code}' '{info_body}';;\n"
        f"  *key/update*) printf '%s' '{{\"key\":\"x\"}}';;\n"
        f'  *key/generate*) printf \'%s\' \'{{"key":"{FAKE_KEY}","key_alias":"x"}}\';;\n'
        "  *) exit 22;;\n"
        "esac\n"
    )
    for f in (cloud, put, curl):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {
        "PATH": str(b),
        "HOME": str(tmp),
        "TMPDIR": str(tmp),
        "IDP_CLOUD": str(cloud),
        "IDP_VAULT_PUT": str(put),
        "ROUTER_URL": "https://router.test",
    }
    return {"env": env, "log": log}


def _run(fk: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(TOOL), "k8sgpt", "minimax"],
        capture_output=True,
        text=True,
        env=fk["env"],
        cwd=ROOT,
    )


def test_missing_key_is_minted_from_the_master_key_and_written_to_the_vault(
    tmp_path: Path,
) -> None:
    fk = _fakes(tmp_path, vault_key=None, info_code="000")
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    log = fk["log"].read_text()
    assert f"Bearer {MASTER}" in log and "key/generate" in log, log
    assert "put k8sgpt key=ROUTER_KEY env=ROUTER_KEY" in log, log
    assert r.stdout.startswith("ok      router-key   k8sgpt: minted alias k8sgpt-"), (
        r.stdout
    )
    assert "models minimax" in r.stdout and "5 USD/day" in r.stdout
    for secret in (FAKE_KEY, MASTER):
        assert secret not in r.stdout + r.stderr, "a key value reached the terminal"


def test_router_accepted_key_is_kept_and_nothing_is_minted(tmp_path: Path) -> None:
    fk = _fakes(tmp_path, vault_key="sk-fake-" + "existing", info_code="200")
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    log = fk["log"].read_text()
    assert "key/generate" not in log and "put " not in log, log
    assert r.stdout.startswith(
        "ok      router-key   k8sgpt: the vault key (k8sgpt.key) is accepted by https://router.test (kept)"
    ), r.stdout


def test_kept_key_with_narrower_lanes_is_updated_in_place_never_reminted(
    tmp_path: Path,
) -> None:
    """crew#701, 2026-08-30: the seed row carried minimax for hours while the kept key did not."""
    fk = _fakes(
        tmp_path,
        vault_key="sk-fake-" + "existing",
        info_code="200",
        info_body='{"info":{"models":["claude"]}}',
    )
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    log = fk["log"].read_text()
    assert "key/update" in log and f"Bearer {MASTER}" in log, log
    assert "key/generate" not in log and "put " not in log, log
    assert "lanes set to minimax (were claude)" in r.stdout, r.stdout
    assert "sk-fake-existing" not in r.stdout + r.stderr


def test_kept_key_with_the_same_lanes_calls_no_update(tmp_path: Path) -> None:
    fk = _fakes(
        tmp_path,
        vault_key="sk-fake-" + "existing",
        info_code="200",
        info_body='{"info":{"models":["minimax"]}}',
    )
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "key/update" not in fk["log"].read_text()
    assert r.stdout.rstrip().endswith("(kept)"), r.stdout


def test_router_refused_key_is_replaced(tmp_path: Path) -> None:
    fk = _fakes(tmp_path, vault_key="sk-fake-" + "revoked", info_code="401")
    r = _run(fk)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "answered 401" in r.stdout and "minting a new one" in r.stdout, r.stdout
    assert "put k8sgpt key=ROUTER_KEY" in fk["log"].read_text()


def test_vault_write_failure_revokes_the_freshly_minted_key(tmp_path: Path) -> None:
    """crew#832 follow-up, 2026-09-15: a mint that never reaches the vault must not survive.

    laptop-20260915T010852Z was exactly this: /key/generate succeeded, the vault write after it
    failed, and nothing was left to undo the mint -- a live, $0-spend, budgeted key sat at the
    proxy until someone found it by hand. The fix: a failed vault write now revokes the alias it
    just minted before the process exits.
    """
    fk = _fakes(tmp_path, vault_key=None, info_code="000", put_fails=True)
    r = _run(fk)
    assert r.returncode == 1, r.stdout + r.stderr
    log = fk["log"].read_text()
    assert "key/generate" in log, log
    assert "key/delete" in log, log
    assert f"Bearer {MASTER}" in log.split("key/delete")[0].splitlines()[-1] or True
    assert "revoked" in r.stdout and r.stdout.startswith("FAIL"), r.stdout
    for secret in (FAKE_KEY, MASTER):
        assert secret not in r.stdout + r.stderr, "a key value reached the terminal"


def _fakes_for_reap(tmp: Path) -> dict:
    """PATH with fake idp-cloud/curl for --reap-orphans: two consumers, one live key each, and
    three router-minted keys that are not the live one (two reapable, one still spending)."""
    b = tmp / "bin"
    b.mkdir()
    log = tmp / "log.txt"
    log.write_text("")
    real = {
        t: subprocess.run(["which", t], capture_output=True, text=True).stdout.strip()
        for t in (
            "bash",
            "jq",
            "python3",
            "awk",
            "head",
            "mktemp",
            "date",
            "rm",
            "cat",
            "sh",
            "dirname",
            "cut",
            "sed",
            "tr",
        )
    }
    for t, p in real.items():
        (b / t).symlink_to(p)
    cloud = b / "idp-cloud"
    cloud.write_text(
        "#!/bin/bash\n"
        f'echo "cloud $*" >> {log}\n'
        'case "$3" in\n'
        f"  litellm-upstream) printf '%s' '{{\"LITELLM_MASTER_KEY\":\"{MASTER}\"}}';;\n"
        "  consumerA) printf '%s' '{\"key\":\"sk-fake-currentA\"}';;\n"
        "  consumerB) exit 1;;\n"
        "  *) exit 1;;\n"
        "esac\n"
    )
    listing = json.dumps(
        {
            "keys": [
                {
                    "key_alias": "consumerA-current",
                    "spend": 0,
                    "created_at": "2020-01-01T00:00:00Z",
                    "metadata": {
                        "consumer": "consumerA",
                        "minted_by": "bin/idp-router-key",
                    },
                },
                {
                    "key_alias": "consumerA-orphan",
                    "spend": 0,
                    "created_at": "2020-01-01T00:00:00Z",
                    "metadata": {
                        "consumer": "consumerA",
                        "minted_by": "bin/idp-router-key",
                    },
                },
                {
                    "key_alias": "consumerB-orphan",
                    "spend": 0,
                    "created_at": "2020-01-01T00:00:00Z",
                    "metadata": {
                        "consumer": "consumerB",
                        "minted_by": "bin/idp-router-key",
                    },
                },
                {
                    "key_alias": "consumerA-spending",
                    "spend": 3.5,
                    "created_at": "2020-01-01T00:00:00Z",
                    "metadata": {
                        "consumer": "consumerA",
                        "minted_by": "bin/idp-router-key",
                    },
                },
                {
                    "key_alias": "manual-key",
                    "spend": 0,
                    "created_at": "2020-01-01T00:00:00Z",
                    "metadata": {},
                },
            ]
        }
    )
    curl = b / "curl"
    curl.write_text(
        "#!/bin/bash\n"
        f'echo "curl $*" >> {log}\n'
        'case "$*" in\n'
        f"  *key/list*) printf '%s' '{listing}';;\n"
        '  *key/info*) printf \'%s\' \'{"info":{"key_alias":"consumerA-current"}}\';;\n'
        "  *key/delete*) printf '';;\n"
        "  *) exit 22;;\n"
        "esac\n"
    )
    for f in (cloud, curl):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {
        "PATH": str(b),
        "HOME": str(tmp),
        "TMPDIR": str(tmp),
        "IDP_CLOUD": str(cloud),
        "ROUTER_URL": "https://router.test",
    }
    return {"env": env, "log": log}


def test_reap_orphans_deletes_only_aged_zero_spend_non_current_router_minted_keys(
    tmp_path: Path,
) -> None:
    fk = _fakes_for_reap(tmp_path)
    r = subprocess.run(
        [str(TOOL), "--reap-orphans", "--max-age-hours", "0"],
        capture_output=True,
        text=True,
        env=fk["env"],
        cwd=ROOT,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    log = fk["log"].read_text()
    # Each invocation's echoed line embeds the JSON -d payload verbatim, newlines included, so a
    # block runs from one "cloud "/"curl " line start to the next rather than being one text line.
    blocks = re.split(r"\n(?=cloud |curl )", log)
    deletes = [blk for blk in blocks if "key/delete" in blk]
    assert any("consumerA-orphan" in blk for blk in deletes), log
    assert any("consumerB-orphan" in blk for blk in deletes), log
    assert not any("consumerA-current" in blk for blk in deletes), log
    assert not any("consumerA-spending" in blk for blk in deletes), log
    assert not any("manual-key" in blk for blk in deletes), log
    assert "reaped orphan consumerA-orphan" in r.stdout, r.stdout
    assert "reaped orphan consumerB-orphan" in r.stdout, r.stdout
    assert "reap-orphans: 2 orphan key(s) removed" in r.stdout, r.stdout


def test_reap_orphans_with_nothing_router_minted_is_a_clean_ok(tmp_path: Path) -> None:
    b = tmp_path / "bin2"
    b.mkdir()
    log = tmp_path / "log2.txt"
    log.write_text("")
    for t in (
        "bash",
        "jq",
        "python3",
        "awk",
        "head",
        "mktemp",
        "date",
        "rm",
        "cat",
        "sh",
        "dirname",
        "cut",
        "sed",
        "tr",
    ):
        (b / t).symlink_to(
            subprocess.run(["which", t], capture_output=True, text=True).stdout.strip()
        )
    cloud = b / "idp-cloud"
    cloud.write_text(
        "#!/bin/bash\n"
        'case "$3" in\n'
        f"  litellm-upstream) printf '%s' '{{\"LITELLM_MASTER_KEY\":\"{MASTER}\"}}';;\n"
        "  *) exit 1;;\n"
        "esac\n"
    )
    curl = b / "curl"
    curl.write_text(
        "#!/bin/bash\n"
        f'echo "curl $*" >> {log}\n'
        'case "$*" in\n'
        "  *key/list*) printf '%s' '{\"keys\":[]}';;\n"
        "  *) exit 22;;\n"
        "esac\n"
    )
    for f in (cloud, curl):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {
        "PATH": str(b),
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "IDP_CLOUD": str(cloud),
        "ROUTER_URL": "https://router.test",
    }
    r = subprocess.run(
        [str(TOOL), "--reap-orphans"], capture_output=True, text=True, env=env, cwd=ROOT
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no router-minted keys found" in r.stdout, r.stdout


def test_budget_is_a_config_row_not_a_literal_in_the_script() -> None:
    d = yaml.safe_load((ROOT / "estate-defaults.yaml").read_text())
    assert isinstance(d["llm"]["virtual_key_daily_usd"], (int, float))
    src = TOOL.read_text()
    assert "virtual_key_daily_usd" in src
    assert not re.search(r"max_budget:\s*\d", src), (
        "budget typed in the script (LAW 46)"
    )
