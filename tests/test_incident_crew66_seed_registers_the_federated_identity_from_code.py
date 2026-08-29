"""crew#66, founder 2026-08-29 ("create one credential by hand, then have that one manage the rest"):
runs 33248757130 and 33249648141 were refused at /api/v2/oauth/token-exchange because the identity
in the console did not match the claims the runner really carries. From here the console is never
the place that is edited: on the runner a refused identity is re-registered from the runner's own
claims (POST /api/v2/tailnet/-/keys keyType=federated, kb/1581) with the one bootstrap credential
(SEED_TAILSCALE_* from bin/idp-set-root tailscale), its id is vaulted as `tailscale-federated`, and
the federated exchange runs again. The seed never mints the operator on the runner."""

import json
import pathlib

from test_incident_crew66_tailscale_operator_client_is_minted_through_the_api import (
    _estate,
    _run,
)

IDP = pathlib.Path(__file__).resolve().parents[1]
# sub=repo:chidionyema@377396/idp@1344360654:ref:refs/heads/main, iss=token.actions.githubusercontent.com
JWT = "h.eyJpc3MiOiAiaHR0cHM6Ly90b2tlbi5hY3Rpb25zLmdpdGh1YnVzZXJjb250ZW50LmNvbSIsICJzdWIiOiAicmVwbzpjaGlkaW9ueWVtYUAzNzczOTYvaWRwQDEzNDQzNjA2NTQ6cmVmOnJlZnMvaGVhZHMvbWFpbiIsICJhdWQiOiAiYXBpLnRhaWxzY2FsZS5jb20vZmVkaWQtdGVzdCJ9.s"


def _runner(tmp_path, seed_env=True, old="kFEDOLD111"):
    env, log, vault = _estate(tmp_path, seed=None)
    sh = pathlib.Path(env["IDP_VAULT_PUT"]).parent
    (sh / "curl").write_text(f'''#!/bin/bash
echo "$@" >> "{log}"
out=/dev/stdout; code=""
args=("$@"); for i in "${{!args[@]}}"; do [ "${{args[$i]}}" = -o ] && out="${{args[$((i+1))]}}"; [ "${{args[$i]}}" = -w ] && code=1; done
body() {{ if [ "$out" = /dev/stdout ]; then cat; else cat > "$out"; printf '%s' "$1"; fi; }}
case "$*" in
  *oidc.test*) echo '{{"value":"{JWT}"}}';;
  *client_id=kFEDNEW222*) echo '{{"access_token":"at-fed","scope":"oauth_keys"}}' | body 200;;
  *token-exchange*) echo '{{"message":"forbidden"}}' | body 403;;
  *oauth/token*) pair=$(cat); case "$pair" in *SEED*) echo '{{"access_token":"at-seed","scope":"oauth_keys"}}';; *) echo '{{"access_token":"at-1","scope":"auth_keys devices:core policy_file users:read"}}';; esac;;
  *DELETE*) printf '204';;
  *keyType\\":\\"federated*) echo '{{"id":"kFEDNEW222","keyType":"federated"}}';;
  *tailnet/-/keys*) echo '{{"id":"kNEW987654","key":"tskey-client-new-1","keyType":"client"}}';;
  *) echo '{{}}';;
esac
''')
    env.update(
        {
            "TAILSCALE_FEDERATED_CLIENT_ID": old,
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://oidc.test/token?api-version=2",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "runner-token",
            "GITHUB_REPOSITORY": "chidionyema/idp",
        }
    )
    if seed_env:
        env.update(
            {
                "TAILSCALE_SEED_CLIENT_ID": "kSEED123456",
                "TAILSCALE_SEED_CLIENT_SECRET": "tskey-client-seed-1",
            }
        )
    return env, log, vault


def test_a_refused_identity_is_re_registered_from_the_runners_claims_and_the_operator_is_minted_federated(
    tmp_path,
):
    env, log, vault = _runner(tmp_path)
    p = _run(env)
    out = p.stdout + p.stderr
    assert p.returncode == 0, out
    calls = log.read_text()
    reg = [l for l in calls.splitlines() if '"keyType":"federated"' in l]
    assert len(reg) == 1, calls
    assert '"issuer":"https://token.actions.githubusercontent.com"' in reg[0]
    assert '"subject":"repo:chidionyema@377396/idp@1344360654:*"' in reg[0], (
        "the subject is the runner's own sub with the ref widened, never typed"
    )
    assert '"scopes":["oauth_keys"]' in reg[0] and "at-seed" in reg[0]
    assert json.load(open(vault))["tailscale-federated"]["client_id"] == "kFEDNEW222"
    assert "keys/kFEDOLD111" in calls and "DELETE" in calls, (
        "the refused identity is retired"
    )
    ex = [l for l in calls.splitlines() if "token-exchange" in l]
    assert "client_id=kFEDOLD111" in ex[0] and "client_id=kFEDNEW222" in ex[-1]
    mint = [l for l in calls.splitlines() if '"keyType":"client"' in l]
    assert mint and "at-fed" in mint[0] and "at-seed" not in mint[0], (
        "the operator is minted with the federated token, never the seed"
    )
    assert json.load(open(vault))["tailscale-operator"]["client_id"] == "kNEW987654"
    assert "registered from code" in out and "tskey" not in out


def test_the_vaulted_identity_wins_over_estate_config_next_run(tmp_path):
    env, log, vault = _runner(tmp_path)
    d = json.load(open(vault))
    d["tailscale-federated"] = {"client_id": "kFEDNEW222", "client_secret": "none"}
    vault.write_text(json.dumps(d))
    p = _run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    calls = log.read_text()
    assert '"keyType":"federated"' not in calls
    assert "client_id=kFEDNEW222" in calls and "kFEDOLD111" not in calls


def test_refused_and_no_seed_names_the_one_hand_and_mints_nothing(tmp_path):
    env, log, vault = _runner(tmp_path, seed_env=False)
    p = _run(env)
    out = p.stdout + p.stderr
    assert p.returncode == 1, out
    assert "HTTP 403" in out and "forbidden" in out, (
        "the refusal is still printed in full"
    )
    assert "bin/idp-set-root tailscale" in out
    assert '"keyType"' not in log.read_text()
    assert "tailscale-operator" not in json.load(open(vault))


def test_the_workflow_hands_the_seed_pair_to_the_bootstrapper():
    wf = (IDP / ".github/workflows/oke-check.yml").read_text()
    assert "TAILSCALE_SEED_CLIENT_ID: ${{ secrets.SEED_TAILSCALE_CLIENT_ID }}" in wf
    assert (
        "TAILSCALE_SEED_CLIENT_SECRET: ${{ secrets.SEED_TAILSCALE_CLIENT_SECRET }}"
        in wf
    )
