# Golden Goose — Engineering Specification v1.0

**Status:** FINAL pending the three rulings in §9. Build starts when §9 lands.
**Source:** founder document `~/.claude/docs/founder/2026-09-02T0046Z-how-do-i-dotgatthe-golden-goose-architecture-pivotto-d531aefa.md`, verbatim, 2026-09-02T00:46Z.
**Scope:** the two pieces of the Golden Goose pivot that are not built. Piece 2, the lightweight decoupled edge, is delivered and is `platform/otto-golden/`; this spec does not touch it.
**Builder:** DeepSeek, one checkpoint at a time, in the order of §8.

---

## 1. What this is

Turning Otto from a bespoke installation into a product a business can buy. Today a new
tenant costs a founder a terminal, a BotFather conversation and a vault write. After this
spec, a tenant costs a sign-up form and sixty seconds.

Two pieces remain:

- **A. Zero-touch channel connect.** The client never sees a bot token.
- **B. `OttoTenant`, a declarative tenant API.** One object in, a running, routed, budgeted
  Otto out, with no manifest written by hand and no pipeline run by a person.

## 2. One correction to the founder document, and it changes piece A

The founder document says: *"You use Telegram's official OAuth flow… The API token is
securely generated and passed directly server-to-server."*

**Telegram has no OAuth flow that mints a bot token.** The Telegram Login Widget and Login
URL authenticate a *human* against a site and return a signed identity payload. They do not
create bots. Bot tokens come from BotFather and nowhere else. Any design that assumes
otherwise cannot be built.

The outcome the founder asked for is still reachable, by a different road, and it is a
better one:

> **The estate owns one bot. Tenants do not have bots.** A client connects by clicking
> "Connect Telegram", which opens `https://t.me/<EstateBot>?start=<signed-invite>`. Telegram's
> own deep link carries the invite to the bot, the bot binds that chat to the tenant, and no
> token exists on the client side at all.

This kills BotFather for the client completely, which is stronger than the original plan.
The Telegram Login Widget is still used, but for what it is actually for: proving who the
person clicking is, so the invite can be signed to them.

**The single-bot decision is a ruling, not a build choice.** It is §9 R1.

## 3. Piece A — zero-touch channel connect

### A.1 Actors and trust boundaries

| Actor | Trusted for | Never handles |
|---|---|---|
| Client's browser | Proving a human identity via the Telegram Login Widget | Any bot token, any vault path |
| Connect service | Signing invites, binding chats to tenants | Long-term secrets beyond its own signing key |
| Estate bot pod | Receiving `/start <invite>`, verifying the signature | Per-tenant credentials |
| Vault | The one estate bot token, the signing key | Anything client-supplied |

### A.2 The flow, end to end

1. Client signs in to the portal and lands on **Connect Telegram**.
2. Portal renders the Telegram Login Widget for the estate bot. The client clicks it.
3. Telegram posts back `{id, first_name, username, auth_date, hash}`. The connect service
   verifies `hash` as an HMAC-SHA256 over the sorted data string, keyed by the SHA256 of the
   bot token, and rejects any `auth_date` older than 300 seconds. This check is mandatory and
   is the whole of the security of the step.
4. Connect service mints an **invite**: a compact token carrying `tenant_id`, `telegram_user_id`,
   `exp` (10 minutes), signed with the estate signing key. Single use.
5. Portal redirects to `https://t.me/<EstateBot>?start=<invite>`.
6. Client presses Start. Telegram delivers `/start <invite>` to the estate bot's webhook.
7. Bot verifies the signature, the expiry, the single-use marker, and that
   `message.from.id` equals the `telegram_user_id` in the invite. On success it writes a
   **ChannelBinding** and replies with a confirmation naming the tenant.
8. Any later message from that chat is routed to that tenant. A message from an unbound chat
   gets one sentence telling the sender to connect through the portal, and nothing else.

### A.3 Data — most of which is already built, do not build it again

**`platform/otto-gateway/` already implements this.** It is a complete layer in git, with its
own Postgres, a seeded `channel_binding` table and a route of `/webhook/<channel>`, and it has
never been applied to the cluster because its Flux row carries `suspend: true`. Anyone
building piece A starts by reading that layer, not by designing a store.

