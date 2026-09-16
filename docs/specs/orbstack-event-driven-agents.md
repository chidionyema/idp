# OrbStack-powered event-driven IDP agent architecture

Full specification and build for a stateless, event-driven, horizontally
scalable agent platform: GitHub and Flux events in, verified PRs out, every
agent turn scored by the verification harness before it is trusted.

## 1. System overview

The system:

- Receives events from GitHub (issues, PRs, CI failures) and Flux
  (reconciliation failures) via webhooks.
- Normalizes events into tasks and pushes them into a Redis queue.
- Runs N identical Python daemons (engines) that pull tasks, create
  ephemeral workspaces, run agent logic, validate changes in isolated
  OrbStack containers, and push results back to GitHub.
- Scores every agent turn through `platform/integration/claude_code_hook.py`
  (the verification harness: `platform/eval/judge_worker.py`,
  `platform/eval/pareval_layer.py`, the red-team span scan, the honesty
  check) before a PR is opened or a review is posted. A turn the harness
  halts never reaches GitHub.
- Guarantees zero zombie state: every workspace is an OS temp directory,
  destroyed after the task completes.
- Scales horizontally by adding engine processes; Redis's atomic `BLPOP`
  guarantees each task is claimed by exactly one engine.

## 2. Relationship to what this repository already runs

This is a new capability, not a replacement for two things that look
adjacent but solve a different problem:

- `dispatch_job` (`extensions/dispatch`, installed via `bin/idp-dispatch-install`)
  launches background work **from inside an interactive agent session** —
  a human or an agent already at the keyboard starting a long-running job.
  It has no webhook listener and does not react to GitHub or Flux events on
  its own.
- `bin/idp-exec` bounds a single command inside a session to a 60s ceiling.
  It is not a queue and does not survive the session ending.

This architecture is the missing piece: an always-on listener that turns a
GitHub issue, a PR, or a Flux reconciliation failure into a task, with no
person or session needed to notice the event and start something. It is the
front door; `dispatch_job` and `bin/idp-exec` remain how work already
running gets its own sub-tasks done.

## 3. Component roles

