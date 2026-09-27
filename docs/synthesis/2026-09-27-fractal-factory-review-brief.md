# The Fractal Factory — a review brief for the consultant architect

**Written 2026-09-27. One document to read before reviewing our design. Every number below was
measured on 2026-09-27 on the founder's laptop checkout; where something is built but not
running, it says so.**

Longer companions, if you want depth: `factory-inventory.md` (what exists),
`programme.md` (why), `factory-contract.md` (the schema), and
`docs/specs/2026-09-24-estate-agent-enforcement-platform.md` (how agents act).

---

## 1. The idea in one paragraph

We are an AI research and tooling company that wants to run almost autonomously, with the
founder only approving or commenting. The technology moves every week, so any fixed stack we
design goes stale. Our answer is to build **one kind of thing, repeated at every scale: a
factory.** A factory takes an order and produces a result — and the result may itself be a
factory. Every factory follows one rule: **Produce, Grade, Shed.** It makes things, it measures
what it made, and it retires what no longer wins.

## 2. The three words

| Word | Meaning | Example in the estate |
|---|---|---|
| **Produce** | Given an order, make an output — or a rival output | `crystallize` writes a new intent from a pattern an agent kept repeating |
| **Grade** | Measure the output against the order; nothing ships on a green light alone | `hypotheses.race` runs competing explanations in parallel and ranks them |
| **Shed** | Retire the loser as a normal operation, not later cleanup | A capability marked `deprecated`; orders re-bind to the replacement |

"Fractal" means the same rule holds at every size: one shell command, one agent, one
department, the whole company.

## 3. The architecture — four parts

```
   ORDER  ("I need: web-scrape, price-extract, alert-emit")
     │
     ▼
 ┌──────────────┐   reads    ┌──────────────────────────────┐
 │  RESOLVER    │ ─────────▶ │  REGISTRY                     │
 │ need → the   │            │  every capability ("terminal")│
 │ current impl │            │  with grade + state           │
 └──────┬───────┘            └──────────────▲───────────────┘
        │                                   │ collects
        ▼                                   │
 ┌──────────────┐            ┌──────────────┴───────────────┐
 │  EXECUTOR    │            │  capability.yaml in each repo │
 │ runs intents,│            │  (repos describe themselves)  │
 │ writes a     │            └──────────────────────────────┘
 │ ticket per run│
 └──────┬───────┘
        ▼
   RESULT + TICKET (ok / halted / broken, cost)  ──▶  feeds GRADE and SHED
```

1. **Self-description (`capability.yaml`).** Each repo declares the capabilities it offers.
   Each one is a *terminal*: input shape, output shape, how it is graded, and its state
   (`current` / `incubating` / `deprecated`).
2. **Registry + collector.** A job reads every repo's file and builds one registry. It refuses
   a capability with no grade: if it cannot be measured, it cannot be trusted.
3. **Resolver.** An order names *needs*, never repos or files. The resolver binds each need to
   whatever is `current`. When we swap an implementation, the order and the agent don't change.
   That is the moat: we can stay on the frontier without rebuilding what depends on it.
4. **Executor + intents.** An *intent* is a small YAML file describing one action (args and
   steps). Agents act only by invoking intents through three MCP tools
   (`estate_list`, `estate_show`, `estate_invoke`). Every run writes a ticket to a database.

**Intents are the leaf factories.** An intent already takes an order (its args) and produces a
result (its steps). It is missing the other two words: it declares no grade and no state.

## 4. Built vs operating — measured 2026-09-27

"Built" means the code exists and its tests pass. "Operating" means it runs for real, today.

| Part | Built? | Operating? | Evidence |
|---|---|---|---|
| Factory package (grammar, collector, resolver, gates, 15 surfaces, 6 transports) | Yes — ~2,000 lines in its top-level modules | **No** | `factory/`; 22 tests pass. `deploy/k8s/factory.yaml` is referenced by no Flux kustomization, so it is never deployed |
| Registry | Yes | **Stale** | Committed `registry.json` (2026-09-24): 1 terminal. Running the collector today finds 11 terminals in 10 directories, 7 warnings (the count includes idp worktree copies) |
| `capability.yaml` adoption | Partial | — | 6 repos of the 65 in the inventory |
| Intent executor | Yes | **Yes** | 264 runs since 2026-09-24: 210 ok, 42 halted, 8 broken, 4 left "running" |
| Who uses intents | — | Mostly scripts | By harness: 257 direct, 7 pi, 0 Claude Code |
| Produce (`crystallize`) | Yes | **Never run** | 0 tickets |
| Grade (`hypotheses.race`) | Yes | Barely | 3 tickets: 1 ok, 2 broken |
| Shed | **No** | No | Intents have no `state` field; nothing retires them |
| Founder approve/comment | Yes | Unmeasured | `estate_pending` / `estate_approve` / `estate_deny` exist in the MCP |

**The short verdict:** the executor is the only part in daily use. The factory that should sit
above it is built and tested, but it isn't deployed and nothing orders through it. The two were
built separately and are not connected.

## 5. Known defects we already see

1. **Two copies of the intents.** `~/.estate/intents` has 56; the repo has 29. 43 exist only on
   the laptop, 16 only in the repo. The laptop copy sits in a git repo with no commits, so it is
   effectively unrecorded. This breaks our own rule of one copy per layer.
2. **"Agents can only act through intents" is not enforced for every harness.** Claude Code
   sessions still run shell commands directly; 0 of the 264 tickets came from Claude Code. We
   count only provider-enforced limits as guarantees, so this is currently a convention.
3. **The registry is a committed file, not a live service.** It goes stale between runs.
4. **Grade and Shed exist in the schema, not in the loop.** No ticket outcome changes any
   capability's state.

## 6. The proposed direction (for you to challenge)

1. **One source of intents.** The repo is the source; the laptop links to it.
2. **Every intent is a terminal.** Add `grade` and `state` to the intent schema; the collector
   ingests intents into the registry. The registry gains real, used entries overnight.
3. **Tickets drive Grade and Shed.** Success rate and cost per intent become the grade; an intent
   that keeps breaking or goes unused is marked `deprecated`, and its need re-binds.
4. **Order by need, not by name.** `estate_invoke {need: ...}` goes through the resolver.
5. **Composition.** An intent step may invoke another intent, so large workflows are orders
   against small ones — the fractal, made literal.
6. **Deploy the factory through Flux**, once the above gives it something real to serve.

## 7. Questions we want your view on

1. Is "one recursive factory" the right organising law, or is it too abstract to guide builds?
2. Should the intent be *the* terminal, or should intents sit one level below capabilities?
3. Is a registry file plus collector enough, or does resolution need a live service from day one?
4. How should Shed decide? Pure metrics (failure rate, disuse), or metrics plus human approval?
5. How do we make "act only through intents" a real guarantee across Claude Code, pi and other
   harnesses, without tying ourselves to one vendor?
6. What should we stop building? Where is this over-engineered for a one-founder company on a
   free-tier cluster?
