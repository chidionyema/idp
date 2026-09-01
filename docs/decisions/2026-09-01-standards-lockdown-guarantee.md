# 2026-09-01. The lock-down guarantee: how a declared standard can never silently drift again

Founder, 2026-09-01: "address all now, least possible steps, do the planning and close the loop
forever, never allow that to happen again, and tell me how it is guaranteed — I'll get my external
consultant to review. We possibly need to go further and lock things down more. We need a migration
risk taskforce to trace any obstacles in us changing or moving any of our critical systems,
including the whole estate and platform."

This document is written for that external review. It states what is guaranteed, by which
mechanism, what each mechanism cannot guarantee, and the least-steps plan that closes every gap.
Nothing in it is aspiration: each mechanism either exists today (named with its file) or is one of
the five numbered steps below.

## 1. The incident class being closed

A value that is a standard (the DNS zone, the GitHub organisation, the image registry, a budget
cap, a model lane, a schedule) was spelled as a literal in many files instead of read from one
declared place. The store carried 158 such lines for the zone alone. The platform had the right
mechanism since crew#269 — one value in `clusters/<cluster>/estate-config.yaml`, substituted
everywhere — but the rule was enforced by a gate that graded one directory of one repository.
A rule enforced by prose or by a partial gate is a wish (LAW 44). Sixteen of the estate's recorded
guard incidents are this same class: the gate landed after the code it should have graded.

## 2. The enforcement chain, and what each link guarantees

Five links. Each is independent: breaching the guarantee requires defeating all five, and four of
the five do not run on any machine an agent controls.

| # | link | mechanism | what it guarantees | what it cannot guarantee |
|---|---|---|---|---|
| 1 | Declarations are founder-only | GitHub **push ruleset** restricting file paths (`clusters/*/estate-config.yaml`, `estate-defaults.yaml`, `policy/**`, `scheduler/schedule.yml`, `platform/llm/config.yaml`, the guards repository), bypass list = the founder alone | GitHub's server refuses any push touching a declaration file from any token an agent holds. Server-side: no local hook, no agent error, no compromised laptop can get past it | Set once by the founder (step L2); until then this link is absent |
| 2 | A copy is refused at the door | `bin/estate-names-gate` grading only the lines a pull request adds; `rule=no_estate_name_added` in `policy/operating_model.rego`, running in the shared gate of idp, crew, hermes-v2 and prospector; made a **required check** by branch ruleset | No pull request that adds a literal can merge, in any estate repository; an exemption is a marked file plus the founder's written `APPROVE:` on that PR — loud, never silent | Grades only added lines (by design: old debt is swept, not blamed); requires the check to be required (step L2) |
| 3 | The founder is the only merger | Branch ruleset + standing ruling (agents never merge, permanent) | Every change on main carries his decision | A ruling is process, not physics; the ruleset (step L2) makes it server-side |
| 4 | Drift cannot sit unread | `.github/workflows/name-drift.yml`: every six hours, and on the estate clock, the gate grades **every repository's main** via the estate App; a red run lands in `delivery.failed_runs` of the estate state document, which every session is handed at start and may not contradict | Even a literal that somehow reaches main (force-push, ruleset gap, new repository) is surfaced within six hours as the red row every agent must read first | Detection, not prevention; six-hour window |
| 5 | It cannot run even if it lands | Kyverno admission policy on the cluster refusing any workload manifest carrying a declared name as a literal (step L3) | The cluster itself refuses to run drifted configuration — the last point where every input merges, per the estate's control ladder | Cluster workloads only; a script on a laptop is links 1–4's job |

**The self-proving property.** Every gate in the chain runs against a good and a bad fixture in the
same run that grades real code (`bin/idp-ci`, `name-drift.yml` first step, the rego tests). A gate
that stops refusing its bad fixture goes red itself. This closes the classic failure of guard
systems — silent green — which is the estate's second most recorded incident class (silent-green, 4).

**The guarantee, stated for review.** Once steps L1–L4 are merged and the founder has set the two
rulesets (L2): *no change that adds a hardcoded estate name can reach any main branch without the
founder's own written approval on that pull request; a breach of main by any other road is surfaced
red within six hours to every session and to the Ops dashboard; and a drifted manifest cannot be
admitted to the cluster at all.* The residual risks are listed in §4 — they are named, not hidden.

## 3. Least possible steps to close the loop (the whole plan is five items)

