# The DeepSeek work order — one queue across three specs

Founder record, verbatim:
`~/.claude/docs/founder/2026-09-05T2132Z-so-review-all-and-lets-plan-this-for-87f5df34.md`
("so review all and lets plan this for deepseek"), and the six records the three specs cite.

Three specs landed the same evening — `zero-trust-boundary.md`, `two-hats-tenant-split.md`,
`key-ingest-door.md` — carrying seventeen changes between them. Read separately they compete for
the same files and the same night. This file is the single ordered queue across all three, and
for every item it says which lane runs it and what command proves it done.

---

## What DeepSeek may assume, and what it may not

DeepSeek is a second model working from this repository. It has the repository and it has
these specs. **It does not have the cluster, the vault, a founder identity, or any credential**,
and it must never be handed one: the cluster refuses writes from user principals altogether — Git
is the only writer, Flux applies. That constraint is a gift here, because it means the work that
matters is repository work.

So each item below carries one of three lanes:

| lane | means | proof it is done |
|---|---|---|
| **repo** | a change to files in this repository, provable by a command that runs offline | `bin/idp-ci` and the named test |
| **estate** | needs the live cluster, the vault, Lago or a real identity | a quoted production log line (THE EMPIRICAL PROOF RULE) |
| **founder** | a decision or a paste only he can make | his own words, recorded |

A **repo** item is a complete unit of work for DeepSeek. An **estate** item is not, and asking a
context-free model to claim one is how a synthetic probe ends up standing in for a fact.

## The five rules a change in this repository obeys

Any item below is finished the same way, and DeepSeek needs no other context to do it:

1. One item is one pull request. Branch from `main`.
2. A rule that can be broken gets a **gate**, and a gate gets a **fixture pair** — one file the
   gate must reject and one it must accept — plus a row in `AGENTS.md` naming both. A gate with
   one fixture proves nothing; both must grade differently in a single run.
3. The gate itself is a shell function or command in `bin/idp-ci`.
   A **drill** is not a gate: it is a scheduled workflow under `.github/workflows/` plus a row in
   `drills/catalogue.yaml` whose `schedule` is copied verbatim from that workflow's cron line.
   `bin/idp-verify` grades only the freshness of the last green run, so a row without a workflow
   is a drill that never fires. A drill needing the cluster runs as the service user `estate-ci`
   through the OIDC identity propagation `oke-check.yml` uses — the only identity excused from
   the cluster's Git-only-writer lockdown.
4. A generator is idempotent: two runs over one inventory produce byte-identical output.
5. No file names where a checkout, a home directory or a machine lives (LAW 46), and no test
   asserts on prose — a test grades behaviour or parsed structure, never sentences in a file
   (`prose_pin_scan`).

`bin/idp-ci` is the whole gate. If it is green and the fixture pair grades both ways, the item is
done as far as the repository can prove it.

---

## Before the queue: the fire, and the blocker

**THE FIRE (LAW 1, lane: estate).** Measured 2026-09-05T21:5xZ: the cluster's 154 NetworkPolicy
objects enforce nothing. Only `kube-flannel-ds` runs, flannel does not implement NetworkPolicy,
and a pod in the both-ways-fenced `dagster` namespace opened TCP to `1.1.1.1:443`, `8.8.8.8:53`
and to a pod in the equally fenced `backstage` namespace. All three connected. Evidence and
remedy: `docs/specs/zero-trust-boundary.md` step 1. Calico in policy-only mode beside flannel
turns every existing policy on at once and rewrites none — which is also the danger: those 154
policies have never been graded against real traffic, so enforcement goes on in log-only posture
first and the flows it would have denied are read before anything is dropped. Nothing else in this queue is worth its
own tests until that lands, because every isolation claim below currently rests on objects the
network ignores.

