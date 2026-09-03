"""crew#66 root trust, R52 (founder 2026-08-29), sweep item 3 of the wrong-root inventory (crew#66
comment 5461144560): bin/idp-bootstrap-vendors drove every vendor's key console with Playwright over
the founder's browser session, minted Gemini through his laptop gcloud SSO, talked to BotFather on
web.telegram.org, and signed him into OCI when no session was live. Each of those is a wrong root:
the founder's hand every time a session lapses. Now every vendor is one named repository secret, set
once; the apply run proves it against the vendor API and writes the vault; no browser, no SSO."""
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REG = yaml.safe_load((ROOT / "platform/vendors/consoles.yaml").read_text())["vendors"]
WF = (ROOT / ".github/workflows/oke-check.yml").read_text()

# well-formed, fake keys; a verify shim answers 2xx to any of them, so nothing here reaches a vendor
FAKE = {
    "SEED_ANTHROPIC_API_KEY": "sk-ant-" + "a" * 64,
    "SEED_OPENROUTER_API_KEY": "sk-or-v1-" + "0" * 64,
    "SEED_DEEPSEEK_API_KEY": "sk-" + "1" * 32,
    "SEED_MINIMAX_API_KEY": "eyJx.eyJy.zzz",
    "SEED_GROQ_API_KEY": "gsk_" + "A" * 40,
    "SEED_GEMINI_API_KEY": "AIza" + "B" * 35,
    "SEED_EXA_API_KEY": "01234567-0123-0123-0123-0123456789ab",
    "SEED_TELEGRAM_HERMES_BOT_TOKEN": "12345678:" + "C" * 35,
    "SEED_TELEGRAM_ALERTS_BOT_TOKEN": "87654321:" + "D" * 35,
    "SEED_STRIPE_SECRET_KEY": "sk_test_" + "E" * 24,
}


def test_every_vendor_is_one_named_secret_and_no_road_drives_a_browser_or_an_sso():
    for name, v in REG.items():
        assert v["kind"] == "secret", f"{name}: kind {v['kind']} is a wrong root (R52)"
        secrets = [t["secret"] for t in v["targets"] if "secret" in t] or [v["secret"]]
        for s in secrets:
            assert re.fullmatch(r"SEED_[A-Z_]+", s), s
            assert s in FAKE, f"{s}: add a well-formed fake to this test"
            assert f"{s}: ${{{{ secrets.{s} }}}}" in WF, f"{s} is not mapped into the apply step"
        assert re.fullmatch(v["shape"], FAKE[secrets[0]]), f"{name}: the fake does not match shape"
    script = (ROOT / "bin/idp-bootstrap-vendors").read_text()
    for wrong in ("playwright", "chromium", "gcloud", "oci session authenticate", "web.telegram.org", "launch_persistent_context"):
        assert wrong not in script, f"{wrong} is a wrong root and may not come back (R52)"
    assert '"--merge", entry' in script


def _tree(tmp_path):
    idp = tmp_path / "idp"
    (idp / "bin").mkdir(parents=True); (idp / "platform/vendors").mkdir(parents=True)
    shutil.copy(ROOT / "bin/idp-bootstrap-vendors", idp / "bin/idp-bootstrap-vendors")
    shutil.copy(ROOT / "platform/vendors/consoles.yaml", idp / "platform/vendors/consoles.yaml")
    log = tmp_path / "calls.log"
    shims = {
        "idp-oci-whoami": "#!/bin/sh\necho estate-ci\n",
        "idp-vault-put": f"#!/bin/sh\nif [ \"$VAULT_PUT_PREFLIGHT\" = 1 ]; then echo 'vault ok'; exit 0; fi\n"
                         f"v=$(cat \"$ESTATE_ENV_FILE\")\necho \"put $1 $2 $3 ${{v#V_KEY=}}\" >> {log}\n",
        "idp-cloud": "#!/bin/sh\nexit 1\n",  # every entry empty: nothing verifies from the vault
    }
    for n, body in shims.items():
        p = idp / "bin" / n; p.write_text(body); p.chmod(p.stat().st_mode | stat.S_IEXEC)
    # verify() uses urllib; point it at a stub by shadowing the module search path
    site = tmp_path / "site"; site.mkdir()
    (site / "sitecustomize.py").write_text(
        "import urllib.request, io\n"
        "class _R(io.BytesIO):\n"
        "    status = 200\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *a): return False\n"
        "def _open(req, timeout=30):\n"
        f"    open({str(tmp_path / 'verify.log')!r}, 'a').write(req.full_url.split('?')[0] + '\\n')\n"
        "    return _R(b'{}')\n"
        "urllib.request.urlopen = _open\n")
    return idp, log, site


def _run(idp, site, env_extra, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("SEED_")}
    # the script calls bare python3 and needs yaml (oci-cli pulls PyYAML in CI); this interpreter has it
    env.update({"PYTHONPATH": str(site), "PATH": f"{Path(sys.executable).parent}:{env.get('PATH', '')}", **env_extra})
    return subprocess.run([str(idp / "bin/idp-bootstrap-vendors"), *args], env=env, capture_output=True, text=True)


def test_roots_from_the_environment_are_verified_then_written_and_never_printed(tmp_path):
    idp, log, site = _tree(tmp_path)
    r = _run(idp, site, FAKE)
    assert r.returncode == 0, r.stdout + r.stderr
    puts = log.read_text().splitlines()
    targets = sum(len(v["targets"]) for v in REG.values())
    assert len(puts) == targets, (len(puts), targets, r.stdout)
    assert all(line.startswith("put --merge ") for line in puts), puts[:2]
    assert "ok      vendors" in r.stdout and f"{len(REG) + 1} written" in r.stdout  # telegram = two roots
    verified = (tmp_path / "verify.log").read_text()
    assert "api.anthropic.com" in verified and "api.telegram.org" in verified
    for value in FAKE.values():
        assert value not in r.stdout and value not in r.stderr, "a root reached stdout"


def test_a_missing_root_is_blind_for_that_vendor_only_and_the_exit_is_two(tmp_path):
    idp, log, site = _tree(tmp_path)
    partial = {k: v for k, v in FAKE.items() if k != "SEED_GROQ_API_KEY"}
    r = _run(idp, site, partial)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND   groq" in r.stdout and "gh secret set SEED_GROQ_API_KEY" in r.stdout
    assert "1 blind" in r.stdout
    assert "GROQ_API_KEY" not in log.read_text() and "ANTHROPIC_API_KEY" in log.read_text()


def test_the_apply_step_tolerates_blind_and_the_hermes_env_step_carries_no_vendor_key():
    step = WF[WF.index("bin/idp-bootstrap-vendors (crew#579, R52)"):]
    step = step[: step.index("\n\n")]
    assert "inputs.mode == 'apply'" in step
    assert '[ "$rc" = 2 ] || exit "$rc"' in step
    assert "SEED_" not in WF[WF.index("hermes-agent-env (crew#516 CP4)"):WF.index("bin/idp-bootstrap-vendors (crew#579, R52)")].split("run: |")[0].replace("SEED_HERMES_", "")
