# AGENTS.md — estate-wide. Every agent on this machine, and every product.

What the estate is and where things live. Enforcement is not in this file; it is in the executor,
the gates and the hooks, which refuse.

---

## 1. The graph

```bash
growmos --root ~/Documents/code/estate-graph context --brief   # cross-repo
growmos context                                               # inside a repo
growmos --root ~/Documents/code/estate-graph remember "<Name>" --type SYSTEM --desc "<fact>"
growmos --root ~/Documents/code/estate-graph link "<A>" "<predicate>" "<B>"
growmos --root ~/Documents/code/estate-graph journal "<what changed and why>"
```

Record durable facts as you learn them. The graph is shared memory; a context window is not.

---

## 2. Never hand-apply. Merge, and let Flux converge.

`kubectl apply` by hand is forbidden. PR merges to `main` → `build-multiarch.yml` builds amd64 +
arm64, Trivy, cosign → tag `ghcr.io/chidionyema/<name>:main-<run>-<sha>` → Flux image-reflector
polls → `image-automation` writes `flux/image-updates` → `deploy-when-green` merges on green.
`bin/build-image` enforces R24. Do not bypass it.

**An agent never hand-walks the commit → push → PR → re-run-CI loop.** That whole path is the
Greenlane's job (`merge-when-green`, `deploy-when-green`, Flux image automation), and it converges
on its own. Open the PR, then STOP. CI runs, `merge-when-green` lands it, Flux deploys it — a real
production log line is the only "done." If the local `gh` CLI (HTTPS) stalls or the pre-push gate
hangs, that is a flaky network path to report and a missing door to add — not a reason to drag the
founder through manual re-runs. `git` over SSH and `curl` to the GitHub API keep working; use those,
or add a governed capability, but never convert a pipeline the estate already runs into a
founder-manned procedure.

---

## 3. Proof, not assertion

Never declare something WORKING from a synthetic probe, a green CI gate, or an HTTP 200. Prove it
with a real production log line. **"Built" and "operating" are different facts** — say which one
you mean. A gate that cannot fail is not a gate; a test that executes nothing is not a test.

This is two rules kept as one because they are one: **narrating instead of proving** and **asserting
instead of proving** are the same defect, an agent producing words where a measurement belongs.

---

## 4. Secrets — by name only, from the vault

Keys arrive through `estate-secrets` (SOPS + age) or the Bitwarden human-vault bridge:

```bash
gh workflow run vault-seed.yml -f entry=laptop
git -C ~/Documents/code/estate-secrets pull
source ~/Documents/code/estate-secrets/scripts/secret-load
```

Never paste a key into a file, an env var in code, a commit, a message, a journal entry, or a graph
node. Reference it by env var name. Never print a secret value. Never ask the founder to carry one
between surfaces.

---

## 5. Coordination

**Docker runs on Rancher Desktop (moby, x86_64) — `docker` lives at `~/.rd/bin`, the engine socket is `~/.rd/docker.sock` via the `rancher-desktop` context; there is no Docker Desktop and no colima (the `colima` context is stale and must not be used).**

`~/Documents/code/crew` is shared coordination; `crew/STATE.md` is the live estate map. Never
restart another agent's process. Never touch the Telegram token's polling.

---

## 6. One of each layer. A second copy is stitching and gets deleted.

The platform is `idp`. Products run on it. Exactly one of each: routing, traces, identity, secrets,
scheduling, catalog, execution boundary, evidence, verification, memory. A product is never deleted
for living outside `idp`; a duplicate layer always is.

**Before building anything, prove it does not already exist** — `growmos query "<what you want to
build>"`, then read the candidate. The estate has built the same capability five to ten times. Do
not make it eleven.

---

## 7. Execution — intents only

Every action the agent performs goes through an **intent YAML** in `~/.estate/intents/`.

```
~/.estate/              # NOT a git repo — lives outside version control
  bin/estate-execute    # executor binary
  intents/*.yaml        # 24 intents: shell.parse, git.branch, ci.run, etc.
  libexec/*.sh, *.py    # helpers: shell-suggest.py, shell-verify.py, etc.

~/Documents/code/idp/mcp/plugins/estate_mcp.py   # MCP plugin (3 tools only)
  estate_list   — list all available intents
  estate_show   — show args for one intent
  estate_invoke — run an intent
```

**Rule: if an action is not a YAML intent, the agent cannot perform it.**

`estate_executor.py` (13 raw tools) is deleted. `estate_simulate.py` is deleted.
Only `estate_mcp.py` remains — it wraps the intent executor.

To add a new capability: write `~/.estate/intents/<name>.yaml`, commit to idp.
To invoke: `estate_invoke { intent: <name> }` via MCP, or `estate-execute <name>` directly.

Design spec: `docs/specs/2026-09-24-estate-agent-enforcement-platform.md`

## 8. Placement — the free tier decides, not the cluster

Nothing goes on the cluster by default. Place every workload by the ladder in
`docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`, first rung
that fits: delete → GitHub Actions schedule → Grafana Cloud free → Cloudflare Workers free →
laptop just in time → KEDA scale-to-zero on the node → always-on on the node. Only free tiers that
need no card or are hard-limited qualify. A PR that adds to the node states its CPU/memory
requests; the node's requests stay under 1.8 CPU. Before any node reboot, resize or drain,
calico-node must be Ready on every node.

## 9. Working style

- Only make the change that was asked for. No unsolicited refactoring.
- Do not guess. Search.
- Do not report a number you did not measure this turn.
- Do not grade a proxy — grade the thing itself.
- **Never use `grep -r`. Use `rg -l "pattern" path`** — `rg -l` finishes in <1s where
  `grep -r` times out at the 60s ceiling. A broad `grep -r` that hits the ceiling is a defect
  in the search, not evidence the thing is absent.
