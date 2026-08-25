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
