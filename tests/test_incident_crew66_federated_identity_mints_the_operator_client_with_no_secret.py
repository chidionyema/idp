"""crew#66 phase 1 (zero-human secrets): in GitHub Actions the Tailscale operator client is minted
from the runner's OIDC token (tailscale.com/kb/1581, /api/v2/oauth/token-exchange). No seed, no paste,
no secret anywhere but the vault entry the API answers with.

2026-08-29. The seed road (bin/idp-bootstrap-tailscale --seed) needed a console-made client pasted
into a laptop prompt; it never ran, the vault entry `tailscale-operator` never existed, and the
tailscale operator, the hermes-agent gateway and guacamole sat Failed on every apply run
(oke-check 33235976992: `could not get secret data`). A federated identity's client id is public,
lives in estate-config, and the exchange needs only the job's `id-token: write`.
"""

import json
import pathlib

from test_incident_crew66_tailscale_operator_client_is_minted_through_the_api import (
    _estate,
    _run,
)

IDP = pathlib.Path(__file__).resolve().parents[1]


def _federated(tmp_path, cid="kFED111111", oidc_ok=True):
    env, log, vault = _estate(tmp_path, seed=None)
    sh = pathlib.Path(env["IDP_VAULT_PUT"]).parent
    mint = '{"id":"kNEW987654","key":"tskey-client-new-1","keyType":"client","tags":["tag:k8s","tag:k8s-operator"]}'
    (sh / "curl").write_text(f'''#!/bin/bash
echo "$@" >> "{log}"
# `-K -` means the config (the credential pair) arrives on stdin; read it the way real curl does.
# Run 33461818477 (idp#1098): this stand-in exited without reading, the writer's printf took
# SIGPIPE, and under pipefail the verify step read "token exchange did not answer" on a green path.
for a in "$@"; do [ "$a" = -K ] && cat >/dev/null; done
# honour -o <file> and -w '%{{http_code}}' the way the federated exchange calls curl
out=/dev/stdout; code=""
args=("$@"); for i in "${{!args[@]}}"; do [ "${{args[$i]}}" = -o ] && out="${{args[$((i+1))]}}"; [ "${{args[$i]}}" = -w ] && code=200; done
body() {{ if [ "$out" = /dev/stdout ]; then cat; else cat > "$out"; printf '%s' "$code"; fi; }}
case "$*" in
  *oidc.test*) echo '{{"value":"{"eyJhbGciOi.jwt.sig" if oidc_ok else ""}"}}';;
  *token-exchange*) echo '{{"access_token":"at-fed","scope":"devices:core devices:core:read policy_file auth_keys oauth_keys users:read"}}' | body;;
  *oauth/token*) echo '{{"access_token":"at-new","scope":"auth_keys devices:core policy_file users:read"}}';;
  *tailnet/-/keys*) echo '{mint}';;
  *) echo '{{}}';;
esac
''')
    cfg = tmp_path / "estate-config.yaml"
    cfg.write_text(f'data:\n  TAILSCALE_FEDERATED_CLIENT_ID: "{cid}"\n')
    env.update(
        {
            "ESTATE_CONFIG": str(cfg),
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://oidc.test/token?api-version=2",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "runner-token",
        }
    )
    return env, log, vault


def test_crew66_in_actions_the_oidc_token_is_exchanged_and_the_client_minted_without_a_seed(
    tmp_path,
):
    env, log, vault = _federated(tmp_path)
    p = _run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    calls = log.read_text()
    assert "audience=api.tailscale.com/kFED111111" in calls
    ex = [l for l in calls.splitlines() if "token-exchange" in l][0]
    assert "client_id=kFED111111" in ex and "jwt=eyJhbGciOi.jwt.sig" in ex
    assert "tailnet/-/keys" in calls and "at-fed" in calls
    assert json.load(open(vault))["tailscale-operator"] == {
        "client_id": "kNEW987654",
        "client_secret": "tskey-client-new-1",
    }
    assert "federated" in p.stdout and "tskey" not in p.stdout


def test_crew66_no_oidc_token_fails_before_any_mint_and_writes_nothing(tmp_path):
    env, log, vault = _federated(tmp_path, oidc_ok=False)
    p = _run(env)
    assert p.returncode == 1 and "FAIL    federated" in p.stdout + p.stderr, (
        p.stdout + p.stderr
    )
    assert "tailnet/-/keys" not in log.read_text()
    assert "tailscale-operator" not in json.load(open(vault))


def test_crew66_outside_actions_with_an_identity_the_script_stops_and_never_falls_to_a_seed(
    tmp_path,
):
    # founder 2026-08-29: if federated fails the script stops; no secret-based fallback
    env, log, vault = _federated(tmp_path)
    for k in ("ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
        env.pop(k)
    p = _run(env)
    out = p.stdout + p.stderr
    assert (
        p.returncode == 1 and "FAIL    federated" in out and "only on the runner" in out
    ), out
    assert (
        "token-exchange" not in log.read_text() and "oauth/token" not in log.read_text()
    )


def test_crew66_the_apply_run_mints_the_operator_client_and_estate_config_names_the_identity():
    wf = (IDP / ".github/workflows/oke-check.yml").read_text()
    assert "bin/idp-bootstrap-tailscale" in wf and "TAILSCALE_FEDERATED_CLIENT_ID" in wf
    assert "id-token: write" in wf
    cfg = (IDP / "clusters/oke/estate-config.yaml").read_text()
    assert "TAILSCALE_FEDERATED_CLIENT_ID:" in cfg
