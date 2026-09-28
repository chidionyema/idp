# The Factory Contract — the self-description schema and the order language

**Document 3 of 3. Written 2026-09-23, for the consultant architect. Companion: the Factory**
**Inventory (doc 1) and the Programme (doc 2).**

Documents 1 and 2 said *what exists* and *why*. This document says *the shape* — the one
machine-readable contract that turns the fractal-factory law from prose into something the
platform can emit, check, and resolve against. It is the concrete bridge between the strategy
and the build. Everything here is a schema, not an opinion: where a key exists because the law
demands it, that is stated.

---

## 1. What this contract is for

Three documents, three jobs, now explicit:

- **Doc 1 (Inventory)** is the *measured tree* — what the seed has grown so far.
- **Doc 2 (Programme)** is the *law* — the spiral, and the factory as its constraint.
- **Doc 3 (this)** is the *contract* — the schema by which every repo declares its branch, and
  by which every order resolves a capability to a branch's current output.

The contract is the single most important build item because it does what the other two cannot:
it makes the platform **describe itself**, and it makes "grant any capability" a **typed,
audited operation** rather than a sentence. Without it, the inventory is a document someone
rewrites by hand (which the spiral will eat). With it, the inventory is a fact the factory emits
every hour, and the builder is real.

---

## 2. The self-description schema — `capability.yaml`

Every repo ships one file declaring the branches it owns and the capabilities each branch
produces. The schema is deliberately small: the estate already has 65 repos and a spiral to
constrain; a heavy schema is another thing to maintain, which is the exact failure it exists to
prevent.

```yaml
# capability.yaml — a repo's self-declaration of the branches it owns.
# One file per repo, committed at the root. A collector rolls every repo's
# file into the living registry (doc 1 §4); nothing is maintained by hand.

schema: "factory.contract/v1"     # the shape version; breakers bump it, never silently

repo:
  name: agent-foundry              # must match the GitHub repo name
  role: seed-expression            # one of: seed-expression | branch | product | rail

branches:                          # the factories this repo owns (>= 1)
  - name: assembly                 # the capability family it produces
    description: >-                # one grounded sentence, not marketing
      Turns an order into a running DAG of nodes over the estate bus.

    # Every branch expresses the law: PRODUCE . GRADE . SHED.
    produce:
      - node: army                 # each produced thing is itself an order-taking factory
        interface: order-in        # the kind of order it accepts
      - node: worker
        interface: job-in
    grade:
      - metric: convergence        # the number that proves the output hit the order
        gate: end-to-end-metered   # the named check that measures it
    shed:
      retires: []                  # what this branch deprecates (empty = nothing yet)

    # The three-way state is machine-readable so a resolver knows what to grant.
    state: current                 # current | incubating | deprecated
    since: "2026-09-07"            # ISO date the state last changed
    supersedes: []                 # repo:branch this one won against, if any

capabilities:                      # the concrete outputs a builder can grant (the leaves today)
  - id: price-alert-army           # stable id; the resolver keys on this
    name: "Price-alert army"
    class: act                     # perceive | act | surface | memory | compute | safety | make
    mode: function                 # function | frontier-call | trained-adapter | human-gate
    scope:                          # what the grant can and cannot touch
      resources: [web]
      tenant_isolated: true         # corporate-vs-personal boundary (doc 1 gap #9)
    produces_again: true            # a factory output may itself be ordered to produce
    state: current
```

### Why each field exists (the contract is brute law, not ceremony)

| Field | The law it encodes |
|---|---|
| `repo.role` | `seed-expression` vs `branch` vs `product` vs `rail` — keeps the fractal honest: products and rails are *also* factories, but they are not the seed; nothing may declare itself the seed twice. |
| `branches[].produce` | the **Produce** rule — every branch names what it births, and every produced thing is an `order-in` factory, so the recursion is explicit, not implied. |
| `branches[].grade` | the **Grade** rule — every branch carries the *metric and the gate* that proves it hit the order. A branch with no `grade` is refused: a factory that cannot be measured cannot be trusted (doc 2 §2). |
| `branches[].shed` | the **Shed** rule — deprecation is a declared, first-class field, not a comment someone leaves later. |
| `branches[].state` | `current` / `incubating` / `deprecated` — the three-way state that is the *entire operational model* of the research lab. The resolver grants only `current`. |
| `capabilities[].id` / `.state` | the resolver's key — the builder grants a capability by `id`, and the id resolves to whichever branch is `current` today. Deprecating an old voice gate does **not** break the order; the resolver re-binds the id. |
| `capabilities[].mode` | the filter-first ladder (`function` → `frontier-call` → `trained-adapter`), inherited from `agent-foundry/ORDER.md` — cheap by default, train only when a traffic gate justifies it. |
| `capabilities[].scope` | the boundary — `tenant_isolated` is what turns the corporate-vs-personal split from a description into an enforced fact. |
| `capabilities[].produces_again` | the fractal claim, made checkable: is this capability itself an order-taking factory? If true, a robot/glasses order can be issued against it; if false, it is (for now) a leaf. |

