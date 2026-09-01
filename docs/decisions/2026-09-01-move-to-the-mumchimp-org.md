# 2026-09-01. The estate moves to the Mumchimp organisation in one swoop

Founder, 2026-09-01, in order: "the issue is build minutes 2000/3000 per month, the failure rate
currently means we are going to hit limits pretty fast"; "agents cannot be committing using my
identity, we need agents to have their own" (crew#789); "regarding org move, needs more planning.
org philosophy is asymmetry. few least steps to get everything done in one swoop with no or minimal
disruption" (R68); "either way all current open work need to ship and close before org is moved".

This is version 3, for sign-off. Nothing in it has been executed. Version 2 (peer-reviewed by
engineering, operations, finance and code-f9) had the right facts and the wrong shape: five steps
spread over days. This version keeps the facts (appendix) and reshapes the work to his word: do
every step that does not depend on the new name first, quietly, then one cutover.

## The problem in three sentences

GitHub counts build minutes only on private repositories; public ones build free on every plan. We
burn about 3,000 minutes a day, and a private organisation is given 2,000 (Free) or 3,000 (Team) a
month, so a private estate on GitHub's machines stops building before the first day ends. The way
out is our own build machines on the cluster, where minutes are free; that needs one more node.

## The shape: prepare everything, then one hour

**Phase A. Prepare, invisible, no disruption.** Every item here works under the old name and the
new one, so it can merge now and nothing changes for anyone.

| # | what | why it is name-independent |
|---|---|---|
| A1 | Waste off: `flux-events` fires only on a failing reconcile (`alerts-github/alert.yaml` `eventSeverity: error`); `otto-parity` and `verdict-signoz` unscheduled with `pending: true` on their rows; agents stop dispatching gates by hand | halves the daily minutes; nothing to do with the move |
| A2 | Pull secret in every namespace that pulls `ghcr.io` (hermes-agent gateway has none today) | a secret is a secret under any owner |
| A3 | Build machines: actions-runner-controller on the cluster in its own fenced namespace, registered to the organisation through the estate App; `uname -m` detection in the four workflows that download x86 tools; a GitHub-hosted fallback label on `ci` and `oke-check` chosen by a repository variable | the controller is installed now and registers on cutover day; the fallback means a cluster outage never darkens the gates |
| A4 | Bot identity: agent worktrees commit as `estate-agents[bot]`, pushes over a lane token, pre-push refuses an agent push authored as him; `kini-finish.yml` and the image-automation writer likewise | identity is per account, not per owner name |
| A5 | `bin/idp-github-app installation` picks the installation whose account is `Mumchimp`, not `.[0]` | a coin toss once the App sits on both accounts |
| A6 | One rename commit per repository, on a branch, green: `uses: chidionyema/idp` to `Mumchimp/idp`, `ghcr.io/chidionyema/` to `ghcr.io/mumchimp/`, the Flux git URL, the three OCI artefact URLs, app-config, Otto's repository list, catalog-info slugs, estate-state (70 idp lines, 10 images) | prepared and proved green now, pushed in the cutover wave |
| A7 | The probe: `repo_must_be_private.py` grades the nine repositories under the new owner and refuses green if any name reappears under the old one | the grader exists before the thing it grades |

