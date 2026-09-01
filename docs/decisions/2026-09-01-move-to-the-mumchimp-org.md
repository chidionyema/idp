# 2026-09-01. Every repository moves to the Mumchimp organisation, private, on our own runners

Founder, 2026-09-01, three messages: every repository goes private; "the problem is not
public/private, we get private for free anyway, the issue is build minutes 2000/3000 per month, the
failure rate currently means we are going to hit limits pretty fast. Our verification needs looking
at. Our ways of working need to align with our reality"; "we have new org mumchimp, need to plan the
move; I need exact plan and need to know changes required before sign-off"; and "agents cannot be
committing using my identity, we need agents to have their own" (crew#789, more rulings to come).

This is the plan for sign-off. Nothing in it has been executed. It replaces the earlier
"every repository goes private" note, whose emphasis on the private switch was wrong: private is free
on every plan; the constraint is minutes, and the fence.

## 1. What is true today (read at 16:0xZ from GitHub, not from memory)

- The organisation `Mumchimp` exists, plan **free**, 0 repositories, the founder is its admin.
- The personal account holds the nine repositories that run the estate: idp, prospector, crew,
  hermes-v2, infra-crew, hermes-agent, estate, claude-guards, claude-estate (30 public, 3 private in
  all). idp carries four active rulesets (estate-default-branch-protection, estate-security-scan,
  founder-only-releases, idp-required-checks); they are the whole of "only the founder merges".
- **Minutes.** GitHub Free for organisations includes 2,000 Actions minutes a month, GitHub Team
  3,000, and "GitHub Actions usage is free for self-hosted runners" on every plan (vendor plans
  page, read today). The estate's measured use is **2,981 billed job-minutes in 24 hours** (crew#785,
  every job's `completed_at - started_at` rounded up, five repositories, 2026-09-01 15:1xZ). Either
  allowance is spent before the first day ends, waste or no waste.
- **Where the minutes go and what is wasted** (every job of every run in the last 24 hours, all
  seven repositories, billed as GitHub bills: job wall time rounded up to the minute; idp's listing
  is capped at 1,000 runs by the API, so idp is understated). Total **3,139 billed job-minutes in
  24 hours**.

  | repository | billed job-minutes | of which not green |
  |---|---|---|
  | idp | 2,498 | 780 (31%): 508 failed, 272 cancelled |
  | prospector | 302 | 38 (13%) |
  | crew | 184 | 29 (16%) |
  | hermes-v2 | 79 | 10 (13%) |
  | claude-guards | 62 | 9 (15%) |
  | estate | 10 | 0 |
  | infra-crew | 4 | 2 |

  The largest sinks, idp: `flux-events` **557 runs, 557 minutes** in one day (one workflow run per
  Flux notification over `repository_dispatch`, 22% of idp's minutes, every one green, so nobody
  looks); `ci` 56 runs, 917 minutes, of which 9 failed pull-request runs cost 167 minutes and 20
  cancelled runs cost 203; `estate-state` 63 dispatched runs, 126 minutes. Red on repeat:
  `otto-parity` failed 16 of 16 runs (88 min), `verdict-signoz` failed 15 of 15 (46 min),
  `oke-check` failed 5 (105 min). Triggers on idp: 556 repository_dispatch, 180 workflow_dispatch
  (agents dispatching gates by hand), 121 pull_request, 56 push, 45 schedule.
- **Identity.** Of the last 200 commits on idp main, 109 are authored as the founder, 77 as
  `estate-agents[bot]`, 13 as his noreply address; on crew, 140 as him, 59 as his noreply, none as
  the bot. The estate already has one GitHub App, `estate-agents` (contents, pull requests, issues,
  workflows, actions: write), with six lanes in `platform/github-app/lanes.json`.
