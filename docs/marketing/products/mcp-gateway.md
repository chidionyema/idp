# MCP Gateway

> One policed door for every tool an agent can reach — identity, policy,
> budget, audit, all on the same plane.

## The problem

You rolled out agents. The agents need tools. The tools live behind MCP
servers. The MCP servers live behind whatever auth each one happened to
ship with. The audit log is whatever each server happened to log. The
budget is whatever the bill says at the end of the month.

That is not governance. That is a tax on the security team.

The MCP Gateway is one door. Every tool an agent can reach goes through
it. The door carries identity (SPIRE), policy (Kyverno/Rego), a budget
(the LLM gateway's spend breaker), and an audit log (the collector). One
place to govern what an agent can do; one place to read the receipts.

## What you get

- **One door, identity-aware.** SPIRE-issued workload identity for every
  MCP server; OIDC for every human who touches the gateway. *Benefit:
  the audit log names the actor, not "the agent."*

- **Policy at the door.** Kyverno admission for the namespace; Rego for
  the tool list. A tool a tenant does not own is not reachable by that
  tenant's agent. *Benefit: one tenant cannot see another's tools.*

- **Budget at the door.** Every MCP call costs tokens or cycles. The
  spend breaker trips when the budget trips. *Benefit: an agent loop
  cannot drain the budget.*

- **Audit at the door.** Every call lands in the collector. The trace
  carries the actor, the tool, the cost, the verdict. *Benefit: the
  auditor gets one log file, not nine.*

- **The Sovereign Bus.** MCP calls are not point-to-point; they ride a
  bus that the platform owns. The bus is the door. *Benefit: when you
  add a tool, you add it to the bus, not to every agent.*

- **Multi-tenant by construction.** The two-hats pattern (decision 0021)
  is the platform's default: a tenant's MCP namespace is reachable no
  other way. *Benefit: the operator can reach any tenant's rows for
  support; a tenant's agent cannot.*

## How it works

The MCP Gateway is the agentgateway + the estate MCP server + the
Sovereign Bus. The bus is the door; every MCP call walks through it.

A tenant brings its MCP servers. The Gateway assigns each one a
SPIRE-issued identity, namespaces it, and stamps the audit log when the
agent calls it. The policy bundle the tenant signs once is the gate.

The platform's MCP servers (GitOps, pods, global limits) live in the
control plane. The tenant's MCP servers (the tenant's repo, database,
CRM) live in the tenant's namespace. The Gateway is the door between.

## Why us

- **Governance, not just an OAuth proxy.** Permit.io ships an OAuth
  proxy. Our door carries identity + policy + budget + audit on the
  same plane as the rest of the platform. *Benefit: governance is the
  platform's default, not an add-on.*

- **Multi-tenant by construction.** The two-hats pattern is on the
  record (decision 0021). *Benefit: a tenant cannot reach another
  tenant's tools, by gate, not by convention.*

- **Spend-bounded.** The same spend breaker that protects the LLM
  gateway protects the MCP gateway. *Benefit: an MCP loop cannot drain
  the budget.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $25/month, up to 5 agents | Single tenant, the door, the audit log, the spend breaker |
| Team | $250/month, up to 25 agents | Multi-tenant, the policy bundle, GitHub issue creation, Slack alerts |
| Enterprise | Contact us | Unlimited tenants, custom policy, SOC 2 conversation, dedicated support |

The Enterprise tier is required for any tenant with regulated workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the MCP gateway
  with one sample tenant in 30 minutes. The drill runs hourly.
- **Read the design.** `docs/explanation/architecture-overview.md` has
  the agent interface layer. `docs/specs/two-hats-tenant-split.md` is the
  multi-tenant boundary.
- **See it in action.** The estate's Otto rides the bus. The collector
  holds the receipts.
- **Call us.** For the Enterprise tier, for a custom policy, or for a
  procurement-grade security one-pager.

The MCP Gateway is one door. Every tool an agent can reach walks
through it.