| Component | Responsibility | Technology |
|---|---|---|
| Gateway | Exposes webhook endpoints, validates payloads, pushes tasks to Redis. | FastAPI + Uvicorn |
| Queue | Atomic task distribution, persistence of pending work. | Redis (list `idp_tasks`) |
| Engine | Polls queue, clones repos, runs agents, executes CI in OrbStack, manages PRs. | Python + Docker CLI (OrbStack) |
| Workspace | Ephemeral, isolated directory for each task. | `tempfile.TemporaryDirectory` |
| Vacuum | Isolated container that runs CI checks with no network access. | OrbStack + Docker |
| Verification harness | Scores every agent turn before it reaches GitHub. | `platform/integration/claude_code_hook.py` (idp#3564) |
| Agent | Worker / Judge / SRE role logic. | Python, LangGraph-ready (stub call sites marked) |

## 4. Data flow

```
GitHub/Flux Webhook
        |
        v
+-----------------+
|    Gateway      |  (FastAPI)
|  /webhook/github|
|  /webhook/flux  |
+--------+--------+
         | push task JSON
         v
+-----------------+
|  Redis Queue    |  (list: idp_tasks)
+--------+--------+
         | blpop
         v
+-----------------+
|  Engine (N)     |  (Python daemon)
|  worker_loop()  |
+--------+--------+
         |
         +-> create temp workspace
         +-> git clone + checkout branch
         +-> run agent (worker/judge/sre), recording real spans
         +-> verify_agent_result() -- the harness, idp#3564
         |     halt -> stop, no PR, no push
         |     pass -> continue
         +-> run_orbstack_vacuum()  (CI in container, --network none)
         +-> git commit + push + gh pr create
         +-> destroy temp workspace
```

The harness call sits **before** the OrbStack CI run and before any push:
a halted verdict (a fabricated tool-call claim, a credential-file read, a
judge score below the halt threshold) stops the task before it can write
anything back to GitHub, not after.

## 5. Security model

- **Network isolation**: the vacuum container runs with `--network none`.
  No exfiltration path exists once CI starts.
- **Token handling**: in-cluster, `engine.py` never holds a static GitHub
  token at all. `mint_gh_token()` calls `bin/idp-github-app token
  agent-workforce`, the estate's existing GitHub App lane, per task —
  a fresh installation token that expires in an hour and never touches
  disk. A local `GH_TOKEN` env var overrides this for a developer's own
  dev loop, never in a deployed engine.
- **Least privilege**: `agent-workforce` (`platform/github-app/lanes.json`)
  is narrowed to `contents: write`, `pull_requests: write`, `issues:
  write`, `metadata/actions/checks: read` — it can open and update PRs and
  push to a branch, and it can never merge, dispatch a workflow, or reach
  a cluster. This architecture reuses that lane rather than minting a new
  App or a new lane: a second GitHub identity for the same role would be
  the second copy of one credential LAW 54 refuses.
- **Webhook signature verification**: `GITHUB_WEBHOOK_SECRET` is required
  in any deployment reachable from the public internet; the gateway
  refuses a request with a missing or invalid `X-Hub-Signature-256` once
  the secret is set. Left unset only for local dev, and the gateway logs
  that verification is off every time it starts in that mode.
- **Redis authentication**: `requirepass` is required outside local dev;
  `REDIS_URL` carries the password.
- **No persistent state**: every workspace is destroyed on task exit. The
  only persistent store this architecture adds is the verification
  harness's own `state/verification.db` (idp#3564), which already exists
  independent of this build.

## 6. Scalability

- **Horizontal**: run `engine.py` as many times as needed; each process
  competes for tasks via Redis `BLPOP`, so adding replicas is the entire
  scaling operation.
- **Vertical**: each engine uses one CPU core and minimal RAM; OrbStack
  shares the host kernel rather than running a full VM per container.
- **Kubernetes-ready**: package the engine as a `Deployment` with
  `replicas: N`; the gateway as a `Service` behind an `Ingress`.

## 7. Project structure

```
idp/
├── platform/
│   └── idp_agent/
│       ├── gateway.py
│       ├── engine.py
│       └── requirements.txt
├── platform/idp_agent/k8s/
│   ├── engine-deployment.yaml
│   └── gateway-deployment.yaml
├── platform/idp_agent/docker-compose.yml   # local Redis only
└── docs/specs/orbstack-event-driven-agents.md   # this file
```

## 8. Local boot

```bash
# 1. Start Redis
docker compose -f platform/idp_agent/docker-compose.yml up -d redis

# 2. Install Python dependencies
pip install -r platform/idp_agent/requirements.txt

# 3. Set environment variables
export REDIS_URL="redis://localhost:6379"
export GH_TOKEN="ghp_..."                 # local dev only: overrides mint_gh_token()'s
                                           # agent-workforce lane mint, so a developer
                                           # doesn't need App credentials just to run locally
export GITHUB_WEBHOOK_SECRET=""           # required outside local dev

# 4. Start the gateway
python platform/idp_agent/gateway.py

# 5. Start N engines
for i in $(seq 1 4); do
  python platform/idp_agent/engine.py &
done
wait
```

## 9. The eval workflow integration (idp#3564)

`engine.py`'s `run_task_through_harness()` is the single point every task
type passes through before a PR is opened or a review posted:

1. The agent function (`run_worker_agent` / `run_judge_agent` /
   `run_sre_agent`) records what it actually did as a list of real spans
   (`{"span_kind": "tool_call", "tool_name": ..., "args": {...}}`) — the
   same span shape `tests/integration/test_claude_code_hook.py` exercises.
2. `engine.py` loads `platform.integration.claude_code_hook` by file path
   (the same `sys.modules` pre-seeding pattern used throughout idp#3564:
   `platform/` has no top-level `__init__.py`, so a bare `import platform`
   — which pytest, and several third-party libraries, do at import time —
   permanently shadows `platform.*` submodules for the rest of the process
   unless the dotted names are seeded directly).
3. `hook.verify_agent_result(...)` runs the full gate suite: transcript
   complete, no reasoning loop, no fault flags, judge calibration
   (`JudgeWorker.evaluate`), red-team scan (credential files, reverse
   shells, SQL injection patterns), and the honesty check (claimed vs.
   actual tool calls).
4. A `halt: true` verdict stops the task immediately — no OrbStack run, no
   commit, no push, no PR. The failure reasons are logged and the task is
   moved to `idp_tasks_dead` for inspection, not retried silently.

This is the concrete answer to "no agent can work on this platform without
using the full harness": every one of the three task handlers
(`handle_worker_feature`, `handle_judge_review`, `handle_sre_revert`) calls
`run_task_through_harness()` before doing anything that leaves the
ephemeral workspace.

## 10. OrbStack is a local-dev boundary, not an in-cluster one

The vacuum container needs the Docker/OrbStack socket, which means whatever
process calls it has host-root-equivalent access. Mounting
`/var/run/docker.sock` into a pod is a known container-escape vector, and
this cluster's Kyverno policy set already refuses that shape of access —
every Deployment here (`platform/jit/deployment.yaml` and the rest) runs
`readOnlyRootFilesystem`, non-root, no added capabilities, and no
`hostPath` into the container runtime.

Docker-in-Kubernetes was never this architecture's real CI boundary; GitHub
Actions already is — the same 14 checks that gate every PR in this
repository today. `engine-deployment.yaml` sets `IDP_SKIP_LOCAL_VACUUM=1`,
which makes `run_orbstack_vacuum` a no-op that defers straight to the PR's
own GitHub Actions run: the harness verdict (judge, red-team, honesty) is
the pre-push gate that has no equivalent elsewhere, and GitHub Actions is
the post-push gate that already exists and does not need reinventing
in-cluster. `run_orbstack_vacuum` itself stays real and useful for the
local-dev loop, where a developer's own OrbStack socket is exactly that:
theirs, not a cluster's.

`GITHUB_WEBHOOK_SECRET` arrives as a file from an `ExternalSecret`-backed
Kubernetes `Secret` (`GITHUB_WEBHOOK_SECRET_FILE`), not an environment
variable — an env var is printed by every crash dump and `kubectl describe
pod`, which is exactly what this cluster's `secrets-not-from-env-vars`
Kyverno policy refuses. The engine fleet needs no secret of its own at
all: `mint_gh_token()` mints a fresh token per task from the already-vaulted
`github-app` entry (docs/reference/policy/root-trust.md), so there is no
static `GH_TOKEN` to store, rotate, or leak in the first place.

## 11. Production hardening checklist

- [ ] `requirepass` set on Redis; `REDIS_URL` carries the password.
- [ ] `GITHUB_WEBHOOK_SECRET` set and configured in the GitHub repo's
      webhook settings.
- [ ] The `idp-engine` ServiceAccount carries whatever OCI workload-identity
      binding `bin/idp-cloud secret get` needs to read the `github-app`
      vault entry in-cluster (not yet resolved — section 12).
- [ ] No `GH_TOKEN` env var is set on the deployed engine: its presence
      would silently skip the per-task App-lane mint (`mint_gh_token()`'s
      local-dev override) in production, exactly the static-token risk
      this design avoids.
- [ ] Vacuum image is a custom, pre-built image with CI dependencies
      baked in — not `apt-get install` on every run (local dev only, see
      section 10).
- [ ] `run_orbstack_vacuum` timeout (default 600s) matches the real CI
      runtime; adjust via `IDP_VACUUM_TIMEOUT_S`.
- [ ] Engine and gateway logs ship to the estate's existing observability
      stack (SigNoz/Langfuse), not stdout only.
- [ ] Webhook endpoints are rate-limited.
- [ ] A task that fails repeatedly moves to `idp_tasks_dead` for manual
      inspection instead of looping forever.

## 12. What is not yet built

- The planning logic inside `run_worker_agent` / `run_judge_agent` /
  `run_sre_agent` (LangGraph) is not written here — each function is a
  real call site that already records a real transcript and goes through
  the harness, so wiring in real planning logic is additive.
- `engine-deployment.yaml`'s `idp-engine` ServiceAccount does not yet
  declare the OCI workload-identity binding `bin/idp-cloud secret get`
  needs to read the `github-app` vault entry from inside the cluster.
  `bin/idp-github-app token agent-workforce` works today from any
  environment with real OCI credentials (a developer's session, CI); the
  in-cluster equivalent wasn't resolved from the code alone and needs
  verifying against however this cluster's other in-pod `bin/idp-cloud`
  callers, if any, are bound before this deploys for real.
- Kubernetes deployment manifests are provided; no Helm chart or Flux
  `HelmRelease` wraps them yet, so they are not reconciled by GitOps the
  way the rest of this estate's workloads are. Follow-up: fold
  `platform/idp_agent/k8s/` into a HelmRelease once the engine is proven
  in staging.