**THE BLOCKER (lane: founder).** The `deepseek` lane in this estate does not answer. `llm/config.yaml`
names `deepseek` in five fallback chains and defines no model row for it (`model_name` rows are
`minimax`, `minimax_m27`, `gemini`, `default`, `fast`, `ollama`, `ollama-vision`, `ollama-llama`);
the router pod carries no DeepSeek environment variable; and `https://api.deepseek.com/models`
answers `401 Unauthorized` with the material we hold. `platform/vendors/consoles.yaml` marks it
`console_lanes: [deepseek]`, so like Kimi it is console-owned and the key is brought through the
LiteLLM console, not through this file.

> **FOUNDER ACTION:** add the DeepSeek key at https://litellm.mumchimp.com → Models → the
> `deepseek` row, the same way the Kimi key was brought on 2026-09-04. Until then `[routing]
> default` and `cheap` in `AGENTS.md` both name a lane the router does not serve.

The queue below does not depend on that: it is written so a DeepSeek session anywhere can execute
it. The blocker only decides whether the estate's own bulk lane can.

---

## The queue

Order is a dependency order, not a priority order. Items at the same number are independent and
can run at once.

| # | item | spec | lane | done when |
|---|---|---|---|---|
| 0 | Calico policy-only beside flannel, **log-only first**: one day of would-be-denied flows collected, the allow rules those flows demand merged, and only then enforcement on | ZT step 1 | estate | the fence-enforcement drill (1) is green against the live cluster and no service lost traffic in the cutover |
| 1 | `fence-enforcement` drill: a scheduled workflow under `.github/workflows/` **and** its row in `drills/catalogue.yaml`. Reachability check first; fails closed when the probe could not run | ZT step 1 | repo | the workflow has one green run, the `drills` row of `bin/idp-verify` is fresh, and a denied path is graded denied while a probe that could not run is graded a failure |
| 2 | The customer bot's binding row moves `estate` → `customer-zero` in `platform/otto-gateway/binding-seed.yaml`; the `alerts-bot:` row stays `estate` | TH change 1 | repo | `SELECT tenant_id, external_id FROM channel_binding` returns the two tenants (estate), and a worker log line quotes `tenant_id=customer-zero` |
| 3 | `bin/idp-tenant-split`: one secret is one tenant; no operator principal on a customer allowlist; the estate tenant owns no customer-facing channel. Fixtures `tests/fixtures/tenant-split/{bad,good}.yaml`, row in `AGENTS.md`, `tenant_split_gate` in `bin/idp-ci` | TH change 2 | repo | `bin/idp-ci` grades the two fixtures differently in one run |
| 4 | `platform/vendors/stores.yaml`: one row per secret store, `write` and `sync` as separate capabilities, `estate-vault` the only `write: true` | KD part 3 | repo | `bin/idp-ci` parses it; a store with `write: false` cannot be selected as a target |
| 5 | `backstage/packages/backend/src/credentialIngest.ts` + registration in `index.ts`: `POST /api/credential-ingest/submit`, allow-list from the `Customer`-owned rows of `docs/reference/policy/root-trust.md`, response carries only an 8-character SHA-256 prefix | KD part 2 | repo | `yarn --cwd backstage test credentialIngest` proves the value is never logged, never returned, never in an error, and an entry outside the allow-list is a 400 |
| 5 | `estate/plane: control \| tenant` on every catalog entity: `bin/catalog-gen` emits it, `bin/catalog-refcheck` refuses an entity without it. Fixtures `tests/fixtures/plane/{bad,good}.yaml`, row in `AGENTS.md` | TH change 5 | repo | `bin/idp-ci` refuses an undeclared entity and accepts a declared one in one run; `bin/catalog-gen` still byte-identical over two runs |
| 6 | `backstage/templates/onboarding/activate-key/template.yaml`, hand-written, carrying the not-generated marker; `bin/idp-portal-buttons` skips any template carrying it, with a fixture pair | KD part 3 | repo | a `bin/idp-portal-buttons` run leaves the template untouched, proved by the fixture pair |
| 6 | OPA at `platform/authz/`, the two Rego rules, the bundle graded by `conftest` in `bin/idp-ci` with a fixture pair and an `AGENTS.md` row | ZT step 2 | repo | `conftest` accepts a same-tenant request and refuses a cross-tenant one in one run |
| 7 | Traefik `ForwardAuth` middleware on every tenant-visible route, pointed at the OPA service | ZT step 2 | estate | a real cross-tenant request answers 403 at the edge and the operator's same request is allowed and appears as operator access in the audit trail |
| 7 | The portal's OCI vault grant, narrowed to `Customer`-owned register entries and generated from the register; a `platform/verification/` wall proving a write to an `Operator`-owned entry is refused | KD part 4 | estate | the wall is red-then-green in one run, in the shape `verdict-key-wall.yaml` already uses |
| 8 | Traefik strips every client-supplied identity header at ingress and injects `x-verified-tenant` from the SPIFFE certificate SPIRE already issues | ZT step 3 | estate | a request carrying a forged `x-verified-tenant: estate` is rewritten, not honoured, and the attempt is logged |
| 8 | Remove every authorization branch from `estate_memory`'s recall path; it filters on the injected header alone | ZT step 3 | repo | no `is_founder`-shaped branch remains in the service, and the recall test passes with the header as its only input |
| 9 | Lago customer `customer-zero` on a real plan at zero price; metering carries no `if tenant == 'estate'` branch | TH change 3 | estate | a message to the customer bot produces a usage event on `customer-zero` read back from Lago's API, and the alerts bot produces none |
| 9 | Every customer-facing drill signs in through Keycloak as customer zero, not the operator's OCI identity. No selector, test id or layout word (LAW 53) | TH change 4 | repo | the drill workflows are green, their `drills/catalogue.yaml` rows are fresh in `bin/idp-verify`, and the same drill run under an operator identity fails |
| 10 | `bin/idp-tenant-new <name>` and `infrastructure/tenants/<name>/`: namespace, fence, SPIRE entry, quota, Lago customer, route registration — a tenant is a merged pull request and nothing else | ZT step 4 | repo | two runs byte-identical; a generated throwaway tenant directory passes `bin/idp-ci` |
| 11 | `tenant-isolation` drill, both directions: delete customer-zero and the estate is unchanged; remove every operator identity and customer zero is still served. Against a restored copy, never production | TH change 6 | repo + estate | one green run whose output quotes both directions — this is decision 0021's diligence test, and until it runs that test is an opinion |
| 12 | gVisor `RuntimeClass` and a Kyverno policy refusing a cell-namespace pod that does not name it or asks for `privileged: true`; default-deny egress on the cell with the gateway the one allowed route | ZT step 5 | repo | admission refuses the bad pod and admits the good one in one run |
| 12 | `conftest` over the tenant directories and a pod-security check, both inside the existing `bin/idp-ci` pass rather than a new pipeline | ZT step 6 | repo | a fence that allows internet egress fails; `privileged: true`, host networking, host path mounts and a missing runtime class in a cell namespace each fail |

Fourteen of the eighteen items are **repo**. That is the answer to the consultant question in its
practical form: almost all of this architecture is executable by a model with the repository and
no privileges at all, and the four items that are not are exactly the four where a synthetic probe
would have lied to us.

## What is deliberately not in this queue

- A CNI migration. Item 0 adds enforcement to the CNI that runs.
- An edge migration. Traefik ships `ForwardAuth`; items 6 and 7 are configuration plus one service.
- A second policy engine. Kyverno already runs; item 12 is one more policy on it.
- gVisor for every tenant. Item 12 is scoped to workloads that execute code a model wrote, which
  do not exist yet, and it is last for that reason.
- Any write that posts plaintext straight at a zero-knowledge store's REST API. Measured
  2026-09-05T22:08Z: that is refused with `400 Key is not a valid encrypted string`, while the same
  write through `bws` succeeds. Such a store is both a sync source and a valid destination, but only
  through its own client (decision 0020 amendment, re-measurable with
  `bin/idp-human-vault-probe --write`).
