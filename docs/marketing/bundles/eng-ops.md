# Engineering Operations Automation

> The bundle for any company whose platform team has 4 hours a week
> for this problem — Linear tickets turn into PRs, CI red turns into
> triage, research runs on a clock, all on the same identity plane as
> the workloads you ship.

## The story the buyer tells their board

> "Linear tickets turn into PRs without a person. CI red turns into
> triage without a person. Research runs on a clock without a person.
> The audit log is the platform's, not the vendor's."

That is Engineering Operations Automation. Five products, one bundle,
one story.

## What you get

The Engineering Operations Automation bundle is the Platform + Cyrus
+ Research Engine + Agent Workforce + Model Forge (CI flake triage),
configured as a single deployment. Every component is a product on its
own; together, they are the answer a buyer's CTO wants to hear when
the platform team is small and the backlog is large.

| Component | What it does | Why it is in the bundle |
|---|---|---|
| **The Platform** | The IDP substrate: catalogue, identity, edge, secrets, scheduling, supply chain, policy | The audit log is the platform's, not the vendor's |
| **Cyrus** | A Linear/GitHub agent that opens a worktree, runs an engine, opens a PR | A ticket that says "do this" turns into a PR that says "done" |
| **Research Engine** | A cronjob that runs recurring research jobs | Research is a clock, not a meeting |
| **Agent Workforce** | A crewAI cronjob with persistent memory | An agent that runs on your plane, with your identity, with your secrets |
| **Model Forge** | A tiny-model factory for narrow tasks | CI flake triage is one task; the pattern extends to commit-message classification, alert severity, test failure categorization |

## What the buyer sees

- **One queue.** Cyrus picks up Linear/GitHub issues; the buyer watches
  the queue. *Benefit: a ticket that says "do this" turns into a PR.*

- **One triage.** The Forge reads a red CI run's log tail and says
  "flake" or "real," abstains below 0.80 confidence. *Benefit: a red
  CI run is triaged in seconds, not in the next standup.*

- **One clock.** The Research Engine runs every Friday and writes a
  markdown file in the repo. *Benefit: research is a clock, not a
  meeting.*

- **One identity.** Every agent runs with SPIRE-issued workload
  identity, on the same OIDC plane as every human user. *Benefit: the
  audit log names the actor.*

- **One persistent memory.** A volume that outlives the pod — the same
  reason the Hermes agent keeps HERMES_HOME on one. *Benefit: a
  founder ruling ingested once is recalled on every run.*

- **No cluster verbs.** Agents do not deploy, do not delete, do not
  change policy. A read is free; a write needs approval. *Benefit: an
  agent that runs with you, not against you.*

## How it works

The bundle is the install wedge with Cyrus, the Research Engine, the
Agent Workforce, and the Forge's CI flake triage task enabled. The
buyer runs `idp/quickstart`, the installer enables the four agents.

Cyrus picks up Linear/GitHub issues and opens PRs. The Forge trains
the CI flake triage model and serves it through the Edge Runtime. The
Research Engine runs recurring jobs. The Agent Workforce runs the
queue.

Every action lands in the platform's collector. Every model call goes
through the LLM gateway, which carries the per-lane budget and the
spend breaker. Every cluster write requires approval — the agent
cannot deploy, cannot delete, cannot change policy.

## Why us

- **Self-hosted.** The whole stack is on the buyer's cluster, under
  the buyer's identity, with the buyer's secrets. There is no "Agent
  Workforce Cloud" to trust. *Benefit: governance is the platform's
  default.*

- **Cluster-aware.** The agents hold no cluster verbs. *Benefit: an
  agent that runs with you, not against you.*

- **The Forge is the engine.** CI flake triage is one task; the
  pattern extends. *Benefit: a buyer pays one training fee and gets a
  library of tasks.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $300/month, up to 1 worker | One tenant, Cyrus, the Research Engine, the Forge |
| Team | $3,000/month, up to 5 workers | Multi-tenant, the Agent Workforce, the spend breaker, Slack alerts |
| Enterprise | Contact us | Unlimited workers, custom tasks, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the bundle
  with one sample worker in 30 minutes. The drill runs hourly.
- **Read the specs.** `platform/cyrus/`, `platform/agent-workforce/`,
  `platform/research-engine/`, `docs/specs/2026-09-06-model-forge-edge-runtime.md`.
- **See it in action.** The estate runs the bundle; the receipts are
  in the collector.
- **Call us.** For the Enterprise tier, for a custom task, or for a
  procurement-grade security one-pager.

The agent is on your plane. The audit log is the receipt.
