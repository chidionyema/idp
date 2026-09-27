# Complete Scripts Index

**Total scripts: 300** | **Last updated:** 2026-09-22 (removed the ten deleted drill scripts)

## Hooks (Active)

| Hook | Script | Timeout | Purpose |
|------|--------|---------|---------|
| SessionStart | `bin/idp-session-bootstrap` | 120s | Initialize session environment |
| Stop | `bin/idp-reasoning-gateway-hook` | 30s | Grade session with reasoning gateway |

---

## IDP Core (205 scripts)

Core platform functionality, administration, and operational commands.

| Script | Purpose |
|--------|---------|
| `idp` | Main CLI entry point |
| `idp-apply` | Apply configurations to this host (crew#186 CP5, R22 mechanism 5) |
| `idp-audit-read` | Reads newline-delimited stream of Kyverno audit events |
| `idp-automerge-stuck` | Check and resolve stuck automerge conditions |
| `idp-autoscaler-seed` | Configure node pool for Cluster Autoscaler management (crew#539 CP4) |
| `idp-blast-grade` | Grade blast radius of changes |
| `idp-bootstrap-cloudflare` | Root trust for Cloudflare, one command (crew#66) |
| `idp-bootstrap-estate` | Estate's root trust bootstrap (crew#66) |
| `idp-bootstrap-macrun` | Otto's key to founder's Mac, one command (crew#66) |
| `idp-bootstrap-sunshine` | Root trust for Sunshine admin credential (crew#66) |
| `idp-bootstrap-tailscale` | Root trust for Tailscale, one command (crew#66) |
| `idp-bootstrap-vendors` | Root trust for all vendor credentials, one command (crew#66) |
| `idp-branch-archive` | Archive branches |
| `idp-budget` | Check and manage budget allocation |
| `idp-calico-deny-log` | Manage Calico deny logs |
| `idp-catalog-push` | Publish catalog/catalog-info.yaml to cluster as OCI artifact |
| `idp-catalogue-drift` | Detect catalogue drift |
| `idp-checkout-drift` | Detect checkout drift |
| `idp-ci` | Offline gate - runs with no secrets or DK dependencies |
| `idp-circuit-breaker` | Circuit breaker logic |
| `idp-clean-tree` | Clean working tree |
| `idp-clickhouse-system-log-ttl` | Manage ClickHouse system log TTL |
| `idp-clickhouse-twin-ttl` | Manage ClickHouse twin TTL |
| `idp-cloud` | Primitive layer between estate operator scripts and cloud APIs |
| `idp-cluster-state` | Read cluster's own state receipt from ObjectStore (crew#345) |
| `idp-compile-helm` | Compile Helm charts |
| `idp-continuity-lane` | Maintain service continuity |
| `idp-contract` | Contract verification |
| `idp-convergence-proof` | Prove system convergence |
| `idp-cost-proof` | Prove cost compliance |
| `idp-crd-then-cr` | Custom Resource Definition then Custom Resource ordering |
| `idp-defs-validate` | Validate definitions |
| `idp-deploy-lag` | Measure deployment lag |
| `idp-dev` | Run laptop process inside staging namespace (crew#584 CP-H) |
| `idp-dispatch-install` | Install dispatch boundary in every session |
| `idp-door-heartbeat` | Front door pulse check |
| `idp-down` | Stop catalogue and unpublish ports |
| `idp-drift-blind` | Blind drift detection |
| `idp-epistemic` | Epistemic fabric control |
| `idp-escrow` | Full copy of every repository the estate manages |
| `idp-estate-audit` | Audit estate against OpenTofu state (read-only) |
| `idp-estate-backup` | Backup estate data |
| `idp-estate-db-push` | Push estate.db to registry |
| `idp-estate-graph-prove` | Prove estate graph structure |
| `idp-estate-seed` | Mint all estate-born credentials in-process |
| `idp-estate-state-build` | Build estate state from measurements |
| `idp-estate-view` | View estate state |
| `idp-exec` | Execute command in idp context |
| `idp-execution-boundary` | Enforce execution boundary |
| `idp-executor-install` | Install executor |
| `idp-executor-status` | Check executor status |
| `idp-expert-manifest` | Generate expert manifest |
| `idp-externalsecret-blockers` | Identify ExternalSecret blockers |
| `idp-features` | List/manage features |
| `idp-fence-enforcement` | Enforce zero-trust boundary |
| `idp-fits-a-node` | Check if workload fits on a node |
| `idp-flux-bootstrap` | Connect Flux to OKE cluster (ADR 0004 step 3) |
| `idp-flux-settle` | Settle Flux deployment (crew#488 CP5) |
| `idp-flux-wait-brake` | Wait for Flux brake |
| `idp-github-app` | One GitHub App for estate agents, one installation token |
| `idp-gitops-drift` | Carry estate drift back to PR that caused it |
| `idp-glass-break` | Break glass emergency procedure |
| `idp-hardcode-scan` | Scan for hardcoded secrets |
| `idp-hc-enroll` | Enrol machine's jobs with estate job monitor (crew#579) |
| `idp-hc-publish` | Publish job-monitor ping key |
| `idp-headlamp-mac` | Debug cluster from phone outside cluster |
| `idp-healthcheck-exists` | Verify healthcheck exists |
| `idp-helmrelease-drift-coverage` | Measure HelmRelease drift coverage |
| `idp-human-vault-probe` | Probe human secret store (Bitwarden) |
| `idp-hydrate` | Hydrate cluster configuration (crew#488 CP1/CP2) |
| `idp-iam-policy-drift` | Detect IAM policy drift |
| `idp-identity-apply` | Provision front door OIDC client |
| `idp-image-only-diff` | Show image-only differences |
| `idp-image-update-pr` | Open/refresh flux image-updates PR (crew#267/439) |
| `idp-install-launchd` | Render and load launchd plists |
| `idp-install-verifier-hooks` | Install verifier gate hooks |
| `idp-inventory` | Graded against git declarations (crew#740) |
| `idp-jit` | Just-in-time access |
| `idp-jit-broker-role` | JIT broker role management |
| `idp-jit-grants` | JIT access grants |
| `idp-jit-morning-summary` | Morning summary of JIT access |
| `idp-jobs-page` | Generate jobs status page |
| `idp-kini` | Start KINI checkpoint workflow |
| `idp-kini-state` | Read KINI run receipt (crew#396 step 4) |
| `idp-kube` | Access cluster kubeconfig (crew#66, founder 2026-08-28) |
| `idp-kubeapi-mac` | Make cluster API reachable from founder's phone |
| `idp-kubeconform` | Validate against schema before policy grading |
| `idp-kyverno-audit-promote` | Promote Kyverno policies from Audit to Enforce |
| `idp-kyverno-dirs` | List platform directories with Kyverno policies |
| `idp-kyverno-own-policies` | List Kyverno policies owned by estate |
| `idp-kyverno-render` | Render all Flux HelmReleases under platform/ |
| `idp-launchd-retire` | Retire launchd configuration |
| `idp-laws-guards-report` | Report on law compliance and guards |
| `idp-limit-raise-only-diff` | Show only limit-raise differences |
| `idp-linear-dispatch` | Dispatch work linearly |
| `idp-loop-meter` | Measure PR time to merge |
| `idp-mac-adopt-otto` | Grant Otto access to founder's Mac |
| `idp-mac-secret-deliver` | Deliver vault secret to Mac-hosted service |
| `idp-mcp-door` | MCP door interface |
| `idp-merge-pin` | Pin merge status |
| `idp-messaging-demo` | Demo messaging platform |
| `idp-models-page` | Generate models status page |
| `idp-no-toil` | No-toil gate runner (crew#66) |
| `idp-ns-fence-gen` | Generate namespace fence |
| `idp-oci-bootstrap` | One-time OCI tenancy bootstrap (ADR 0004) |
| `idp-oci-login` | OCI login provider door |
| `idp-oci-s3` | OCI S3 provider door |
| `idp-oci-whoami` | Check OCI identity |
| `idp-oke-break-glass` | Break-glass cluster recovery (crew#539, 2026-08-28) |
| `idp-oke-rebuild` | Full cluster rebuild (crew#220, founder 2026-08-25) |
| `idp-oke-surge-node` | Replace worker node with surge |
| `idp-one-scheduler` | Single scheduler instance |
| `idp-otlp-headers` | Print OTLP Authorization header |
| `idp-otto-door-key-agrees` | Verify Otto door key agreement |
| `idp-otto-homes` | Manage Otto home directories |
| `idp-phone-kubeconfig` | Put cluster on founder's phone |
| `idp-pipeverdict` | Conditional verdict pipeline for grep |
| `idp-portal-buttons` | Generate portal buttons |
| `idp-pr-age` | Measure PR age |
| `idp-pr-arm` | Arm robot-opened PR for merge |
| `idp-pr-landable` | Check if PR is landable |
| `idp-pr-secrets` | Scan PR for secrets with gitleaks |
| `idp-precommit-verify` | Pre-commit gate |
| `idp-prepush-verify` | Pre-push gate |
| `idp-priority-class-exists` | Verify PriorityClass exists |
| `idp-prm` | Prompt Reasoning Model grading |
| `idp-probe-host` | Probe host capability |
| `idp-probe-mutations` | Probe mutation handling |
| `idp-prove` | Prove claimed behavior |
| `idp-publish` | Make primary portal URL public |
| `idp-push-on-green` | Refuse push to PR that's not green |
| `idp-realm-diff` | Realm configuration differences |
| `idp-reasoning-gateway-hook` | Grade session with reasoning gateway |
| `idp-reconcile` | Reconcile state |
| `idp-recreate-guard` | Refuse apply that would recreate resource |
| `idp-repo-root` | Print primary checkout directory |
| `idp-reports-render` | Render reports for viewing |
| `idp-request-ceiling` | Apply request ceiling limits |
| `idp-rollback-only-diff` | Show rollback-only differences |
| `idp-root-trust` | Verify root trust origin |
| `idp-router-key` | Mint LiteLLM virtual key for consumer |
| `idp-router-lanes` | Show router lanes snapshot (2026-09-03) |
| `idp-router-rows-to-console` | Route rows to console output |
| `idp-sandbox-sweep` | End expired buyer sandbox |
| `idp-science-facts` | Read cluster science-facts receipt (crew#516 CP5) |
| `idp-scope-replay` | Replay scope operations |
| `idp-script-compiles` | Verify script compiles |
| `idp-session-bootstrap` | Initialize session environment (crew#654 CP1) |
| `idp-set-root` | Set founder's root provider (crew#66) |
| `idp-shadow` | Shadow mode operations |
| `idp-shadow-sync` | Sync shadow state |
| `idp-shadow-verify` | Verify shadow mode |
| `idp-shop-backup` | Backup shop database (crew#713 CP3) |
| `idp-surface-liveness` | Prove CP5 founder-surface selectors resolve (cluster receipt) |
| `idp-signoz-key` | Manage SignOz API key |
| `idp-sleep-ban` | Ban sleep operations |
| `idp-slow-tests` | Identify slow tests |
| `idp-spend-floor` | Enforce minimum spend threshold |
| `idp-split-brain` | Detect split-brain condition |
| `idp-state-guard` | Refuse local OpenTofu state overwrite |
| `idp-status` | What is serving right now |
| `idp-store-can-reach-its-vault` | Verify datastore reaches its vault |
| `idp-stray-checkout` | Find stray checkouts |
| `idp-tailscale-policy` | Manage Tailscale policy (crew#516 CP5) |
| `idp-telemetry-coverage` | Measure telemetry coverage (crew#320) |
| `idp-tenant-split` | Handle tenant split condition |
| `idp-tests-for` | Print test files for changed code |
| `idp-ticket-facts` | Extract ticket facts |
| `idp-ticket-verify` | Verify ticket status |
| `idp-trajectory` | Trajectory planning |
| `idp-truthteller-demo` | Demo truthteller capability |
| `idp-up` | Start catalogue and publish ports |
| `idp-vault-put` | Put JSON secret into estate vault |
| `idp-vault-reads` | Verify cluster reads vault |
| `idp-vault-refs` | Verify vault keys still exist |
| `idp-vault-split-guard` | Refuse secret split across vaults |
| `idp-vendor-render` | Render vendor configuration |
| `idp-verdict` | Generate operation verdict |
| `idp-verdict-fresh` | Ensure verdict is fresh |
| `idp-verifier-curl` | Verify MCP verifier client |
| `idp-verifier-oath` | Verifier OATH token |
| `idp-verify` | Verify published matches inventory |
| `idp-verify-claims` | Verify claimed facts |
| `idp-wake-blocked` | Wake blocked operations |

---

## Estate (18 scripts)

Estate platform administration and monitoring.

| Script | Purpose |
|--------|---------|
| `estate-checkpoint` | Estate checkpoint operation |
| `estate-cleaner` | Clean up estate resources |
| `estate-clocks` | Estate time synchronization |
| `estate-diagram` | Visualize estate structure |
| `estate-digest-keeper` | Local ops tier slot 7 (crew#928) |
| `estate-digest-worker` | Recurrent "update / what changed" digest |
| `estate-drift-reconciler` | Reconcile estate drift |
| `estate-founder` | Founder operations interface |
| `estate-next` | Show next operations to execute |
| `estate-proof` | Prove estate correctness |
| `estate-request-router` | Route estate requests |
| `estate-security-rollout` | Rollout security patches to repos |
| `estate-security-scan` | Scan security and generate evidence |
| `estate-session-recorder` | Record session data |
| `estate-showcase` | Showcase estate capabilities |
| `estate-twin-runtime` | Query estate as code (ask graph not cluster) |
| `estate-zone-gate` | Zone configuration gate (founder 2026-08-26) |

---

## Catalog (6 scripts)

Backstage catalog and component management.

| Script | Purpose |
|--------|---------|
| `catalog-gen` | Generate catalog from inventory |
| `catalog-links-check` | Validate catalog links |
| `catalog-platform` | List catalog platform/tooling components |
| `catalog-refcheck` | Verify all entity references resolve |
| `catalog-render` | Render catalog views |

---

## Kubernetes & Cluster (2 scripts)

Kubernetes-specific operations.

| Script | Purpose |
|--------|---------|
| `nodesoftware-operator-gate` | Gate for NodeSoftware operator |
| `idp-cluster-state` | Read cluster's own state |

---

## Cloud & Infrastructure (1 scripts)

| Script | Purpose |
|--------|---------|
| `cloud-agnostic-gate` | Validate cloud-agnostic requirements |

---

## Security (1 scripts)

| Script | Purpose |
|--------|---------|
| `security-policy-gate` | Validate security policy proofs |

---

## Gates & Verification (12 scripts)

Policy gates and verification logic.

| Script | Purpose |
|--------|---------|
| `idp-api-version-gate` | API version compatibility gate |
| `idp-availability-gate` | Availability SLA gate |
| `idp-bdd-proof-gate` | BDD proof verification |
| `idp-envsubst-gate` | Environment substitution gate |
| `idp-evidence-gate` | Evidence collection gate |
| `idp-flux-subst-gate` | Flux substitution gate |
| `idp-mechanism-gate` | Mechanism validation gate |
| `idp-reasoning-gateway-hook` | Session grading hook |
| `idp-simulate-gate` | Simulate gate behavior |

---

## Utilities (43 scripts)

Generic utilities and helpers.

| Script | Purpose |
|--------|---------|
| `actions-pinned` | Every GitHub workflow `uses:` action versions |
| `ai-act-gate` | AI action gate |
| `bind-audit` | List processes listening on ports |
| `budget_governor.py` | Budget governance logic |
| `build-image` | Single way to build estate images |
| `contract_executor.py` | Contract execution logic |
| `dockerfiles` | Single list of estate images |
| `dod-live-claim-gate` | Live claim validation |
| `epistemic_firewall.py` | Epistemic fabric firewall |
| `exec-daemon` | launchd entry point |
| `gvisor-cell-fence-gate` | gVisor sandbox fence validation |
| `gvisor-cell-gate` | gVisor sandbox gate |
| `incident-register` | Register incidents |
| `intent-compile` | Compile intent |
| `intent-hydrate` | Hydrate intent |
| `law32-gate` | LAW 32 compliance gate |
| `main-verdict-gate` | Main branch verdict gate |
| `matrix-gate` | Matrix validity gate |
| `migration-gate` | Migration validation gate (R22 mechanism 1) |
| `multiarch-gate` | Multi-architecture validation |
| `ns-fence-gate` | Namespace fence validation |
| `owner-account-gate` | Owner account validation |
| `placement-audit` | Audit laptop placement policies |
| `plist-gate` | plist validation gate |
| `port-gate` | Port availability gate |
| `pr-report` | PR to operating_model input reshape |
| `prm_grader.py` | PRM grading logic |
| `reasoning_gateway_hook.py` | Session grading implementation |
| `repo-rulesets` | Repository ruleset management |
| `sb` | Sovereign Bus shim (bash) |
| `sb-windows.ps1` | Sovereign Bus shim (Windows PowerShell) |
| `spec-gate` | Spec requirement validation |
| `static-secret-gate` | Static secret validation |
| `supply-chain` | Supply chain validation |
| `test-executes-gate` | Test execution validation |
| `test-prose-gate` | Test prose validation |
| `trace-matrix` | Trace matrix generation |
| `trajectory_lock.py` | Trajectory locking logic |
| `treewalk.py` | Tree walking utility |
| `vendor-agnostic-gate` | Vendor independence validation |
| `vendor-name-collision-gate` | Vendor name collision check |
| `vm-shared-path` | Validate VM shared paths |

---

## Database (1 scripts)

| Script | Purpose |
|--------|---------|
| `db-gen` | Generate SQLite database from inventory |

---

## Services (16 scripts)

Backend service management and control.

| Script | Purpose |
|--------|---------|
| `langfuse-down` | Stop Langfuse observability |
| `langfuse-password` | Manage Langfuse password |
| `langfuse-status` | Check Langfuse status |
| `langfuse-up` | Start Langfuse service |
| `langfuse-verify` | Verify observability working |
| `litellm-down` | Stop LiteLLM proxy |
| `litellm-status` | Check router status and spend |
| `litellm-up` | Start LiteLLM proxy |
| `mcp-down` | Stop Agentgateway and MCP servers |
| `mcp-status` | Verify MCP backend round-trip |
| `mcp-up` | Start MCP infrastructure |
| `scheduler-down` | Stop Dagster scheduler |
| `scheduler-import` | Import scheduled jobs |
| `scheduler-migrate` | Migrate scheduler configuration |
| `scheduler-status` | Check scheduler health |
| `scheduler-up` | Start Dagster scheduler |

---

## Pi Agent Scripts (9 scripts)

Located: `~/.pi/agent/scripts/`

| Script | Type | Purpose |
|--------|------|---------|

---

## Pi Agent Extensions (7 scripts)

Located: `~/.pi/agent/extensions/`

| Extension | Purpose |
|-----------|---------|

---

## Pi Agent Workflows (7 scripts)

Located: `~/.pi/agent/workflows/`

| Workflow | Purpose |
|----------|---------|

---

## Notes

- All 310 bin scripts are version-controlled in repository
- Scripts are primarily Python (60%) and Shell (35%), with some node and PowerShell
- Active hooks defined in root `settings.json` (SessionStart, Stop)
- Pi agent configuration and extensions in `~/.pi/agent/`
- Comprehensive categorization enables quick lookup and understanding
