# 2026-09-01. Every repository moves to the Mumchimp organisation, then to our own runners, then private

Founder, 2026-09-01, three messages: every repository goes private; "the problem is not
public/private, we get private for free anyway, the issue is build minutes 2000/3000 per month, the
failure rate currently means we are going to hit limits pretty fast. Our verification needs looking
at. Our ways of working need to align with our reality"; "we have new org mumchimp, need to plan the
move; I need exact plan and need to know changes required before sign-off"; and "agents cannot be
committing using my identity, we need agents to have their own" (crew#789, more rulings to come).

This is the plan for sign-off. Nothing in it has been executed. It replaces the earlier
"every repository goes private" note, whose emphasis on the private switch was wrong: private is free
on every plan; the constraint is minutes, and the fence.

**Reviewed 2026-09-01 16:xxZ** by the engineering, operations and finance specialists and by the live
peer session code-f9 (code-0c was asked and had not answered at the time of writing). They found
four blockers and nine smaller gaps; every one is folded in below and marked *(review)*. The two
decisions the review changed: the order (move while public, go private last, so the move never
depends on the runners) and the runner cost (it does not fit under the cluster's $50 cap; the
founder decides the cap, section 5).

## 1. What is true today (read at 16:0xZ from GitHub, not from memory)

- The organisation `Mumchimp` exists, plan **free**, 0 repositories, the founder is its admin.
- The personal account holds the nine repositories that run the estate: idp, prospector, crew,
  hermes-v2, infra-crew, hermes-agent, estate, claude-guards, claude-estate (30 public, 3 private in
  all). idp carries four active rulesets (estate-default-branch-protection, estate-security-scan,
  founder-only-releases, idp-required-checks); they are the whole of "only the founder merges".
- **Minutes.** GitHub Free for organisations includes 2,000 Actions minutes a month, GitHub Team
  3,000, and "GitHub Actions usage is free for self-hosted runners" on every plan (vendor plans
  page, read today). Minutes are only billed on **private** repositories; public repositories run
  free on every plan. So the allowance is a constraint on going private, not on moving. The estate's
  measured use is **2,981 billed job-minutes in 24 hours** (crew#785, every job's
  `completed_at - started_at` rounded up, five repositories, 2026-09-01 15:1xZ). Either allowance is
  spent before the first day ends, waste or no waste.
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
- **What the money says** *(review, finance)*. At today's burn a private estate on GitHub-hosted
  runners overruns the Team allowance by about 87,000 minutes a month: **$456 to $547 a month** at
  the vendor's per-minute rates (arm64 to x64); after the waste cuts below, still **$261 to $313**.
  The cluster's own budget has no room: `estate-defaults.yaml` sets `monthly_cap_usd: 50` and
  `node_pool.budget_monthly_usd: 50`, the declared spend is $49.54, headroom **$0.46**, and the one
  worker node (`VM.Standard.A1.Flex`, 6 OCPU, 24 GB, `free_ocpus: 2`) is shared with every
  workload. A second node of the same shape is about **$70 a month**. A GitHub Team seat is $4 a
  month per human; Apps and bots take none.
- **Identity.** Of the last 200 commits on idp main, 109 are authored as the founder, 77 as
  `estate-agents[bot]`, 13 as his noreply address; on crew, 140 as him, 59 as his noreply, none as
  the bot. The estate already has one GitHub App, `estate-agents` (contents, pull requests, issues,
  workflows, actions: write), with six lanes in `platform/github-app/lanes.json`.
