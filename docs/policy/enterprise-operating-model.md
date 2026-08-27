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

Gate: `rule=provisioning_complete` in `policy/operating_model.rego`. Proof: `bin/policy-test`
rows `opmodel-ok` (0) and `opmodel-half-provisioned` (1).

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
| `cost_budget` | a `platform/oci/` change with no `Cost-delta-usd-month:` line, or one above `estate-defaults.yaml` `infrastructure.monthly_cap_usd` | reduce the change, or raise the cap in its own approved PR |
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

## The operating model

| Before (friction) | After (enterprise) |
|---|---|
| "Sign in to OCI console and add a user" | tofu block or policy statement in a PR, OPA gate, `APPROVE: estate-tofu-role`, auto-apply |
| "Create a GitHub OAuth App" | OIDC client by Terraform in the estate identity domain (`platform/oci/identity`); GitHub has no API that creates OAuth Apps, so it is not the estate's IdP |
| "4/24 or 2/12 node pool?" | policy `auto-scale-when-free-full`: PR with the cost estimate, `APPROVE: scale` or `DENY: stay-free` (crew#289) |
| "Push or delete AwesomeProject?" | policy `stale-repo-auto-delete-after-7d` (estate-defaults.yaml `policy.stale_repos`): deletion staged, `APPROVE: delete` or `DENY: keep` |
| "Review mumchimp.com vs Medusa" | a recon agent posts the screenshot diff; `APPROVE: A` or `APPROVE: B` |

The approval word is optional in the PR body (`Approval-word:`) and is only a handle for his veto;
since 2026-08-27 (crew#473) nothing waits for `APPROVE:`. `STAGED:` handoffs (crew#281) keep their timer; the reply words are
`APPROVE: <word>` and `DENY: <word>`.

## Phase 0

Tracked on crew#286 with one checkbox per row; children crew#287 (estate-tofu role), crew#288
(OAuth clients by API), crew#289 (node pool policy). Landed with this file: the Rego gate, its
six fixtures, `bin/pr-report`, the CI job, and the `manage domains in tenancy` statement in
`bin/idp-oci-bootstrap`.
