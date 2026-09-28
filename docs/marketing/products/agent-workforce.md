# Agent Workforce + Research Engine

> Self-hosted engineering operations automation — Linear tickets turn
> into PRs, CI red turns into triage, research runs on a clock, all on
> the same identity plane as the workloads you ship.

## The problem

You want an agent that picks up Linear tickets and opens PRs. You want
an agent that reads a red CI run and says "flake" or "real." You want
a research job that runs every Friday and writes a markdown file in
your repo.

You do not want to give a vendor access to your repo and your cluster.
You do not want a chat box that talks to a model. You want the agent
on your plane, with your identity, with your secrets, with your audit
log.

The Agent Workforce + Research Engine is that, packaged. Cyrus picks up
Linear/GitHub issues and opens PRs. The Forge trains a CI flake
triage model. The Research Engine runs recurring jobs. The whole
stack is on your cluster, under your identity, with your audit log.

## What you get

- **Cyrus: tickets to PRs.** A Linear/GitHub agent that opens a
  worktree, runs an engine, and opens a PR. *Benefit: a ticket that
  says "do this" turns into a PR that says "done."*

- **The Forge: CI flake triage.** A small model reads the failed
  step's log tail and says "flake" or "real," abstains below 0.80
  confidence. *Benefit: a red CI run is triaged in seconds, not in
  the next standup.*

- **The Research Engine: recurring research.** A cronjob that runs on
  a clock, pulls from the sources, writes the result to a volume.
  *Benefit: research is a clock, not a meeting.*

- **Cluster-aware, identity-aware.** Every agent runs with SPIRE-issued
  workload identity, on the same OIDC plane as every human user.
  *Benefit: the audit log names the actor.*

- **Persistent memory.** A volume that outlives the pod — the same
  reason the Hermes agent keeps HERMES_HOME on one. *Benefit: a
  founder ruling ingested once is recalled on every run.*

- **No cluster verbs.** Agents do not deploy, do not delete, do not
  change policy. A read is free; a write needs approval. *Benefit: an
  agent that runs with you, not against you.*

- **Audit at the door.** Every action lands in the collector with the
  actor, the tool, the cost, the verdict. *Benefit: the auditor gets
  one log file, not nine.*

## How it works

The Agent Workforce is a crewAI cronjob with a persistent volume. The
job reads the queue, plans an action, executes the action, and writes
the receipt. The Forge trains the small models; the Research Engine
runs the periodic jobs.

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
  pattern extends to commit-message classification, alert severity,
  test failure categorization. *Benefit: a buyer pays one training fee
  and gets a library of tasks.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $100/month, up to 1 worker | One tenant, Cyrus, the Research Engine, the audit log |
| Team | $1,000/month, up to 5 workers | Multi-tenant, the Forge integration, the spend breaker, Slack alerts |
| Enterprise | Contact us | Unlimited workers, custom tasks, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Agent
  Workforce with one sample worker in 30 minutes. The drill runs
  hourly.
- **Read the spec.** `platform/agent-workforce/` is the cronjob.
  `docs/specs/otto-five-capabilities-finished.md` is the Otto
  capability list.
- **See it in action.** The estate's own Agent Workforce runs the
  research engine. The receipts are in the collector.
- **Call us.** For the Enterprise tier, for a custom task, or for a
  procurement-grade security one-pager.

The agent is on your plane. The audit log is the receipt.
