# Spend-bounded LLM Gateway

> A model router that cannot lose you money — per-lane budgets, a spend
> breaker, a trace on every call, and a router that picks the lane the
> budget can afford.

## The problem

You bought an LLM API. Then another. Then a third for the agents. The
spend on each one is a surprise at the end of the month. A lane priced
at $0.0000 per call can drain your budget in hours and the bill arrives
after the budget is gone. The trace is whatever the vendor happened to
log. The audit story is "we trust the vendor."

That is not a gateway. That is a tax.

The Spend-bounded LLM Gateway is the alternative. One router, per-lane
budgets, a spend breaker that trips before the bill surprises you, a
trace on every call, and a router that picks the lane the budget can
afford. The breaker's verdict is on the record; the trace is in your
collector; the spend is on your dashboard.

## What you get

- **One endpoint, any provider.** OpenAI, Anthropic, Google, DeepSeek,
  Kimi, local Ollama — all behind one URL. *Benefit: the buyer does not
  hardcode a vendor path that changes when the vendor changes.*

- **Per-lane budgets.** Each provider, each model, each tenant has a
  budget. The budget is on the proxy, not on the bill. *Benefit: a
  surprise is a number on a dashboard, not a number on an invoice.*

- **A spend breaker.** The breaker tripped once, on a $0/minimax row
  bug drained $0.00 over 6 hours. The breaker is now in
  `platform/llm/spend-breaker-digest.yaml`, rewritten 2026-09-04 — the
  original measured nothing and stopped nothing. *Benefit: a
  budget-draining bug is caught before the bill.*

- **A trace on every call.** Langfuse for the LLM trace, OTel as the
  fallback, SigNoz for the metrics. The buyer owns the collector.
  *Benefit: the auditor gets one log file, not nine.*

- **A cost-per-team view.** Every team's spend is a row on the
  dashboard. The cost is on the receipt. *Benefit: a finance team knows
  what engineering is buying.*

- **Fallbacks on the router.** When the primary lane answers 429, the
  router hops to the next lane. When all lanes are exhausted, the
  router fails open with an explicit verdict. *Benefit: a model outage
  is not a customer outage.*

## How it works

The gateway is LiteLLM with the platform's policy bundle. Every model is
a row in `platform/llm/config.base.yaml`; every row carries a price.
The breaker reads the Langfuse spend log on a clock; when a lane's
velocity exceeds its budget, the breaker refuses new calls.

The trace is OpenTelemetry — every call carries a span with the actor,
the model, the prompt, the cost. The span lands in the estate collector.

The router is on the same plane as the rest of the platform — same
identity, same secrets, same audit log. There is no second runtime.

## Why us

- **The breaker is on the proxy, not on the bill.** Most gateways tell
  you what you spent. Ours tells you what you cannot spend. *Benefit:
  the surprise is on the dashboard, not on the invoice.*

- **The trace is yours, not the vendor's.** Langfuse + OTel collector;
  the buyer owns the data. *Benefit: a vendor change is a router
  change, not a trace change.*

- **The original bug is on the record.** The spend breaker was broken
  in deployment; it measured $0.00 every five minutes and never once
  tripped. The fix is in; the receipt is in the spec
  (`platform/llm/spend-breaker-digest.yaml`). *Benefit: a buyer can
  read the fix, not the slide.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $50/month, up to 1M tokens | One tenant, the breaker, the trace, the cost dashboard |
| Team | $500/month, up to 100M tokens | Multi-tenant, per-team budgets, GitHub issue on trip, Slack alerts |
| Enterprise | Contact us | Unlimited tokens, custom lanes, SOC 2 conversation, dedicated support |

Token pricing is in addition to the platform fee; the platform fee
covers the gateway, the breaker, the trace, and the dashboard.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the gateway with
  one sample tenant in 30 minutes. The drill runs hourly.
- **Read the fix.** `platform/llm/spend-breaker-digest.yaml` is the
  rewritten breaker. The bug is on the record.
- **See it in action.** The estate's own LLM spend is on the dashboard.
  The drill runs hourly.
- **Call us.** For the Enterprise tier, for a custom lane, or for a
  procurement-grade security one-pager.

The gateway is one endpoint. The breaker is on the proxy. The trace is
yours.
