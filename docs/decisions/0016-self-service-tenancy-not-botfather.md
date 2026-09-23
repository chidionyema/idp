# Self-service tenancy: nobody ever touches BotFather, a vault command, or a manifest

Founder direction, 2026-09-02 (records:
`~/.claude/docs/founder/2026-09-02T0046Z-how-do-i-dotgatthe-golden-goose-architecture-pivotto-d531aefa.md`
and the two follow-ups the same night: "Time to Value" and "self service"). His words: if it
takes the creators two days to deploy a bot, a paying customer refunds in two hours. This
page is the plan he asked for; nothing past the baseline is built until he says the word.

## What he named, and the one answer to each

### 1. Kill BotFather for clients

The fact, from Telegram's own page ([core.telegram.org/api/bots](https://core.telegram.org/api/bots)):
Telegram has no OAuth flow that mints a bot token. What it does offer is managed bots:
"Users can create managed bots (which are controlled by a specific manager bot) directly
through the MTProto API, without interacting with @BotFather."

The answer: one platform-owned bot, shared by every tenant. A client clicks "Connect
Telegram" on the portal, which opens a `t.me/<our-bot>?start=<one-time-code>` link; pressing
Start binds their chat to their tenant row. No token ever exists on the client's side — not
in a terminal, not in a clipboard — which is stronger than the OAuth the pivot doc wished
for. A tenant who must have their own brand name on the bot is the second phase: the managed
bots road above, where our manager bot mints theirs server-to-server and seeds the vault
with no human in the loop.

### 2. The lightweight edge

Already half-true and finished cheaply: the `otto-staging` Flux row depends only on the
secret store, never on Dagster or Notify — the bot lane reconciles even while the data lane
is red. What remains is that our own reporting calls the whole cluster FAIL when any row is
red, so a healthy bot looks broken. The answer is per-lane health: the estate state document
keeps the cluster row and gains one row per product lane, so "Otto: measured OK" can stand
next to "Dagster: measured FAIL" without either lying.

### 3. A tenant in under a minute

Crossplane, not a hand-written operator (the law: never write a script for a problem a
proven platform already solves). An `OttoTenant` composite resource is a schema plus a
composition — namespace, quota, route with its header-match rule, vault-fed secret, pod —
all the manifests PR #1123 proved by hand become the template the composition stamps out.
Signing a tenant up is one object created by the portal's backend; no command line, no
agent, no founder hand. A bespoke operator is a second platform layer and gets deleted on
sight.

## The order of work

1. Land the baseline first (his own doc says so): PR #1123's lane green and deployed, the
   Dagster and Notify reds closed. A control plane stamped from a broken template scales
   the breakage.
2. Tenant binding on the shared bot: portal button, start-code, tenant table.
3. Per-lane health rows.
4. The `OttoTenant` composition, stamped from the proven otto-staging manifests.
5. Managed bots (brand-name tenants) last — the only step needing new Telegram surface.

## What this record is not

Not built, not started. It is the written plan the permission rule requires; the word that
starts step 2 onward is the founder's.