**Gate. Open work at zero.** The cutover may not start while any pull request is open in the seven
repositories or any crew item is in flight. Proved by one board query, not by a person's memory:
`gh pr list --state open` on each repository answers 0, and the crew board's open count is the
items parked on purpose (this one, crew#789, the doctor monitoring), each named. Today: idp 4,
crew 1, prospector 1, claude-guards 5, infra-crew 1 open pull requests, all green and waiting on his
merge. The move is last, never parallel with anything.

**Phase B. Cutover, one hour, his hands and one push wave.**

1. He upgrades Mumchimp to GitHub Team (so rulesets and the merge fence survive going private) and
   installs the estate App on it; the vault records the installation id (A5).
2. He transfers the nine repositories: `gh api -X POST repos/chidionyema/<r>/transfer -f new_owner=Mumchimp`,
   nine lines, 202 each, no acceptance step. GitHub redirects git, the API and every link, so the 102
   local checkouts and all prose keep working and are fixed lazily.
3. He grants the two reusable-workflow repositories organisation access
   (`actions/permissions/access` on idp and claude-guards).
4. He re-registers the two things GitHub does not redirect: the Tailscale federated subject
   (`estate-config.yaml:36-42` names his account; a string, not a link) and the App installation
   (step 1).
5. Crew pushes the prepared rename commits (A6) in one wave; the first build publishes every image
   under `ghcr.io/mumchimp`; the runners (A3) register to the organisation and the repository
   variable points `runs-on` at them.
6. He flips the nine repositories private. The probe (A7) goes green. Done.

**Rollback** is the same hour in reverse: transfer back (same call, `new_owner=chidionyema`), flip
the runner variable to the GitHub-hosted label, revert the rename merges. Never create a repository
at an old name: that deletes the redirects for good.

## What he decides

- `APPROVE: crew#785 org move`: starts Phase A (branches only; nothing on the cluster or the account
  until he merges).
- `APPROVE: crew#785 cap 120`: raises the cluster cap from $50 to $120 for the runner node (about
  $70 a month; the alternative, GitHub-hosted minutes on a private estate, is $261 to $313 a month
  after the waste cuts). Without it, Phase A still happens, the move still happens, and the estate
  stays public.
- GitHub Team on Mumchimp, one seat, $4 a month: his billing page, on cutover day.

## Appendix: the measurements behind it (2026-09-01, read from GitHub and the tree, not memory)

- Minutes: 3,139 billed job-minutes in 24 hours across seven repositories; idp 2,498 of which 780
  (31%) not green. `flux-events` 557 runs, 557 minutes, all green; `otto-parity` 16 of 16 red;
  `verdict-signoz` 15 of 15 red; `ci` cancelled runs 203 minutes; 180 hand dispatches a day. Waste
  cuts (A1) save about 1,200 idp minutes a day.
- Money: Free 2,000 min/month, Team 3,000, self-hosted free; hosted overage $456 to $547 a month
  today, $261 to $313 after A1. Cluster: `estate-defaults.yaml` cap $50, declared $49.54, headroom
  $0.46; one `VM.Standard.A1.Flex` node, 6 OCPU / 24 GB, arm64; second node about $70 a month.
- Names: 35 `uses:` lines (crew, hermes-v2, prospector); `ghcr.io/chidionyema/` for 10 images;
  `gotk-sync.yaml` git URL; OCI artefacts `clusters/oke/catalog.yaml:11`,
  `platform/mcp/estate-mcp.yaml:49,108`, `platform/hermes-agent/estate.yaml:112`;
  `app-config.container.yaml:173-176`; `provider-github.yaml:15`; `image-automation/backstage.yaml:48`;
  `hermes-agent/estate.yaml:20,58,113`; `kini-finish.yml:55`; catalog-info project-slugs;
  estate-state.yml; 70 idp lines in all; 102 local remotes (lazy); prose 909 files (redirect).
- Transfer semantics (vendor page, read today): keeps issues, pull requests, webhooks, secrets, deploy
  keys, history; redirects all links; packages may lose their link; a new repository at the old name
  deletes the redirects; private repositories on Free lose protected branches.
- x86 downloads: `ci.yml`, `verify-claims.yml`, `operating-model-gate.yml`, `estate-inventory.yml`
  (`grep -ln linux_amd64 .github/workflows/*.yml`).
- Flux alarm: `.github/workflows/flux-events.yml:54-72` opens the P0 on `severity == error`;
  `platform/alerts-github/alert.yaml:10` is `eventSeverity: info`; `platform/alerts/alert.yaml:14`
  is suspended. So `flux-events` stays and its trigger narrows.
- Installation pick: `bin/idp-github-app:157` takes `.[0].id`.
- Identity: last 200 idp commits, 109 as him, 77 as the bot; crew 140 as him, none as the bot.
- Reviews: crew#785 comments of 2026-09-01 (engineering, operations, finance, code-f9); founder
  rulings R68 and the open-work addendum, comments 5496869170 and 5496879891.
