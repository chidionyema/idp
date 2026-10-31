# Estate memory: one plane, captured and delivered by the machine, proven across surfaces

Date: 2026-10-31. Status: proposed, for founder sign-off. Supersedes nothing until signed; amends ADR 0036.
Evidence: this checkout (`~/Documents/code/idp`, which is behind `main`), the command ledger (09-19 to 10-31),
`memory-register.json`, and the first audit run (`first-run/`). Facts about the cluster are as recorded in
the repo, not re-measured.

## 1. The decision

Memory is delivered and recorded by the machine at the points every agent must pass, not by the agent
choosing to call a tool. It is one plane with one register, one recurring audit, and one proof: a fact
captured on any surface appears in the brief on every other surface. Nothing else is built until that proof
is green. Cortex is held, not adopted, until it beats the plain store on a replay benchmark.

## 2. What the estate has already learned (only what changes the design)

| Date | What happened | Design consequence |
|---|---|---|
| 09-28, 10-20 | Founder: "agents should have no choice", "all models, agents and harnesses need to use it ... rather than implementing multiple places." Capture and injection were built into the **router** (`graph_capture.py`, `active_memory.py`). | Right idea, one place. But both die with the router. |
| 10-02 | 8 memory systems, 3 worked; one root cause, no embeddings. | Measure before adopting. The audit is that, permanently. |
| 10-15 vs 10-18 | #6227 closed "Operational"; three days later found "deployed-but-dead": 500 on prefetch, silent write loss, row-security setting missing. | No lane is operating without a live probe. |
| 10-19 | Enforcement (refuse unbriefed edit, refuse stop without write-back) built, **Claude Code only**. | Move the rule to claim-open / lane-submit, which every harness passes. |
| 10-20 | 24h server log: 5 recalls, 20,166 health probes. | Count use, not health. |
| 10-23 | Pi agents not using memory "the way Claude agents do". | Per-runtime adapters are the shape that produced the gap. |
| 10-29 | OKE control plane removed. Door unreachable since; fail-open hid it. | Fail-open is fine, silent is not. |

## 3. The design

```
 agent (any harness: claude-code cline codex cursor gemini opencode pi)
   |
   | claim-open  ---> estate-memory-claim-brief ---> brief file in the worktree   (INJECT, machine)
   | ... work ...
   | lane-submit ---> estate-memory-capture     ---> capture record + outcome     (CAPTURE, machine)
   |
   +-- also, when present: router injection / capture, Claude Code hooks, Pi/opencode extensions
                        (belt and braces; each is its own lane with its own probe)
        v
   local spool + growmos graph  --(when a home exists)-->  unified-memory-server  --(only if it wins)--> Cortex engine
        v
   estate-memory-canary   (writes on A, expects on B, every ordered pair, daily)
   estate-memory-audit    (register + probes, every 4h on the Mac, every 6h in CI, events -> Telegram)
```

Why claim-open and lane-submit: they are the path AGENTS.md already forces (claims are GitHub issues; work
lands only through the Greenlane). No new adapter per harness, no dependency on the router, no dependency on
a hook. If a harness can edit a file in this estate, it has passed both.

Local-first: capture writes to a spool and the growmos graph, which are the only memory that has run
continuously since 09-23. The door and store are an upgrade path, not a prerequisite.

## 4. Consolidation (the register is the source; this table is its summary)

KEEP (must reach `operating`): door, store, runtime-hooks, pi-opencode-injection, router-inject,
router-capture, growmos-graph, checkpoint, machine-capture (new), canary (new), audit (new).

HOLD: **cortex**. It has `cortex.toml`, a StatefulSet and manifests on this checkout, but no Dockerfile and no
vendored source, so it cannot be built. Unfreeze when the canary is green and a replay benchmark shows it helps.

RETIRE (red until the code is deleted): `bin/memory-mcp`, `memory-a2m`, `memory-dream` (each execs into a
`.memory/` directory that does not exist); `curation_worker.py` (never deployed). Not verifiable from this repo,
so listed as unverifiable until a probe from their own repo proves it: otto fast_recall / otto_facts / store Job,
Hindsight, the nine hermes plugins.

DECIDE: claude-mem (2026-09-05 spec; no evidence it was installed).

