# AGENTS.md — the rules of this repository, and the gate that reads them

This file is the version-controlled boundary for agent work in `idp` (crew #180, CP6).
The estate's laws live in `~/AGENTS.md`; this file holds only what is specific to this
repo. Each row names the gate that enforces it and the two fixtures that document what the
gate calls bad and good.

The rung that re-ran every gate against those two fixtures on every single run was deleted on
2026-09-04 (founder: "run each of the nine gates in the AGENTS.md table against its two
fixtures ... this is stupid"). It graded this file's own fixtures, so no defect in the estate
could ever fail it and no change to the estate could ever pass it differently. The gates
themselves still run, against the repository, where a real defect can trip them.

Every rule lives in `rules.yaml`, one row each: the statement, the law it serves, the argv that
grades it, the fixture pair that proves it both ways, and the planes it is enforced on (the
repository's CI, a session hook, the cluster's admission controller). `bin/idp-rules` is the only
thing that reads it -- `run` grades the repository, `cluster` checks the admission policy a row
names is on disk, `session` grades the files a hook hands it, and `render-agents-md` writes the
table below. The table is generated: edit `rules.yaml`, not these lines. `bin/idp-ci` runs
`bin/idp-rules render-agents-md --check`, so a row and its rule cannot drift apart.

Before 2026-09-07 each rule was a bash rung in `bin/idp-ci`, a hand-written row here and, for
several, a third copy inside `bin/policy-test` -- so a rule could be worded one way, graded
another, and listed a third. Fifteen fixtures under `policy/fixtures` were named by no runner at
all. Founder, the Unification Move: "Ruthless Deletion ... Do not leave them as dead code. Do not
deprecate them. Eradicate them."


<!-- BEGIN GENERATED RULES TABLE (bin/idp-rules render-agents-md) -->
| rule | law | gate | must-fail | must-pass |
|---|---|---|---|---|
| No shell parameter expansion (${NAME:-...} and kin) in a Flux-reconciled manifest; Flux substitution rewrites it before the pod runs it | incident 2026-09-06, otto-gateway | `python3 bin/idp-flux-subst-gate` | tests/fixtures/flux-subst/bad.yaml | tests/fixtures/flux-subst/good.yaml |
| A Flux Kustomization never sets both wait: true and healthChecks; wait wins, the checks the author wrote are discarded, and the row then waits on every object in its path -- so one optional Job going Failed holds every change to that path out of the cluster | incident 2026-09-10, otto-gateway held out by Job/otto-memory-store-6 | `python3 bin/idp-flux-wait-brake` | tests/fixtures/flux-wait-brake/bad.yaml | tests/fixtures/flux-wait-brake/good.yaml |
| No probe or lifecycle handler names a host: PodSecurity restricted refuses the pod at create, not the manifest at apply, so a workload carrying one merges green, reconciles green, and then its ReplicaSet fails to make a pod forever while the old pod keeps serving | incident 2026-09-10, otto-gateway three homes Available=False for hours | `python3 bin/idp-probe-host` | tests/fixtures/probe-host/bad.yaml | tests/fixtures/probe-host/good.yaml |
| No provider-specific annotation or Service outside the compute provisioner | R36 | `python3 bin/cloud-agnostic-gate` | tests/fixtures/cloud-agnostic/bad | tests/fixtures/cloud-agnostic/good |
| The DNS zone is one value in clusters/*/estate-config.yaml; a platform file naming it as a literal fails, in the tree and in a pull-request diff | R46 | `python3 bin/estate-zone-gate` | tests/fixtures/estate-zone/bad | tests/fixtures/estate-zone/good |
| A compose publication not declared in catalog/ports.yaml, or off loopback without non_loopback, fails | R22 mechanism 4, R20 | `python3 bin/port-gate` | tests/fixtures/ports-bad | catalog/ports.yaml |
| A listener bound to a different address than its ports.yaml row declares is refused | R20 | `python3 bin/port-gate` | tests/fixtures/ports-live/inventory.bad.json | tests/fixtures/ports-live/inventory.good.json |
| A control on the security policy page without a proof command that exists is a wish | LAW 44 | `python3 bin/security-policy-gate` | tests/fixtures/security-policy/bad.md | tests/fixtures/security-policy/good.md |
| Every vault entry an ExternalSecret reads is born by a bootstrapper on disk or ticketed | R52 | `python3 bin/idp-root-trust` | tests/test_incident_crew66_root_trust_register.py | platform/secrets |
| Every registered AI system has its Annex IV file, risk entries and declared data (Arts. 9, 10, 11) | AI Act, kept voluntarily | `python3 bin/ai-act-gate` | tests/fixtures/ai-act/bad | tests/fixtures/ai-act/good |
| A new bin file ships with docs/tutorials/demo and docs/how-to/onboarding, above the prose floor and in the nav | LAW 32 | `python3 bin/law32-gate` | bin/feature-with-no-pages | bin/supply-chain |
| Every launchd template renders to a plist that parses and names its job | LAW 45 | `python3 bin/plist-gate` | tests/fixtures/plist/bad.plist.tmpl | tests/fixtures/plist/abandoned-children.plist.tmpl |
| A migration whose second apply adds a resource is refused | R22 mechanism 1 | `bin/migration-gate` | tests/fixtures/migration-not-idempotent | bin/scheduler-migrate |
| Zero static secrets on disk; a key or a .env in the tree is refused | security-policy.md, kini-master-spec 4.1/4.4 | `bin/static-secret-gate` | tests/fixtures/static-secret/bad | tests/fixtures/static-secret/good |
| Every provider account names a second owner | R54 | `bin/owner-account-gate` | tests/fixtures/owner-accounts/bad.yaml | tests/fixtures/owner-accounts/good.yaml |
| Only the gateway binds a non-loopback address; everything else is 127.0.0.1 or nothing | R20 | `bin/bind-audit` | tests/fixtures/listeners.bad.txt | tests/fixtures/listeners.good.txt |
| The founder's ethos is seven measured tenet rows; a row without a command is refused | LAW 44 | `python3 bin/idp-conscience` | a tenet row with no command | bin/idp-conscience |
| Every scheduled job reaches the Dagster UI with a description of what it does | LAW 28 | `python3 -m` | tests/fixtures/schedule-undescribed.yml | tests/fixtures/schedule-described.yml |
| A VM mount source outside the shared tree is refused; one inside it is permitted | R19 | `bin/vm-shared-path` | /private/tmp | $HOME |
| No namespace without a both-ways default-deny NetworkPolicy, a ResourceQuota, a LimitRange and a DNS exception | crew#191, crew#839 | `python3 bin/ns-fence-gate` | tests/fixtures/ns-fence/bad.yaml | tests/fixtures/ns-fence/good.yaml |
| A workflow that grades main never cancels main's own run; stale pull-request runs still are | crew#865 | `python3 bin/main-verdict-gate` | tests/fixtures/main-verdict/bad.yml | tests/fixtures/main-verdict/good.yml |
| A test grades behavior or parsed structure, never prose: no test function may only assert sentences or string membership in file text | R76 | `python3 bin/test-prose-gate` | tests/fixtures/prose-pin/bad.py | tests/fixtures/prose-pin/good.py |
| One credential is one tenant's; the operator's road never widens the customer's | decision 0021 | `python3 bin/idp-tenant-split` | tests/fixtures/tenant-split/bad.yaml | tests/fixtures/tenant-split/good.yaml |
| A grant the JIT broker may mint can never be turned into standing access: no token for a verb that rewrites a pod spec, no secrets or RBAC, no core namespace, no wildcard, a TTL under the ceiling and a declared rate | WJ.5 | `python3 bin/idp-jit-grants` | tests/fixtures/jit-grants/bad.yaml | tests/fixtures/jit-grants/good.yaml |
| A profile of a denied packet is only ever a wall when the probe proved it could reach an allowed path; a probe that could not run is a fail-closed FAIL, never a pass | zero-trust-boundary.md step 1 | `python3 bin/idp-fence-enforcement` | tests/fixtures/fence-drill/gate-broken-fence.json | tests/fixtures/fence-drill/gate-good.json |
| The 39 generated policies stay unwired until a deny feed has been read over a full cycle; an empty log feed is a fail-closed FAIL, never a clean bill | platform/calico README | `python3 bin/idp-calico-deny-log` | tests/fixtures/calico-denyflow/feed-no-evidence.log | tests/fixtures/calico-denyflow/feed-with-deny.log |
| A pod in the gVisor sandbox cell must name runtimeClassName gvisor and must not be privileged, host-networked or mount a hostPath | zero-trust-boundary.md step 5 | `python3 bin/gvisor-cell-gate` | tests/fixtures/gvisor-cell/bad.yaml | tests/fixtures/gvisor-cell/good.yaml |
| A gVisor-cell namespace fence is default-deny with the gateway the one allowed route; a fence granting the cell internet egress is a break caught in the pull request | zero-trust-boundary.md step 6 | `python3 bin/gvisor-cell-fence-gate` | tests/fixtures/gvisor-cell-fence/bad.yaml | tests/fixtures/gvisor-cell-fence/good.yaml |
| Every surface the founder can open survives losing one node, and so does every fail-closed admission webhook -- losing one of those costs not a hostname but the cluster's ability to apply anything, its own repair included | docs/reference/policy/availability-standard.md | `python3 bin/idp-availability-gate` | tests/fixtures/availability/bad | tests/fixtures/availability/good |
| The policy/*_test.rego unit tests run in CI; a test no job runs is decoration | LAW 3 | `conftest verify` | — | — |
| No dependency whose licence blocks a sale; a scan with no licences is not clean | LAW 40 | `conftest test` | policy/fixtures/sell-blocking.json | policy/fixtures/clean.json |
| No scheduled job on this laptop that runs in the sleep window or is never pinged | LAW 28 | `conftest test` | policy/fixtures/placement-misplaced.json | policy/fixtures/placement-ok.json |
| Paid capacity is auto-defaulted up to estate-defaults.yaml node_pool.budget_monthly_usd and refused above it | R14 | `conftest test` | policy/fixtures/capacity-over-cap.json | policy/fixtures/capacity-under-cap.json |
| A pull request carries its identity and grant together, no console step, a canary label on a paid-capacity change, and no estate-zone literal in the lines it adds | LAW 51, ZCP | `conftest test` | policy/fixtures/opmodel-half-provisioned.json | policy/fixtures/opmodel-ok.json |
| A doc that tells a person to mint a credential by hand is refused; a FOUNDER ACTION line is not | LAW 47, R52 | `conftest test` | policy/fixtures/notoil-doc-manual.json | policy/fixtures/notoil-doc-founder-action.json |
| The conscience rules judge a pull request both ways | LAW 44 | `conftest test` | policy/fixtures/conscience-bad.json | policy/fixtures/conscience-clean.json |
| Every bash script in bin/ passes shellcheck at warning level | LAW 45 | `shellcheck` | tests/fixtures/shell-lint/bad.sh | tests/fixtures/shell-lint/good.sh |
| No file names where the checkout, home directory or machine lives | LAW 46 | `bin/idp-hardcode-scan` | tests/fixtures/hardcoded-path.bad.sh | tests/fixtures/hardcoded-path.good.sh |
| A code location loads the way workspace.yaml loads it: by file path, not as a package | LAW 45 | `bin/idp-defs-validate` | tests/fixtures/definitions/relative-import.py | tests/fixtures/definitions/loads-by-path.py |
| A workload that runs must be one the nodes that exist could place again; a pod the scheduler has refused, and a pod that fits on no other node, are both named | LAW 45 | `python3 bin/idp-fits-a-node` | tests/fixtures/fits-a-node/bad | tests/fixtures/fits-a-node/good |
| Reloader is off on a workload a custom resource owns; that operator owns its config rollout, and Reloader on top of an operator is a loop, not a control. A Secret re-minted on a timer says what Reloader does with it (ignore, or a sentence why the roll is wanted); a silent one is refused | crew#684 rung 2 | `kyverno` | tests/fixtures/reloader-blind | tests/fixtures/reloader |
| Dagster is the estate's one scheduler; a recurring job declared in launchd, a GitHub Actions cron or a Kubernetes CronJob is named here until it is folded in | THE HEADLINE (one platform layer, not a stitched one) | `python3 bin/idp-one-scheduler` | tests/fixtures/one-scheduler/bad | tests/fixtures/one-scheduler/good |
| The broker, its grant catalogue, the RBAC floor and bin/idp-kube never land on a green check alone: no auto-merge, no self-approval, and the founder's own review or nothing | WJ.8 | `python3 bin/idp-glass-break` | tests/fixtures/glass-break/bad.json | tests/fixtures/glass-break/good.json |
| An infrastructure pull request reaches the merge gate with a Proof-of-Convergence; a body with no such block, or whose proof's run is not a green run on its own head commit, is refused -- a missing or unparseable proof is a fail-closed FAIL, never a pass | W2.3 | `python3 bin/idp-convergence-proof` | tests/fixtures/convergence/no-proof.md | tests/fixtures/convergence/proved.md |
| A Secret cloned into the shadow dimension is a same-shape shell or it is refused; a live value must never survive re-shaping -- a non-shell Secret in a shadow state-set is a fail (secrets are never copied into a vcluster, only keyed dummies so a Deployment mounts) | W2.1 | `python3 bin/idp-shadow-sync` | tests/fixtures/shadow-sync/verbatim | tests/fixtures/shadow-sync/shelled |
| A change to a workload passes the low-risk lane only when its sole difference is a strict increase of a resources.limits.memory/cpu value on one workload; a request change (which the scheduler counts), a lower limit, or any other edit is refused -- YAML ancestry is read from the full parsed old and new files, never guessed from a git hunk | W3.1 | `python3 bin/idp-limit-raise-only-diff` | tests/fixtures/limit-raise/request | tests/fixtures/limit-raise/good |
| A pull request rolls one workload back only when every changed line is a newTag: whose value that same file has already carried on origin/main; a tag never on main is a forward deploy and waits, and a change that edits anything but a tag is refused -- the prior footprint is proved from history, never assumed from age | W3.2 | `python3 bin/idp-rollback-only-diff` | tests/fixtures/rollback/forward-new-tag.diff | tests/fixtures/rollback/rollback-known-good.diff |
| A sovereign agent's command is inside the allowlist or it is denied; an allowlist that defaults to allow is a denylist wearing the wrong name | spec v1.0 4.2 | `conftest test` | policy/fixtures/command-not-allowlisted.json | policy/fixtures/command-allowed.json |
| Every fixture pair in the tree is named by a registry case or a test; a fixture graded by nothing is a rule nobody runs, and the ledger of the ones still unwired only shrinks | LAW 45 | `python3 bin/idp-rule-coverage` | tests/fixtures/rule-coverage/bad | tests/fixtures/rule-coverage/good |
| The broker mints only what it already holds: its own ClusterRole carries no escalate, no bind, no impersonate, no wildcard and no secrets, and no ClusterRoleBinding names it -- the absence that makes KSV-0050 on that file an accepted risk rather than a defect | WJ.5 | `python3 bin/idp-jit-broker-role` | tests/fixtures/jit-broker-role/bad.yaml | tests/fixtures/jit-broker-role/good.yaml |
| A deck that replaces a vendor operator never reuses the operator's cluster-scoped names; a ClusterRole has no namespace, so moving the ServiceAccounts does not separate them | platform/calico/raw/README.md | `python3 bin/vendor-name-collision-gate` | tests/fixtures/vendor-names/bad.yaml | tests/fixtures/vendor-names/good.yaml |
| A RuntimeInstall CR names a runtime in the closed set the NodeSoftwareOperator knows, requires a canary on ProgressiveCanary rollouts, and rejects pause durations that would make the canary pause a no-op | NodeSoftwareOperator option c, goal b9217bea | `bin/nodesoftware-operator-gate` | tests/fixtures/nodesoftware-operator/bad.yaml | tests/fixtures/nodesoftware-operator/good.yaml |
| A conditional's verdict is never a pipeline into grep in a script that sets pipefail: a failing left-hand stage inverts the answer silently. Capture the output first and grade the text. | LAW 55 | `bin/idp-pipeverdict` | tests/fixtures/pipefail-verdict.bad.sh | tests/fixtures/pipefail-verdict.good.sh |
| One cloud resource has exactly one owner: a Crossplane external-name that matches an OpenTofu resource under platform/oci is two controllers undoing each other, forever | decision 0026 | `python3 bin/idp-split-brain` | tests/fixtures/split-brain/bad | tests/fixtures/split-brain/good |
| A mechanism this repository depends on may not be switched off, deleted or unproduced: every `uses:` resolves to a workflow in the tree, and every workflow GitHub is not running is named with a reason in .github/disabled.yaml -- a registry, and never inside .github/workflows/, where GitHub tries to run it | incident 2026-09-08, ten days of nothing merging and nothing red | `python3 bin/idp-mechanism-gate` | tests/fixtures/mechanism/bad | tests/fixtures/mechanism/good |
| A ClickHouse system table the operator gives an <engine> carries its retention inside that engine string, never as a sibling <ttl>; ClickHouse exits 36 on boot when both are present | incident 2026-09-08, signoz-clickhouse CrashLoopBackOff | `python3 bin/idp-clickhouse-system-log-ttl` | tests/fixtures/clickhouse-system-log-ttl/bad.yaml | tests/fixtures/clickhouse-system-log-ttl/good.yaml |
| A Crossplane Provider and an instance of a kind its package installs never share a Flux Kustomization path; Flux dry-runs the whole path first, so neither the instance nor the Provider ever lands | incident 2026-09-08, crossplane-providers | `python3 bin/idp-crd-then-cr` | tests/fixtures/crd-then-cr/bad | tests/fixtures/crd-then-cr/good |
| A secret store that authenticates outside the cluster has a fence that lets it get there: egress_internet, and egress_metadata too when its identity is fetched at run time | incident 2026-09-08, ClusterSecretStore/estate-vault | `python3 bin/idp-store-can-reach-its-vault` | tests/fixtures/store-reach/bad | tests/fixtures/store-reach/good |
| A package manager may mint its own webhook Service without a catalogue label, and an undeclared door in the same namespace still may not | R38 -- a guard that refuses correct work is an outage | `kyverno` | tests/fixtures/catalogue-entity-runtime-service-blind | tests/fixtures/catalogue-entity-runtime-service |
| Every priorityClassName a workload names is a PriorityClass this tree declares or one of the two Kubernetes ships; a class that exists nowhere is refused at admission, not at apply | incident 2026-09-08, nodesoftware-operator | `python3 bin/idp-priority-class-exists` | tests/fixtures/priority-class-exists/bad | tests/fixtures/priority-class-exists/good |
| A state-changing estate MCP tool (an @mcp.tool() named execute_* or exec_*) is refused unless the same module registers a simulate twin to propose its change first (MUM-288, ADR 0006) | MUM-288, ADR 0006 | `python3 bin/idp-simulate-gate` | tests/fixtures/simulate-grade/bad | tests/fixtures/simulate-grade/good |
<!-- END GENERATED RULES TABLE -->

Rules that are already types or tools, and so need no row: compose files must parse
(`docker compose config`), the gateway config must match its release schema
(`check-jsonschema`), every catalog entity must match the Backstage schema, and every
script must pass `shellcheck`, every generator must be idempotent (two runs over one
inventory, byte-identical), the generated catalogue must carry a relationship graph, and
every entity reference in it must resolve to an entity something defines
(`bin/catalog-refcheck`, proved both ways in the same run). Those run unconditionally in
`bin/idp-ci`.

Adding a rule: add a row to `rules.yaml`, add both fixtures, run `bin/idp-rules render-agents-md`
and `bin/idp-ci`. No new rung, no new gate script.

## Platform queries go through the estate MCP server (ADR 0006)

Founder, 2026-08-25: the platform is self-aware; one interface answers questions about it. So: a
question about estate state is one `mcp__estate__*` tool call, not a shell recon. A new query tool
summarises by default and drills only on request, under a byte ceiling. Any tool that changes state
is two calls, propose then execute, and execute refuses when the state hash in the proposal no longer
matches. Events reach agents debounced through the Sovereign Bus, never raw. Extend `mcp/`; never add
a second server. Full text: `docs/decisions/0006-the-platform-answers-for-itself-over-one-mcp.md`.

## Living policy (crew#219 R38): the block below is code, not prose

`sovereign/policy.py` parses the one ```toml block in this file, and `sovereign/config.py`
builds its `budget.usd_per_day.*`, `cost.*`, `routing.*` and `merge.*` keys from it. The
numbers config.py declares on its own are repeated under `[invariants]`, and
`sovereign/tests/bdd/test_policy.py` fails when the two disagree. Change a value here and the
code follows; change it in config.py alone and the suite goes red. Every key still takes the
usual env override (`sb config --lint` lists them).

- **Capabilities** (spec 4.4): what each agent class may do unattended. `destructive` ops need
  quorum and a hardware signature on top of budget; `nondestructive` need budget only.
- **FSM rules** (spec 4.3): `init -> planning -> tool_use -> synthesis -> terminal`; the
  cycle path repeated `max_cycles` times pauses the session before the next one.
- **Budget defaults** (spec 8, R40): USD per day per spender. The sum over `days_per_month`
  must sit inside the `[cost]` contract, $0 to $150 a month; the test proves it.
- **Model routing**: LiteLLM aliases from `llm/config.yaml`. `cheap` is the last entry of every
  fallback chain there, and the only one with zero marginal cost.
- **Merge criteria** (R41): `dev` is permissive, `main` is strict. A PR targeting a strict
  branch fails when any feature is still `pending`, or when a pending mark has no owner or
  says `unclaimed`. `.github/workflows/ci.yml` sets `SB_BDD_STRICT` from the PR's base branch,
  and `sovereign/tests/bdd/conftest.py` enforces it.

```toml
[capabilities]
nondestructive = ["fs_commit", "fs_read", "git_status", "tool_result", "doc_commit", "budget_refill"]
destructive = ["fs_delete", "git_push_force", "db_drop", "service_destroy", "rewind"]
engine = ["fs_read", "fs_commit", "git_status", "tool_result", "doc_commit"]
intake = ["fs_commit", "doc_commit"]
shadow = ["fs_read"]

[fsm]
initial_state = "init"
terminal_state = "terminal"
cycle_path = ["planning", "tool_use", "synthesis"]
max_cycles = 5

[budget.usd_per_day]
litellm = 3.0      # frontier calls through the proxy; llm/config.yaml max_budget is the hard ceiling
consensus = 1.0    # the three-model vote on destructive ops
vision = 0.5       # photo intake (spec 2.3)
ollama = 0.0       # local, no marginal cost
langfuse = 0.0     # self-hosted

[cost]
contract_min_usd_month = 0
contract_max_usd_month = 150
days_per_month = 31   # the longest month, so a sum under the cap holds in every month

[routing]
# 2026-09-08, the founder's cost mandate. `default` and `cheap` both named `deepseek`, an
# account at $0 that has answered 401 since 2026-09-04 -- so the estate's default model and
# its cheap model were the same dead lane, and test_cp30 enforced that every fallback chain
# ended there. They move to the one lane measured answering from inside the router pod today.
# This is a stopgap, not the destination: `cheap` belongs on a FREE lane, and becomes `groq`
# the moment SEED_GROQ_API_KEY exists (platform/vendors/consoles.yaml).
default = "minimax"
vision = "vision"
cheap = "minimax"
# deepseek stays a voter: the lane is console-owned, so it rejoins the moment its key is added
# without a pull request. Until then quorum needs both minimax and gemini, and gemini is
# rate-limited -- consensus is one refusal from failing. The third live voter is groq.
consensus = ["deepseek", "minimax", "gemini"]

[merge]
strict_branches = ["main"]
require_bdd_green = true
pending_owner_required_on = ["main"]

[invariants]
"consensus.quorum" = "2/3"
"consensus.timeout_s" = 30
"branch.count" = 3
"branch.budget_pct" = 10
"approval.timeout_min" = 15
"blind.halt_after_min" = 5
"alerts.digest_over_per_hour" = 50
"spiffe.max_missed_heartbeats" = 3
```


## THE EMPIRICAL PROOF RULE (founder 2026-09-05, verbatim; record: `~/.claude/docs/founder/2026-09-05T1415Z-he-generalized-rule-empirical-proof-over-synthetic-probes-a79801e5.md`)

NEVER declare a system "WORKING" or "MEASURED_OK" based solely on synthetic probes, CI gates, or HTTP 200 health checks. Synthetic checks lie.

Before claiming a fix is successful, you MUST prove it empirically:
1. **Read live traffic:** Fetch the actual pod logs (`kubectl logs --tail=100`) and quote a real, end-to-end user transaction completing successfully.
2. **Check for silent failures:** Look at the most recent cluster events (`kubectl get events`) to ensure the pod isn't crashing or OOMing immediately after answering a probe.
3. **Verify the critical path:** If it's a bot, verify the upstream webhook and LLM generation path. If it's a database, verify a real row was written.

If you cannot quote a successful production log line, the system is NOT working.
