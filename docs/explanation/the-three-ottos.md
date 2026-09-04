# The three Ottos, and how they connect

Measured against the running cluster on 2026-09-03 between 20:20 and 20:45 UTC. Nothing here
is read from documentation; every state below came from a probe.

One container image, `ghcr.io/chidionyema/hermes-agent`, tag `main-65-3c2b68b9`. Three
commands. Three different jobs. Two are running and the third has never been switched on.

| Layer | Command | State |
|---|---|---|
| `hermes-agent-gateway` | `python -m hermes` | Running, and blind |
| `otto-golden` | `python -m otto.boot` | Live |
| `otto-gateway` | `python -m otto.ingress` | Written, parked, never applied |

## How a message reaches each one

All three share the host `otto.${ESTATE_ZONE}`, which is `otto.mumchimp.com`. What separates
them is the path, and each path belongs to exactly one of them.

```
                        Telegram
                    (two bots, two webhooks)
                            |
                            v
                 Edge, one host: otto.mumchimp.com
                            |
        +-------------------+-------------------+
        |                   |                   :
        v                   v                   v  (never applied)
 hermes-agent-gateway   otto-golden         otto-gateway
 @Ottototbot            @numun_bot          any channel
 1 replica              2 replicas          2 replicas
 50 GiB memory volume   /telegram-webhook   /webhook/<channel>
        |                                       :
        v                                       v
 estate query server:                   own Postgres,
 NO ADDRESS                             channel_binding table
 so it wakes up not                     one row per connected chat
 knowing the estate
```

Solid lines carry traffic today. The dotted path exists in the repository and has never
reached the cluster.

## The three in detail

### hermes-agent-gateway, the Otto you already talk to

Namespace `hermes-agent`. One replica, replaced rather than doubled, because only one process
may hold the Telegram lock. It has run seven days without a restart and holds the 50 GiB
memory volume at `/data`. It has emitted 21,876 traces.

Its Telegram side is healthy. The webhook is registered, nothing is queued, and Telegram
reports no delivery errors.

**Its one fault:** its live configuration file, rewritten fresh on this morning's boot,
contains no entry for the estate's query server. It holds the credential for that server but
not its address. So it starts up unable to look anything up about the estate, and the two red
rows in its parity drill are both this single fault. The server itself is running with two
healthy pods in the `mcp` namespace. Only the address is missing. Ticket crew#736 CP2.

### otto-golden, the next Otto

Namespace `otto-golden`. Two replicas. Bot `@numun_bot`. Health path answering 200. Its
allowlist holds exactly one chat, labelled founder. Its model lane is kimi, with the router
key minted by code rather than by a person.

A job runs every five minutes and re-registers its Telegram webhook, so a door that goes
quiet repairs itself rather than waiting for somebody to notice.

It runs alongside the old Otto deliberately, so it can be proved before it replaces anything.

### otto-gateway, the universal door

Namespace `otto-gateway`, which does not exist on the cluster yet. Two replicas. Its own
Postgres in the same layer. Paths `/webhook/<channel>`, one per channel, so carrying a channel
this estate has never carried before does not require a new route.

Its premise is the important part: **connecting a new customer channel is a database write,
not a deployment.** It carries a `channel_binding` table, seeded with one row for the estate's
own operator chat so the first message has somewhere to land.

| Column | Holds |
|---|---|
| `tenant_id` | which customer this chat belongs to |
| `channel` | telegram today, and the column is why Slack costs a row rather than a rewrite |
| `external_id` | the chat as the channel knows it |
| `secret_ref` | a pointer into the vault, never the credential |
| `token_fingerprint` | a one-way fingerprint, so a dumped table leaks nothing |
| `status` | revoking a chat is a write, never a delete |
| `created_at` | when the chat was connected |

The pod holds no channel credential itself, only that fingerprint.

## Why the door is off

It was parked deliberately, and the file that parks it gives two reasons. Neither is a fault,
and both are still true.

1. **The message bus it publishes into is parked too.** The estate refuses to run a workload
   nobody reads, so a bus with no publisher stays off. This door is that publisher, which
   means the two wake together or neither does.
2. **The processor budget has no room.** The running platform asks for 6.90 of the 6.9 cores
   the guard allows. This layer wants 0.10 more. A parked layer is not charged, so switching
   it on is a spending decision, and that one is the founder's.

The cutover is small: turn this row and the bus row on in the same change, and account for the
extra tenth of a core. Everything else is already written.

## What this means for the Golden Goose spec

A large part of what `docs/specs/golden-goose-SPEC-v1.md` proposed building already exists
here, written and reviewed, waiting behind an off switch. The binding store and the routing of
a message to its tenant are done. What is genuinely missing is the step in front of them: a
customer clicking a button and a signed invitation binding their chat, with nobody typing a
token. The spec has been corrected so nobody builds this table twice.

## What holds the three together

| Shared thing | How it binds them |
|---|---|
| one image | all three run the same image and differ only by command |
| one update rule | a single automation bumps all three tags on every build, because two automations on one branch collide |
| one host | `otto.mumchimp.com`, split by path so no two claim the same one |
| one vault | every credential is pulled from the estate store, none written by hand |
| one model router | keys minted by code, lanes declared in the platform config |

---

Sources: the platform manifests on `main`, parity drill run 33800019287, and direct probes of
the `hermes-agent`, `otto-golden`, `otto-gateway` and `mcp` namespaces.
