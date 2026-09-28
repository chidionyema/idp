# Two hats — the build spec

Governed by decision 0021, "The founder wears two hats, and the platform never confuses them".
Six changes, in order, each its own pull request with its own fixture pair. Written to be
implemented without asking questions.

Founder instructions, verbatim:

> "that is basically the model we follow for the enterprise product shaping across platform so
> founder is both whole estate superadmin and also an enterprise customer 0"
> — `~/.claude/docs/founder/2026-09-05T1904Z-document-e37607fd.md`

> "actually are we confident or should we get a consultant to design this? not sure we have done
> enough research"
> — `~/.claude/docs/founder/2026-09-05T2025Z-ok-need-do-addrees-quicck-wwe-have-deepseek-29766295.md`

> "You aren't just building features; you are building the boundaries. ... Every time you build a
> new feature — whether it's the MCP, a new dashboard, or a GitOps pipeline — the architectural
> reflex has to be: *Is this an Estate capability that manages the platform, or a Tenant
> capability that uses it?*"
> — `~/.claude/docs/founder/2026-09-05T2124Z-got-it-zooming-out-entirely-you-re-talking-7347474b.md`

The answer to the consultant question, encoded here rather than argued: the shape is not the
unknown — a vendor-owned tenant beside a separate control-plane identity is what AWS, Stripe and
Auth0 all converge on, and nobody needs paying to redraw it. What is unknown is whether **our**
estate holds the line, and no consultant can measure that. So decision 0021's own diligence test
stops being prose and becomes the acceptance gate of change 6.

---

## Part 0 — what already holds. Do not rebuild any of it.

| Already true | Where |
|---|---|
| `TaskEnvelope.tenant_id` is required, immutable and threaded end to end | otto ingress → worker → memory |
| The gateway matches a binding by token fingerprint and stamps the envelope | `otto/ingress/store.py` |
| Spans and logs carry `tenant` as an attribute, omitted when empty | never a Resource attribute |
| Operator identity is OIDC on OCI with `founder_emails` | OCI identity domain |
| Customer identity is a Keycloak realm reached through the portal | `shop.yaml`, onboarding template |
| Money is outside the application | decision 0011, Lago |
| Secrets resolve by ExternalSecret from a namespaced vault path | decision 0017 |
| Both bots answer as themselves | hermes-v2 #85, shipped |

**One correction to decision 0021.** It says `bin/idp-estate-seed` gains the one-secret-one-tenant
refusal. That script mints estate-born credentials and never touches binding rows; the rows live
in the SQL of `platform/otto-gateway/binding-seed.yaml`. The refusal therefore lands in a new gate,
`bin/idp-tenant-split`, in the shape of `bin/idp-root-trust`: it reads the seed SQL, it grades it,
and it gets a row in `AGENTS.md` with two fixtures. Nothing else about the decision changes.

---

## Part 1 — the planes, and the reflex that has to be graded

The founder's table, restated as the estate's own layers. Every row is a boundary something
already crosses or is about to, and the point of the table is that **a capability belongs to
exactly one plane and declares which**.

| Layer | Control plane — the estate | Tenant plane — customer zero and every customer after |
|---|---|---|
| Identity and routing | OCI OIDC, `founder_emails`; may reach any tenant's rows, audited as operator access | Keycloak realm user; the gateway binds every request to one `tenant_id` and it is immutable |
| Agent compute | orchestration: health, scale, deploy a new tenant | workers running the customer's business logic inside that customer's namespace |
| State and storage | `estate-state`: the registry, cross-tenant telemetry, platform billing, global configuration | the tenant's own rows and memory, keyed by `tenant_id`, reachable no other way |
| Observability | SigNoz and Langfuse across the estate: cross-cluster health, total burn | a scoped view of that tenant's own agents, usage and traces |
| MCP tools | the estate MCP server: GitOps, pods, global limits | business tools: the tenant's own repositories, database, CRM |
| Secrets | every Operator- and Supplier-owned register row | the tenant's own Customer-owned rows, and only those (`docs/specs/key-ingest-door.md` part 4) |

The reflex the founder names cannot live in anyone's head, so change 5 makes it a field and a
gate: every catalog entity declares `estate/plane: control` or `estate/plane: tenant`, and an
entity that declares neither is refused. That is the whole mechanism — a question nobody can skip
because the catalogue will not build without an answer.

---

## Change 1 — the customer bot becomes a tenant of its own

File: `platform/otto-gateway/binding-seed.yaml`.

Today both rows are `'estate'`. The first row is the customer-facing Otto; the second, prefixed
`alerts-bot:`, is the operator's alerts bot. Change the first row's `tenant_id` to
`'customer-zero'` and leave the second `'estate'`.

The `ON CONFLICT ... DO UPDATE SET` clause already sets `tenant_id = excluded.tenant_id`, so the
existing row migrates on the next seed run with no manual SQL. That is deliberate and must not be
changed.

Accept when, against the live database:

```sql
SELECT tenant_id, external_id FROM channel_binding ORDER BY external_id;
-- customer-zero  <chat id>
-- estate         alerts-bot:<chat id>
```

and a message to the customer bot produces an envelope whose `tenant_id` is `customer-zero`,
quoted from a real worker log line (THE EMPIRICAL PROOF RULE).

