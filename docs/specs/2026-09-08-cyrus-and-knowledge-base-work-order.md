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
| `backup/2026-09-08/fix/backstage-reaches-github` | 1 | 2026-09-07 | ns-fences: the portal's buttons reach api.github.com again | **land first**; every portal button that calls GitHub is dead without it |
| `backup/2026-09-08/portal/hide-claude-internals` | 2 | 2026-09-07 | home page buttons unified to one tonal pill (crew#799); Claude internals hidden from the front page | land |
| `backup/2026-09-08/portal/no-everyday-band` | 1 | 2026-09-07 | the everyday band taken back off the front page | land, after hide-claude-internals (same file) |
| worktree `~/dev/code/wt-portal-search` (`feat/portal-one-glance-search`, unpushed, 1 dirty file) | 1 | 2026-09-07 | live "On the cluster" card on each estate component's overview | commit the dirty file, push, land |
| worktree `.../edea3807.../wt-portal` (`fix/one-button-family`, unpushed, 3 dirty files) | 2 | 2026-09-07 | the tile's Open is a link, and the test asks for one | commit the dirty files, push, land |
| `feat/portal-modern-home` | 1 | 2026-09-03 | one-click nav and a fixed home, not a drag board | rebase; if the hide-claude-internals branch already covers it, close |
| `fix/portal-look-crew612` | 4 | 2026-09-03 | visit-tracking test and portal look fixes | rebase; land what still applies |
| `feat/portal-catalogue-complete` | 3 | 2026-09-02 | local guest Enter so the catalogue overlay is reachable | rebase; land |
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
