# Founder self-service through Backstage: the field, 2026-08-28

Research note behind [ADR 0008](../decisions/0008-every-founder-action-is-a-portal-button.md); every claim carries its URL.

# Backstage full self-service for a non-technical founder — research note

## Findings

1. **`github:actions:dispatch` fires a real workflow, doesn't wait.** Template step takes `repoUrl`, `workflowId`, `branchOrTagName`, `workflowInputs`, `token`; it dispatches `workflow_dispatch` but discards the response — no run ID, no wait-for-completion (open feature requests #29727, #33104). A template must therefore poll the Actions API in a follow-up step (or via `http:backstage:request`) to find and link the run. https://roadie.io/backstage/scaffolder-actions/github-actions-dispatch/ · https://github.com/backstage/backstage/issues/29727 · https://github.com/backstage/backstage/issues/33104

2. **`http:backstage:request` calls any Backstage-proxied API using the *calling user's* token**, not the backend's — good for a "verify entity exists" or "call Slack/GitHub via proxy" step after `fetch:template`. https://roadie.io/backstage/scaffolder-actions/http-backstage-request/

3. **GitHub auth: token vs GitHub App**, set under `integrations.github` in `app-config.yaml`. A GitHub App gives higher rate limits, a clearer per-repo authorization model, and scoped permissions (e.g. `contents`, `pull_requests`, `actions: write`) instead of a broad PAT; the app's private key/credentials file is explicitly flagged "must not be committed" — feed it via a secret store, not the repo. https://backstage.io/docs/integrations/github/github-apps/ · https://backstage.io/docs/integrations/index

