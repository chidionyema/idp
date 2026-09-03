"""crew#66 / crew#590: the Tailscale operator credential is minted through the vendor's API from a
one-scope seed, never by driving the admin console.

2026-08-28. bin/idp-bootstrap-tailscale merged claiming "no endpoint creates an OAuth client" and
drove the console with Playwright: four selector patches in one night, a description the console
refused, a 10-minute read window that expired while the founder was asking what the scopes meant.
The claim was measured from the console, not the API. The vendor's own SDK
(tailscale-client-go-v2 keys.go, KeysResource.CreateOAuthClient) posts
{"keyType":"client","scopes":[..],"tags":[..],"description":..} to /api/v2/tailnet/-/keys.

No test here opens a socket: `curl` is a shim on PATH that records every call and answers canned
JSON; the vault helpers are shims named by IDP_VAULT_PUT / IDP_CLOUD / IDP_OCI_WHOAMI. The
assertions are the request the API would receive and the bytes the vault would hold.
"""
import json
import os
import pathlib
import subprocess

IDP = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = IDP / "bin" / "idp-bootstrap-tailscale"


def _estate(tmp_path, operator=None, seed=("kSEED123456", "tskey-client-seed-1"), mint_ok=True, delete_code="204", seed_scope="oauth_keys"):
    sh = tmp_path / "shims"; sh.mkdir()
    log = tmp_path / "curl.log"; vault = tmp_path / "vault.json"; log.touch()
    vault.write_text(json.dumps({k: v for k, v in {
        "tailscale-seed": seed and {"client_id": seed[0], "client_secret": seed[1]},
        "tailscale-operator": operator and {"client_id": operator[0], "client_secret": operator[1]},
    }.items() if v}))
    mint = '{"id":"kNEW987654","key":"tskey-client-new-1","keyType":"client","scopes":["auth_keys","devices:core","policy_file","users:read"]}' if mint_ok else '{"message":"scope oauth_keys required"}'
    (sh / "curl").write_text(f'''#!/bin/bash
echo "$@" >> "{log}"
case "$*" in
  *oauth/token*) pair=$(cat); echo "$pair" >> "{log}"; case "$pair" in *dead*) echo '{{"message":"invalid_client"}}';; *SEED*) echo '{{"access_token":"at-seed","scope":"{seed_scope}"}}';; *) echo '{{"access_token":"at-1","scope":"auth_keys devices:core policy_file users:read"}}';; esac;;
  *DELETE*) printf '{delete_code}'; exit 0;;
  *tailnet/-/keys*) echo '{mint}';;
  *) echo '{{}}';;
esac
''')
    (sh / "vault-put").write_text(f'''#!/bin/bash
[ "$2" = --preflight ] && {{ echo "ok vault"; exit 0; }}
python3 - "$1" "$ESTATE_ENV_FILE" "{vault}" <<'PY'
import json, sys
name, envf, vf = sys.argv[1:]
kv = dict(l.strip().split("=", 1) for l in open(envf) if "=" in l)
d = json.load(open(vf)); d[name] = {{"client_id": kv["V_client_id"], "client_secret": kv["V_client_secret"]}}
json.dump(d, open(vf, "w"))
PY
''')
    (sh / "cloud").write_text(f'''#!/bin/bash
python3 -c 'import json,sys; d=json.load(open("{vault}")); v=d.get(sys.argv[1]); print(json.dumps(v)) if v else sys.exit(1)' "$3"
''')
    (sh / "whoami").write_text("#!/bin/bash\necho estate-test\n")
    for f in sh.iterdir():
        f.chmod(0o755)
    # the seed road is exercised only where no federated identity is configured (ADR 0010):
    # point the script at an empty estate-config, never at the real one
    (tmp_path / "no-federated-config.yaml").write_text("data: {}\n")
    env = {**os.environ, "PATH": f"{sh}:{os.environ['PATH']}", "IDP_VAULT_PUT": str(sh / "vault-put"),
           "ESTATE_CONFIG": str(tmp_path / "no-federated-config.yaml"), "TAILSCALE_FEDERATED_CLIENT_ID": "",
           "IDP_CLOUD": str(sh / "cloud"), "IDP_OCI_WHOAMI": str(sh / "whoami"), "TAILSCALE_API_URL": "https://api.test"}
    return env, log, vault