The table as `platform/otto-gateway/binding-seed.yaml` declares it, primary key
`(channel, external_id)`:

| Column | Notes |
|---|---|
| `tenant_id` | Matches an `OttoTenant` name. |
| `channel` | `telegram` today. The column is why Slack costs a row, not a rewrite. |
| `external_id` | The chat as the channel knows it. |
| `secret_ref` | A pointer into the vault. Never the credential. |
| `token_fingerprint` | One-way. A dumped table leaks nothing. |
| `status` | Revocation is a write, never a delete. |
| `created_at` | When the chat was connected. |

Two additions this spec does need, and they are the only schema work:

- `bound_by`, the channel user id that redeemed the invite, so a binding can be attributed.
- An `invite` table holding `jti` and `redeemed_at` only, so replay is refused without the
  token itself ever being stored.

The same definition lives in `otto/ingress/store.py`, and
`tests/test_otto_gateway_manifests_are_releasable.py` is the control that stops the two
drifting. Any column added here is added in both places or that test fails, which is correct.

### A.4 Refusals, all of which are tested

- A login payload whose `hash` does not verify: rejected, no binding, one audit line.
- A login payload older than 300 seconds: rejected.
- An invite presented by a different Telegram user than the one it was signed to: rejected.
- An invite presented twice: rejected on the second.
- A message from an unbound chat: no tenant work is done, and no tenant is named in the reply.

### A.5 What this deletes

`docs/runbooks/otto-golden.md` currently has a section "Founder action — create the bot and
hand over its token", with BotFather and a Bitwarden write. When piece A lands, that section
is deleted and replaced with a link to the portal flow. A spec that leaves the manual runbook
standing has not finished.

## 4. Piece B — the `OttoTenant` API

### B.1 Build it as a Crossplane composite, not a Go operator

The estate does not need a bespoke controller to stamp out namespaced Kubernetes objects, and
a Go operator is a codebase somebody has to own forever. Crossplane's `CompositeResourceDefinition`
plus a `Composition` does exactly this job declaratively, is applied by the Flux the estate
already runs, and is a thing a buyer's engineer recognises on sight.

**The risk, stated plainly:** Crossplane is a control plane to install and keep upgraded, and
nothing in the estate uses it yet, so this adds a dependency for one API. It earns that only
because tenant provisioning will not be the last composed resource. If §9 R2 rules against
adding Crossplane, the fallback is `kro`, and the fallback after that is a Flux
`Kustomization` per tenant generated by the connect service, which works and is uglier.

### B.2 The API

`XOttoTenant` / `OttoTenant`, group `otto.mumchimp.com`, version `v1alpha1`, namespaced.

```yaml
apiVersion: otto.mumchimp.com/v1alpha1
kind: OttoTenant
metadata:
  name: acme
  namespace: tenants
spec:
  displayName: "Acme Ltd"
  plan: starter                    # starter | growth | enterprise; sets the quota block
  modelLane: kimi                  # a lane that exists in platform/llm/config.yaml
  channels:
    - type: telegram               # bindings arrive from piece A; this declares the channel is allowed
  retentionDays: 30
status:
  phase: Ready                     # Pending | Ready | Degraded
  url: https://acme.otto.mumchimp.com/healthz
  boundChats: 1
  conditions: [...]
```

`spec.quota` is deliberately absent. The plan sets the quota, so a tenant cannot ask for more
CPU than it pays for by editing its own object.

### B.3 What one `OttoTenant` composes

| Resource | Name | Notes |
|---|---|---|
| `Namespace` | `tenant-<name>` | Labelled `availability.idp/tier: tenant`, `otto.mumchimp.com/tenant: <name>` |
| `ResourceQuota` | `plan` | From `spec.plan`. Starter is the `otto-golden` request profile. |
| `Deployment` | `otto` | The `otto.boot` image, pinned by the same image policy that pins `otto-golden` |
| `Service`, `HTTPRoute` | `otto` | Host `<name>.otto.${ESTATE_ZONE}` |
| `ExternalSecret` | `otto-router-key` | The tenant's LiteLLM key, minted by code, never by a person |
| `NetworkPolicy` | `default-deny` plus egress to the router, the collector and Telegram | A tenant pod reaches no other tenant |
| `PodDisruptionBudget` | `otto` | Growth and enterprise only |
| Catalog entity | `tenant-<name>` | Emitted so the tenant appears in Backstage without a hand-written file |