## Change 2 — the gate that keeps them apart

New file `bin/idp-tenant-split`, Python, no network, in the shape of `bin/idp-root-trust`. It
parses the `INSERT INTO channel_binding ... VALUES` block of every `*.yaml` under
`platform/otto-gateway/` and grades three things:

1. **One secret, one tenant.** A `secret_ref` or `outbound_secret_ref` that appears under two
   different `tenant_id` values is a FAIL. Decision 0021 rule 4, and the check that would have
   caught the original merge.
2. **No operator identity on a customer allowlist.** A row whose `tenant_id` is not `estate` may
   not carry an operator principal in `principal_allowlist`. Rule 2.
3. **The estate tenant owns no customer-facing channel.** A row with `tenant_id = 'estate'` must
   carry the `alerts-bot:` external-id prefix, or another prefix listed in the gate's
   `OPERATOR_CHANNELS`. Rule 1.

Fixtures `tests/fixtures/tenant-split/bad.yaml` (one `secret_ref` under two tenants) and
`tests/fixtures/tenant-split/good.yaml`. New row in `AGENTS.md`:

```
| One credential is one tenant's; the operator's road never widens the customer's (decision 0021) | tenant_split_gate | tests/fixtures/tenant-split/bad.yaml | tests/fixtures/tenant-split/good.yaml |
```

with `tenant_split_gate` defined in `bin/idp-ci`. Accept when `bin/idp-ci` runs it and the two
fixtures grade differently in one run.

## Change 3 — Lago carries customer zero at zero

A Lago customer `customer-zero`, on the same plan a paying tenant would buy, priced at zero.
Usage metered from the customer bot lands on it; usage from the alerts bot lands nowhere, because
the operator is not billed. No code branches on the customer being ours — that is the point, and a
`if tenant == 'estate'` anywhere in the metering path is the defect this change exists to prevent.

Accept when a message to the customer bot produces a usage event on the `customer-zero` Lago
customer, read back from Lago's API, and a message to the alerts bot produces none.

## Change 4 — every customer drill signs in as customer zero

`drills/catalogue.yaml` gains, and every existing customer-facing drill moves to, the customer
road: portal sign-in through Keycloak as customer zero, not the operator's OCI identity. A drill
that reaches a customer surface under an operator identity fails.

Per LAW 53 a drill grades behaviour, never look and feel: sign in, pages answer, links work, the
bot replies. No selector, no test id, no layout word appears in any of them.

Accept when the drill rows are green in `bin/idp-verify` and a deliberately operator-identity run
of the same drill fails, proved in one run.

## Change 5 — every capability declares its plane

The founder's reflex, made unskippable.

- Every entity in `catalog/` gains the annotation `estate/plane: control | tenant`.
  `bin/catalog-gen` emits it; an entity without it is refused by `bin/catalog-refcheck`, in the
  same run that already proves every entity reference resolves.
- A `tenant`-plane workload may not hold a credential whose register Owner is `Operator` or
  `Supplier`, and may not name `estate-state` in any connection string or ConfigMap. The check is
  a function in `bin/idp-tenant-split`, so there is one gate for the boundary and not two.
- The estate MCP server's tools each carry the same field. A tool that reads across tenants is
  `control` and is refused to a tenant-plane caller; the refusal is proved by a fixture, not
  asserted in a docstring.

Fixtures `tests/fixtures/plane/bad.yaml` (a tenant-plane workload mounting an Operator-owned
secret) and `tests/fixtures/plane/good.yaml`, and a row in `AGENTS.md`. Accept when the two grade
differently in one run and `bin/catalog-refcheck` refuses an undeclared entity.

## Change 6 — the diligence test, executable

This is the change the consultant question actually asked for, and the only one that produces new
knowledge rather than new structure.

New drill `tenant-isolation`, row in `drills/catalogue.yaml`, owner `idp`, daily. Against a
restored copy of the production database in an ephemeral namespace — never production — it runs
decision 0021's own test in both directions:

1. Delete every row, span, memory and Lago record whose tenant is `customer-zero`. Then run the
   estate's own smoke: Flux reconciles, the alerts bot answers, `bin/idp-verify` is green. **The
   estate must be unchanged.** Anything that breaks is operator function that had been leaning on
   customer data, and it is a finding.
2. Restore, then remove every operator identity from the customer road: no `founder_emails`
   principal on any customer binding allowlist, no operator grant in the customer's Keycloak
   realm. Then message the customer bot as customer zero. **It must still answer.** Anything that
   breaks is a customer function that had been leaning on operator privilege, and it is the
   finding a buyer's engineer will find first.

`proves:` line for the catalogue row:

> Deleting the customer-zero tenant leaves the estate running, and removing every operator
> identity leaves customer zero served: the two roads are separable, measured, not asserted.

Accept when the drill has one green run and its output quotes both directions. Until then decision
0021's diligence test is an opinion, and this spec says so.

---

## Order, and why

1 before 2, because the gate must have a correct tree to grade. 2 before 3 and 4, because the gate
is what stops the split regressing while the slower changes land. 5 after 2 because it extends the
same gate rather than adding a second one. 6 last, because it grades all five. Each is one pull
request; none is large; none needs a decision that is not already made.
