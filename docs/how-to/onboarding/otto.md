# Onboarding: Otto (crew#561)

## What it is

Otto is the founder's agent: the hermes-agent gateway pod on the cluster, the one process that
holds the Telegram bot token. It replaced the gateway that ran on the founder's Mac, and the rule
is parity: everything the Mac gateway could do, this pod can do, and a drill proves each part.

## Where it lives

```
platform/hermes-agent/gateway.yaml     the Deployment (one replica, Recreate: one Telegram poller at a time)
platform/hermes-agent/mac-run.tpl      the ssh wrapper that reaches the founder's Mac
platform/hermes-agent/estate.yaml      what the pod may call on the estate
platform/hermes-agent/kustomization.yaml   the image tag, rewritten by Flux image automation; never by hand
clusters/oke/estate-config.yaml        FOUNDER_MAC_USER / FOUNDER_MAC_TS_IP, the only two facts about the Mac
hermes-v2/                             the image: config.yaml, templates/skills/*, Dockerfile (gh cli baked in)
```

## What it is wired to

| Capability | Where it comes from | Proved by |
|---|---|---|
| Telegram | `TELEGRAM_BOT_TOKEN` in the vault entry `hermes-agent-env` | gateway banner in the pod log after boot |
| Models | the one router, `llm` row (`config.yaml` base_url + `LITELLM_API_KEY` from `hermes-agent-env`) | otto-parity `model-lane` |
| Memory | self-hosted Hindsight, `platform/hindsight`; `HINDSIGHT_API_URL` env, `config.yaml` memory.provider: hindsight | otto-parity `hindsight-answers` |
| GitHub | `gh` in the image; `GITHUB_TOKEN` field of `hermes-agent-env`, minted by the github-app lane (`platform/github-app/token-consumers.json`) | `gh auth status` from Telegram; parity step `gh-token-works` (crew#561) |
| The founder's Mac | `mac-run <cmd>`: ssh over the tailscale sidecar (tag:k8s -> tag:founder-mac port 22, `platform/tailscale/policy.hujson`), key in vault entry `hermes-mac-run`, public half adopted by `bin/idp-mac-adopt-otto` | otto-parity `key-usable`, `key-direct`, `tailnet-up`, `mac-run-hostname` |
| Agent-to-agent | `A2A_BEARER_TOKEN` in `hermes-agent-a2a` | otto-parity `a2a` |
| Cron lanes | the jobs file under HERMES_HOME, installed at boot by `hermes-v2/bin/install-cron.py` | otto-parity `cron-lanes-installed` |
| State | PVC `hermes-agent-data` at `/data` (HERMES_HOME): state.db, sessions, known_hosts | `no-restart-loop` |

Secrets are named here, never valued (R49). Every one is a vault entry synced by external-secrets;
`bin/idp-oke-break-glass architect-doctor` prints `Ready=True SecretSynced` per entry.

## How to prove Otto is whole

```
gh workflow run oke-check.yml -R chidionyema/idp -f mode=break-glass -f playbook=otto-parity
```

Every step in the run log reads `ok`. The founder's own proof is two Telegram messages:
`gh auth status` (answers his GitHub login) and `mac-run hostname` (answers the Mac's name).

## Known shape of failures

- A new image is a 4 to 5 minute outage: one replica, Recreate, the boot renders skills and
  installs cron lanes before Telegram connects. `gateway-ready` waits 60s and can read FAIL while
  the pod is still booting; `no-restart-loop` tells the two apart.
- `mac-run` exit 2: the key is not synced yet (oke-check apply mints it). Exit 255: ssh reached
  nothing (tailnet, ACL or the Mac asleep). Since idp#949 the wrapper copies nothing: it passes
  the mounted key to `ssh -i`, so a `cp: Permission denied` means the pod is serving an old script.
- A change to `mac-run.tpl` rolls the pod by itself: the ConfigMap comes from a
  `configMapGenerator`, so its name carries a content hash (idp#970). A `subPath` mount is never
  refreshed in place, and Reloader misses a change that lands in the same reconcile as its
  annotation. The story is in [Otto on the founder's Mac](../../explanation/otto-on-the-mac.md).
- Skills under `hermes-v2/skills/` are gitignored; a skill lives in `templates/skills/<name>/SKILL.md.tmpl`
  or it never reaches the image.

## Where it is tracked

crew#561 (parity), crew#516 (the move to the cluster), crew#524 (Hindsight), crew#562 (tailnet identity).