---

## 3. The order language — `capabilities: [...]`

This is the missing half of the `agent-foundry` order object (doc 1 gap #8). An order asks for a
goal **and** the capabilities that goal needs; the resolver binds each capability id to the
`current` branch that produces it. The order never names a repo or a file — it names a *need*,
and the factory satisfies it.

```jsonc
{
  "order_id": "ord_<ulid>",
  "tenant_id": "ten_<...>",        // corporate or personal — the same factory, two kinds of order
  "goal": "watch my competitors' prices and alert me when mine is 10% dearer",
  "capabilities": [
    { "id": "web-scrape",      "mode": "function" },       // resolves to a current branch
    { "id": "price-extract",   "mode": "frontier-call" },
    { "id": "alert-emit",      "mode": "function" }
  ],
  "assembly": { "mode": "factory", "shed": "on-gate" }      // produce . grade . shed, named
}
```

### The resolving rule (the one line that makes it a factory, not a lookup table)

> **Every `id` resolves to the `current` output of its branch. When a branch sheds an old
> output and births a new one, the `id` re-binds — the order does not change, and neither does
> the agent. Shelleing is invisible to the thing that was ordered.**

That single property is the whole moat (doc 2 §2): an agent ordered today keeps working tomorrow
*and* is automatically running the better implementation the instant it graduates, with no
rebuild, because the agent binds to the branch, never to the implementation.

---

## 4. The collector (how the contract becomes the inventory, automatically)

One collector (a `catalog-gen`-style job) reads every repo's `capability.yaml` and rolls it into
the living registry. It enforces the law mechanically:

1. **No duplicate seed** — at most one repo may declare `role: seed-expression`; a second is
   refused, not merged.
2. **Every branch proves itself** — a `grade` with a `metric` and a `gate` is required; a
   branch that cannot be measured is reported, and a resolver refuses to grant an ungraded
   output as `current`.
3. **Every shed is recorded** — when a branch flips to `deprecated`, the collector writes the
   shed to the trace branch (Aevum/ledger), so the estate's memory of every shed is a produced
   fact, not a changelog someone remembers to update.
4. **The registry is emitted, not maintained** — doc 1 becomes a *generated* artifact. The hand
   version of the inventory is the seed data; after the collector runs, the hand version is the
   fallback, not the source of truth.

This is the fractal factory applied to its own description: **the platform produces the map of
itself with the same produce-grade-shed rule it uses for everything else.**

---

## 5. What the architect builds first (the ordered build list)

This contract gives the architect the first concrete increments — the ones that make docs 1 and
2 real, in dependency order:

1. **The schema as a gate** — `check-jsonschema` against `capability.yaml` in `bin/idp-ci`, so a
   repo that declares itself is validated like any other manifest (the estate already does this
   for the gateway; extend the same rung).
2. **The `capabilities: [...]` field on the order** — the grant operation (doc 1 gap #8),
   resolving ids against the registry.
3. **The collector** — the job that rolls 65 repos' `capability.yaml` into one living registry,
   emitting the inventory as a generated artifact.
4. **The resolver's `current` bind** — the one-line rule from §3, so deprecation is invisible to
   the ordered agent (the moat, made mechanical).
5. **`tenant_isolated` enforcement** — the corporate-vs-personal boundary as an enforced fact,
   not a flag (doc 1 gap #9).

Each of these is small, typed, and checkable. Together they are the transformation documents 1
and 2 describe — and because they are all expressions of the same rule, none of them is a new
kind of thing. They are the seed growing its own contract.

---

*End of document 3 of 3. The three documents together — inventory, programme, contract — are
the brief: shape the product from the tree (doc 1), constrain it with the rule (doc 2), and
machine-check the shape (doc 3).*