- **What names the current owner** (the change list is only exact if this is; the review found the
  first count short, so this is the full one). In workflows: `uses: chidionyema/idp/...` in 35 lines
  across crew, hermes-v2 and prospector (spec-gate 11, security-scan 11, operating-model-gate 10,
  wake-blocked 3); 19 of 36 idp workflow files, 5 of 11 crew, 5 of 6 hermes-v2. Images:
  `ghcr.io/chidionyema/<image>` for **10** images (backstage, estate-mcp, hermes-agent,
  idp/estate-catalog, idp/estate-db, idp/estate-state, mirror/external-dns, prospector-store-api,
  prospector-store-web, sovereign-worker) in cluster manifests, the five Flux ImageRepository files
  under `platform/image-automation/`, and Dockerfiles. Git and OCI sources: the Flux git source
  `ssh://git@github.com/chidionyema/idp` (`clusters/oke/flux-system/gotk-sync.yaml`); OCI
  artefacts at `oci://ghcr.io/chidionyema/...` in `clusters/oke/catalog.yaml:11`,
  `platform/mcp/estate-mcp.yaml:49,108` and `platform/hermes-agent/estate.yaml:112`. Configuration
  that names the owner *(review)*: `backstage/app-config.container.yaml:173-176` (prospector
  catalogue URL), `platform/alerts-github/provider-github.yaml:15` (Flux dispatch target),
  `platform/image-automation/backstage.yaml:48` (the `idp-writer`/`flux-writer` author identity),
  `platform/hermes-agent/estate.yaml:20,58,113` (Otto's repository list), `platform/mcp/estate-mcp.yaml:64`,
  `.github/workflows/kini-finish.yml:55` (commits as his `user.name`), the `project-slugs` in every
  `catalog-info.yaml`, `estate-state.yml`; **70 lines of configuration and code in idp** by the
  review's sweep. Identity that names the owner: the Tailscale federated subject
  `repo:chidionyema@377396/idp@1344360654` in `clusters/oke/estate-config.yaml:36-42`, which the
  transfer breaks (a subject is a string, not a redirect). Outside git: 102 local checkouts whose
  `origin` is `chidionyema/...`; prose, idp 189 files, crew 485, hermes-v2 101, claude-guards 134
  (the vendor redirect covers those; second pass).
- **What a transfer keeps** (vendor page "Transferring a repository", read today): issues, pull
  requests, wiki, stars, watchers, webhooks, secrets, deploy keys, git history, LFS; "all links to the
  previous repository location are automatically redirected"; collaborators reset to the
  organisation's defaults; packages "may lose their repository link"; and "if you create a new
  repository or fork at the previous repository location, the redirects ... will be permanently
  deleted". "Private repositories transferred to GitHub Free accounts lose features like protected
  branches." The call is `POST /repos/{owner}/{repo}/transfer` with `new_owner`, answers 202, and a
  transfer into an organisation where the caller may create repositories needs no acceptance.
- **What the transfer does not carry** *(review)*: the ghcr packages (they stay under his account
  until the first build publishes under the organisation); an organisation-scoped runner serves
  only repositories in that organisation, so a `runs-on` pointed at it before the transfer has no
  runner; the Tailscale federated subject above; the App installation, which is per account.

## 2. The decision

- **Order: move first, while public; cut the waste; then runners; private last.** Public
  repositories bill no minutes on any plan, so the move to Mumchimp costs nothing and blocks on
  nothing. Going private is the step that needs the runners, so it is last, and it is the step the
  probe grades. *(review, operations: the first draft flipped visibility and `runs-on` in the same
  hour as the transfer, which darkens every gate if the runners are late.)*
- **Plan: GitHub Team on Mumchimp, one seat (the founder).** Free loses protected branches and
  rulesets on private repositories, which deletes the merge fence. $4 a month.
- **Minutes: our own runners on the cluster**, GitHub's actions-runner-controller (mature tool, Helm
  chart, no script of ours), registered to the organisation through the estate App, every
  workflow's `runs-on` pointed at them. The review found three things the first draft missed:
  1. **They do not fit under today's cap** *(finance)*. Two runner pods at 1 CPU / 2 GB each need
     the second node; the second node is $70 a month against $0.46 of headroom. The founder decides
     the cap (section 5): raise `monthly_cap_usd` and `node_pool.budget_monthly_usd` to **$120**,
     or stay on GitHub-hosted and pay $261 to $313 a month after the waste cuts. The
     recommendation is the node: it is a fifth of the price, it is ours, and it is the buyer's
     "self-hosted CI" row.
  2. **The node is arm64 and four workflows download x86 tools** *(engineering)*: `ci.yml`,
     `verify-claims.yml`, `operating-model-gate.yml`, `estate-inventory.yml` fetch `linux_amd64`
     binaries. Each gets `uname -m` detection before the flip; `build-multiarch` keeps QEMU.
  3. **A cluster outage must not take the gates with it** *(operations)*. `ci.yml` and
     `oke-check.yml` keep a GitHub-hosted fallback label (`runs-on` group with `ubuntu-latest` as
     the break-glass, chosen by a repository variable, never by editing the workflow during an
     incident); the runner namespace gets the fence (default-deny, ResourceQuota, limits) and a
     PrometheusRule on `runners_available == 0` for longer than ten minutes, routed to the channel
     he reads.
