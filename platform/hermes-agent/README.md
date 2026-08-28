# hermes-agent (Otto)

Otto is the one pod holding the single Telegram poller lock (`gateway.yaml`, `replicas: 1`,
`strategy: Recreate`) and, since crew#516 CP5, the one that runs its shell tools on the founder's
Mac through `mac-run` (`mac-run.yaml`) over a Tailscale sidecar (`tailscale.yaml`) — never a key
of its own, never the container's own sandbox.

## How it reaches the Mac

- `tailscale.yaml`'s sidecar joins the tailnet using the same OAuth client that authenticates the
  in-cluster operator (`platform/tailscale/`); a Tailscale OAuth client secret is itself a valid
  device auth key, so no second credential is generated or held.
- `mac-run.yaml` is a ConfigMap mounted executable at `/usr/local/bin/mac-run` in the `gateway`
  container. It runs `ssh` through the sidecar's SOCKS5 proxy to `${FOUNDER_MAC_USER}@${FOUNDER_MAC_TS_IP}`
  — both Flux `postBuild` substitutions from `clusters/oke/estate-config.yaml` (LAW 46: those two
  values are never written as literals anywhere else in this repository).
- Authentication is Tailscale SSH: node identity, no keypair, no `authorized_keys`. The tailnet
  policy that allows it (`tag:k8s` → `tag:founder-mac`) lives in `platform/tailscale/policy.hujson`
  and is applied by `bin/idp-tailscale-policy`, run from CI (`oke-check`'s apply job).

## Founder hand, total: one

Two repository secrets, `SEED_TAILSCALE_OAUTH_CLIENT_ID` and `SEED_TAILSCALE_OAUTH_CLIENT_SECRET`,
carry the one Tailscale OAuth client this estate needs (scope `auth_keys` + `policy_file`, tag
`tag:k8s`) — the same seeding path every other provider key in this estate uses (Minimax,
Anthropic, R2, GitHub App: `.github/workflows/vault-seed.yml`, entry `tailscale-operator`). Fill
`FOUNDER_MAC_USER` and `FOUNDER_MAC_TS_IP` in `clusters/oke/estate-config.yaml`, and run
`tailscale up --ssh --advertise-tags=tag:founder-mac` on the Mac (`docs/founder/mac-remote-desk/README.md`).
Nothing else here needs a hand.

## Not done

- The gateway image (`ghcr.io/chidionyema/hermes-agent`, built from the separate `hermes-v2` repo)
  is not confirmed from this checkout to carry `ssh`/`nc` — `mac-run`'s two binaries.
- The "sleeping Mac" Telegram sentence (`docs/founder/otto-on-the-mac.md`) is application behaviour
  in `hermes-v2`, a separate repository; this row wires the transport, not the reply text.
