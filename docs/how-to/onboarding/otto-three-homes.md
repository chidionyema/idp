# Onboarding: Otto's three homes

**Door (from the UI):** Backstage → **Create** → *Which home is Otto on?*. One button, no
parameters, and its verdict is a token Otto actually generated rather than a health check. You
never need a terminal to know which brain answered the founder. The button dispatches
`.github/workflows/otto-homes.yml`, which runs the `otto-homes` playbook of
`bin/idp-oke-break-glass`; the Backstage template is generated from that workflow's header by
`bin/idp-portal-buttons`, so the button and the check can never drift apart.

## Why this exists

Founder, 2026-09-09: *"otto must have 3 homes. Otto is founders personal assistant, has never
been stable even once. affirmative action, end of get it done"* and *"we must have the
alternative to litellm"*.

Record: `~/.claude/docs/founder/2026-09-09T2250Z-you-built-a-distributed-multi-agent-workforce-but-e6a3b096.md`,
`~/.claude/docs/founder/2026-09-09T2246Z-tells-litellm-if-anthropic-is-down-route-to-d96ca971.md`.

## The shape

```
Telegram ──> otto-gateway pod
               ├── gateway    (Otto himself; LITELLM_BASE_URL = http://127.0.0.1:4010/v1)
               ├── otto-brain (litellm, non-database image, loopback only)   <- the switch
               └── tailscale  (userspace; HTTP proxy on 127.0.0.1:1055)      <- the road home 3

  otto-brain's three upstreams, in order:
    home 1  http://litellm.llm.svc.cluster.local:4000/v1   the estate router
    home 2  https://api.minimax.io/v1                       direct, no cluster, no router
    home 3  http://${FOUNDER_MAC_TS_IP}:11434/v1            the founder's Mac, local silicon
```

## Where each thing lives

| thing | file |
|---|---|
| the three homes and their order | `platform/otto-gateway/three-homes.yaml` |
| home 2's key, and the pod's tailnet key | `platform/otto-gateway/three-homes-secrets.yaml` |
| the two sidecars, and Otto's one changed line | `platform/otto-gateway/deployment.yaml` |
| the Mac's tailnet address | `clusters/oke/estate-config.yaml`, `FOUNDER_MAC_TS_IP` |
| tag:k8s may reach the Mac on 11434 | `platform/tailscale/policy.hujson` |
| Ollama bound where the tunnel can reach it | `launchd/ai.estate.otto-home3.plist.tmpl` |
| the lane names Otto asks for | `platform/otto-gateway/router-lanes.yaml` |

## Changing the order

Edit the `fallbacks:` block of `platform/otto-gateway/three-homes.yaml` and open a pull
request. Reloader rolls the door on the change. Do not add a home whose lane cannot answer:
this estate has written the same sentence into `platform/llm/config.yaml` twice — *"a hop that
always refuses is latency, not redundancy"* — and a dead home costs a timeout on the one turn
that mattered.

## Adding a fourth home

Add a `model_list` row with its own `api_base`, and name it at the tail of each chain. Keep the
free lane last: `llm/config.yaml:166` records the rule — *"ollama is last because it is local
and cannot run out of credit"*.

## What this is not

It is not a second estate router. The estate keeps one router and home 1 is it: every
happy-path turn still walks `litellm.llm.svc`, still spends against the estate's budgets and
still lands in Langfuse. Homes 2 and 3 carry no policy and no ledger and are reached only when
home 1 could not answer. A lifeboat, not a fleet — and no other workload gets one, because no
other workload is the founder's assistant.

## If Otto goes quiet anyway

1. Which home answered last: the Backstage card above.
2. Is the switch itself up: the `otto-brain` container's own probe is
   `/health/liveliness` on `127.0.0.1:4010`, and it needs no upstream, so a red probe there is
   the sidecar and never a vendor.
3. Is home 3 reachable: `tailscale status` on the Mac should list `otto-pod`.
4. Is home 3 serving at all: `lsof -nP -iTCP:11434 -sTCP:LISTEN` on the Mac must show a
   listener on `*:11434`, not only on `127.0.0.1:11434`. Ollama.app runs its own server on
   loopback and that one is invisible to the tailnet; the launchd job is the one that matters,
   and the two coexist happily on the same port.
5. After editing the plist, reload it with `launchctl kickstart -k gui/$(id -u)/ai.estate.otto-home3`.
   `bootout` followed immediately by `bootstrap` returns `Bootstrap failed: 5: Input/output error`
   while the old job is still tearing down, and leaves home 3 loaded but not running — measured
   2026-09-10.
6. Cold versus warm, so a slow first answer is not read as an outage: measured on the founder's
   Mac 2026-09-10, a warm `qwen2.5-coder:7b` answered in 12.7s and a cold one took over 120s.
   The job sets `OLLAMA_KEEP_ALIVE=-1`, so that load is paid once after a reboot and never on
   the message he sends while the cluster is down.