Documents: ARCHIVE the two 10-02 measurement reports (their job is now the audit) and `hosted-session-memory`;
KEEP the 10-19 Active Memory spec and the checkpoint ADR; AMEND ADR 0036 and the Cortex adoption spec to say HOLD.
ADR numbering: 0007, 0011, 0012, 0016 are each used twice here; 0036 is used twice on `main` (the second is
"a claim is stored only if it can be re-executed"). One renumbering pass; the audit then refuses a repeat.

Tickets and lanes known from the ledger (state not seen by me; the audit gains a `gh` probe to list them):
#6156 (install manifest), #6227 (active runtime, closed), #6228 (attribution), #6260, #6507, #6543,
`lane/memory-second-home` (red), `lane/memory-plane-cortex-engine` (abandoned), ticket 05 (agent URN in provenance:
keep, it becomes a field on the capture record), ticket 18 (door diagnose: the cause is already on record, so
split it into the infra decision and the hand-back patch's spool, which `machine-capture` absorbs).

## 5. The recurring audit (this is how nobody has to dig again)

- `memory-register.json` lists every lane with a verdict, static probes, live probes and the files it owns.
- Status per lane is computed, never typed: operating / built / blind / down / broken / unknown / retire-pending.
  Only `operating` is green, and only the Mac can say it (CI cannot see `~/.estate` or the door).
- Findings that turn it red: a KEEP lane not operating, a KEEP lane with no live probe, a runtime with no
  memory path, memory code or a memory document nobody classified, a repeated decision number, a register older
  than 7 days, an empty register.
- Output: `memory-audit.json`, `memory-audit.md`, and `events.jsonl` in the special-forces event shape, so the
  Telegram alerter tails it with no new code.
- When anyone asks about memory, the answer is the latest `memory-audit.md`.

First run, on this checkout (live probes blind): 18 lanes, 0 operating; 27 findings. Notable: no memory path at
all for **cline and codex**; **cursor and gemini** have the tool but nothing injects it; three launchers point at
a directory that does not exist; Cortex cannot be built; `pi-opencode-injection`, `router-inject` and `checkpoint`
have no live probe, so they can never be proven.

## 6. The bar (what "better than Meta and OpenAI" means here, measurably)

Public chat-memory benchmarks (LoCoMo, LongMemEval, BEAM) measure something this estate is not. The bar is ours:

1. Cross-surface canary: every ordered pair of required runtimes, daily. Target 100%.
2. Replay hit rate: for each failure in the ledger, did the brief available at claim time contain the lesson that
   prevents it. Reported with sample size; committed baseline; may not fall.
3. Repeat-failure rate: share of failures whose root cause already had a recorded lesson. Must fall; a lesson that
   failed to prevent its repeat becomes an enforced gate (memory that executes).
4. Stale served: facts whose own probe fails but were served as current. Target 0.
5. Door-down detection: minutes from outage to founder alert. Target under 15.
6. Coverage: required runtimes with machine capture. Target 7 of 7.

Compounding, not magic: every closed failure class stays closed, so the repeat rate decays, bounded by the
failure space. Nobody else can run 2 or 3: they have no outcome truth and no cross-vendor view.

## 7. Order of work (nothing here needs the cluster)

0. Today: put the register, audit, workflow and plist on main; wire `events.jsonl` to Telegram; delete the dead
   launchers and the curation worker; classify the documents; renumber the decisions.
1. `machine-capture`, `claim-brief` and `canary` against the local spool and growmos. Acceptance: `memory.feature`.
2. Runtime coverage falls out of 1; no per-harness work.
3. When a home exists (k3s or pay-as-you-go): bring up the store, reconcile it with growmos, write embeddings.
4. Replay benchmark; engine decision by data (Cortex, or embeddings in the existing server).
5. Lessons become gates; consolidation ("dreaming") as a bounded unit whose report is diffable.

## 8. Needs the founder

1. Store home: single-node k3s, or pay-as-you-go. Blocks step 3 only.
2. Cortex: HOLD as proposed, or keep "adopted" and accept it is unbuildable today.
3. claude-mem: retire or revive.
4. Who runs the live audit: launchd on the Mac (proposed) and install once.
5. Sign-off that the claim-open / lane-submit hooks may refuse a submit with no capture record.
