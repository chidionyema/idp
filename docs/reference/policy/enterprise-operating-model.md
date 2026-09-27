# Estate-as-Platform: the enterprise operating model

Founder, 2026-08-26, verbatim (crew#286): "The founder is the approving authority, never the
implementing operator. Agents are platform engineers with scoped credentials. Every change is a
PR. Every approval is a structured message. Nothing touches a GUI."

This file is the law for how the estate is operated. Each standard below names the gate that
enforces it and the command that proves it, because a standard without a gate is a wish (LAW 44).

## The five standards

### 1. Zero-Click Provisioning (ZCP)

An agent that creates an identity provisions its role, secret and policy binding in the same PR.
If the agent lacks the privilege, it opens a privilege-elevation issue (the shape of crew#287:
measured refusal, root cause, the one statement that fixes it, the one command the founder runs
in his own session). It never sends "please sign in".

Incident: `bin/idp-oci-bootstrap` created `estate-tofu` without `manage domains in tenancy`; the
first identity-domain apply was a 401 and a console request (Telegram 14017).

Gate: `rule=provisioning_complete` in `policy/operating_model.rego`. Proof: `bin/idp-rules run --only operating-model-policy`, whose cases are
`opmodel-ok` (pass) and `opmodel-half-provisioned` (refuse).

### 2. Policy-as-Code Gate (PaC)

Every operational change (provisioning, deploy, config, secret rotation) passes an OPA gate before
merge. The gate runs in CI (`operating-model-gate` job, `bin/pr-report <n> --comment`) with the
same conftest that judges licences and job placement.

Rules, all in `policy/operating_model.rego`:

| rule | refuses | fix the message names |
|---|---|---|
| `provisioning_complete` | an identity resource with no grant, policy or membership in the PR | add the binding in this PR |
| `no_gui_actions` | an instruction line (`FOUNDER ACTION:`, `STAGED:`, `Use:`) with a console, click or browser step | a command, a Terraform block or an `APPROVE:` word |
| `founder_denied` | a PR whose declared `Approval-word:` the founder answered with `DENY: <word>` from his GitHub login | do not merge; address his reason in a new PR. No rule waits for `APPROVE:`: a green PR merges (founder, 2026-08-27: "approve all, no founder friction", crew#473) |
| `canary` | a `platform/oci/` change with no `canary` label | label it once the plan names its canary step |

Structured rejection: every deny line is `rule=<name> | <what is wrong> | fix: <what to change>`
and CI posts them as one PR comment. An agent repairs from the comment; the founder is not in
the loop.

### 3. Immutable Audit Trail (IAT)

Every agent action exists in two places or not at all: the git commit (what changed) and a
Langfuse trace tagged `crew#N` (why: the reasoning). This is the EU AI Act record and the due
diligence package. Gate: crew#286 CP6 (open): a session start that cannot reach Langfuse reports
BLIND, never proceeds silently.

### 4. Self-Service Catalog (SSC)

Backstage is the single pane of glass. Every service, URL, secret reference and agent is a
catalogued entity with links. The founder never asks "what is the URL?"; he opens the catalogue.
Gate: `estate-urls.py --missing` (hermes-v2#20) and the catalogue links row of `bin/idp-verify`;
an entity with no link fails the PR (crew#282 CP4).

### 5. Scoped Agent Identity (SAI)

Every agent session carries its own identity and role; no agent operates as the founder or with
his personal token. Roles: `platform-engineer` (writes Terraform, merges infra PRs),
`application-engineer` (writes product code, cannot touch identity), `founder-proxy` (read-only).
First step (crew#286 CP7): GitHub App tokens per lane replace the personal token in agent
credential stores. Target: SPIFFE SVIDs per session (`spiffe://estate.local/session/<id>`,
crew#227 CP4); a rogue session is revoked by rotating its SVID.

### 6. Headroom Is Guarded, Not Discovered (HGC)

Every resource class the platform can exhaust has a declared ceiling, a live count, and a gate
that refuses growth past it. A limit that is only discovered when it blocks a deploy is an
outage with a schedule.

Incident, measured 2026-09-18: OKE's `oke-resource-leak-protection` webhook refused every create
because the cluster held **2,650 Secrets against a 2,000 limit**. Thirty Flux objects went
NotReady -- Backstage, Crossplane, commerce, otto-gateway, prospector, via-negativa among them --
and nothing in the estate reported the count until Crossplane stopped deploying. The sprawl was
ordinary rather than stupid, which is the point: 2 declared Secret manifests, ~2,648 created
dynamically (Helm revisions, cert-manager renewals, ExternalSecret materialisations), with
`maxHistory` set on no HelmRelease and nothing pruning. (The field is `spec.maxHistory`;
the name `history-max` appears nowhere in the CRD, and an earlier draft of this standard
used it -- read the field, do not remember it.)

Three obligations, each with a gate:

1. **A ceiling is declared.** `platform/estate-defaults.yaml` carries the limit OKE enforces, so
the number is in the repo rather than in a vendor dashboard.
2. **The count is read and published.** A `secrets` row in `bin/idp-cluster-state`, rendered on
the portal's capacity tile. Absence of the row is FAIL, never clean -- the same rule the
`capacity` row already follows (crew#584).
3. **Growth is bounded at the source.** Every HelmRelease declares `spec.maxHistory: 3`; a release
without one is refused by the gate. Default 3 (the estate keeps three revisions, which is what
a rollback needs; ten is Helm's default and is pure sprawl at this fleet size).

Gate: `rule=secret_headroom` in `policy/operating_model.rego`. Proof: `bin/idp-rules run --only
operating-model-policy` with cases `hgc-ok` (count under ceiling, every release bounded) and
`hgc-over-ceiling` (refuse, naming the count and the ceiling).

### 7. One Click To A Device, Nothing By Hand (OCD)

A new device reaches production through **one browser sign-in**. Every step after it is
automatic, and no step requires a terminal, a vault read, or a second script.

**Production already satisfies this and must not be "fixed".** CI exchanges its GitHub OIDC
token for a one-hour OCI session and acts as `estate-ci`; no OCI API key exists on that path
(`oke-check.yml` header, crew#227 CP2). No standing keys. That is the enterprise pattern and it
is the reference for the laptop path below it.

Incident, measured 2026-09-18: the laptop path read the vault **before** authenticating, so
`idp-oci-login` rendered `~/.oci/config` from files that no longer exist (commit `76ba8be` moved
the estate's dev secrets into OCI Vault), and reading OCI Vault needs an OCI identity. Three
scripts each re-created the circle, and each one's only advice was another one that could not
help. `idp-oci-bootstrap` exited **100 with no output at all**.

**This is a bootstrap bug, not a security feature.** The trust root is correct and stays: one
key per device, mints `agent-reader`, dies on its own. What was wrong is the ORDER, and the
distinction the model draws is:

| | identity | needs |
|---|---|---|
| `oci session authenticate` | a browser login | a **region** and a **tenancy name** -- identifiers, public in every console URL |
| vault access | the secret store | an OCI identity, which is what the login just produced |

So the login must never be gated behind a vault read. It is not: `bin/idp-oci-session` takes the
identifiers from the environment, falls back to the vault only when readable, and otherwise says
exactly what to type. **Nothing on the path that matters reads a secret.**

The three obligations:

1. **The road is a line, not a circle.** `bin/idp-oci-session` -> `idp-cloud` ->
   `idp-mac-secret-deliver` -> agent key -> reads. Each step's only input is the previous one's
   output; no step's input is its own output.
2. **A script that cannot proceed says why, in one line, and exits non-zero.** Silence is the
defect (`idp-oci-bootstrap`, exit 100). A missing vault file and a decryption failure are
different facts and read differently.
3. **Renewal is none of the human's business.** The agent token lives one hour and
   `bin/idp-jit-device-renew` re-mints it on a ten-minute timer. There is deliberately no Renew
   button, because re-minting `agent-reader` is not a decision -- the broker's own words:
   "agent-reader holds reads and nothing else ... so there is nothing to approve."

The ONE action a human owns is putting the agent key on a device that has never had one. It is
offered as a portal button that opens the local handoff (`idp-device://`), never as a command.
Gate on that: `no_gui_actions` above already refuses a PR that instructs a browser step; this
standard adds the converse, that the founder's ONE browser action is not replaced by a terminal.

## The operating model

| Before (friction) | After (enterprise) |
|---|---|
| "Sign in to OCI console and add a user" | tofu block or policy statement in a PR, OPA gate, `APPROVE: estate-tofu-role`, auto-apply |
| "Create a GitHub OAuth App" | OIDC client by Terraform in the estate identity domain (`platform/oci/identity`); GitHub has no API that creates OAuth Apps, so it is not the estate's IdP |
| "4/24 or 2/12 node pool?" | policy `auto-scale-when-free-full`: PR with the cost estimate, `APPROVE: scale` or `DENY: stay-free` (crew#289) |
| "Push or delete AwesomeProject?" | policy `stale-repo-auto-delete-after-7d` (estate-defaults.yaml `policy.stale_repos`): deletion staged, `APPROVE: delete` or `DENY: keep` |
| "Review mumchimp.com vs Medusa" | a recon agent posts the screenshot diff; `APPROVE: A` or `APPROVE: B` |
| "Run `bin/idp-oci-login`, then `idp-mac-secret-deliver`, then `idp-jit identity`" | **one click** on the portal's Device access tile, then a browser sign-in; the agent runs the rest |
| "The cluster is refusing new resources?" | the capacity tile shows `2,650 / 2,000` before anything breaks; the platform prunes and the gate refuses unbounded growth |

The approval word is optional in the PR body (`Approval-word:`) and is only a handle for his veto;
since 2026-08-27 (crew#473) nothing waits for `APPROVE:`. `STAGED:` handoffs (crew#281) keep their timer; the reply words are
`APPROVE: <word>` and `DENY: <word>`.

## Phase 0

Tracked on crew#286 with one checkbox per row; children crew#287 (estate-tofu role), crew#288
(OAuth clients by API), crew#289 (node pool policy). Landed with this file: the Rego gate, its
six fixtures, `bin/pr-report`, the CI job, and the `manage domains in tenancy` statement in
`bin/idp-oci-bootstrap`.
