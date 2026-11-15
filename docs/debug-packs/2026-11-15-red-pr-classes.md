# Debug pack — the red-PR classes of 2026-11-15

Every failure that turned a pull request red on 2026-11-15, mapped to its class, its root cause,
and the earliest place it can now be refused. The rule this pack exists to serve: **a red pull
request is a gate that ran too late**, not an incident to triage.

Shared wall: `.githooks/pre-push` (laptop) and `.github/workflows/fast-gate.yml` (every agent,
cloud included) both call `IDP_CI_FAST=1 bin/idp-ci`. Anything deterministic goes there.

| check that went red | class | root cause | now refused at | falsifier |
|---|---|---|---|---|
| `fast-gate / language` (UnicodeDecodeError) | `GATE_CRASHES_ON_BINARY` | `bin/language-gate` read every changed file with `text=True`; the OKE archive zip raised `UnicodeDecodeError` and the rung died instead of judging | pre-push (same script) | `tests/test_language_gate.py`; lane `32bf4192` proved it |
| `fast-gate / language` (missing trailer) | `LANGUAGE_GATE` | a new Python file with no `Language-Exception: <path> -- <reason>` | pre-push | `bin/language-gate` refuses, then passes after the trailer |
| `fast-gate / ruff-fmt` | `FORMAT_DRIFT` | touched Python was not `ruff format`-clean | pre-push | `ruff format --check <files>` |
| `registry-workflow-dependency-preflight` | `REGISTRY_WITNESS` | the committed capability registry was not the generator's exact output at HEAD | **pre-push (new rung)** | `tests/test_prepush_pr_parity.py` — a witness lagging by one record must be refused |
| `gate / fast-gate` — `bddproof ... the proof names X, but the head is Y` | `STALE_PROOF` | a branch update created a new head; the BDD proof still named the old sha | PR only (needs a re-run of the suite) | none yet — the class is the audit's "recurring BDD-proof/head mismatch" |
| `claim-gate` | `NO_CLAIM` | no `Claim: owner/repo#n` covering the changed paths | pre-push (`bin/claim-gate` stage) | `bin/claim-open --issue N` stamps it |
| `guarded-paths` | `GUARDED_PATH` | a protected path changed without the approval trailer | PR only (needs a reviewer) | the workflow refuses |
| `verify` (argon) | `GENESIS_ENVELOPE` | missing `Genesis-*` trailers, or a trailer block split by a blank line (only the last paragraph parses) | pre-push (`ops/git/pre_push_governance.sh` on argon) | local `node verify_handoff.mjs` run |
| `verify` (argon, gate change) | `GENESIS_GATE_CHANGE` | `.github/workflows/` or `ops/git/` changed: two peer reviews + a founder approval record are required | **cannot be local**: needs two humans/agents and the founder | the gate refuses; never fabricate |
| `no-harness-folders` absent, PR blocked forever | `REQUIRED_CHECK_WITH_NO_WORKFLOW` | the ruleset required a check whose workflow had been deleted (prospector) | restored the workflow; the check now runs | the workflow's own grep |
| `build (...)` "no CRITICAL vulnerability ships" | `IMAGE_CVE` | `zip 8.6.0` (fixed 9.0.5) in `platform/edge-runtime/Cargo.lock`; other images carry their own | CI image build (needs docker + network) | `trivy` on the built image |
| `DIRTY` merge state | `CONFLICT` | the branch conflicts with main | `git merge-tree` at pre-push | a local merge dry-run |
| `escrow` | `LEASE_ESCROW` | a job-bound capability lease was not escrowed | PR only | the escrow gate |
| `deterministic-gate / control-primitive-freeze` | `CONTROL_FREEZE` | a protected control changed without the freeze process | PR only | the deterministic gate |
| `prove-derived-dependencies` | `REGISTRY_WITNESS` | the committed witness lagged the repository | **pre-push (new rung)** | same as above |

## What a future session should do first

1. Run `IDP_CI_FAST=1 bin/idp-ci` in the branch worktree. If it is green, the PR cannot go red on
   any deterministic check — `fast-gate` runs the same script.
2. If it prints `BLIND`, the laptop is missing a tool, not the code. `bin/idp-install-deps` is the
   fix for the Python 3.12 rung; `yarn install` in `backstage/` is the fix for `tsc`.
3. `STALE_PROOF` and `GUARDED_PATH`/`GENESIS_GATE_CHANGE` are the classes that cannot be local:
   they need a re-run of the suite or a human approval. Do not fake them; name them.

## Memory

Recorded in the estate graph as `red-pr-classes-2026-11-15` with this path as the evidence.
