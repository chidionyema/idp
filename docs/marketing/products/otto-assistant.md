# Otto Assistant

> A personal agent that runs your platform from a chat — Telegram in, PR or
> run out, with five capabilities that hold a conversation, see a photo, hear
> a voice, and tell you the verdict.

## The problem

You run a platform. The platform has a state, a clock, a spend, a queue, and
a list of things that are red right now. You want to ask "what's broken?"
and get an answer. You want to say "open a PR for that" and have it land.
You want to send a photo of a printout and have the assistant tell you
what is on it.

Most platforms give you a dashboard. Some give you an API. The ones that
give you an agent give you a chat box that talks to a model and does not
touch the system you are running. Otto is the agent that does touch the
system you are running — your platform, your repos, your cluster — because
Otto is on the same identity, the same secrets, the same audit log as the
workloads you ship.

Otto lives where you live: a Telegram chat, a phone, the portal. From any
of those surfaces, Otto can act.

## What you get

- **Five capabilities, one assistant.** Voice replies (text-to-speech), voice
  messages (speech-to-text), vision (a photo becomes a description),
  screenshot handler (a screen becomes a story), bench (the agent's own
  metrics). *Benefit: the assistant meets you where you are — keyboard,
  microphone, camera.*

- **Cluster-aware, identity-aware.** Otto runs with a SPIRE-issued workload
  identity, on the same OIDC plane as every human user. When Otto opens a PR,
  the PR carries Otto's identity in the audit log. *Benefit: you know who
  did what, and what "did" means.*

- **Spend-bounded.** Every model call Otto makes goes through the LLM gateway,
  which carries the per-lane budget and the spend breaker. *Benefit: an
  assistant loop cannot drain your budget; the breaker trips before the bill
  surprises you.*

- **Cross-session memory.** Otto remembers across sessions. The Hindsight API
  is the persistence layer; the gateway is the same door every request walks
  through. *Benefit: yesterday's question is today's context.*

- **One chat, any channel.** Telegram is the founder's surface; the same
  agent binds to Slack, Discord, or the portal's chat. *Benefit: the
  surface a buyer already lives in is the surface Otto lives in.*

- **Governed by the same policy as the platform.** Otto asks only for the
  unundoable (decision 0024). A read is free; a write needs the founder's
  approval. The audit log carries every action, with the same receipts the
  collector expects. *Benefit: Otto does not become the new shadow IT.*

## How it works

Otto has three layers:

1. **The channel binding.** A Telegram bot (or a Slack app, or a webhook)
  receives a message, stamps an envelope, and hands it to the gateway.
  The binding knows who sent the message and which tenant it belongs to.

2. **The Sovereign Bus.** The gateway routes the envelope to the engine,
  which plans the action. The plan may be a read (cheap), a write (needs
  approval), or a tool call (audited). The Sovereign Bus is the door
  every request walks through.

3. **The engine.** The engine runs the plan against the platform: the LLM
  gateway, the MCP gateway, the catalogue, the cluster. Five capabilities
  (TTS, STT, vision, screenshot, bench) sit beside the engine as tools
  the agent calls.

The stack is the same one a buyer's platform runs on — same identity, same
secrets, same audit log. There is no second runtime.

## Why us

- **Self-hosted.** Otto runs in your cluster, under your identity, with your
  secrets. There is no "Otto Cloud" to trust; there is Otto on the same
  plane as your workloads.
- **Cluster-aware.** Otto holds no cluster verbs (decision 0024 — agents
  do not deploy, do not delete, do not change policy). Otto asks for
  approval on anything that is unundoable. *Benefit: an agent that runs
  with you, not against you.*
- **Five capabilities, all built.** Per the spec, the pieces are all there
  (Edge-TTS voice replies, faster-whisper STT, vision via Gemini, screenshot
  handler, bench). The finish line is the live log line. *Benefit: when a
  capability is "built but not proved," we tell you, instead of pretending.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $30/month | One channel binding, the five capabilities, the LLM gateway, the trace |
| Team | $300/month, up to 5 channels | Multi-channel, Hindsight memory, the audit log, GitHub issue creation |
| Enterprise | Contact us | SOC 2 conversation, custom capabilities, dedicated support, on-prem binary |

The Enterprise tier is required for any binding that touches a buyer's
production cluster.

## Get started

- **Run the install wedge.** `idp/quickstart` spins up Otto with a Telegram
  binding in 30 minutes. `/start`, then any question.
- **Read the spec.** `docs/specs/otto-five-capabilities-finished.md` is the
  canonical capability list. `docs/specs/otto-door-hands-and-senses.md` is
  the design.
- **See it in action.** The estate's own Otto answers the founder from his
  phone. The drill runs hourly. The receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom channel, or for a
  procurement-grade security one-pager.

Otto is the agent that lives where you live.