4. **Scaffolder secrets are the weak point.** By default actions cannot read host env vars (deliberate isolation); passing a GitHub token into a template step means either a per-user prompt or a custom action that pulls from Vault/ExternalSecrets/AWS Secrets Manager at request time — Backstage has no built-in JIT secret fetch (open RFC #32600). Rotating the GitHub App key means restarting/redeploying Backstage unless secrets are injected via a mounted Kubernetes Secret/ExternalSecret rather than env-at-boot. https://github.com/backstage/backstage/issues/32600 · https://danielwessendorf.com/workshops/confluent_self_service_with_backstage_and_terraform/06-building-a-custom-plugin-for-secret-handling/

5. **Permission framework gates parameters, steps and actions**, not just whole templates. Tag a parameter/step with `backstage:permissions`, then write a policy against `templateParameterReadPermission`/`templateStepReadPermission` (and action-level permissions) to hide/block by user or group — e.g. "only catalog owner of this entity can run the destroy step." Task-visibility policy can also restrict "see only your own runs" vs a grant to view all. https://backstage.io/docs/features/software-templates/authorizing-scaffolder-template-details/ · https://backstage.io/docs/features/software-templates/authorizing-parameters-steps-and-actions/

6. **Audit events are built in.** Scaffolder backend emits structured audit events (`execute` event grouped by eventId/subEventId) capturing task start/end; actions can read `ctx.user?.entity?.spec.profile?.email` to attribute a run to a person — this is the receipt for "who fired the button." https://backstage.io/docs/features/software-templates/audit-events/

7. **Kubernetes plugin is read-heavy; write actions (pod restart) aren't a stock button** — the plugin surfaces pod/deployment status; mutating actions go through custom scaffolder actions or kubectl-proxy calls, gated by the Backstage-side ServiceAccount's RBAC. **Flux plugin ships real day-2 buttons**: sync and suspend/resume reconciliation, explicitly gated — "requires additional permissions," and can be forced read-only (`readOnly: true`) by either disabling it in the Kubernetes proxy or scoping the ServiceAccount to read-only. **ArgoCD plugin is status-only** (shows sync state), no first-party sync/suspend button noted. https://github.com/backstage/community-plugins/blob/main/workspaces/flux/plugins/flux/README.md · https://roadie.io/backstage/plugins/argo-cd/

8. **Terraform from a template is a working pattern**, wiring `fetch:template` → `publish:github` → `github:actions:dispatch` against a `terraform-plan.yml`/`terraform-apply.yml` workflow that holds the actual `terraform`/`tofu` binary and cloud creds — Backstage never runs Terraform itself, it only triggers CI that does. https://www.cncf.io/blog/2024/01/29/creating-infra-using-backstage-templates-terraform-and-github-actions/

9. **Notifications + Signals close the loop.** `notification:send` scaffolder action (module `plugin-scaffolder-backend-module-notifications`) posts to a user or broadcasts after steps like `catalog:register`; the Signals plugin pushes it over WebSocket instantly instead of poll-refresh, landing on the Backstage notifications page. https://backstage.io/docs/notifications/ · https://roadie.io/backstage/scaffolder-actions/notification-send/

10. **What "self-service actions/golden paths" means across vendors**: Port lets you build a data model + scorecards + self-service actions via UI config instead of code (Backstage's build-it-yourself model, productized); Cortex is scorecards/maturity-grading only — explicitly *not* self-service execution or infra actions; Humanitec does infra provisioning via API, no portal. Common checklist across all: a catalog of named actions bound to an entity, an approval/permission gate per action, status/result rendered back on the entity page, and a scorecard showing template/golden-path adoption. https://encore.dev/articles/platform-engineering-tools · https://www.port.io/glossary/spotify-backstage

11. **CNCF maturity model has four rungs**: Provisional → Operational → Scalable → Optimizing, scored across investment, adoption, interfaces, operations, measurement — self-service maturity is explicitly one of the graded dimensions, not a binary. https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/

12. **Case-study evidence**: Spotify's own numbers — new-service creation went from ~14 days to <5 minutes via golden-path templates; adopters cited include Zalando, Expedia Group, Netflix, American Airlines. Also explicitly noted: Backstage templates alone don't cover day-2 actions (restart, request access, open incident) — those need the plugin ecosystem (Flux, K8s, PagerDuty, etc.) layered on top. https://roadie.io/blog/backstage-microservices-strategies/ · https://blog.container-solutions.com/how-developer-experience-portal-backstage-solved-spotifys-complexity

## What this estate should ship (priority order)

1. **A named "Deploy / Rollback" template per product** — `fetch:template` → `publish:github` → `github:actions:dispatch(workflowId: deploy.yml)`. Credential: GitHub App (not PAT) scoped `contents:read`, `actions:write`, `pull_requests:write` on the product repos only. Proven by: audit event `scaffolder.task.execute` showing founder's identity + linked Actions run URL fetched via `http:backstage:request` in a follow-up step.

2. **GitHub App, not PAT, as the platform's only GitHub identity**, key delivered to the Backstage pod via ExternalSecret from the estate's secret store, never baked into `app-config.yaml` or checked in. Proven by: `kubectl get externalsecret` + `grep -R token app-config.yaml` returning nothing.

3. **Permission policy: one action per catalog owner.** Tag every mutating step `backstage:permissions`, write the policy so a founder-facing "Restart / Redeploy / Rotate secret" button only fires for entities the founder (or platform team) owns. Proven by: attempt from a non-owner identity denied and logged.

4. **Flux plugin wired for sync/suspend**, ServiceAccount scoped to only the namespaces the founder's products run in (not cluster-admin). Proven by: `readOnly: false` only on that ServiceAccount's RBAC bindings, verified with `kubectl auth can-i --as=<sa>`.

5. **Kubernetes plugin in read-only mode** for pod/deployment status; pod-restart exposed only as a named scaffolder action calling a locked-down custom action, never raw kubectl from the frontend. Proven by: no `create`/`delete` verb in the Backstage K8s proxy RBAC.

6. **Terraform/OpenTofu apply as a template**, plan output posted back to the entity page via notification, apply gated behind a second approval step (permission-tagged). Proven by: PR containing `terraform plan` output attached before any `apply` job runs.

7. **Secret-rotation template** that calls a custom action hitting the estate's secret store API (ExternalSecrets refresh), never scaffolder env vars. Proven by: rotation timestamp visible in the secret store's own audit log, cross-checked against the scaffolder audit event.

8. **`notification:send` + Signals on every mutating template's last step**, so "your deploy finished" reaches the founder without a refresh. Proven by: WebSocket signal observed in browser dev tools / notifications page populated within seconds of run completion.

9. **Scaffolder audit events shipped to the estate's central collector** (LAW 50), not just Backstage's local log — every button press attributable and queryable centrally. Proven by: querying the collector backend for a `scaffolder.task.execute` row matching a just-run template.

10. **Entity-page scorecard** (adoption of golden paths / templates used vs manual work) so "self-service" has a measurable rung on the CNCF ladder, reviewed weekly. Proven by: scorecard value changing after a new template's first run.