def _run(env, *args):
    return subprocess.run([str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60)


def test_incident_crew66_the_operator_client_is_minted_by_post_keys_with_the_four_scopes_and_vaulted(tmp_path):
    env, log, vault = _estate(tmp_path)
    p = _run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    calls = log.read_text()
    assert "https://api.test/api/v2/tailnet/-/keys" in calls
    body = json.loads([l for l in calls.splitlines() if "tailnet/-/keys" in l][0].split(" -d ", 1)[1].split(" https://")[0])
    assert body["keyType"] == "client"
    assert body["scopes"] == ["auth_keys", "devices:core", "policy_file", "users:read"] and body["tags"] == ["tag:k8s"]
    v = json.load(open(vault))["tailscale-operator"]
    assert v == {"client_id": "kNEW987654", "client_secret": "tskey-client-new-1"}
    assert "tskey-client" not in p.stdout, "a secret reached stdout"
    for l in log.read_text().splitlines():
        if "oauth/token" in l:
            assert "tskey-client" not in l, "a client secret reached curl's argv"


def test_incident_crew66_no_seed_is_one_named_human_step_and_nothing_is_minted(tmp_path):
    env, log, vault = _estate(tmp_path, seed=None)
    p = _run(env)
    assert p.returncode == 1 and "--seed" in p.stdout, p.stdout + p.stderr
    assert "tailnet/-/keys" not in log.read_text()
    assert "tailscale-operator" not in json.load(open(vault))


def test_incident_crew66_a_working_entry_is_kept_and_check_reads_it_without_the_seed(tmp_path):
    env, log, vault = _estate(tmp_path, operator=("kOLD111111", "tskey-client-old-1"), seed=None)
    assert _run(env).returncode == 0
    assert _run(env, "--check").returncode == 0
    assert "tailnet/-/keys" not in log.read_text()
    assert json.load(open(vault))["tailscale-operator"]["client_id"] == "kOLD111111"


def test_incident_crew66_a_dead_entry_fails_check_and_mint_replaces_it(tmp_path):
    env, log, vault = _estate(tmp_path, operator=("kdead111111", "tskey-client-dead"))
    assert _run(env, "--check").returncode == 1
    p = _run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.load(open(vault))["tailscale-operator"]["client_id"] == "kNEW987654"


def test_incident_crew66_rotate_mints_anew_and_deletes_the_client_it_replaced(tmp_path):
    env, log, vault = _estate(tmp_path, operator=("kOLD111111", "tskey-client-old-1"))
    p = _run(env, "--rotate")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "DELETE" in log.read_text() and "keys/kOLD111111" in log.read_text()
    assert json.load(open(vault))["tailscale-operator"]["client_id"] == "kNEW987654"


def test_incident_crew66_an_api_refusal_writes_nothing(tmp_path):
    env, log, vault = _estate(tmp_path, mint_ok=False)
    p = _run(env)
    assert p.returncode == 1 and "scope oauth_keys required" in p.stdout, p.stdout + p.stderr
    assert "tailscale-operator" not in json.load(open(vault))


def test_incident_crew66_a_refused_delete_on_rotate_is_a_failure_not_a_deleted_line(tmp_path):
    """Reviewer 14ed6c8b on idp#624: curl without -f exits 0 on 403, so a refused DELETE printed
    "deleted" while the superseded credential stayed live."""
    env, log, vault = _estate(tmp_path, operator=("kOLD111111", "tskey-client-old-1"), delete_code="403")
    p = _run(env, "--rotate")
    assert p.returncode == 1 and "NOT deleted" in p.stdout and "403" in p.stdout, p.stdout + p.stderr
    assert "deleted" not in p.stdout.replace("NOT deleted", "")
    assert json.load(open(vault))["tailscale-operator"]["client_id"] == "kNEW987654", "the new client is vaulted before the old one is retired"


def test_incident_crew66_a_seed_with_more_than_oauth_keys_is_refused_before_minting(tmp_path):
    env, log, vault = _estate(tmp_path, seed_scope="oauth_keys users devices:core")
    p = _run(env)
    assert p.returncode == 1 and "more than oauth_keys" in p.stdout, p.stdout + p.stderr
    assert "tailnet/-/keys" not in log.read_text()


def _federated(tmp_path, scope):
    """Road 2 (ADR 0010): the runner's OIDC token is exchanged for a Tailscale token; no seed in the vault."""
    env, log, vault = _estate(tmp_path, seed=None)
    sh = pathlib.Path(env["IDP_CLOUD"]).parent
    (sh / "curl").write_text(f'''#!/bin/bash
echo "$@" >> "{log}"
case "$*" in
  *github.test/token*) h=$(printf '{{"alg":"none"}}' | base64 | tr -d '=\n'); c=$(printf '{{"iss":"gh","sub":"repo:x"}}' | base64 | tr -d '=\n'); printf '{{"value":"%s.%s."}}' "$h" "$c";;
  *oauth/token-exchange*) for a in "$@"; do case "$prev" in -o) printf '{{"access_token":"at-fed","scope":"{scope}"}}' > "$a";; esac; prev=$a; done; printf 200;;
  *tailnet/-/keys*) echo '{{"id":"kNEW987654","key":"tskey-client-new-1","keyType":"client"}}';;
  *oauth/token*) pair=$(cat); echo '{{"access_token":"at-1","scope":"auth_keys devices:core policy_file users:read"}}';;
  *) echo '{{}}';;
esac
''')
    env.update({"TAILSCALE_FEDERATED_CLIENT_ID": "tFED111CNTRL", "ACTIONS_ID_TOKEN_REQUEST_URL": "https://github.test/token?x=1",
                "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "gh-req"})
    return env, log, vault


def test_incident_crew66_run_33266374431_a_federated_identity_holding_the_operator_scopes_mints(tmp_path):
    """2026-08-29 run 33266374431: the identity held every operator scope (Tailscale: an actor grants only what
    it holds) and the script refused it with the seed road's one-scope rule. On the federated road the rule
    is the opposite: the token must cover the four operator scopes."""
    env, log, vault = _federated(tmp_path, "devices:core devices:core:read policy_file auth_keys oauth_keys users:read")
    p = _run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "identity scopes cover the operator's" in p.stdout and "more than oauth_keys" not in p.stdout
    assert "tailnet/-/keys" in log.read_text()
    assert json.load(open(vault))["tailscale-operator"]["client_id"] == "kNEW987654"


def test_incident_crew66_a_federated_identity_missing_an_operator_scope_is_refused_before_minting(tmp_path):
    env, log, vault = _federated(tmp_path, "oauth_keys")
    p = _run(env)
    assert p.returncode == 1 and "lacks scope auth_keys" in p.stdout, p.stdout + p.stderr
    assert "tailnet/-/keys" not in log.read_text()


def test_incident_crew66_a_seed_pair_from_the_environment_mints_and_is_vaulted_so_the_repo_secret_can_go(tmp_path):
    """Founder 2026-08-29: one master credential, made once, then code. Road c: the pair arrives as
    TAILSCALE_SEED_CLIENT_ID / _SECRET (oke-check apply reads repository secrets), never a prompt."""
    env, log, vault = _estate(tmp_path, seed=None)
    env = {**env, "TAILSCALE_SEED_CLIENT_ID": "kSEED123456", "TAILSCALE_SEED_CLIENT_SECRET": "tskey-client-seed-1"}
    p = _run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    v = json.load(open(vault))
    assert v["tailscale-seed"] == {"client_id": "kSEED123456", "client_secret": "tskey-client-seed-1"}
    assert v["tailscale-operator"] == {"client_id": "kNEW987654", "client_secret": "tskey-client-new-1"}
    assert "tskey-client" not in p.stdout, "a secret reached stdout"
    assert "https://api.test/api/v2/tailnet/-/keys" in log.read_text()
    for l in log.read_text().splitlines():
        if "oauth/token" in l:
            assert "tskey-client" not in l, "a client secret reached curl's argv"


def test_the_apply_run_mints_the_operator_client_and_estate_config_names_the_identity():
    """Kept when the federated fake-curl file was deleted (2026-08-31): that file drove
    bin/idp-bootstrap-tailscale under a `curl` the test wrote, and the double answered the token
    endpoint without reading the config off stdin -- `printf ... | curl -sS -K -` then took SIGPIPE
    whenever the double exited first, which is a coin toss on a loaded runner. It reddened
    bdd-suites on five open pull requests while main's own run was green on the same tree. This
    assertion was the one thing in that file that touched no fake: it reads the workflow and the
    cluster config as they are on disk."""
    wf = (IDP / ".github/workflows/oke-check.yml").read_text()
    assert "bin/idp-bootstrap-tailscale" in wf and "TAILSCALE_FEDERATED_CLIENT_ID" in wf
    assert "id-token: write" in wf
    cfg = (IDP / "clusters/oke/estate-config.yaml").read_text()
    assert "TAILSCALE_FEDERATED_CLIENT_ID:" in cfg