| # | step | who | size |
|---|---|---|---|
| L1 | The one shot: `estate-zone-gate` becomes `estate-names-gate`, reading **every** `ESTATE_*` key from estate-config (zone done today; add org, registry, cluster, alert chat id); one scripted sweep per repository turns every literal into a reference — the same pass that took the store from 158 to 0 today | agents, one branch per repository | the zone took one session; each remaining name is smaller |
| L2 | The rulesets: one push ruleset (declaration paths, bypass = founder) and one branch ruleset (required checks incl. the shared gate; merges = founder) at organisation level | founder, two `gh api` calls agents prepare verbatim | minutes |
| L3 | Admission: one Kyverno policy generated from the same declarations file, refusing a literal in any admitted manifest | agents, one branch | small |
| L4 | The laws into git: `rulings.json` moves to the guards repository with the same push-ruleset protection — today R67–R69 exist only on one laptop, which is this incident class happening to the rules themselves | agents, one branch | trivial, urgent |
| L5 | Standing: every `crew/docs/STANDARDS.md` row gains a `gate` column; a row without a gate is rendered as a wish on the page itself; the drift workflow runs each repository's declared gates, not only names | agents, one branch | moderate |

Nothing else. In particular: no new service, no new scanner, no second policy engine — every step
widens machinery that already runs (the gate, the rego policy, the drift workflow, Kyverno, Flux).

## 4. Residual risks, named for the consultant

1. **The founder's own account** is the bypass on every link; its compromise defeats the chain.
   Mitigation: passkeys (standards Identity row, unverified today) — a finding for the review.
2. **New value classes** are not protected until declared. That is the taskforce's job (§5): the
   register exists so "we did not know it was a standard" cannot recur.
3. **Prose and docs are exempt** by design; a doc can state a stale name. Graded a documentation
   defect, not a breach — docs do not run.
4. **The six-hour window** on link 4, and force-push scenarios between runs. Ruleset L2 disables
   force-push on main estate-wide, shrinking this to the window alone.
5. **Founder-approved exemptions** (the marked file) are deliberate holes, each carrying his
   written word on the PR; the drift run lists them so they cannot be forgotten.

## 5. The migration-risk taskforce (standing, generated, never hand-kept)

**Charter.** For every critical system, keep a live register answering: if the founder decided
tomorrow to change or move it — provider, name, host, cloud, whole estate — what stands in the way?
Each obstacle is traced to files by a gate-style measurement (the way the zone's 158 was counted),
filed as a tracked item, and burned down. The register is **generated** by a job, never edited by
hand, and rendered on the standards page and Backstage.

**Seed register, measured 2026-09-01.**

| system | move it means | obstacles today | state |
|---|---|---|---|
| DNS zone / domain | one value + reconcile | closed today (crew#796): 158→0, gate on three planes | GREEN |
| GitHub organisation | transfer 9 repositories | 61 owner files, 35 `uses:` lines, packages do not transfer, App re-install, Tailscale subject; planned as one `ORG` value + one wave | crew#785, planned |
| Image registry | retag + re-pull | 40 `ghcr.io/<owner>` mentions; pull secrets per namespace | crew#785 A6/B5 |
| Cloud / cluster | re-point Flux at any managed k8s | provider-coupled resources in `platform/oci` (the 58 counted on crew#516 CP6), OCI Vault as secret backend, object-storage buckets, instance principals | RED — largest single risk; portability gate (LAW 19) is the burn-down |
| Scheduler | clocks off the Mac | launchd jobs on one laptop; Dagster-on-cluster in flight | crew#716, in flight |
| Model providers | change a lane | one place already (`platform/llm/config.yaml`); stray vendor ids in agent configs | AMBER, L1 covers it |
| Messaging (Telegram) | change the channel | gateway is a Mac launchd job; chat ids hardcoded | AMBER, L1 + crew#516 CP4 |
| Secrets backend | change the vault | ESO abstracts consumers; the backend config is provider-coupled | AMBER |
| Payments (store) | change processor | not yet measured — first taskforce task | UNKNOWN |
| The laws themselves | survive any machine loss | `rulings.json` uncommitted on one laptop | RED — step L4 |

**Cadence.** The register regenerates on the estate clock beside the inventory run; a RED row that
ages without a tracked item is itself a red row on the Ops dashboard.

## What the founder decides

- `APPROVE: crew#802 lockdown` — starts L1, L3, L4, L5 as branches for his merge.
- L2 is his: two prepared commands, delivered as a `FOUNDER ACTION:` when L1's gate is green.
- The taskforce charter above: his word makes it standing (it is filed as its own crew item).