- **Waste: cut the day roughly in half before going private**, so the runners are not carrying
  garbage. `flux-events` **stays** *(review, engineering: it is the only live Flux alarm; it opens
  and closes the `P0: Flux cannot reconcile` issue, and `platform/alerts/alert.yaml:14` is
  suspended)*; what changes is `platform/alerts-github/alert.yaml:10`, `eventSeverity: info` to
  `error`, so only a failing reconcile dispatches a run, not every successful one. `otto-parity`
  and `verdict-signoz` stop being scheduled until the reason for 40 straight reds is fixed, and
  their rows in `drills/catalogue.yaml` get `pending: true` so the Ops page prints n/a instead of
  red *(review, operations)*. Agents do not `workflow_dispatch` gates to iterate (local proof
  first, R57; one push wave, one CI run). The `ci` concurrency cancel stays. Revised saving: about
  **1,200 of idp's 2,498 billed minutes a day** (flux-events near all of 557, red repeats 239,
  cancelled ci 203, hand-dispatched verdict runs about 200), not the 1,300 first claimed.
- **Schedules to the estate clock** *(review, operations)*: 9 of idp's 22 `schedule:` workflows
  are not in the dispatcher's WORKFLOWS list (`platform/drills/drill-dispatcher.yaml:230`), so
  moving them is a list edit plus a catalogue row each, not a new mechanism.
