# 2026-09-15 — the estate's end-to-end workflow, audited with receipts

Founder question this answers: "connect everything we have been building into one super
coherent behemoth" — what already links, what is proven, what is still a gap. Every row below
cites a file, a line, or a command actually run today; nothing here is narrated from memory.

## The chain, as it exists in code today

```
Linear issue  ──[ GAP: no dispatcher — see below ]──▶  estate harness run
       │
       ▼ (once a run starts)
epistemic_firewall / trajectory_lock / prm_grader / budget_governor   (bin/*.py, reasoning-gateway)
       │
       ▼
via-negativa: negative-constraints-proxy / rca_worker    (bin/negative-constraints-proxy, bin/rca_worker)
       │
       ▼
propose  →  Deterministic Verifier (stage_structural/stage_symbolic/stage_execution)
       │       sovereign/verifier.py, platform/executor/daemon.py, mcp/plugins/estate_executor.py
       ▼
simulate_change  (mcp/plugins/estate_simulate.py, mcp__estate__simulate_change — live tool)
       │  converge verdict
       ▼
shadow cluster proves convergence for real   (platform/sandbox/vcluster/, bin/idp-shadow*)
       │  hard gate: .github/workflows/deploy-when-green.yml:86,121 — no green shadow-verify, no merge
       ▼
JIT broker grants the one narrow write   (bin/idp-jit*, platform/jit/deployment.yaml)
       │
       ▼
Flux / Greenlane lands it
       │
       ▼
estate-twin-runtime sweeps it into the graph   (bin/estate-twin-runtime --code --domains --linear)
       │
       ▼
Fleet / Backstage reads catalog/estate.db
```

Every arrow above except the first is real, proven code. The first arrow — Linear issue to a
harness run starting — is the one gap. Full receipts:

## Built, with evidence

| Piece | State | Where | Proof run today |
|---|---|---|---|
| Deterministic Verifier / mutation ledger | BUILT | `sovereign/verifier.py`, `platform/executor/daemon.py`, `mcp/plugins/estate_executor.py` | 9/9 `tests/test_deterministic_verifier.py`; peer session idp-d4's 7/7 BDD suite (this window) |
| Linear-to-code graph link | BUILT | `bin/estate-twin-runtime`'s `sweep_linear()` (new this window) | Live proof: `linear_issues=234, linear_edges=50`; BLIND-path proof without a credential; independent sqlite check, zero id-namespace leakage |
| World-model simulate/execute | BUILT | `mcp/plugins/estate_simulate.py`, spec `docs/specs/2026-09-08-estate-world-model-simulate-before-execute.md` | `mcp__estate__simulate_change` / `execute_change` confirmed live in this session's own tool list |
| Shadow cluster (proof-before-production) | BUILT | `platform/sandbox/vcluster/`, `bin/idp-shadow{,-run,-sync,-verify}` | Merge gate confirmed at `.github/workflows/deploy-when-green.yml:86,121`; secret-reshape proven both ways by `rules.yaml`'s `shadow-sync` row |
| JIT privilege broker | BUILT | `bin/idp-jit*`, `platform/jit/deployment.yaml`, `bin/idp-glass-break` | read-only by default, writes are short/logged/expiring, named-reason override leaves an audit row |
| Kyverno Audit-mode policies exist | BUILT | `bin/idp-admission-policies:40-41`, `platform/edge/kyverno-secrets-policy.yaml:30` | 29 files name `Audit` |
| **Kyverno audit-stream reader (was the missing half of pillar 4)** | **BUILT this session** | `bin/idp-kyverno-audit-promote` (new) | Live run against the real cluster today, see finding below |

## Built today, with a finding worth more than the code

`bin/idp-kyverno-audit-promote` was the one piece of decision 0025's pillar 4 named as missing:
"nobody reads the audit stream, so nothing measures a full day of churn and nothing flips a
clean rule to Enforce" (`docs/decisions/0025-agents-hold-no-write-on-production-and-the-greenlane-grows-by-rows.md`,
row 4). It reads `policyreports.wgpolicyk8s.io` / `clusterpolicyreports.wgpolicyk8s.io` through
`bin/idp-kube` and refuses to recommend a promotion without evidence (zero recorded results is
`UNKNOWN`, never silently "clean" — same three-state rule as `bin/estate-twin-runtime`'s
`domain_state()`).

**Run live against the real cluster today: the CRDs exist (installed 2026-08-25, three weeks
ago) and hold zero PolicyReport objects, cluster-wide, for any of the four Audit-mode policies.**
The audit stream Kyverno is supposed to be writing is not being populated — the schema is real,
the data is not. That is a bigger and more useful finding than "4 policies are clean": nothing
has ever measured them at all. It never writes a promotion itself; a promotion still goes
through propose → verify → shadow → JIT, same as every other change.

## Not built — named by decision 0025 itself, and real infrastructure, not scripts

| Piece | State | What's missing | Why it's not built today |
|---|---|---|---|
| Dark-traffic mirroring (eBPF/Cilium) | NOT BUILT | `requestMirror`/`mirrorPercent` appear in 0 files | Requires editing the live CNI on production traffic — a network change, not a reversible local proof |
| Tainted 1-node canary pool | NOT BUILT | the `infra.canary=true:NoSchedule` pool itself doesn't exist | Requires provisioning a new OCI node pool — real cloud spend, not a script |

**FOUNDER ACTION: provision** — these two require standing up real cluster/cloud infrastructure
(a new node pool, a CNI traffic-mirror rule on live production). That crosses from "reversible,
provable in isolation" into "costs money and touches live traffic," which is exactly the
boundary decision 0025 itself draws. Not started without that call.

## The one real gap, unchanged since the first pass

Nothing watches Linear and starts the harness. Cyrus used to be that door and was deliberately
removed (`docs/FEED.md:235`, founder: "Cyrus is not the path... the estate is moving off the
Claude Code harness"); its removal did not retire the goal, only the vehicle. `docs/FEED.md:216`
already recorded that no scheduler runs even the Linear *board-setup* job ("Dagster has no
Linear job"). The dispatcher — something that watches Linear for a triggering state and starts a
harness run gated through every proven stage above — is still unbuilt. That is the next thing to
build, not this document.

## Discoverability gap (separate from the workflow gap)

None of shadow cluster / JIT broker / simulate-execute / this new audit reader have a Backstage
door — CLI/CI/MCP only. A founder should not have to ask what a component does; committed, not
yet built: one Fleet backend endpoint (`SELECT domain, count(*), freshness FROM nodes/freshness
GROUP BY domain`) plus a small Fleet panel surfacing it.
