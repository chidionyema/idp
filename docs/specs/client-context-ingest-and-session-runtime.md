# Client context ingest, and where an agent session runs

Founder, 2026-09-05, on finding that the estate snapshot only reached agents through a hook on his
laptop: "no this has failed too nany tines and we need to naybe think again, first of all having it
run nac is silly, it should be a product featire for enterprose custoners"; "bility to ingest client
info should be featire and properly desiged and awareness of contsraint s na dworkaornuds etc";
"personal aget sessions dont run on nc book eithwe"; "infact these laptop bound agents ... not sure
it can be the only option".

This document is the design those four sentences ask for. It replaces the mechanism that failed:
`estate-state-relay.py`, a SessionStart hook that read one machine's `~/.claude.json`, held a bearer
key in a client config file, and delivered context to exactly one laptop. That shape cannot be sold,
and it did not work — no entry was ever written, so every session on that machine started blind and
nothing noticed for days.

## What the customer is buying

An agent that starts a session already knowing the customer's platform: what is running, what the
customer's constraints are, and which oddities are deliberate. Without it the agent re-derives the
estate every session, proposes changes the customer's constraints forbid, and "fixes" workarounds
that are there on purpose.

## What already exists, and is not to be rebuilt

- **The one door.** Agentgateway in front of the estate MCP server (`platform/mcp`), reached at
  `mcp.<estate zone>`; ADR 0006 fixes one MCP server and forbids a second.
- **Estate state.** `.github/workflows/estate-state.yml` publishes a structured snapshot every 15
  minutes; `mcp/plugins/estate_state.py` serves it as `get_estate_state` with a staleness window.
- **Inventory, workload state and logs.** Three more plugins on the same door.
- **Durable memory.** Hindsight on the one estate Postgres, with `remember` and `recall` on the door
  (idp#1642).
- **The catalogue.** Backstage holds services, systems and owners.
- **Identity.** OIDC at the gateway (decisions 0003 and 0007); no surface ships its own login.

The gap is not the store and not the door. It is that only one kind of context exists (ours,
machine-generated), and that delivery depended on a per-machine client registration.

## The design

### 1. Four kinds of context, one shape

Every context item carries `kind`, `source`, `generated_at`, `expires_at` and `confidence`, so an
agent is told what is stale instead of being handed old data silently.

| kind | what it holds | where it comes from |
|---|---|---|
| `estate` | what is running, and what is red | generated, every 15 minutes |
| `catalog` | services, systems, owners | Backstage |
| `constraint` | what the agent may not do: change windows, regions, budget ceilings, compliance boundaries, do-not-touch workloads | declared by the customer |
| `workaround` | why something is deliberately odd, who decided it, when it should be revisited | declared by the customer |

`constraint` and `workaround` are the new ones, and they are what makes the feature about the
client rather than about us. An expired workaround surfaces as a review item rather than
disappearing, so the register does not rot into folklore.

### 2. Several roads in, because a customer's information already lives somewhere

Not one ingest path. The customer picks any combination:

- **Declared in their platform repository** — YAML under `context/`, validated in their pipeline.
  The road for a customer who wants review and history on every constraint.
- **Pushed to the context API** on the same door, authenticated the same way. The road for a
  customer whose source of truth is a service, not a repository.
- **Pulled from a system they already run** — the catalogue, a change-management or wiki source —
  through a reader that normalises into the same four kinds. Readers are additive; the platform
  ships the catalogue reader and the interface, never a single mandated source.

### 3. Delivery, without a hook on anybody's machine

The door serves context as MCP resources as well as tools, so a compliant client picks it up on
connect with no client-side script. Two runtimes, and neither is the only option:

- **Platform-hosted sessions.** The agent session runs as a workload on the platform and is reached
  from any device, through the channels that already exist (the Universal Event Gateway, Telegram,
  the portal, a native app). Nothing depends on a particular laptop being awake, and the session's
  identity is a workload identity rather than a key in a file. This is the enterprise default.
- **The engineer's own client.** Claude Code, an IDE, or any MCP-capable tool on a workstation,
  pointed at the same door and authenticated by the same identity layer. Supported on purpose: a
  customer's engineers will not all give up their local tools, and vendor-neutrality is the point.

Both roads read exactly the same context through exactly the same door. Neither carries a bearer
key in a hand-edited client config: the workstation road authenticates through the identity layer,
so revoking a person revokes their agent.

### 4. Provenance and refusal

An agent must be able to say where a claim came from. Every context item is attributable to its
source and its age; a constraint that cannot be read is a refusal to proceed on that action, not a
silent omission. The failure this design exists to prevent is a quiet green: the previous mechanism
reported BLIND correctly and no one was watching, so the platform-hosted road treats a session that
cannot read context as an alert, not a log line.

## Build order

1. The context schema and the four kinds, with validation and the `expires_at` review path.
2. The git road and the catalogue reader, served as MCP resources on the existing door.
3. The context API road, on the same authentication.
4. The platform-hosted session runtime, and the alert when a session starts without context.
5. The feature rows made selectable (they ship as `status: planned` until their switch exists).

## What this deletes

`estate-state-relay.py` and its SessionStart hook, and the per-machine `mcpServers` registration
that keeps it alive, once step 2 lands. Until then the registration stays only so this estate's own
sessions are not blind; it is not part of the product and nothing new is built on it.
