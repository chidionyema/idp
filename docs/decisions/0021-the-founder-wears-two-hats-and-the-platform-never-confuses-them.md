# 0021 — The founder wears two hats, and the platform never confuses them

- Status: DECIDED 2026-09-05 on the founder's instruction, recorded verbatim at
  `~/.claude/docs/founder/2026-09-05T1904Z-document-e37607fd.md`
- Deciders: founder
- Supersedes: nothing. Gives LAW 54 (the founder is enterprise client zero) its data model, and
  extends 0011 (money never enters the application) and 0020 (a key has a lifecycle the client
  chooses every road on).
- Affects: every tenant-keyed row and attribute in the estate: `channel_binding`, the
  TaskEnvelope, spans and log attributes, Lago customers, Keycloak realms, vault paths, the
  portal's onboarding template, and every drill that grades a customer-facing feature.

## The instruction

> "that is basically the model we follow for the enterprise product shaping across platform so
> founder is both whole estate superadmin and also an enterprise customer 0"

He said it while the two Telegram bots were being separated: the customer-facing Otto and the
estate alerts bot had been seeded as two rows of one tenant, `estate`, and the worker answered
every message through the first row's token. Both bots were the founder's, so nobody had asked
which hat was talking. That is the mistake with a shape: when the operator and the first customer
are the same person, the shortest code path merges them, and a buyer's engineer then finds a
platform with one tenant that happens to be its owner.

## The decision

**Two principals, two roads, one person.** The founder holds two identities that the platform
treats as strangers to each other:

| hat | identity | road | what it may touch |
|---|---|---|---|
| estate operator (superadmin) | OCI identity domain, OIDC, `founder_emails` | Flux, root-trust, `bin/idp-*`, the estate MCP server, alert bots | every namespace, every tenant's rows, in the open, audited |
| customer zero | a Keycloak realm user of tenant `customer-zero` | the portal, the onboarding template, the customer Otto, Lago | its own tenant's rows and nothing else |

Four rules follow, and each is a gate, not a wish:

1. **Customer zero is a tenant row, not a flag on the estate.** `channel_binding.tenant_id` for
   the customer Otto becomes `customer-zero`; the alerts bot stays `estate`. A TaskEnvelope
   minted for the customer bot carries `tenant_id = customer-zero`, and every span, log line and
   memory row it produces carries that attribute. The estate tenant never appears in a customer
   transaction, and a query for `tenant_id = customer-zero` returns a complete customer's history
   and nothing of the operator's.
2. **Superadmin is a grant on the operator road, never a widening of the customer road.** The
   founder reads every tenant through the estate MCP server and `bin/idp-kube` under his OCI
   identity, where it is audited as operator access. The customer Otto, the portal and Lago
   recognise him only as customer zero: `principal_allowlist` on a customer binding names a
   customer principal, and no allowlist ever carries an operator identity.
3. **Every customer-facing feature is graded on the customer-zero tenant.** A drill that signs
   in, pages, links, or messages a bot does so as customer zero (LAW 53, LAW 54). If a feature
   works only on the operator road, it is not built; if the founder needs a terminal, a repo
   secret or a fresh key to use it as a customer, that is the defect the drill files.
4. **The two hats never share a secret.** The customer Otto's token lives at the customer's vault
   path; the alerts bot's at the estate's. One secret referenced from two tenants is a merge of
   the roads and is refused by the seed (`bin/idp-estate-seed` rejects a `secret_ref` that
   appears under two `tenant_id`s).

Diligence test: a buyer's engineer must be able to delete tenant `customer-zero` and find the
estate running exactly as before, and delete every operator identity and find customer zero
still served. Either failing is the stitched design, and it is what gets deleted.

## What already holds

- Tenant identity is threaded end to end: `TaskEnvelope.tenant_id` is required and immutable;
  the gateway matches a binding by token fingerprint and stamps the envelope; spans and logs
  carry `tenant` as an attribute, omitted when empty.
- The operator identity is OIDC on OCI with `founder_emails`; the customer identity is a
  Keycloak realm (`shop.yaml`) reached through the portal's onboarding template, which opens a
  binding-request PR rather than writing a secret anywhere.
- Money is already outside the application (0011): Lago holds customers and usage; the estate
  meters usage by tenant attribute, so a `customer-zero` tenant is a Lago customer at a zero
  price, not a special case in code.
- Secrets are already split by provenance (0017) and resolved by ExternalSecret from a
  namespaced vault path, so the two-tenant rule is a path convention the seed can check, not a
  new store.

## What changes, in order

1. `platform/otto-gateway/binding-seed.yaml`: the customer bot row moves to
   `tenant_id = 'customer-zero'`; the seed gains the one-secret-one-tenant refusal.
2. `bin/idp-estate-seed`: the refusal, and a `must-fail` / `must-pass` fixture pair under
   `tests/fixtures/tenant-split/` with a row in `AGENTS.md`.
3. Lago: a `customer-zero` customer on the same plan a paying tenant would buy, priced at zero.
   Usage from the customer bot lands on it; usage from the alerts bot lands nowhere, because the
   operator is not billed.
4. Drills: every customer drill in `platform/drills/` signs in as customer zero; a drill that
   reaches a customer surface under an operator identity fails.
5. Portal: the onboarding template's tenant field is the customer's, never `estate`; the estate
   is not an option a customer can choose.

## Consequences

- The founder's own Telegram history splits: the customer bot's memory stays with customer zero,
  the alerts bot's with the estate. That is the point; a buyer sees a customer, not the owner.
- Langfuse stays one project (one estate org); tenancy there is the trace attribute, and a
  per-tenant project is not needed until a customer asks to read their own traces, at which point
  0020's rule applies: their road, their choice.
- Namespace fences stay per platform service, not per tenant. Tenancy is a row and an attribute,
  not a namespace; a tenant per namespace is the second scheduler in fence form.

## Rejected

- **A `superadmin` flag on the customer identity.** One login that is sometimes the operator is
  the exact merge the instruction forbids, and it is what a buyer's engineer finds first.
- **Keeping both bots under `estate` and routing by binding.** It answers as the right bot (that
  fix shipped, hermes-v2 #85) but leaves the customer's history inside the operator's tenant.
  Correct reply, wrong owner.
- **A tenant per namespace.** Rejected above: fences are per service, and a tenant is data.