- **Identity: agents commit as `estate-agents[bot]`** with a lane token, never as him (crew#789).
  Lane tokens cannot merge on protected branches, so "agents never merge" becomes something GitHub
  enforces. `kini-finish.yml:55` and `image-automation/backstage.yaml:48` stop writing as him.

## 3. The exact order, with the change each step needs

**Step 0. Founder, two actions, before anything else.** Upgrade Mumchimp to GitHub Team (billing is
his). Install the `estate-agents` App on Mumchimp (one tap on the App's install page). The vault
then records the new installation id with `bin/idp-github-app installation`, **after** that command
learns to pick the installation whose `account.login` is `Mumchimp` *(review, operations: today it
takes `.[0].id`, line 157, and with the App on both accounts that is a coin toss)*.

**Step 1. Crew, on his word, while the repositories are still public and personal.** Each item is one
branch per repository, green on its own gates, merged by him; all are harmless before the move.

| # | change | where | size |
|---|---|---|---|
| 1 | Owner rename, the full inventory from section 1: 35 `uses:` lines; 10 images in manifests, the 5 ImageRepository files and Dockerfiles; `gotk-sync.yaml`; the 3 OCI artefact URLs; app-config prospector URL; provider-github target; the Otto repository list; catalog-info project-slugs; estate-state.yml; the 70 idp lines. Each written so the redirect covers the hour between merge and flip (a public repository answers under both names) | idp, crew, hermes-v2, prospector, claude-guards, infra-crew | one scripted pass, one diff per repository, grader: `grep -rIl "chidionyema/" --exclude-dir=docs` is empty on each |
| 2 | `bin/idp-github-app installation` filters by `account.login`; `bin/idp-github-app token` unchanged | idp `bin/idp-github-app` | one function, one fixture |
| 3 | Private-readiness fixes: App token on the 13 cross-repository checkouts, GITHUB_TOKEN into the catalogue pod for Backstage, hermes-v2 Dockerfile clone via build secret, ssh clones in bootstrap and onboarding, fail-loud where a token is optional today; **and an `imagePullSecrets` on `platform/hermes-agent/gateway.yaml:279`** and every other pod pulling `ghcr.io` that has none today, so the package-private switch later cannot black-hole a pull *(review)* | crew 2 files, hermes-v2 2, idp 7, scripts 2 | small, each with its test |
| 4 | Identity: `git config user.name/user.email` to the bot in every agent worktree (one pass over the 102 checkouts), pushes over `bin/idp-github-app token <lane>`, pre-push refuses an agent push authored as him; `kini-finish.yml:55` and `image-automation/backstage.yaml:48` to the bot | claude-guards (the pre-push rung), `~/.claude/scripts`, idp 2 files | one pass plus one guard with its two fixtures |
| 5 | Waste: `alerts-github/alert.yaml` `eventSeverity: error`; unschedule `otto-parity` and `verdict-signoz` with `pending: true` on their catalogue rows; add the 9 uncovered schedules to the dispatcher WORKFLOWS list with a catalogue row each; 6 crew and 2 hermes-v2 schedules likewise where they are drills | idp `platform/alerts-github`, 2 workflows, `drills/catalogue.yaml`, `platform/drills/drill-dispatcher.yaml` | about 1,200 of idp's 2,498 minutes a day |
| 6 | Runners: HelmRelease for actions-runner-controller in `platform/runners/`, org-scoped runner scale set registered via the App, own namespace with the fence, PrometheusRule for zero runners, `uname -m` detection in the four x86-download workflows, fallback label on `ci.yml` and `oke-check.yml` chosen by repository variable. `runs-on` in every workflow points at the label **but the branch is merged only in step 3, after the transfer**, because the runners serve organisation repositories only | idp (36 workflows), crew (11), hermes-v2 (6), prospector, claude-guards, infra-crew (2); `estate-defaults.yaml` and `platform/oci/variables.tf` for the second node | one HelmRelease, one sed pass over `runs-on:`, four arch fixes |
| 7 | Probe: `~/.claude/scripts/estate/repo_must_be_private.py` extended to the nine repositories and to the new owner, so the private flip has a grader | claude-guards | one file |

**Step 2. Founder merges** branches 1 to 5 and 7. Branch 6 waits.

**Step 3. The move, one pass, from his login, one line per repository, while everything stays public.**
`gh api -X POST repos/chidionyema/<r>/transfer -f new_owner=Mumchimp` for the nine repositories (202
each; no acceptance step for an organisation he administers); then
`gh api -X PUT repos/Mumchimp/idp/actions/permissions/access -f access_level=organization` (and the
same for claude-guards) so the reusable workflows keep working; then the 102 local remotes in one
pass (`git remote set-url origin` per checkout); then, **his console step, the one R52 allows**:
re-register the Tailscale federated subject for `Mumchimp/idp` (the old subject names his account
and the transfer does not carry it) and update `estate-config.yaml:36-42` in the same hour. Then he
merges branch 6 (runners), and the cluster budget change if he chose the node. Deploy keys and
secrets travel with the repository; Flux keeps reading (redirect plus the new URL from step 1).

**Step 4. Prove the move in the same hour** (two angles each): one empty push to each repository runs
its gates green on a runner named `oke-...` in the run log; the fallback label runs one job green on
`ubuntu-latest` (break-glass proved, not assumed); the catalogue's prospector entry still renders;
Flux has applied the declared state since the move; the hourly login drill stays green; the four
rulesets are listed on `Mumchimp/idp` (the vendor page does not promise they travel, so this is
checked); the Tailscale-backed drill passes; a `git log` of the first agent commit after the move
shows `estate-agents[bot]`; a `git push` authored as him from an agent worktree is refused.

**Step 5. Private, once step 4 is green for a full day.** `gh repo edit Mumchimp/<r> --visibility
private` for the nine; the probe answers 404 for all nine under the old owner and private under
the new; every gate runs on our runner (a GitHub-hosted minute now bills). Package visibility is a
separate, later switch (section 4).

**Step 6. Never create a repository at an old name.** That deletes every redirect (vendor page).

## 3b. Rollback *(review, operations: the first draft had none)*

- **Transfer**: `POST repos/Mumchimp/<r>/transfer -f new_owner=chidionyema` is the same call in
  reverse; redirects follow the repository, so links and remotes keep resolving during the hour.
- **Rename branch (1)**: `git revert` of one merge per repository; every line was written to work
  under both names while the redirect stands, so the revert is safe in either state.
- **Runners (6)**: the fallback label is the rollback; flipping the repository variable puts every
  gate back on GitHub-hosted runners without a commit.
- **Private (5)**: `gh repo edit --visibility public`; the probe turns red on purpose until the
  founder says so.
- **Old-name guard**: the probe also refuses green if any repository exists under `chidionyema/<r>`
  again, so a rollback that recreates a name is caught the same hour.

## 4. Deliberately not in this move

- Making the ghcr packages private: separate switch after step 5; images are published under
  `ghcr.io/mumchimp` by the first build after the move, and every namespace that pulls them carries
  a pull secret first (branch 3).
- Moving prose links (189 + 485 + 101 + 134 files): the redirect covers them; one lazy pass later.
- Anything the founder's further rulings on agent identity change (crew#789).
- A cluster-wide alerting change: the runner alarm above is one PrometheusRule on the existing
  route, not a new channel.

## 5. What the founder signs

Two words, because one is money:

- `APPROVE: crew#785 org move` starts step 1 (seven branches, nothing on the cluster, nothing on the
  account). Steps 0, 3 and 5 are his hands; steps 2 and 4 are his word and the probe's output.
- `APPROVE: crew#785 cap 120` raises the cluster's monthly cap from $50 to $120 for the runner
  node (about $70 a month, against $261 to $313 a month of GitHub-hosted overage after the waste
  cuts). Without it, branch 6 is not written and step 5 (private) does not happen; the estate
  moves to the organisation and stays public.

## Evidence

- Org: `gh api orgs/mumchimp` (plan free, total_private_repos 0); role: `gh api orgs/mumchimp/memberships/chidionyema` (admin).
- Rulesets: `gh api repos/chidionyema/idp/rulesets` (four, active).
- Billed minutes by workflow and outcome: minutes.py (every job of every run, quoted on crew#785), 2026-09-01 16:1xZ; triggers and run counts: runs.py, same comment.
- Owner mentions: `grep -rIl "chidionyema/"` per checkout; `uses:` and `ghcr.io` counts from the same sweep; the review's 70-line idp sweep excluded docs.
- Cluster cost: `estate-defaults.yaml:8-16`, `platform/oci/variables.tf` (6 OCPU / 24 GB / 2 free), `platform/oci/main.tf:34,69` (A1.Flex); hosted overage from the measured 24-hour burn times 30 at the vendor's published per-minute rates.
- Flux alarm: `.github/workflows/flux-events.yml:54-72` (opens the P0 on `severity == error`); `platform/alerts-github/alert.yaml:10` (`eventSeverity: info`); `platform/alerts/alert.yaml:14` (suspended).
- x86 downloads: `grep -ln linux_amd64 .github/workflows/*.yml` (four files).
- Installation pick: `bin/idp-github-app:157`.
- Vendor pages read today: GitHub plans; Transferring a repository; REST "Transfer a repository".
- Commit authorship: `git log --format='%an <%ae>' -n 200 | sort | uniq -c` on idp and crew.
- Reviews: crew#785, comments of 2026-09-01 (engineering, operations, finance, code-f9).
