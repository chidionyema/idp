# Work order: Cyrus does real work, and the knowledge base leaves Claude Code

Founder, 2026-09-08: "we need to move our knowledge base outside claude code and get linear cyrus
working asap". Repair lane: DeepSeek. Planning seat: the one Claude Code session (standing rule,
`~/.claude/docs/founder/2026-09-08T1740Z-standing-rule-only-one-claude-code-session-allowed-c807cd20.md`).

## 1. Cyrus restarts every ten minutes, so it never finishes anything

Measured 2026-09-08 17:50Z:

- `kubectl -n cyrus get rs` shows a new ReplicaSet at 11m, 21m, 31m ... 91m: one rollout every ten minutes.
- `platform/cyrus/external-secret.yaml`: `cyrus-github` is a `GithubAccessToken` generator with
  `refreshInterval: 10m`. Every refresh mints a new installation token, so the Secret changes every ten minutes
  (its resourceVersion is 45011073 against ~40.9M for the others).
- `platform/cyrus/deployment.yaml` carries `reloader.stakater.com/auto: "true"`. Reloader sees the Secret
  change and rolls the Deployment. The init container re-clones three repositories each time.
- `platform/cyrus/entrypoint.sh:26` exports the token into the environment once at boot, which is why the
  restart was "needed": an installation token lives one hour and Cyrus had no other way to see a new one.
- Consequence: any Cyrus run longer than the window between rollouts is killed. Linear's webhook is registered
  and enabled (`https://cyrus.mumchimp.com/linear-webhook`, resource types Issue, Comment, IssueLabel; read
  through Linear's API from the pod), yet `kubectl -n cyrus logs deploy/cyrus --since=72h` holds zero
  deliveries, and `curl -X POST https://cyrus.mumchimp.com/linear-webhook` from the internet times out at 25s
  while sibling hosts on the same gateway (`llm.`, `hc.`) answer in 0.3s. The in-pod call answers 403 in 7ms.

This is the class the repository rule already names: "Reloader on top of a rotating secret is a loop, not a
control" (`rules.yaml`, crew#684 rung 2).

Fix, three edits, one pull request:

1. `platform/cyrus/deployment.yaml`: replace `reloader.stakater.com/auto: "true"` with
   `secret.reloader.stakater.com/reload: "cyrus-webhook,cyrus-github-app-pem,ghcr-pull"` and
   `configmap.reloader.stakater.com/reload: "<the cyrus configmap name>"`. The generated token is excluded.
2. `platform/cyrus/entrypoint.sh`: stop exporting `GITHUB_TOKEN` at boot. Install a git credential helper that
   reads `/secrets/github/CYRUS_GITHUB_TOKEN` on every call, and set `GH_TOKEN` the same way for `gh` (a
   wrapper on PATH that reads the file and execs the real binary). The kubelet refreshes the mounted Secret
   within its sync period, so a new token reaches Cyrus without a restart.
3. `platform/cyrus/external-secret.yaml`: `refreshInterval: 30m` on `cyrus-github` (token TTL is 60m; two
   refreshes per TTL is enough and halves the mint rate).

Definition of done, in commands:

```
kubectl -n cyrus get rs | awk 'NR>1 && $2>0' | wc -l                      # 1, and the same RS one hour later
kubectl -n cyrus get pod -l app=cyrus -o jsonpath='{.items[0].metadata.creationTimestamp}'  # older than 60m
curl -s -o /dev/null -w '%{http_code}\n' -m 10 -X POST https://cyrus.mumchimp.com/linear-webhook -d '{}'  # 403 in under a second (HMAC refused, door open)
# then, from Linear: label one issue "claude" and watch
kubectl -n cyrus logs deploy/cyrus --since=10m | grep -i "linear-webhook\|worktree\|pull request"   # a delivery, a worktree, a PR URL
```

The test file for this (LAW 3): a feature under `tests/` that fails when a Deployment mounting a Secret born
by a `GithubAccessToken` generator carries `reloader.stakater.com/auto: "true"`. Name it in the PR.

## 2. The knowledge base leaves Claude Code

Today: 2,537 observations in `~/.claude-mem/claude-mem.db` on the founder's Mac, 163 MB, written by a
Claude Code plugin whose observer is out of allowance since 11:18Z. Nothing else can read it.

Target, already chosen by the platform: `hindsight-api` in namespace `hindsight` on the estate database
(`mcp__estate__remember` / `recall` are its doors). DeepSeek's recovery (founder record
`~/.claude/docs/founder/2026-09-08T1817Z-update-entory-the-estate-platform-recovery-is-done-6089258a.md`)
landed #2574, #2586, #2605, #2607 and left one residual it called application-internal: the lifespan hangs
after both models load and the router lane verifies, and the startup probe kills the pod (exit 137, eight
restarts). Measured 2026-09-08 18:2xZ inside the pod: two sockets in `SYN_SENT` to `3.174.141.51:443`, an
address in `huggingface.co`'s A records; the namespace egress policy admits estate-db, llm and observability
only; both models are already in `/home/hindsight/.cache/huggingface/hub`. It is the fence, not the app.
Fix: `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` on the api env, pull request `fix/hindsight-offline-hub`.

