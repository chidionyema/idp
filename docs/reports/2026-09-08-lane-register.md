# Lane register, 2026-09-08

Generated from the crew and idp issue lists, every remote branch touched since 2026-08-25 that is ahead of main, every worktree on the founder Mac, the spec files under docs/specs, and one live read of the cluster. Numbers are counts, not opinions. The commands are in the session that wrote it (e5728c64) and the raw lists in its scratchpad `map/` directory.

## 1. The lanes

| lane | spec and issue | open issues | unmerged branches / commits ahead | live state, measured | resume from |
|---|---|---|---|---|---|
| networking/CNI/fences | zero-trust-boundary.md, 2026-09-08-dataplane-root-cause-work-order.md; crew#539 (closed), #720 | 3 | 26 / 48 | FIRE: two CNIs, Flux 26/80, 92 pods on flannel addresses | `fix/calico-node-kubevirt-watch` (2, 09-08); `roll/wave-1-estate-apps-onto-calico` (2, 09-08); `fence/law-50s-own-grant-is-a-deny-on-the-wire` (2, 09-08) |
| shadow/ephemeral cluster | crew#892 Otto: verified, tree-searched fixes (the sandbox is CP4 of that spec; 0 boxes on the issue), #581 ephemeral trust (0/6), #720 brain-split blueprint (3/4) | 5 | 16 / 101 | staging 1/1 running; no sandbox or k3d namespace on the cluster | `feat/crew892-cp4-gvisor-sandbox` (6, 09-07); `sandbox/launch` (1, 09-07); `backup/20260903/feat/demo-sandbox` (7, 09-03) |
| gvisor cell | crew#892 CP4 (branch feat/crew892-cp4-gvisor-sandbox, 09-07), zero-trust-boundary.md steps 5-6 | 1 | 5 / 8 | RuntimeClass present, zero pods use it, node operator has no pods | `fix/nodesoftware-operator-never-applied` (1, 09-08); `fix/red-main-three-rungs` (1, 09-07); `backup/20260903/fix/crew301-main-image-builds-ne` (2, 08-29) |
| crossplane/oci/tofu | decision 0026; crew#740 inventory matrix, #736 | 10 | 91 / 232 | core 2/2, 21 CRDs, zero providers, zero managed resources | `wj1/the-agent-reaches-the-cluster-without-the-oc` (8, 09-08); `feat/crossplane-operator` (6, 09-08); `decision/crossplane-owns-day-2` (4, 09-08) |
| huggingface/model forge/edge | 2026-09-06-model-forge-edge-runtime.md; crew#513, #885 | 2 | 2 / 6 | no namespace; one compiled ExternalSecret; edge 4/5 | `forge/edge-runtime-v1` (4, 09-06); `forge/edge-runtime-v1-main` (2, 09-06) |
| otto/hermes | otto-answering-floor.md, otto-capability-inventory.md, otto-door-hands-and-senses.md, otto-five-capabilities-finished.md; crew#773 (0/7), #717, #13 | 40 | 52 / 142 | gateway 2/2, golden 2/2, hermes 2/2; probe, memory-store, reconciler jobs Error | `fix/golden-rehearses-the-door` (2, 09-08); `fix/one-source-for-the-lanes` (2, 09-08); `fix/memory-store-job-rerun` (1, 09-08) |
| llm router/cost | crew#795 squad model, #506 consultant review, #527 board science (4/5) | 39 | 58 / 153 | LiteLLM 3/3; DeepSeek $0, OpenRouter unfunded; cost fix on main, not applied | `fix/router-rate-limits` (3, 09-08); `feat/free-first-router` (2, 09-08); `fix/gemini-heads-no-chain` (2, 09-08) |
| backstage/portal/showcase | backstage-as-a-product.md (CP1-2 done, CP3-8 not), 2026-09-06-portal-100.md; crew#627 (0/7), #612 (0/6), #412, #883 | 25 | 106 / 364 | catalogue 2/2; unreachable: oauth2-proxy CrashLoopBackOff 14 | `feat/estate-autobot-surface` (12, 09-08); `audit/2026-09-07-product-audit` (11, 09-08); `chore/showcase-demo-clean` (2, 09-08) |
| jit/rbac/identity | key-ingest-door.md, two-hats-tenant-split.md; crew#832 (0/7), #581 | 14 | 57 / 127 | SPIRE 4/4, JIT 1/1; identity 0/2 | `wj7/the-signed-record-leaves-the-node` (5, 09-08); `rbac/agent-reader-sees-the-crds` (5, 09-08); `jit-ask-is-loud` (1, 09-08) |
| secrets/vault | vendor-key-activation.md, key-ingest-door.md; crew#832 | 9 | 38 / 79 | external-secrets 4/4, cannot sync over the broken Service path | `feat/intent-secret-capability` (3, 09-08); `backup/2026-09-08/docs/rotating-a-vendor-key` (1, 09-07); `fix/crew727-intervals-one-value` (4, 09-05) |
| observability/memory | hosted-session-memory.md; crew#853 CP4, #668, #258 | 4 | 26 / 62 | 9/13 deployments; snapshot job dead since 2026-08-27; memory observer out of allowance | `fix/langfuse-startup-probe-right-size` (5, 09-08); `fix/signoz-unstall-clickhouse` (2, 09-08); `fix/webhooks-restart-playbook` (3, 09-05) |
| scheduler/dagster/temporal | crew#396 (0/4), #567, #248, #792 | 16 | 41 / 114 | Dagster 5/5; Temporal 7/7 suspended on the founder's word; 1,967 Job warnings | `fix/dagster-limits-not-requests` (1, 09-08); `fix/dagster-runner-scope` (1, 09-08); `fix/dagster-cpu-throttling` (1, 09-08) |
| agents/workforce/research | client-context-ingest-and-session-runtime.md; crew#850 CP1-6 as #851-856, store #857-859, #609 product (0/5) | 64 | 75 / 235 | workforce and research pods not ready; CP issues #851-859 untouched | `feat/estate-checkpoint` (3, 09-07); `fix/estate-checkpoint-dry-run-is-not-throttled` (1, 09-07); `feat/kubeconform-before-merge` (6, 09-05) |
| gates/rules/process/ci | AGENTS.md rules.yaml; crew#739, #652 (0/5), #526 | 37 | 90 / 230 | freeze #739 unenforced; three merges under it today | `feat/nodesoftware-operator-image-automation` (6, 09-08); `fix/pipeverdict-header-list-is-measured` (4, 09-08); `fix/one-issue-per-fire-not-one-per-kustomization` (3, 09-08) |
| product/store/money | deepseek-work-order.md, deepseek-brief.md; crew#609, #32, #248 | 16 | 10 / 60 | prospector 4/4; scheduler unverified since 2026-08-16 | `spec/the-dual-engine-restores-w0-through-w5` (1, 09-08); `commerce/lago-can-recover` (1, 09-07); `fix/commerce-onto-estate-db` (1, 09-04) |
| voice gate/cyrus/warden/other infra | docs/marketing/products/voice-gate.md only | 2 | 11 / 15 | cyrus 1/1; no voice-gate namespace | `fix/cyrus-drop-webhook-alias` (1, 09-06); `backup/20260903/fix/the-judge-grades-the-pod-adm` (1, 08-30); `backup/20260903/fix/kyverno-judge-grep-q-sigpipe` (1, 08-29) |
| unclassified | - | 96 | 172 / 523 | session branches and founder pastes filed as issues | `feat/spectacular-demo-experience` (16, 09-08); `state/live-diagram` (9, 09-08); `fix/generator-rows-in-one-registry` (4, 09-08) |

