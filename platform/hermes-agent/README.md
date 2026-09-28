# hermes-agent (Otto)

Otto is the one pod holding the single Telegram poller lock (`gateway.yaml`, `replicas: 1`,
`strategy: Recreate`) and, since crew#516 CP5, the one that runs its shell tools on the founder's
Mac through `mac-run` (`mac-run.tpl`) over a Tailscale sidecar (`tailscale.yaml`) — never the
container's own sandbox.

## How it reaches the Mac

- `tailscale.yaml`'s sidecar joins the tailnet with the operator OAuth client CI mints from the
  federated identity (`bin/idp-bootstrap-tailscale`, vault `tailscale-operator`); a Tailscale OAuth
  client secret is itself a valid device auth key, so no second tailnet credential exists.
- `mac-run.tpl` is a ConfigMap mounted executable at `/usr/local/bin/mac-run` in the `gateway`
  container. It runs `ssh` through the sidecar's SOCKS5 proxy to `${FOUNDER_MAC_USER}@${FOUNDER_MAC_TS_IP}`
  — both Flux `postBuild` substitutions from `clusters/oke/estate-config.yaml` (LAW 46).
- Authentication is an ed25519 key to macOS Remote Login (sshd). Tailscale SSH was the first
  design and was measured impossible on the founder's Mac: the App Store Tailscale build refuses
  `tailscale up --ssh` ("does not run in sandboxed Tailscale GUI builds", kb/1193), and the Mac is tagged `tag:founder-mac` (measured), so every rule names the tag. The key is minted on a CI
  runner by `bin/idp-bootstrap-macrun` into vault `hermes-mac-run`, reaches the pod through
  `mac-run-key.yaml` (ExternalSecret, decoded, mounted at `/run/secrets/hermes-agent-mac-run`), and
  its public half is authorised on the Mac by `bin/idp-mac-adopt-otto`, which reads it from the
  apply run's log. No value is shown, pasted or typed anywhere.
- The tailnet policy (`platform/tailscale/policy.hujson`, applied by `bin/idp-tailscale-policy` from
  CI) lets `tag:k8s` at the Mac on 22 (mac-run) and 5900 (Guacamole's VNC egress) and nothing
  else, and the founder's login at the Mac on every port.

## Founder hand, total: none (one command on the Mac, run by a session)

`FOUNDER_MAC_USER` and `FOUNDER_MAC_TS_IP` are measured on the Mac and already filled; the tailnet
login is read from the API; the key is born in CI. The only step that must run on the Mac itself is
`bin/idp-mac-adopt-otto`, and a session on the Mac runs it. The image (`ghcr.io/chidionyema/hermes-agent`,
built from `hermes-v2`) carries `ssh` and `nc`, mac-run's two binaries (hermes-v2 Dockerfile).

## Proof

`oke-check` mode `break-glass`, playbook `otto-parity` (`bin/idp-oke-break-glass`): gateway ready
and not restarting, key mounted, tailnet up, `mac-run hostname` answers with the Mac's name, the
memory service answers, the cron lanes are installed, and the model lane is printed. A red step is
the finding. This is the from-scratch proof; nothing here is claimed from a laptop.

## hermes-v2 is this workload

The product repository `chidionyema/hermes-v2` is the source: its Dockerfile and
`.github/workflows/build-agent-image.yml` push `ghcr.io/chidionyema/hermes-agent` on every merge
to its main, `platform/image-automation/hermes-agent.yaml` moves the tag in `kustomization.yaml`,
and the `hermes-agent` row in `clusters/oke/platform.yaml` is the one road it rides to OKE. The
catalogue holds it three ways: the platform layer `layer-hermes-agent`, the founder card
`founder-otto`, and the Hermes company domain `bin/catalog-gen` builds. Traces: model calls go
through the router (traced there, STANDARDS observability row) and the agent's own go to the
in-cluster Langfuse with keys from the vault (`langfuse-key.yaml`); logs and metrics ride the
SigNoz k8s-infra collector like every pod.

There is no `platform/hermes-v2/` and there must never be one: a second Deployment of one
Telegram poller on one token is 409s on both. The five-day audit of 2026-09-03 (section 5) listed
"onboard hermes-v2 onto the Flux road" as open; it was already this row, and
`tests/test_hermes_v2_rides_the_hermes_agent_row.py` now refuses a second row, another image,
a catalogue that forgets it, or a trace key typed into the env.