Work, once `hindsight-api` is Available:

1. One idempotent job that reads every row of `observations` (sqlite) and writes it through
   `hindsight-api` with the observation id as the idempotency key. Run twice, same count.
2. Point `~/.claude-mem/settings.json` at no provider: the plugin stops writing; the estate remembers.
3. Every agent (DeepSeek lanes, Otto, Cyrus) uses `mcp__estate__remember` and `recall`; the memory row on
   `crew/docs/STANDARDS.md` names hindsight as the one memory layer.

Definition of done:

```
kubectl -n hindsight get deploy hindsight-api -o jsonpath='{.status.availableReplicas}'   # 1
# a recall for "cyrus reloader" returns the observation written from this work order
```

## 3. Backstage work that never reached a release

Founder, 2026-09-08 19:30Z: "what about the backstage work that never made it to release".

Counted on 2026-09-08 19:30Z with `git rev-list --count origin/main..origin/<branch>`. The
portal on the cluster runs main; none of the rows below is in it.

| branch | ahead of main | last commit | what it carries | verdict |
|---|---|---|---|---|
| `backup/2026-09-08/fix/backstage-reaches-github` | 1 | 2026-09-07 | ns-fences: the portal's buttons reach api.github.com again | already on main (rebase empty, 20:35Z); close |
| `backup/2026-09-08/portal/hide-claude-internals` | 2 | 2026-09-07 | home page buttons unified to one tonal pill (crew#799); Claude internals hidden from the front page | conflicts with main on rebase (20:35Z); resolve by hand, then land |
| `backup/2026-09-08/portal/no-everyday-band` | 1 | 2026-09-07 | the everyday band taken back off the front page | already on main (rebase empty, 20:35Z); close |
| worktree `~/dev/code/wt-portal-search` (`feat/portal-one-glance-search`, unpushed, 1 dirty file) | 1 | 2026-09-07 | live "On the cluster" card on each estate component's overview | commit the dirty file, push, land |
| worktree `.../edea3807.../wt-portal` (`fix/one-button-family`, unpushed, 3 dirty files) | 2 | 2026-09-07 | the tile's Open is a link, and the test asks for one | commit the dirty files, push, land |
| `feat/portal-modern-home` | 1 | 2026-09-03 | one-click nav and a fixed home, not a drag board | conflicts with main on rebase (20:35Z); resolve by hand or close |
| `fix/portal-look-crew612` | 4 | 2026-09-03 | visit-tracking test and portal look fixes | conflicts with main on rebase (20:35Z); resolve by hand, land what still applies |
| `feat/portal-catalogue-complete` | 3 | 2026-09-02 | local guest Enter so the catalogue overlay is reachable | conflicts with main on rebase (20:35Z); resolve by hand, land |
| `backstage-arm64` | 9 | 2026-09-05 | "wip: salvage uncommitted work" from an arm64 image experiment | close; the image is built by the platform image workflow now |
| `backstage-container`, `fix/backstage-tag-main-517`, `fix/diagnose-backstage-log` | 8, 3, 1 | Aug 25–29 | stale image and diagnostic branches | close |

Order of work for the DeepSeek lane, one pull request per row, oldest dependency first:

1. `fix/backstage-reaches-github` (fence row; without it steps 2–5 land buttons that cannot call out).
2. `portal/hide-claude-internals`, then `portal/no-everyday-band` rebased on it.
3. The two unpushed worktrees: commit the dirty files under their branch names, push, open the PR.
4. The three September-2 and September-3 branches, rebased on main; a branch whose diff is now empty is closed with one line saying which merged PR covers it.
5. Close the four August and arm64 branches with `gh pr close`/`git push origin --delete`, one line each naming why.

Done when, for each row marked land: the PR is merged, the platform image workflow has rolled the
portal, and `kubectl -n backstage rollout status deploy/catalogue` returns, and the founder opens
the portal home page and sees the change. `git branch -r --no-merged origin/main | grep -Ei 'backstage|portal'`
then lists nothing outside `backup/`.

## 4. FleetView: the agent-session board becomes a Backstage offering

Founder, 2026-09-08 19:50Z: "needs to be exponentially better and on Backstage, but we need this
developed as an offering." Spec, checkpoints, lane plan and DoD commands:
`docs/specs/2026-09-08-fleetview-backstage-offering.md`. Feature files: `features/fleetview/`.
Marketing page: `docs/marketing/products/fleetview.md`. This outranks sections 1–3 for lane
count: CP1 starts today with two lanes; sections 1–3 take the other lanes.

## 5. The register stays audited: a gate, not a person

Founder, 2026-09-08 20:00Z: "we missed so much from the investor pitch because inventory isn't
audited, we don't know what we have"; "capabilities even if undeveloped or appear trivial, the
question is: is it useful for business and engineers".

`docs/marketing/capabilities.yaml` is the register (50 rows, five ranges). It was written by a
sweep, once. The lane makes it a gate:

1. `bin/capability-register-gate` (Python, one file) runs in CI and reads two planes and
   nothing else: the GitHub organisation (`gh api /user/repos` and each repository's tree, for
   README and test files) and the cluster inventory the daily estate-inventory workflow already
   writes. It never reads a laptop path; the dev root, `~/dev/code`, is not a plane (founder,
   2026-09-08 20:25Z: "an enterprise startup's inventory is depending on laptop?"). A repository
   or a directory with a README or a test file and no register row fails, naming it. A register
   row whose path no longer exists on GitHub fails. A row with empty `useful_for` older than 30
   days fails until it is retired or argued. Corollary, done first: every repository under the
   dev root is on GitHub with nothing unpushed. Counted 2026-09-08 20:26Z: crew 37 dirty files,
   hermes-v2 223, mumchimp-medusa 20, QAlgo 8, maestro and survival-stack one unpushed commit
   each; prospector-main, popdd-py and popdd-ts are not repository checkouts on this machine
   and must be confirmed on GitHub before the register cites them.
2. `docs/marketing/capabilities.md` is rendered from the yaml by the gate (`--render`), the way
   `bin/idp-rules render-agents-md` renders AGENTS.md; `--check` in `bin/idp-ci` refuses drift.
3. A row in `rules.yaml` with fixtures `tests/fixtures/capability-register/{bad,good}`; LAW 32
   pages for the new bin file.

Done when: `bin/capability-register-gate` is green on main, and adding an empty directory with a
README under `sovereign/` turns it red in a pull request.

## 6. Tying the threads: the product range

The register's five ranges are the product range. The catalogue index is regrouped by range
(run agents, govern agents, run the platform, private AI, products on the platform); every
capability marked `surfaced: none` and useful to business gets a one-page product entry in the
same shape as the others, or a line in the register saying why not. The investor brief reads
its "what we have" figures from the register.

## 7. Nothing load-bearing on the laptop

Founder, 2026-09-08 20:20Z: "why should we rely on laptop?" We should not. The cluster is the
platform; the laptop is a client. The one-scheduler ledger already says so: all six launchd
templates are marked "pending: to be declared as a Dagster schedule". The lane finishes the fold:

| laptop job | goes to | then |
|---|---|---|
| ai.estate.cockpit | FleetView on the portal (order 1) | template deleted |
| ai.estate.sovereign-worker | already runs in the cluster (commit c2733b99) | template deleted |
| ai.estate.scheduler | Dagster on the cluster, one schedule per row | template deleted |
| ai.estate.idp | the Deployment that already serves the portal on the cluster | template deleted |
| ai.estate.headlamp | the Headlamp release on the cluster behind the gateway | template deleted |
| ai.estate.kubeapi | a client convenience (kube API tunnel); keep as a client tool, not a job | moved out of launchd/ |

The 32 register rows marked laptop-or-command-only are each given a cluster home (a Deployment,
a Dagster job, or a portal button) or a `retire` verdict in `capabilities.yaml`.

Done when: `launchd/` holds no `.plist.tmpl`, `platform/scheduling/one-scheduler.yaml` has no
row of kind "launchd job on the laptop", `bin/idp-one-scheduler` is green, and the register has
no row whose state says laptop or CLI only without a `retire` verdict.

## 8. The root cause, and the stage that fixes it: after merge, operational or red

Why things are built and not shipped: the pipeline ends at merge. Pull request, CI green, merge,
Flux applies. No stage after that asks whether the thing runs, is reachable, is on the
catalogue, has a product page, or is still alive a week later. Sessions reply `INVENTORY:`
(merged and green) and end. So "operational" is nobody's stage, and the cockpit could die on
28 August with nobody told.

The fix is one stage, built from parts that exist:

1. Every row in `docs/marketing/capabilities.yaml` gets a `probe:` command that proves it runs
   (a rollout status, a URL that must answer 200 behind the gateway, a Dagster run that must
   have succeeded in the last day). A row without a probe is `UNKNOWN` and shown as such;
   never green by default (the three-state service rule).
2. One Dagster job, `capability_probes`, runs every probe hourly, writes
   `reports/capabilities.json` with `MEASURED_OK | MEASURED_FAIL | UNKNOWN` per row, and pages
   through the existing Alertmanager route when a row that was OK turns FAIL.
3. The portal shows the register with those states (the founder's god's view, R38, already
   renders receipts); FleetView (order 1) reuses the same feed for agent runtimes.
4. `bin/idp-ci` refuses a pull request that adds a directory with a README or tests without a
   register row and a probe. This is order 4's gate with the probe made mandatory.

Done when: `reports/capabilities.json` exists on main with a state for all 50 rows, the count of
`UNKNOWN` is on the portal home, and killing a running capability turns its row FAIL within an
hour with a page to the founder. This order outranks 4, 5 and 7, which it absorbs.

## 9. EXECUTE NOW — DeepSeek owns this, in this order, no spec sheets (founder 2026-09-08 18:44Z)

Founder record: `~/.claude/docs/founder/2026-09-08T1844Z-ou-are-completely-right-to-be-fed-up-d4794a6e.md`.
Founder, 18:50Z: "let deepseek handle it". Claude Code writes nothing further on this; every step below
is DeepSeek's, ten agents in parallel, one agent per bullet where the bullets are independent.

### 9.1 Mass commit and push (counted 18:46Z)

| repo | branch | dirty files | unpushed commits |
|---|---|---|---|
| hermes-v2 | feat/crew751-cursor-hermes-primary | 223 | 0 |
| crew | main | 37 | 0 |
| mumchimp-medusa | main | 20 | 0 |
| QAlgo | main | 8 | 0 |
| maestro | main | 0 | 1 |
| survival-stack | main | 0 | 1 |

Per repo, on a branch `wip/2026-09-08-unpushed-work` (hermes-v2 stays on its feature branch):
`gitleaks protect --staged` after staging, drop any file it names, commit, `git push origin <branch>`,
`gh pr create --fill`. maestro and survival-stack: `git push origin main`. Done when the table's
dirty and unpushed columns read 0 on a fresh count.

### 9.2 Merge the Backstage branches to main

Twelve remote branches and six worktrees (list: `git branch -r --no-merged origin/main | grep -Ei
'backstage|portal'` and `git worktree list`). One landing branch `portal/land-all-2026-09-08`; merge
each branch into it oldest first; a conflict is resolved by hand in the same sitting, never rebased
and parked; the three worktrees with unpushed commits (fix/one-button-family, portal/no-everyday-band,
feat/portal-one-glance-search) are committed and merged the same way. One pull request; merge-when-green
lands it; the cluster's portal Deployment is the validation. Rescue and recovery branches whose diff
is already on main are deleted from origin. Done when the grep lists nothing outside `backup/`.

### 9.3 Kill the laptop dependency

Delete the six templates under `launchd/`, their six rows in `platform/scheduling/one-scheduler.yaml`,
and the installer's rendering of them; `launchctl bootout gui/$(id -u)/ai.estate.<name>` for each loaded
one (scheduler, headlamp, kubeapi are loaded at 18:46Z). The cockpit gets a Deployment next to the
sovereign worker in `platform/temporal/` on the same image; Headlamp is a HelmRelease under
`platform/`; scheduler and sovereign-worker already run on the cluster; idp and kubeapi are deleted.
The manifests go through a pull request because Flux owns the cluster and reverts a hand apply; a
merge is the apply. Done when `launchd/` is empty, `bin/idp-one-scheduler` is green and
`kubectl -n <ns> get deploy cockpit` is Ready.

### 9.4 Enforce the gate

A row in `rules.yaml`: a pull request that adds a file under `launchd/`, or a new service entrypoint
(a Dockerfile, a `*/server.py`, a `bin/` file that binds a port) with no manifest under `platform/`
naming it, is refused. Fixture pair `tests/fixtures/ships-to-cluster/{bad,good}`, gate
`bin/idp-ships-to-cluster`, `bin/idp-rules render-agents-md`. Done when a test pull request adding
`launchd/x.plist.tmpl` turns red.

### 9.5 Then the founder leaves Claude Code

Founder, 18:47Z: "we get away from claude code and move over to linear and cyrus". Section 1 (Cyrus
stops rolling every ten minutes) is the prerequisite and runs in parallel with 9.1–9.4. When Cyrus
holds a pod for an hour, every open order on this page becomes a Linear issue assigned to Cyrus.
