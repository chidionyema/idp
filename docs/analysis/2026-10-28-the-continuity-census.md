# The continuity census — what the estate owns, and what is at risk of vanishing

Measured 2026-10-28 on the founder's laptop with the estate's own doors (`work-inflight`,
`work.discover`, `disk-free`, `router-doctor`, `router-lane-health`, `gh-api`). Every number here
is a measurement from this turn.

## The board

`work-inflight` (7-day window) measured **233 work items** across **66 claims**:

| state | count | what it means |
|---|---|---|
| LIVE | 5 | a claim with a heartbeat inside 2h — an agent is holding it right now |
| RECOVERABLE | 88 | the content is not on main but it still exists and can be finished |
| LANDED | 140 | the content is on `origin/main` |
| DEAD | 0 | not on main and not recoverable anywhere |

Ledger: `~/.estate/results/work-inflight/latest.json` (and `latest.md`).

## The five LIVE items

| kind | what | where | claim | distance | what is still missing |
|---|---|---|---|---|---|
| branch | `lane/aei-ops-2` | origin | #7311 pi-aei-ops (LIVE) | pushed | 4 commits not on main |
| branch | `lane/aei-ops` | origin | #7311 pi-aei-ops (LIVE) | pushed | 2 commits not on main |
| worktree | `lane/the-imported-instruments` | `~/Documents/code/idp-worktrees/instruments` | #7142 pi (LIVE) | local only | 4 uncommitted changes; the branch is not on origin; 1 commit not on main |
| branch | `lane/the-imported-instruments` | local only | #7142 pi (LIVE) | local only | the branch is not on origin; 1 commit not on main |
| branch | `backup/preserve-20261026-router-front` | origin | #7142 pi-repair-zai (STALE) | pushed | 1 commit not on main |

## The void risks, ranked by how much work they would take with the machine

1. **`lane/the-imported-instruments` — a commit on no remote.** The two founder-supplied packages
   (Estate AEI, Estate Component Atlas) are imported, tested (AEI 14 tests, Atlas 10 tests, both
   green on Python 3.9.6) and committed as `22d98c3f5`. The push is refused by the pre-push fast
   gate (`❌ pre-push REFUSED: idp-fast-gate caught errors`), so the work exists only here.
2. **`lane/the-capacity-convergence` — six edited files, no commit.** `AGENTS.md` §5a,
   `estate-defaults.yaml`, `platform/oci/main.tf`, `platform/oci/variables.tf`,
   `platform/oci/autoscaler/cluster-autoscaler.yaml`, `platform/llm/litellm.yaml`. Nothing is
   committed; a crash loses all of it.
3. **The main checkout is dirty and detached.** Other agents' work is in it; it is not authoritative.
4. **Four stashes, local only**, and three `preserve-plan` worktrees whose commits are reachable
   only from their own HEAD (`board` `21073018e`, `efda-preserve` `a728d800`, `wt` `01645533`).
   These are **not** abandoned: `~/.estate/libexec/disk-cleanup.sh` refuses to remove a worktree
   whose commits exist only in its own HEAD, and their content is on origin as
   `backup/preserve-20261026-*` and `backup/preserve-20261027-*` branches (13 of them).
5. **The census's own source is not in the repository.** `work-inflight.py` exists only in the
   runtime on this laptop.

## The one reason nothing could be landed: the disk floor

`estate_execute`, `estate_run_gate` and `estate_run_tests` all refuse with the same line:

```
error: the volume has 414 MB free, under this door's 1500 MB floor; a job started now makes the
machine slower for every other agent running on it.
```

`disk-free` and `disk-cleanup` (phases critical, clones, caches, docker, worktrees, temp, scan)
freed **0 M**: every candidate worktree is claimed by a live claim, holds uncommitted or untracked
files, holds commits reachable only from its own HEAD, or is locked; the critical tier keeps
`nvm v22.15.1`, the rustup default toolchain, the ollama models and the Chrome code-sign clone.

Where the space is: **7.7 GB** in 27 agent worktrees; **5.5 GB** in owner-decided caches
(`~/.cache/estate-tools` 2210M, nvm 3273M, rustup 1341M, go modcache 773M, a Chrome code-sign
clone 1439M held open by a running Chrome, ollama models held open by a running server).

The floor is not lowered. A gate that cannot fail is not a gate, and a starved machine is slower
for every agent on it. The answer is the estate's own cleaner plus the claim law: a claim whose
paths no longer hold work should stop protecting a worktree.

## The router, measured

`router-doctor` (heal): the front is up (`liveliness HTTP 200`), both launchd agents running, the
OAuth patch staged, the `claude-*` lane present. One failure, and it is the founder's to fix:
`FIX: max-token  no Claude Code login in the keychain -- run: claude  then  /login`.

The lanes behind it are degraded:

- `voice`: 63 calls, **100% refused** — `litellm.BadRequestError: You passed in model=voice.
  There are no healthy deployments for this model`.
- `groq`: 40 calls, **95% refused** — `429 rate-limit` for `openai/gpt-oss-120b`.
- the cloud route: `curl: (35) TLS connect error: … unexpected eof while reading` (`HTTP:000`).

So the estate's fallback chain is thinner than the design assumes: the cloud leg is down and the
laptop's own lanes are rate-limited. The rung that cannot be rate-limited is the local ollama free
floor, and the laptop's `default`/`fast` chain does not fall back to it.

## What this analysis asks for

1. **Automate the continuity** (ADR 0039): the census on a schedule, and a rescue that copies
   local-only work to origin so a dead machine — or a dead headless session — takes nothing with it.
   The rescue goes after the headless agent's work first: a claim whose heartbeat has lapsed names
   a session that is gone.
2. **Free the disk** through the estate's own doors: shrink claim #7142's path list so the cleaner
   can release the worktrees whose work is already landed, and let the stale ones be archived to
   `~/.estate/quarantine/worktrees/` rather than deleted.
3. **Land the two lanes** above. The import lane needs the fast gate to pass on the vendored
   packages; the capacity lane needs a commit. Both need the executor, which needs the disk.