- **What names the current owner** (a count, so the change list is exact): `uses: chidionyema/idp/...`
  in 35 workflow lines across crew, hermes-v2 and prospector (spec-gate 11, security-scan 11,
  operating-model-gate 10, wake-blocked 3); `ghcr.io/chidionyema/<image>` 37 mentions of 8 images in
  cluster and build files; the Flux git source `ssh://git@github.com/chidionyema/idp`
  (`clusters/oke/flux-system/gotk-sync.yaml`); 19 of 36 idp workflow files, 5 of 11 crew, 5 of 6
  hermes-v2; 102 local checkouts whose `origin` is `chidionyema/...`; and in prose, idp 189 files,
  crew 485, hermes-v2 101, claude-guards 134 (the vendor redirect covers those; second pass).
- **What a transfer keeps** (vendor page "Transferring a repository", read today): issues, pull
  requests, wiki, stars, watchers, webhooks, secrets, deploy keys, git history, LFS; "all links to the
  previous repository location are automatically redirected"; collaborators reset to the
  organisation's defaults; packages "may lose their repository link"; and "if you create a new
  repository or fork at the previous repository location, the redirects ... will be permanently
  deleted". "Private repositories transferred to GitHub Free accounts lose features like protected
  branches." The call is `POST /repos/{owner}/{repo}/transfer` with `new_owner`, answers 202, and a
  transfer into an organisation where the caller may create repositories needs no acceptance.

## 2. The decision

- **Plan: GitHub Team on Mumchimp, one seat (the founder).** Free loses protected branches and
  rulesets on private repositories, which deletes the merge fence. GitHub Apps and bots take no seat;
  human crew take one each. Cost is his to see on the billing page; the plan page does not print it.
- **Minutes: our own runners on the cluster**, GitHub's actions-runner-controller (mature tool, Helm
  chart, no script of ours), registered to the organisation through the estate App, every workflow's
  `runs-on` pointed at them. Self-hosted minutes are free on every plan. Risk, one sentence: the
  OKE nodes are arm64 and shared with the workloads, so runner pods get a ResourceQuota of their
  own and `build-multiarch` keeps QEMU; if a workflow needs x86 only, it is named on the board
  before the flip, not discovered after.
- **Waste: cut the day roughly in half before the flip**, so the runners are not carrying garbage:
  `flux-events` stops dispatching a workflow per event (the event goes to the collector, LAW 50,
  and the Ops page reads it there); `otto-parity` and `verdict-signoz` stop being scheduled until
  the reason for 40 straight reds is fixed (a red instrument nobody reads); agents do not
  `workflow_dispatch` gates to iterate (local proof first, R57; one push wave, one CI run); the
  `ci` concurrency cancel stays.
