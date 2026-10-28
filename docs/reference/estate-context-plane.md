# The estate's context plane — a reference

**What this is:** how to ask the estate's context engine a question, and what happens to the
answer on the way back. One engine, one compiler, one door.

**The decision:** [`docs/decisions/2026-10-27-the-estate-context-broker-is-the-only-door.md`](../decisions/2026-10-27-the-estate-context-broker-is-the-only-door.md)
**The spec:** [`docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`](../specs/2026-10-26-context-compiler-and-execution-gateway.md)

---

## The shape, in one picture

```
client ──▶ agentgateway  /context/mcp ──▶ broker (the door, the policy) ──▶ engine (private)
   (pi, claude, any MCP client)              platform/estate/context/          gortex v0.64.11
                                             broker.py + server.py            127.0.0.1, no Service,
                                                                             no route, no public address
```

The **engine** does retrieval, ranking, symbol resolution and impact analysis. It is
[gortex](https://github.com/zzet/gortex) v0.64.11, pinned by the SHA-256 of its release
tarball, and it is the estate's only one of those things.

The **broker** decides whether an answer may be served. It is the estate's law as code: a
claim, a commit, a budget, a secret name, a provenance envelope.

The **compiler** (`bin/estate-context-compile`) is a client of the engine. It does not rank; it
keeps the engine's order, fits the answer to the budget, names what it dropped, and hashes the
result so two builds of the same tree are identical.

## The three ways in

### 1. The MCP tools (the normal door, in the cluster)

The gateway serves two tools on `/context/mcp`:

| Tool | What it does | Required |
|---|---|---|
| `estate_context` | Answers a question about the estate's code, inside the caller's live claim, at a commit whose index is proven. Returns the answer, the verdict, and a provenance envelope per excerpt. | `task`, `claim_issue`, `claim_agent` |
| `estate_context_status` | The indexed commit, the engine's health, and the caller's claim state. | — |

`claim_issue` and `claim_agent` are not ceremony: the broker reads the issue's `CLAIM`
comment and refuses any path the claim does not cover.

### 2. The compiler (a plan, not an answer)

```bash
bin/estate-context-compile --task "how does the broker decide freshness" --json
bin/estate-context-compile --task "..." --budget-tokens 8000 --tier standard --door local
```

The plan carries: the items (file, lines, SHA-256 of the file and of the excerpt, the engine's
rank, the impact evidence, and a sentence saying why it is there), the commit it was read at,
the commit the index was built from, `used_tokens` against `budget_tokens`, the items that
were **dropped for budget** and the impact nodes **not covered**, and `plan_hash`.

`--door auto` (the default) uses the cluster broker when it answers and the laptop daemon
otherwise. `--door cluster` and `--door local` choose.

### 3. The local fallback (a laptop, when the cluster is out)

```bash
gortex daemon start --http-addr 127.0.0.1:7411     # the engine, on this machine
```

This is the **fallback** door (AGENTS.md §7a: the cloud is the default, the laptop route is
the fallback). The laptop daemon is the same engine, running here, with the same policy
applied by the same code.

## The verdicts a refusal can carry

A refusal names the door that would work. It never says "not allowed" and stops.

| Verdict | Means |
|---|---|
| `ALLOW` | Served. |
| `STALE_REJECT` | The index is not the commit you asked about. Rebuild it, or ask for the commit it holds. |
| `UNPROVEN_INDEX` | There is no index for that commit. The artifact has not been published, or the pod has not pulled it. |
| `ASYNC_REINDEX` | Working-copy mode: the answer is from the working tree, and the index is catching up. |
| `PATH_REFUSED` | A path you asked about is outside your claim. |
| `TOOL_REFUSED` | That tool is not on the read-only surface. |
| `BUDGET_REFUSED` | The answer does not fit the budget you set. |
| `ENGINE_UNREACHABLE` | The engine did not answer. The policy fails closed for authorization and open for observation. |

## What leaves the door

- **Secrets do not.** A secret value is replaced with `REF:<NAME>` before the answer goes out.
- **Provenance always does.** Every excerpt says which file, which commit, which lines, which
  digest.
- **Nothing mutates.** Context is read-only. The broker allows 18 read-only engine tools and
  refuses 18 mutating ones, and the two lists are checked against the engine's own catalogue
  (`gortex tools list --format json`) **and against the engine itself** (`gortex call <name>`),
  because the catalogue is preset-filtered and does not publish every callable tool.

## The gate

```bash
bin/estate-context-gate            # admit the context plane, or refuse
bin/estate-context-gate --self-test   # prove the gate can fail
```

It checks six things: one ranker; the read-only surface against the engine's live catalogue;
the engine's privacy (loopback, no published port, no route under `platform/`); the policy's
strictness (each refusal, with a deliberately lax broker in the self-test); the plan
contract (the engine's order, the required fields, the budget, the ceiling, the deterministic
hash); and **every allowlisted tool is a tool the engine actually has**.

That last one exists because a catalogue is not the whole truth: `gortex tools list` is
preset-filtered, so absence from it proves nothing. The gate therefore *asks* the engine
(`gortex call <name>`), and a name the engine does not have comes back as *'unknown tool'*.
That check found a real falsehood on 2026-10-27: `affected` was on the read-only allowlist
and the engine had never heard of it. A missing live catalogue, and an unreachable engine,
each degrade the corresponding check to a **warning that names the reason**; they never pass
as "aligned" or as "checked".

## Where it runs

| Piece | Where |
|---|---|
| The engine | a private sidecar in the broker's pod (`platform/mcp/estate-context-broker.yaml`), loopback only |
| The broker | the same pod, the only public door; the only holder of the engine token |
| The route | `agentgateway` → `/context/mcp` → `estate-context-broker.mcp.svc:8002` |
| The index | built per commit by `.github/workflows/context-index.yml`, signed, published as `oci://ghcr.io/chidionyema/idp/context-index`, pulled by the pod |
| The images | `ghcr.io/chidionyema/estate-context-broker`, `ghcr.io/chidionyema/gortex-engine` (one pod, one automation, both tags move together) |
