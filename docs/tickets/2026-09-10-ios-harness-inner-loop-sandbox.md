# Ticket: the IOS harness inner-loop sandbox

**Opened:** 2026-09-10
**Origin:** founder spec, delivered as a paste across four messages (package.json,
`src/server.ts`, `src/linear.ts`, then the two-plane sandbox blueprint and a Docker
sandbox design).
**Plane:** code plane only. The infrastructure plane is served by the existing shadow
dimension (`bin/idp-shadow`, `docs/how-to/prove-a-change-in-the-shadow.md`) and is
explicitly out of scope here.

## What is being built

A daemon that receives a Linear webhook, asks a model for a source patch, proves that
patch against a real test suite inside a hermetic ephemeral container, and — only on
exit 0 — pushes a branch and opens a pull request. It comments back on the ticket.

**The inner loop is a hermetic sandbox, not the shadow dimension.** The shadow applies
manifests to a vcluster and asserts a workload converges; it has no opinion about
whether source code passes its own tests. Putting `npm test` into the shadow would
pollute its purpose, and that separation is the load-bearing decision in this ticket.

## The two planes

| | code plane (inner loop) | infrastructure plane (outer loop) |
|---|---|---|
| proves | logic — does the code pass its tests | state — does the infrastructure converge |
| artifact | source patch | image + manifest |
| tooling | node, npm, jest/vitest | API server, kubelet, controllers |
| failure mode | syntax error, failed assertion | CrashLoopBackOff, failed probe |
| gate | the pull request | Flux sync |
| mechanism | **this ticket: hermetic container** | existing shadow dimension |

## The sandbox contract

Four properties, none negotiable:

1. **Ephemeral.** Seconds, not hours. Boot, run, return an exit code, die.
2. **Blind to the cluster.** No Kubernetes API access, no credentials, no route to
   internal services. `--network none`.
3. **Sterile.** No `.env`, no API keys, no live credentials ever enter the container.
   Nothing model-generated runs with a secret in its environment.
4. **Disposable.** `docker rm -f` and delete the temp directory regardless of outcome.

Execution flow:

1. **Stage** — make a unique temp directory, write the patched sources into it.
2. **Run** — start a container from a pre-baked image with a populated `node_modules`,
   mounting only the temp directory over the source path.
3. **Isolate** — `--network none`, non-root user, hard timeout (30s).
4. **Capture** — exit 0 proves the patch; 1 or timeout captures stderr and feeds it back
   to the model as context for the next attempt.
5. **Sweep** — force-remove the container and the temp directory, always.

The pre-baked image is the speed decision: waiting on `npm install` per attempt destroys
the feedback loop. CI rebuilds it whenever `package.json` changes.

## Known blockers, measured 2026-09-10

| # | Blocker | Evidence |
|---|---|---|
| 1 | **Docker daemon is not running.** No container can start, so the sandbox cannot execute at all. | `Cannot connect to the Docker daemon at unix:///Users/chidionyema/.colima/default/docker.sock, is the docker daemon running?` — `docker --version` reports 29.7.2, so the CLI is present and only the daemon is down |
| 2 | **No target repository chosen.** An ephemeral sandbox needs a real suite to run and a real `package.json` to bake. | see candidates below |
| 3 | **Linear write-back is blocked.** The daemon cannot comment on a ticket or move its state. | `externalsecret/cyrus-linear-oauth` is `SecretSyncedError`: `no secret found for project id 18e57b2f-... and name cyrus-linear-client-id` (crew#832, crew#834) |

### Candidate target repositories (found on this machine, 2026-09-10)

| path | remote | test script | last commit |
|---|---|---|---|
| `~/dev/code/popdd-ts` | company-root-vault | `vitest run` | 2026-09-03 |
| `~/dev/code/mumchimp-medusa` | mumchimp-medusa | `turbo test` | 2026-09-08 |
| `~/dev/code/survival-stack` | survival-stack | `node --test test/*.test.js` | 2026-09-08 |
| `~/dev/code/ecommerce-clean` | ecommerce-frontend | none | 2025-03-21 |
| `~/dev/code/ecommerce-frontend` | ecommerce-frontend | none | 2025-05-20 |

`popdd-ts` is the strongest candidate: a single vitest command, no build step, a live
remote, and activity within the last week.

## What does not carry over from the original paste

Recorded so no session re-proposes these.

| # | item | why it is refused | gate |
|---|---|---|---|
| 1 | `.env` holding `LINEAR_WEBHOOK_SECRET`, `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY` | static secrets on disk | `bin/static-secret-gate` |
| 2 | daemon binding `:8080` non-loopback | only the gateway binds a non-loopback address | `bin/bind-audit`, `bin/port-gate` |
| 3 | direct calls to `api.deepseek.com` / `api.anthropic.com` with bare keys | bypasses the estate router, budget and traces | LAW 52, `llm/config.yaml` |
| 4 | `git push origin` of an unproven model patch | no proof before it reaches the merge gate | `bin/idp-convergence-proof` |
| 5 | its own webhook ingress and its own SQLite idempotency store | a second ingress and a second state store are the stitching the headline forbids | THE HEADLINE |

Two latent defects in the original patcher, kept because they are real:

- `normContent.includes(search)` followed by `normContent.replace(search, …)` replaces the
  **first** occurrence, which may not be the anchored one. Silent corruption.
- `targetPath.startsWith(path.resolve(workspaceDir))` passes for a sibling directory named
  `<workspace>-evil`. Path traversal escapes.

Both are refused in this design: a patch is applied inside a container with a 30-second
life and no network, so a bad patch fails its tests rather than corrupting a checkout.

## Open decisions — founder only

1. **Target repository.** `popdd-ts` is my recommendation; confirm or name another.
2. **Linear write-back: API key or OAuth?** API key is one paste into Bitwarden and works
   immediately. OAuth needs an app registration and one consent click.
3. **Where it runs.** This machine (Docker via colima, currently down), a VPS, or inside
   the estate. The first two keep it entirely out of the estate's gates.

## Definition of done

- `docker run --network none` proves a patch: a deliberately broken patch exits non-zero,
  a correct patch exits 0, and both leave no container and no temp directory behind.
- A patch that passes tests opens a pull request. The daemon never pushes to a default
  branch.
- A container launched with no `--env` file cannot read any estate credential — proved by
  the container failing to find one.
- The whole loop is demoed from a real Linear ticket moving through the state machine.
