"""R52 (founder 2026-08-29): one root credential per provider, set once as a named secret, then code.
bin/idp-bootstrap-cloudflare drove dash.cloudflare.com with Playwright to make a root token and asked
the founder to sign in. With CLOUDFLARE_ROOT_TOKEN in the environment (oke-check apply reads repository
secret SEED_CLOUDFLARE_ROOT_TOKEN) no browser is driven, the DNS and R2 children are minted through
POST /user/tokens, and the standing root is kept, never revoked."""

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _estate(tmp_path):
    idp = tmp_path / "idp"
    (idp / "bin").mkdir(parents=True)
    (idp / "clusters" / "oke").mkdir(parents=True)
    shutil.copy(
        ROOT / "bin" / "idp-bootstrap-cloudflare",
        idp / "bin" / "idp-bootstrap-cloudflare",
    )
    (idp / "clusters" / "oke" / "estate-config.yaml").write_text(
        "ESTATE_ZONE: example.test\n"
    )
    (idp / "estate-defaults.yaml").write_text("r2:\n  bucket: prospector-test\n")
    log = tmp_path / "curl.log"
    log.touch()
    vault = tmp_path / "vault.json"
    vault.write_text("{}")
    sh = tmp_path / "shims"
    sh.mkdir()
    (sh / "curl").write_text(f'''#!/bin/bash
echo "$@" >> "{log}"
case "$*" in
  *"POST"*user/tokens*) echo '{{"success":true,"result":{{"id":"tok-child","value":"cf-child-secret-value-000000000000000000"}}}}';;
  *user/tokens/verify*) echo '{{"success":true,"result":{{"status":"active"}}}}';;
  *permission_groups*) echo '{{"result":[{{"id":"g-dns","name":"DNS Write","scopes":["com.cloudflare.api.account.zone"]}},{{"id":"g-r2","name":"Workers R2 Storage Write","scopes":["com.cloudflare.api.account"]}}]}}';;
  *"zones?name="*) echo '{{"result":[{{"id":"z1","account":{{"id":"a1"}}}}]}}';;
  *dns_records*) echo '{{"success":true}}';;
  *r2/buckets*) echo '{{"success":true}}';;
  *) echo '{{"success":true,"result":[]}}';;
esac
''')
    (idp / "bin" / "idp-oci-whoami").write_text("#!/bin/bash\necho estate-test\n")
    (idp / "bin" / "idp-vault-put").write_text(f'''#!/bin/bash
[ "$2" = --preflight ] && {{ echo "ok vault"; exit 0; }}
python3 - "$ESTATE_ENV_FILE" "{vault}" "$@" <<'PY'
import json, sys
envf, vf = sys.argv[1:3]; args = sys.argv[3:]
kv = dict(l.rstrip("\\n").split("=", 1) for l in open(envf) if "=" in l)
d = json.load(open(vf)); name = [a for a in args if not a.startswith("--") and "=" not in a][0]
d.setdefault(name, {{}}).update({{a.split("=")[0]: kv[a.split("=")[1]] for a in args if "=" in a}})
json.dump(d, open(vf, "w"))
PY
''')
    (idp / "bin" / "idp-cloud").write_text(f'''#!/bin/bash
case "$2" in
  put) python3 -c 'import json,sys; d=json.load(open("{vault}")); d[sys.argv[1]]=open(sys.argv[2]).read(); json.dump(d,open("{vault}","w"))' "$3" "$5";;
  get) exit 1;;
esac
''')
    for f in list(sh.iterdir()) + [
        idp / "bin" / n
        for n in (
            "idp-oci-whoami",
            "idp-vault-put",
            "idp-cloud",
            "idp-bootstrap-cloudflare",
        )
    ]:
        f.chmod(0o755)
    env = {
        **{k: v for k, v in os.environ.items() if k != "R2_BUCKET"},
        "PATH": f"{sh}:{os.environ['PATH']}",
        "ESTATE_HOME": str(tmp_path / "home"),
        "CLOUDFLARE_API_URL": "https://api.test/client/v4",
        "CLOUDFLARE_ROOT_TOKEN": "cf-root-secret-value-00000000000000000000",
    }
    return idp, env, log, vault


def test_incident_crew66_a_root_from_the_environment_mints_the_children_and_drives_no_browser(
    tmp_path,
):
    idp, env, log, vault = _estate(tmp_path)
    p = subprocess.run(
        [str(idp / "bin" / "idp-bootstrap-cloudflare")],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    calls = log.read_text()
    assert (
        "playwright" not in (p.stdout + p.stderr).lower()
        and not (tmp_path / "home" / "bootstrap-venv").exists()
    )
    assert (
        calls.count(
            'POST -H Authorization: Bearer cf-root-secret-value-00000000000000000000 -H Content-Type: application/json -d {"name":"estate-dns'
        )
        == 1
    )
    assert "estate-r2 prospector-test" in calls
    assert "DELETE" not in calls, "the standing root was revoked"
    assert "standing root kept" in p.stdout
    v = json.load(open(vault))
    assert v["cloudflare-api-token"] == "cf-child-secret-value-000000000000000000"
    assert (
        v["prospector-engine-env"]["R2_ACCESS_KEY_ID"] == "tok-child"
        and v["prospector-engine-env"]["R2_BUCKET"] == "prospector-test"
    )
    assert "cf-root-secret" not in p.stdout and "cf-child-secret" not in p.stdout, (
        "a secret reached stdout"
    )