Totals: 383 open crew issues, 876 unmerged branches carrying 2499 commits ahead of main, 74 worktrees.

## 2. Specs with no issue, issues with no branch

Spec files under docs/specs that reference no crew issue, so no checkpoint box can ever be ticked for them:

- `backstage-as-a-product.md` (last edit 2026-09-06): Backstage as a product: catalogue.\<zone\> for a buyer, not a link far
- `client-context-ingest-and-session-runtime.md` (last edit 2026-09-05): Client context ingest, and where an agent session runs
- `deepseek-brief.md` (last edit 2026-09-05): Brief for DeepSeek — paste this whole file
- `deepseek-work-order.md` (last edit 2026-09-05): The DeepSeek work order — one queue across three specs
- `hosted-session-memory.md` (last edit 2026-09-05): Session memory is hosted and sold, never a store on a machine
- `otto-five-capabilities-finished.md` (last edit 2026-09-05): Spec: the five Otto capabilities, finished and proved
- `two-hats-tenant-split.md` (last edit 2026-09-05): Two hats — the build spec
- `vendor-key-activation.md` (last edit 2026-09-05): API key lifecycle — the build spec
- `zero-trust-boundary.md` (last edit 2026-09-05): The zero-trust boundary — the build spec

Checkpoint issues whose number appears in no branch name and no worktree, so their work, if any, cannot be found from the issue:

- crew#865 (2026-09-05): One spec: cut shared fate at the edge, and make one-per-thing the rule
- crew#859 (2026-09-05): Store CP4 — checkout ends at a running capability, not at a pull request to revi
- crew#858 (2026-09-05): Store CP3 — connections are shown at the moment of choosing, not discovered late
- crew#857 (2026-09-05): Store CP1+CP2 — the catalogue prices itself, and the form stops being hand-copie
- crew#856 (2026-09-05): CP1 — the workforce runs as a Flow with state that survives the pod (crew#850)
- crew#855 (2026-09-05): CP6 — the company becomes departments the workforce staffs, as data (crew#850)
- crew#854 (2026-09-05): CP5 — CrewAI 1.9.3 to 1.15.20, with native planning, reasoning and evaluation (c
- crew#853 (2026-09-05): CP4 — one memory, scoped per department, on the estate's own layer (crew#850)
- crew#852 (2026-09-05): CP3 — the authority boundary becomes an enforced control, not an absent tool (cr
- crew#851 (2026-09-05): CP2 — the estate answers for itself: MCP tools replace the hand-written client (
- crew#833 (2026-09-04): crew#832 CP3, corrected: the key warden runs as a drill, not as a pushgateway jo
- crew#793 (2026-09-01): INC4 register row: commerce, commerce-data and event-bus Flux rows are dark by d
- crew#792 (2026-09-01): INC3 register row: temporal Flux row is suspended on the founder's word (2026-08
- crew#770 (2026-08-31): Otto roadmap — platform to embodiment (critical estate project, NOT yet starting
- crew#739 (2026-09-08): FREEZE: nothing is released (founder, 2026-08-31)

## 3. Uncommitted work on the founder Mac

| files | last commit | branch | worktree |
|---|---|---|---|
| 14 | 2026-09-08 | `feat/idp-lands-its-own-green-pull-requests` | `idp` |
| 6 | 2026-09-08 | `fix/one-issue-per-fire-not-one-per-kustomization` | `wt-noise` |
| 3 | 2026-09-08 | `fix/admission-webhooks-survive-a-node` | `wt-webhook-ha` |
| 3 | 2026-09-07 | `fix/one-button-family` | `wt-portal` |
| 1 | 2026-09-07 | `catalog/fold-agent-ledger-shards` | `wt-catalog` |
| 1 | 2026-09-07 | `feat/portal-one-glance-search` | `wt-portal-search` |

## 4. Where the context of every session lives

Thirteen recovery files, one per session, rewritten after every turn by the estate hook:
`~/.claude/projects/-Users-chidionyema-dev-code-idp/checkpoints/RECOVERY-<session>.md`. Each holds
the founder's asks verbatim, the last thing the session said, the files it wrote, its last
commands and its git state. That is the context. No transcript needs reading to recover a lane.

## 5. The recovery procedure, one lane at a time

1. Open the lane's row above. Its spec and issue are the contract; if the spec has no issue
   (section 2), file the issue first with the spec's checkpoints as boxes, then continue.
2. Take the newest branch in `resume from`, rebase it on main, open its pull request as a draft
   naming the issue and the checkpoint it serves. The other branches in that lane are either
   folded into it or deleted the same day; a branch that is not on the register does not exist.
3. Commit or discard every dirty worktree in section 3 before any new work starts there.
4. Tick a box only on the done command in the spec, run on the cluster, output quoted on the
   issue. A box with no quoted output is unticked by the register on its next run.
5. Regenerate this register (the script in session e5728c64's scratchpad, to be moved to `bin/`)
   and it must show the lane's branch count going down and its box count going up. If it does
   not, the lane did not move, whatever the session said.

Nothing moves on the cluster until the dataplane work order
(`docs/specs/2026-09-08-dataplane-root-cause-work-order.md`) reaches Flux 80 True. Every lane
above resumes at that moment from its `resume from` cell.