### B.4 The sixty-second claim, and how it is measured

The founder document says "less than 60 seconds". That is the acceptance test, not a slogan:
from the `OttoTenant` object being created to its `status.phase` reading `Ready` with the
health endpoint returning 200. It is measured by a drill row, and the row fails if the median
of three creations exceeds 60 seconds.

## 5. Security

- The estate bot token lives in the vault, is mounted by the estate bot pod only, and is
  never in a tenant namespace.
- The invite signing key is separate from the bot token, rotatable without re-binding chats.
- Cross-tenant reachability is refused by NetworkPolicy and proved by a drill that tries it.
- Every binding, revocation and tenant creation writes an audit line carrying the actor.
- No admin path exists that binds a chat without a verified login payload. Not even for the
  founder, because that path is the one an attacker asks for.

## 6. Observability

Both pieces emit to the estate collector, per LAW 50: `otto_tenant_provision_seconds`,
`otto_channel_bindings_total{result}`, `otto_invite_rejections_total{reason}`, and traces on
the connect flow. Coverage is proved by querying the backend, never by reading the manifests.

## 7. What is explicitly out of scope

Billing, plan upgrades in flight, tenant self-service deletion, channels other than Telegram,
and any migration of the existing `otto-golden` pod into a tenant. `otto-golden` stays exactly
as it is and becomes tenant zero later, in its own change.

## 8. Build order

| CP | Deliverable | Done when |
|---|---|---|
| CP0 | Rulings in §9 answered and recorded | Three answers on the issue |
| CP1 | Login payload verification and invite minting, as a library with tests | The five refusals in §A.4 are tested and red without the code |
| CP2 | Connect service and portal button | A person binds a chat end to end on the estate bot, no token seen |
| CP3 | Wake `platform/otto-gateway`, add `bound_by` and the invite table, prove routing by binding and the unbound-chat refusal | A message from a bound chat reaches its tenant; unbound gets the one sentence. Waking the layer needs §9 R3, because it wakes with the event-bus row and costs 0.10 cores. |
| CP4 | XRD and Composition, one tenant provisioned by hand | `OttoTenant` created, pod answers on its host |
| CP5 | Connect service creates the `OttoTenant` on sign-up | Sign-up to answering bot with no human step |
| CP6 | Drill row, the 60-second measurement, and the runbook section deleted | Drill green three consecutive runs |

## 9. Rulings that gate the start

1. **R1, one bot or many.** One estate-owned bot with deep-link binding, as §2 argues, or a
   bot per tenant with the client still meeting BotFather. This spec assumes one bot.
2. **R2, Crossplane.** Approve adding Crossplane to the estate for the tenant API, or take
   the `kro` fallback, or the generated-Kustomization fallback.
3. **R3, capacity.** Two separate asks. Waking `platform/otto-gateway` costs 0.10 cores against
   a platform already asking 6.90 of the 6.9 the guard allows, and it wakes together with the
   suspended `event-bus` row. Each tenant after that costs roughly the `otto-golden` profile.
   Both need headroom bought or the budget raised.

---

## 10. What already exists, so it is not built twice

| Piece | State | Where |
|---|---|---|
| The door itself, one path per channel | Written, never applied | `platform/otto-gateway/` |
| `channel_binding` table and its seed row | Written | `platform/otto-gateway/binding-seed.yaml` |
| Per-tenant pod shape, quota, route, network policy | Written for one tenant | `platform/otto-golden/` is the reference profile |
| Model lane keys minted by code | Working | `platform/otto-golden/router-key.yaml` |
| Webhook self-repair every five minutes | Working | `platform/otto-golden/registration-reconciler.yaml` |
| Signed-invite connect flow | **Missing** | this spec, §3 |
| Tenant provisioning API | **Missing** | this spec, §4 |

The wiring of the three existing Otto layers is mapped in
`docs/explanation/the-three-ottos.md`. Read it before CP1.

---

Anything in this document that the build cannot satisfy is a defect in this document. Say so
on the issue rather than building around it.
