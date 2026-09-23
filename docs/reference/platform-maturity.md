# What is missing to be enterprise grade

Founder question, 2026-08-25: "what are we missing from platform engineering to be
bleeding edge enterprise grade".

**The answer in one sentence: not capabilities — enforcement, identity and
measurement.** Almost every layer a buyer asks about exists here as a script that
can prove something when a person runs it. A platform is graded on what it
*refuses* without being asked and what it *measures* without being asked, and on
those two axes this platform scores close to zero. Nothing on this machine
refuses a deploy, nobody has to log in to read the catalogue of every asset we
own, and no number anywhere says whether last week was better than the week
before.

Every row below is a command, run 2026-08-25 against `main` at `66b4e43`. Where a
row says MISSING it means the command found nothing, not that nobody has thought
about it.

## How the bar is set

Three published frames, so "enterprise grade" is somebody else's definition and
not ours:

- The [CNCF Platform Engineering Maturity Model](https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/)
  grades a platform on five dimensions: Investment, Adoption, **Interfaces**,
  **Operations**, **Measurement**. The last one is the one people skip.
- The [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
  fixes the capability vocabulary — catalog, golden paths, provisioning,
  delivery, observability, policy.
- For the AI half, the 2026 shape is an [agent control plane](https://preloop.ai/resources/ai-agent-control-plane-2026):
  a model gateway, an MCP/tool gateway, per-agent identity, human approval for
  sensitive actions, and one trace across all three. Microsoft shipped agent
  identity as a first-class construct this year rather than a reused service
  principal; that is the direction the whole category is moving.

## The scorecard

| Capability | The bar | Here today | Receipt | |
|---|---|---|---|---|
| Software catalog | Every asset, with an owner | 291 entities, regenerated from one inventory | `grep -c '^kind:' catalog/catalog-info.yaml` → 291 | LIVE |
| Docs as code | Rendered in the portal | TechDocs, this page included | `mkdocs.yml` | LIVE |
| Golden paths | A template per archetype, producing a repo already wired to CI, ownership and a catalogue entity | One template, and it does wire all three | `find . -name '*.yaml' \| xargs grep -l 'kind: Template'` → 1 | PARTIAL |
| **Portal identity** | **SSO, and a permission policy** | **`guest: {}` and `allow-all-policy`** | `app-config.yaml:171`, `packages/backend/src/index.ts:45` | **MISSING** |
| **Scorecards** | Automated production-readiness grade per component | Nothing grades the 291 | `grep -rl 'scorecard\|tech-insight'` → no matches | **MISSING** |
| **GitOps delivery** | Declared desired state, drift detection, rollback | `docker compose up` from a laptop | `grep -rli gitops` → one ADR, no manifests | **MISSING** |
| **Admission policy** | Kyverno refusing a workload that breaks the rules | No policy on any cluster; the cluster is not running | `k3d cluster list` → `estate 0/1` | **MISSING** |
| Supply chain, build side | SBOM, CVE scan, signature, licence policy | syft + grype + cosign + OPA, all in CI | `bin/supply-chain`, `.github/workflows/build-multiarch.yml:195` | LIVE |
| **Supply chain, deploy side** | The signature is *verified before the thing runs* | Signed and verified inside the same workflow that made it; nothing downstream checks | `grep -rli 'policy-controller\|ratify\|kyverno'` → prose only | **MISSING** |
| Workload identity | Short-lived SVIDs, no long-lived secret in a pod | SPIRE values and a proof target written | `platform/spire/values.yaml`, `make spire-proof` | UNPROVEN — cluster down |
| Secrets | One vault, env-segregated, nothing in argv | Ruled (sops+age directory vault); not built | crew `docs/STANDARDS.md`, Secrets row | IN PROGRESS |
| Agent traces | OpenTelemetry GenAI semconv, self-hosted | Langfuse live, plus a collector fallback that shares no runtime | `bin/langfuse-status`, `observability/otel-fallback.yaml` | LIVE |
| **Service observability** | Metrics and logs for the platform's own services, with dashboards | Traces only, for agents only | `ls observability/` → 3 files, none of them a metrics pipeline | **MISSING** |
| **SLOs and error budgets** | A target per user-facing surface, and a budget that gets spent | No target exists | `grep -rli 'error budget\|\bSLO\b' docs bin platform` → no matches | **MISSING** |
| **DORA / DevEx metrics** | Deploy frequency, lead time, change failure rate, MTTR | Not measured, and the tail is where the damage is: 25 of 26 pull requests merged in 1–24 minutes, the 26th took 3h50m and it was the one carrying the fix for the failing hourly job | `gh pr list --state merged --json createdAt,mergedAt` | **MISSING** |
| **Dead-man job monitoring** | An alert when a scheduled job *does not run* | Nothing. `ai.estate.idp` has failed for over a day through two different causes and told nobody either time | `launchctl list \| grep ai.estate.idp` → exit `3`, then `1` after the first cause was fixed | **MISSING** |
| **Backup and restore** | A restore drill on a schedule | No backup of the portal database, the vault or `~/.estate` | crew `docs/STANDARDS.md`, Backups row: "to adopt" | **MISSING** |
| Environments | dev / stage / prod, plus ephemeral preview envs | One, and it is `dev` | `cat ~/.estate/env` → `dev` | PARTIAL |
| Policy as code | Machine-checked rules over the estate | Licence and placement policy in rego, gated in CI | `policy/licences.rego`, `bin/policy-test` | LIVE |
| AI system register | Every system that calls a model, classified | Register, risk register, Annex IV technical file, gate | `bin/ai-act-gate`, `platform/ai/systems.yaml` | **AHEAD** |
| AI conformity evidence | Auditable, generated, not hand-written | `bin/conformity-report` renders Annex VI from the register | `bin/conformity-report` | **AHEAD** |

## The five that matter, in the order a buyer finds them

**1. Anybody who reaches the portal is an administrator.** The catalogue is a map
of every asset, repository, container and open port the estate owns, and it is
served with the guest provider and a permission policy called `allow-all`. This
is a ten-second grep in a diligence session and it is the finding that colours
everything after it. It is also the cheapest to fix and the only one on this
list that needs the founder: an OIDC provider has to be registered to somebody.
ADR 0003 already says identity is OIDC; the portal is the one surface that has
not implemented its own decision.

**2. Nothing refuses anything.** CI signs an image with cosign and verifies the
signature in the next step of the same workflow. That proves the signing worked.
It does not prove that an unsigned image cannot run, because nothing downstream
ever asks. There is no admission controller, no GitOps controller reconciling a
declared state, and the local cluster those would run on is stopped. Until one
component refuses a deploy, the supply-chain work is evidence rather than
control — good evidence, but a buyer's engineer knows the difference.

**3. Nothing measures.** Measurement is one of five dimensions in the CNCF model
and this platform scores zero on it: no SLO, no error budget, no DORA metric, no
scorecard over the 291 catalogued entities. The consequence is not a missing
dashboard, it is that no claim about the platform improving can be substantiated
— which is the same failure mode the estate already knows from the other side
(exit 0 is not proof of work).

**4. Nothing notices when a job does not run.** This estate's characteristic
failure is silence, not error. `ai.estate.idp` — the hourly portal refresh —
exited 3 for a day because `catalog-gen` refused to run, and after that was
fixed it exits 1 for a second, different reason. No alert fired for either; both
were found by reading `launchctl list` by hand. Reachability monitoring cannot
catch this at all, because the portal it would probe answers 200 throughout
(`curl -o /dev/null -w '%{http_code}' localhost:3100` → `200`, measured while the
job was failing). It needs a dead-man switch, which is the Healthchecks row
already on the standards page as "the estate's biggest gap".

**5. No restore has ever been performed.** The portal's Postgres volume, the
secrets vault and `~/.estate` have no backup and no drill. The `idp-up` script
contains a long comment explaining that losing `backstage/.env` bricks the stack
because the password and the volume are one pair — that comment is a description
of an unmitigated single point of data loss.

## Six: the queue is where the outage lived

This one was demonstrated rather than looked up, in the course of writing this
page. The hourly portal job had been failing for a day. The fix already existed:
pull request #22, "One catalogue: delete the second renderer", opened at 21:20,
CI green, mergeable, and untouched. Nobody was blocking it; nothing was watching
it either.

Measured over the last 26 merged pull requests on this repository, 25 went from
opened to merged in 1 to 24 minutes. #22 took 3 hours 50 minutes. The average
looks excellent and the average is not the thing that hurt — the tail is, and the
tail is invisible because nothing measures it. This is the same shape as gap 4:
the estate's failures are quiet, and every quiet failure here is a queue with no
timer on it.

Ten pull requests are open on this repository as this is written, five of them
more than three hours old. That is not a backlog problem, it is the missing half
of gap 3: a platform that does not measure its own flow cannot notice when its
own fix is stuck.

## Where this platform is actually ahead

Do not lose this in the gap list. The 2026 bleeding edge for platform
engineering is the AI control plane, and the part of it everyone is missing is
governance: not routing models, but being able to say which systems in the
estate call a model, what they are classified as under the EU AI Act, and
producing the evidence on demand rather than writing it during an audit.

That exists here and it is not common: `platform/ai/systems.yaml` is a register,
`bin/ai-act-gate` refuses a system with a missing Annex IV section or an overdue
review, `platform/ai/risk-register.yaml` carries an Art. 9 risk management system
kept voluntarily for every tier, and `bin/conformity-report` generates the Annex
VI assessment from those files instead of from somebody's memory. The piece in
flight joins it to the catalogue, so a component that calls a model and has no
AI Act classification fails a gate — which makes the register impossible to
quietly fall behind.

An acquirer buying an AI product in Europe in 2026 is buying that liability. A
platform that can answer it by command is worth more than one that cannot, and
this is the differentiator to widen rather than a compliance chore to finish.

## What this changes

Nothing on the MISSING list is exotic and none of it is a build. Each row has a
mature tool that the standards page has already picked or already names as a
candidate. The order above is the order to do them in, because it is the order a
buyer finds them in.

Row 1 is the only one that needs a founder decision — who the portal
authenticates against.

## The cheapest half of that list is already installed and switched off

The gaps above read as work. Some of them are not. Dagster and Backstage are
both mature platforms, and this estate runs each as a thin shell around the one
feature it was first reached for: Dagster as a cron replacement, Backstage as a
list of things. Two of the six gaps have their fix sitting in the venv and the
`package.json`, unused.

### Dagster: 41 schedules, 0 assets

| What it offers | Used here | Receipt |
|---|---|---|
| Assets — declare the artifact, get lineage, staleness and a graph | **No.** Every job is an `@op` that shells out and scrapes stdout | `grep -c '@asset' scheduler/estate_scheduler/definitions.py` → `0`; 19 `op`, 41 `schedule` |
| **Freshness policies** — an asset is red when it has not been produced in time | **No** | superseded freshness checks in 1.12; nothing declares one |
| Asset checks — pass/fail with severity, attached to the artifact | **No.** These checks exist, in `bin/idp-ci`, and only run in CI | `bin/idp-ci` is 350 lines of exactly this |
| Declarative Automation (`AutomationCondition`) — run when upstream changed | **No.** 41 fixed crons instead | `grep -c AutomationCondition` → `0` |
| **`dagster-pipes`** — the supported way to run an external script and get structured logs, metadata and materializations back | **No — and it is installed** | `pip list \| grep dagster-pipes` → `1.13.19`; `grep -c pipes definitions.py` → `0`; `grep -c subprocess.run` → `2` |
| Per-op `RetryPolicy` | **No.** One global `max_retries: 1` for a network fetch and a migration alike | `grep -c RetryPolicy definitions.py` → `0`; `scheduler/dagster.yaml:run_retries` |
| Partitions and backfills | Barely — 1 reference | daily audits are unpartitioned |
| `dagster-graphql` — the run history is queryable | **Installed, nothing queries it** | this is where DORA numbers come from |
| `run_status_sensor` | **Yes** — job chaining and a circuit breaker | `definitions.py:229` |

The one that matters most: **a freshness policy is the dead-man's switch that
gap 4 says is missing.** `ai.estate.idp` failed for a day and told nobody
because Dagster was asked "did this script exit 0" instead of "does
`catalog/catalog-info.yaml` exist and is it younger than an hour". The first
question cannot detect a job that never ran. The second cannot miss it.

`dagster-pipes` is the sharper embarrassment. It was installed, and then the
same job was hand-rolled with `subprocess.run` and `context.log.info(proc.stdout[-20000:])`.
That is LAW 43 inside our own dependency list.

### Backstage: 280 entities, 1 of them documented

| What it offers | Used here | Receipt |
|---|---|---|
| Software catalog | **Yes**, and well — 254 Resource, 26 Component, 5 System, 1 Domain, 233 `dependsOn` | `grep -c '^kind:' catalog/catalog-info.yaml` |
| TechDocs | **1 entity out of 280 carries a `techdocs-ref`** — the `idp` component | `grep -c 'backstage.io/techdocs-ref'` → `1` |
| `kind: API` + api-docs plugin | **Plugin installed, zero APIs registered** | `grep -c '^kind: API'` → `0`; `providesApis` → `0` |
| Scaffolder golden paths | **One template** | `backstage/templates/estate-component/` |
| Kubernetes plugin | **Installed front and back, renders nothing** — the cluster is `0/1` | `k3d cluster list` |
| **Notifications + Signals backend** | **Installed, nothing sends one** | `backend/src/index.ts:66-67`; no caller in `bin/`, `scheduler/`, `.github/` |
| `mcp-actions-backend` — the portal as an MCP server for agents | **Added, no client configured** | `index.ts:70`; only the vendor's own comments in `app-config.yaml` |
| Tech-Insights / Scorecards | **Not installed** — this is gap 3 | not in either `package.json` |
| Permission framework | **`allow-all-policy`** — gap 1 | `index.ts:44` |
| Catalog graph | Installed, and there is real graph data to draw | 233 `dependsOn` |

Same shape as Dagster. **The notifications backend is the missing alert channel
from gap 4, already running.** The portal has a notification system, the
scheduler has a run-status sensor, and the failing job told nobody — because the
two were never connected, not because either was absent.

### What to do about it, in one line each

1. Turn the six things `bin/idp-up` produces into Dagster **assets** with
   **freshness policies**. That is gap 4 closed with a feature we already pay
   for, and it makes "is the catalogue stale?" a probe instead of an opinion.
2. Move the `bin/idp-ci` checks that grade *artifacts* (not code) into **asset
   checks**, so they run against production and not only against a pull request.
3. Wire `run_status_sensor` failures into the **Backstage notifications
   backend**. One sender, and every gap-4 silence becomes a message.
4. Add `techdocs-ref` to the 26 Components. TechDocs is running for one entity.
5. Install **Tech Insights**, and make the first scorecard the six checks in
   this document. Gap 3 stops being "nothing measures".
6. Replace the `subprocess.run` op factory with **`dagster-pipes`**, which is
   already in the venv.

None of these is a build. Every one is switching on something bought.
