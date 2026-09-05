# Session memory is hosted and sold, never a store on a machine

Founder, 2026-09-05, on `claude-mem` being installed with its default local store: "no, need no
way"; "this is a feature we sell not sonething we hav on nachine".

`claude-mem` (MIT, thedotmack, v13.24.0) is a good capture mechanism: it watches a coding session
and writes observations without anyone remembering to. Its default runtime is the wrong tier — a
SQLite file and a localhost worker on one laptop, which dies with the machine, is invisible to every
other agent, and cannot be sold to anyone. Its own CLI already offers the right tier: `install
--runtime server --server-url <url>`, where the store is Postgres and Redis behind an API, and the
client keeps nothing.

## The shape

- **The store is the platform's, not a second one.** A database and a role on the one estate
  Postgres (`estate-rw.estate-db`), through `CLAUDE_MEM_SERVER_DATABASE_URL`. No new database
  platform; LAW: one Postgres in the estate.
- **The queue** uses `CLAUDE_MEM_REDIS_URL` against an estate Redis, not a Docker Compose Redis
  brought up beside a laptop.
- **The model calls go through the router.** The compression model is configured by an
  OpenAI-compatible base URL, key and model name, so it points at LiteLLM (`platform/llm`) and
  inherits per-lane budgets, fallbacks and Langfuse traces. No vendor key, no Anthropic key, no
  reseller.
- **One door, one identity.** The API sits behind the gateway with the estate's identity layer, the
  same as every other surface; a person losing access loses their agent's memory access with it.
- **Every client is thin.** His Mac, an engineer's IDE, a hosted agent session: all configured with
  `--runtime server --server-url`, storing nothing locally. This is the same rule as the context
  design: the laptop is one of the roads, never the place the data lives.

## Its relationship to Hindsight

Hindsight remains the estate's memory layer for agents that reason over the platform — Otto, crew,
k8sgpt — reached through the one MCP door with `remember` and `recall` (idp#1642). `claude-mem`
covers a different surface: what happened inside a coding session, captured passively. They are one
feature to a buyer ("your agents remember"), which is why this is a tier of the existing
`agent-memory` row rather than a new row, and why the two share the one Postgres. A second memory
*platform* would be stitching; a second capture surface on the same store is not.

## What has to be built

1. A container image. Upstream publishes an npm package and a Compose file, not an image, so the
   image is built in our CI from the pinned package version and carried by the estate's existing
   image automation.
2. `platform/claude-mem`: the Deployment, its database and role on estate-db, its ExternalSecret,
   its route behind the gateway, and the namespace fence.
3. The client side: the install command and the URL in the onboarding page, so a new engineer's
   session is hosted from the first run and never writes a local store.
4. The switch, which makes the `session-memory` tier of `agent-memory` selectable.

Until step 2 lands, the local install stays as a capture client only; nothing is built on its local
store and nothing reads it as though it were the estate's memory.
