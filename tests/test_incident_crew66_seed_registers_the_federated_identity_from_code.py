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
  *client_id=kFEDNEW222*) echo '{{"access_token":"at-fed","scope":"auth_keys devices:core policy_file users:read oauth_keys"}}' | body 200;;
  *token-exchange*) echo '{{"message":"forbidden"}}' | body 403;;
  *oauth/token*) pair=$(cat); case "$pair" in *SEED*) echo '{{"access_token":"at-seed","scope":"oauth_keys"}}';; *) echo '{{"access_token":"at-1","scope":"auth_keys devices:core policy_file users:read"}}';; esac;;
  *DELETE*) printf '204';;
  *keyType\\":\\"federated*) echo '{{"id":"kFEDNEW222","keyType":"federated"}}';;
  *-/keys/kFEDNEW222*) echo '{{"id":"kFEDNEW222","keyType":"federated","tags":["tag:k8s","tag:k8s-operator"]}}';;
  *tailnet/-/keys*) echo '{{"id":"kNEW987654","key":"tskey-client-new-1","keyType":"client","tags":["tag:k8s","tag:k8s-operator"]}}';;
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
    assert (
        '"scopes":["auth_keys","devices:core","policy_file","users:read","oauth_keys"]'
        in reg[0]
        and "at-seed" in reg[0]
    ), (
        "the identity holds every scope it grants the operator (Tailscale grants only what the actor holds)"
    )
    assert '"tags":["tag:k8s","tag:k8s-operator"]' in reg[0], (
        "the identity carries every tag it mints the operator with (an actor mints only tags its own tags own, kb/1215)"
    )
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


def test_an_identity_that_exchanges_but_carries_no_tags_is_re_registered_with_them(
    tmp_path,
):
    """Run 33756246171 (2026-09-03): the identity exchanged fine and the operator mint answered
    'requested tags [tag:k8s tag:k8s-operator] are invalid or not permitted' because the identity
    itself had been registered with no tags. The script reads the identity's own key record and
    re-registers it with both tags before minting."""
    env, log, vault = _runner(tmp_path, old="kFEDNOTAG333")
    sh = pathlib.Path(env["IDP_VAULT_PUT"]).parent
    shim = (sh / "curl").read_text()
    refused = [l for l in shim.splitlines() if "*token-exchange*)" in l]
    assert len(refused) == 1, shim
    shim = shim.replace(
        refused[0],
        '  *client_id=kFEDNOTAG333*) echo \'{"access_token":"at-notag","scope":'
        '"auth_keys devices:core policy_file users:read oauth_keys"}\' | body 200;;\n'
        '  *-/keys/kFEDNOTAG333*) echo \'{"id":"kFEDNOTAG333","keyType":"federated","tags":[]}\';;\n'
        + refused[0],
    )
    (sh / "curl").write_text(shim)
    p = _run(env)
    out = p.stdout + p.stderr
    assert p.returncode == 0, out
    calls = log.read_text()
    assert "keys/kFEDNOTAG333" in calls, "the identity's own key record is read"
    reg = [l for l in calls.splitlines() if '"keyType":"federated"' in l]
    assert len(reg) == 1 and '"tags":["tag:k8s","tag:k8s-operator"]' in reg[0], calls
    assert "carries no tag:k8s" in out and "re-registering" in out, out
    assert json.load(open(vault))["tailscale-federated"]["client_id"] == "kFEDNEW222"
    mint = [l for l in calls.splitlines() if '"keyType":"client"' in l]
    assert mint and "at-fed" in mint[0] and "at-notag" not in mint[0], (
        "the operator is minted with the re-registered identity, never the tagless one"
    )


def test_a_tagless_identity_with_no_seed_re_registers_itself_on_the_runner(tmp_path):
    """Run 33780730463 (2026-09-03 16:53Z): the drift check found the identity carried no tag,
    fell to road b, and road b died on 'no seed exists to register the identity from code' (the
    seed was retired once the identity answered). The identity holds oauth_keys itself, so on
    the runner it registers its tagged replacement with its own token and retires itself; no
    hand."""
    env, log, vault = _runner(tmp_path, seed_env=False, old="kFEDNOTAG333")
    sh = pathlib.Path(env["IDP_VAULT_PUT"]).parent
    shim = (sh / "curl").read_text()
    refused = [l for l in shim.splitlines() if "*token-exchange*)" in l]
    assert len(refused) == 1, shim
    shim = shim.replace(
        refused[0],
        '  *client_id=kFEDNOTAG333*) echo \'{"access_token":"at-notag","scope":'
        '"auth_keys devices:core policy_file users:read oauth_keys"}\' | body 200;;\n'
        '  *-/keys/kFEDNOTAG333*) echo \'{"id":"kFEDNOTAG333","keyType":"federated","tags":[]}\';;\n'
        + refused[0],
    )
    (sh / "curl").write_text(shim)
    p = _run(env)
    out = p.stdout + p.stderr
    assert p.returncode == 0, out
    assert "re-registers itself" in out, out
    calls = log.read_text()
    reg = [l for l in calls.splitlines() if '"keyType":"federated"' in l]
    assert len(reg) == 1 and "Bearer at-notag" in reg[0], (
        "the registration is made with the identity's own token, no seed",
        calls,
    )
    assert '"tags":["tag:k8s","tag:k8s-operator"]' in reg[0], reg
    gone = [l for l in calls.splitlines() if "DELETE" in l and "kFEDNOTAG333" in l]
    assert gone and "Bearer at-notag" in gone[0], (
        "the tagless identity retires itself",
        calls,
    )
    assert json.load(open(vault))["tailscale-federated"]["client_id"] == "kFEDNEW222"
    mint = [l for l in calls.splitlines() if '"keyType":"client"' in l]
    assert mint and "at-fed" in mint[0] and "at-notag" not in mint[0], calls


def test_a_tagless_identity_whose_self_registration_is_refused_names_the_one_hand(
    tmp_path,
):
    """If Tailscale refuses the tagless identity's tagged registration, the failure names the
    vendor's answer and the one hand; nothing is retired."""
    env, log, vault = _runner(tmp_path, seed_env=False, old="kFEDNOTAG333")
    sh = pathlib.Path(env["IDP_VAULT_PUT"]).parent
    shim = (sh / "curl").read_text()
    refused = [l for l in shim.splitlines() if "*token-exchange*)" in l]
    shim = shim.replace(
        refused[0],
        '  *client_id=kFEDNOTAG333*) echo \'{"access_token":"at-notag","scope":'
        '"auth_keys devices:core policy_file users:read oauth_keys"}\' | body 200;;\n'
        '  *-/keys/kFEDNOTAG333*) echo \'{"id":"kFEDNOTAG333","keyType":"federated","tags":[]}\';;\n'
        + refused[0],
    )
    reg_line = [l for l in shim.splitlines() if "keyType" in l and "federated*)" in l]
    assert len(reg_line) == 1, shim
    shim = shim.replace(
        reg_line[0],
        reg_line[0].split(" echo ")[0]
        + ' echo \'{"message":"requested tags are invalid or not permitted"}\';;',
    )
    (sh / "curl").write_text(shim)
    p = _run(env)
    out = p.stdout + p.stderr
    assert p.returncode == 1, out
    assert "not permitted" in out and "bin/idp-set-root tailscale" in out, out
    calls = log.read_text()
    assert not [l for l in calls.splitlines() if "DELETE" in l], calls
    assert "tailscale-federated" not in json.load(open(vault)), (
        "nothing vaulted on a refusal"
    )