- **Identity: agents commit as `estate-agents[bot]`** with a lane token, never as him (crew#789).
  Lane tokens cannot merge on protected branches, so "agents never merge" becomes something GitHub
  enforces.

## 3. The exact order, with the change each step needs

**Step 0. Founder, two actions, before anything else.** Upgrade Mumchimp to GitHub Team (billing is
his). Install the `estate-agents` App on Mumchimp (one tap on the App's install page; the vault then
records the new installation id with `bin/idp-github-app installation`).

**Step 1. Crew, on his word, while the repositories are still public and personal.** Each item is one
branch per repository, green on its own gates, merged by him; all are harmless before the move.

| # | change | where | size |
|---|---|---|---|
| 1 | Runners: HelmRelease for actions-runner-controller in `platform/runners/`, org-scoped runner scale set registered via the App, its own namespace with the fence (default-deny, quota, limits); `runs-on: [self-hosted, oke]` in every workflow | idp (36 workflows), crew (11), hermes-v2 (6), prospector, claude-guards, infra-crew (2) | one sed pass over `runs-on:` plus one HelmRelease |
| 2 | Owner rename: `uses: chidionyema/idp/` becomes `uses: Mumchimp/idp/`; `ghcr.io/chidionyema/` becomes `ghcr.io/mumchimp/` in cluster manifests, Flux ImageRepository objects (`platform/image-automation`, 5 files) and Dockerfiles; `gotk-sync.yaml` git URL | 35 `uses:` lines, 37 image mentions, 1 git URL | one scripted pass, reviewed as one diff per repository |
| 3 | Private-readiness fixes 1 to 5 from the earlier note: App token on the 13 cross-repository checkouts, GITHUB_TOKEN into the catalogue pod for Backstage, hermes-v2 Dockerfile clone via build secret, ssh clones in bootstrap and onboarding, fail-loud where a token is optional today | crew 2 files, hermes-v2 2, idp 6, scripts 2 | small, each with its test |
| 4 | Identity: `git config user.name/user.email` to the bot in every agent worktree (one pass over the 102 checkouts), pushes over `bin/idp-github-app token <lane>`, pre-push refuses an agent push authored as him | claude-guards (the pre-push rung), `~/.claude/scripts` | one pass plus one guard with its two fixtures |
| 5 | Waste: remove the `flux-events` dispatch (the Flux notification Provider of kind `githubdispatch`) and read events from the collector; unschedule `otto-parity` and `verdict-signoz` until fixed; move the 22 idp, 6 crew, 2 hermes-v2 scheduled workflows to the estate clock where they are drills | idp `platform/flux-notifications`, the two workflows, schedules | the largest saving: about 1,300 of idp's 2,498 billed minutes a day (flux-events 557, red repeats 239, cancelled ci 203, hand-dispatched verdict runs) |
| 6 | Probe: `~/.claude/scripts/estate/repo_must_be_private.py` extended to the nine repositories and to the new owner, so the flip has a grader | claude-guards | one file |

**Step 2. Founder merges** the branches from step 1.

**Step 3. The flip, one pass, from his login, one line per repository.**
`gh api -X POST repos/chidionyema/<r>/transfer -f new_owner=Mumchimp` for the nine repositories (202
each; no acceptance step for an organisation he administers); then
`gh repo edit Mumchimp/<r> --visibility private`; then
`gh api -X PUT repos/Mumchimp/idp/actions/permissions/access -f access_level=organization` (and the
same for claude-guards) so the reusable workflows keep working; then the 102 local remotes in one
pass (`git remote set-url origin` per checkout). Deploy keys and secrets travel with the repository;
Flux keeps reading (redirect plus the new URL from step 1).

**Step 4. Prove it in the same hour** (two angles each): the probe answers 404 for all nine under the
old and private under the new owner; one empty push to each repository runs its gates green on a
runner named `oke-...` in the run log; the catalogue's prospector entry still renders; Flux has
applied the declared state since the flip; the hourly login drill stays green; the four rulesets are
listed on `Mumchimp/idp` (the vendor page does not promise they travel, so this is checked, not
assumed); a `git log` of the first agent commit after the flip shows `estate-agents[bot]`.

**Step 5. Never create a repository at an old name.** That deletes every redirect (vendor page).

## 4. Deliberately not in this move

- Making the ghcr packages private: separate switch; images are published under `ghcr.io/mumchimp`
  by the first build after the flip, and every namespace that pulls them carries `ghcr-pull` first.
- Moving prose links (189 + 485 + 101 + 134 files): the redirect covers them; one lazy pass later.
- Anything the founder's further rulings on agent identity change (crew#789).

## 5. What the founder signs

`APPROVE: crew#785 org move` starts step 1 (six branches, nothing on the cluster, nothing on the
account). Steps 0 and 3 are his hands; steps 2 and 4 are his word and the probe's output.

## Evidence

- Org: `gh api orgs/mumchimp` (plan free, total_private_repos 0); role: `gh api orgs/mumchimp/memberships/chidionyema` (admin).
- Rulesets: `gh api repos/chidionyema/idp/rulesets` (four, active).
- Billed minutes by workflow and outcome: minutes.py (every job of every run, quoted on crew#785), 2026-09-01 16:1xZ; triggers and run counts: runs.py, same comment.
- Owner mentions: `grep -rIl "chidionyema/"` per checkout; `uses:` and `ghcr.io` counts from the same sweep.
- Vendor pages read today: GitHub plans; Transferring a repository; REST "Transfer a repository".
- Commit authorship: `git log --format='%an <%ae>' -n 200 | sort | uniq -c` on idp and crew.
