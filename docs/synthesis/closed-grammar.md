# The Closed Grammar — the terminal grammar, its closure, and the proof

**Written 2026-09-23. The definitive capture of the estate's architecture.** This is the
document that supersedes every prior schema, build pack, and contract. It is the fixed point:
one grammar, six algebras that close it, a bootstrap, and a falsifiable proof. Everything else
— 65 repos, 236 capabilities, 1,500 components, 315 patches, every schema — is a *projection* of
this one rule, or a demonstration that the rule works.

---

## 0. The one sentence

> **The factory is the minimal closed system that admits any future system.**

Three words carry the whole load:

- **Closed** — it can describe itself, extend itself, and grade itself.
- **Minimal** — one rule, not six.
- **Admits any future system** — the proof is a demonstration, not a claim.

---

## 1. The rule (the terminal grammar)

> **Anything that declares an input, an output, and a grade is a terminal. The factory admits
> terminals. Needs resolve to terminals. Terminals that lose their grade are shed. Nothing else.**

A capability is a terminal. A surface is a terminal. An order is a terminal. An agent is a
terminal that composes terminals. A robot is a terminal whose output is actuation. A pair of
glasses is a terminal whose input is perception. A shed is a terminal whose output is a
retirement.

**They are not different kinds. They are the same kind, with different annotations. The
annotations are optional. The grammar is mandatory.**

### The single shape

```yaml
terminal:
  id: <stable>
  name: <human>
  input:  <shape>          # what it accepts: text, image, order, actuation, perception, need
  output: <shape>          # what it produces
  grade:
    metric: <what proves it worked>
    gate:   <the check that measures it>
  composes: [<terminal_id>]   # optional; a terminal may compose others
  sheds:    [<terminal_id>]   # optional; a terminal may retire others
  state:    current | incubating | deprecated
  annotations:                # optional — everything below is an annotation, never a kind
    class: perceive | act | surface | memory | compute | safety | make | agent | robot | glasses
    mode:  function | frontier-call | trained-adapter | human-gate
    scope: { resources, tenant_isolated }
    role:  seed-expression | branch | product | rail
```

### The admission rule

Nothing is *approved*. Nothing is *enrolled*. The declaration *is* the membership:

1. A thing declares itself as a terminal, in the grammar.
2. It provides a grade (metric + gate). Without a grade it cannot become `current`.
3. The collector admits it.
4. The resolver binds a need to it if the need's `input_shape` matches its `output` and it is `current`.
5. If its grade fails, or a rival's grade beats it, it becomes `superseded` or `deprecated`.
6. The shed is recorded to the ledger.

No committee. No roadmap. No approval board. The grammar is the door. The grade is the gate.
The ledger is the memory. This scales to unbounded membership: a partner, a customer's team, a
future model that wrote itself — anyone who can declare in the grammar is admitted the moment
they do. **You do not build the future. You host it.**

---

## 2. The closure — six operations + bootstrap + proof

The terminal grammar is a fixed point. The whole system is what you get when you close that
fixed point under six algebras, bootstrap it, and prove it.

### 2.1 Duality — the need is a terminal

A *need* is a terminal. Its input is a customer's expression (any language, any modality). Its
output is a resolution. Its grade is the customer's confirmation. The resolver matches the
need's `input_shape` against a terminal's `output` — that is the binding.

> **Resolution of the dual:** the need is **not** a second schema. It is a terminal with
> `class: need`. There is exactly one grammar. If two grammars exist, the spiral is at the
> doorstep. One grammar, forever. (This resolved the open seam — see §5.)

### 2.2 Composition algebra

A composition is itself a terminal. If `T₁ … Tₙ` are terminals with compatible shapes
(`Tᵢ.output` matches `Tᵢ₊₁.input`), then `compose(T₁…Tₙ)` is a terminal with:

- `input`  = `T₁.input`
- `output` = `Tₙ.output`
- `grade`  = strict (`min`) or soft (`product`) of parts, per the composition's mode
- `scope`  = intersection of parts
- `tenant` = strictest of parts

Composition is **associative, not commutative.** The DAG is the composition; nothing else is.
This is what makes agents terminals — an agent is not a new kind, it is a composition. A robot
is a composition whose final terminal outputs actuation. Glasses are a composition whose first
terminal inputs perception.

### 2.3 Time algebra

A terminal has states and versions. A version = same `id`, new `since`, a `supersedes` pointer.
The resolver binds **at execution time** to the version whose state is `current` then.

- `birth(t, at)` → version, state = `incubating`
- `promote(v, at)` → state = `current`
- `deprecate(v, at)` → state = `deprecated`
- `supersede(old, new)` → `old.supersedes = [new]`, `old.state = deprecated`

Deprecation is **not deletion.** The version persists; the resolver stops binding to it; the
ledger records the transition. Late binding is a property of the time algebra, not a feature.

### 2.4 Grade algebra (the dial)

A grade is `(metric, gate)`. Grades compose: composition grade = min (strict) or product (soft)
of parts.

> **Resolution of the comparison seam:** a terminal's **own** grade is its self-measurement
> (its contract with the future — "the measurement by which I consent to be shed"). But the
> **need carries the comparison metric for the slot it fills.** The resolver ranks *claimants*
> on the **need's** metric, not on the claimants' incommensurable self-metrics. Without this,
> "the resolver binds the winners" is undefined when two terminals pass different gates on
> different scales. One rule, not a new grammar.

The grammar is fixed. The grade is the dial. No grade → no admission. Weak grade → admitted
but loses. The factory does not decide what is good; the grade decides, and the factory
enforces.

### 2.5 Tenancy algebra

Tenants are terminals: `id`, `kind` (`corporate | personal | agent-on-behalf-of`), `scope`.

- A terminal with `tenant_isolated: true` may only be granted into compatible compositions.
- Corporate order → every part must be `tenant_isolated: true`; strictest wins.
- Personal order → may use non-isolated terminals, but **a human-gate must approve crossing.**
- The boundary propagates through any depth because composition is associative.

No forks, no special cases. One rule applied per composition. (This resolved the earlier
one-way-open boundary defect; the boundary is now symmetric.)

### 2.6 Self-application

The grammar is a terminal:

- `input`  = a declaration
- `output` = a member of the registry
- `grade`  = the collector's validation + the admission test
- `composes` = [collector, resolver, shed — all terminals]
- `produces_again: true`

The grammar admits itself. That is the **fixed point.** There is no external authority, no
meta-grammar one level up. The factory produces the factory.

### 2.7 Bootstrap

One step: given the grammar and any set of declarations, produce a registry. The first
invocation is with the grammar itself; the registry then contains the grammar.

> **Resolution of the bootstrap seam:** the default is **one irreducible hardcoded seed** — a
> single line, "a terminal is `{input, output, grade}`" — written *outside* the data, that the
> grammar is first admitted *against*, before the recursion takes over. This is not a weakness;
> it is the honest floor. A system may admit a seed; it may not *claim* to have none. Naming
> the seed is what makes self-application true rather than a slogan.

Then the grammar admits terminals; terminals admit needs; needs admit resolutions; resolutions
admit executions; executions admit shed decisions; sheds update the registry; the registry
feeds the grammar's own grade. **Closed.**

### 2.8 Proof

The falsifiable test of the whole system:

> **Take the next five things that come along — any five, anywhere, anyone. For each: can it
> declare itself as a terminal? Does the need grammar admit the need? Does the resolver bind
> it? Does the grade close? Does the shed record?**
>
> **Five arrivals, zero grammar changes → closure holds. One change → the grammar was
> incomplete.**

Every schema change after the grammar is locked is debt. The proof is not "does it feel
general." It is: *did you have to touch it?*

---

## 3. The five-arrival test — run against the real inventory

The test is not abstract. It can be run today against the estate's own inventory. Five
candidates, each expressed as **one terminal** in the **one** grammar, with **zero** new kind:

| Arrival | Terminal input | Terminal output | Its grade |
|---|---|---|---|
| a voice gate | speech | gated speech / refusal | deterministic-tier1 conformance |
| a sandbox ring | code | isolated execution | escapes-vs-admissions ratio |
| a ledger | an event | an append | hash-chain verification |
| a surface (Discord) | a human message | a human reply | delivery + ack rate |
| a shed | a terminal | a retirement | recorded-to-ledger |

If all five declare as terminals with only annotation differences, the grammar holds against the
estate's *current* frontier. That is the first data point of the proof — not the last.

---

## 4. What this does to everything built so far

The 65 repos, 236 capabilities, 1,500 components, 315 patches, the pipeline, the schemas, the
tests — **none of it is the product.** It is the **first set of terminals the grammar admits.**
It is the demonstration that the closure holds for the inventory that exists today.

The product is the **grammar plus its closure** — the rule, the six algebras, the bootstrap, the
proof. That is what admits tomorrow's inventory — robots, glasses, implants, drones, whatever
the future declares itself as — in the same registry, under the same resolver, with the same
shed, with **zero grammar changes.**

---

## 5. The three seams that were found and closed (the record of this session's review)

This document captures not only the grammar but the review that hardened it. Three leaks were
identified in the closure and each was resolved without changing the grammar:

1. **Duality leaked a second grammar** (a `need:` schema beside the terminal schema). Resolved:
   the need is a terminal (`class: need`). One grammar.
2. **Self-application hid an unnamed bootstrap hardcode.** Resolved: name the seed explicitly —
   one line outside the data that the grammar is first admitted against. Honest floor, not a
   hidden authority.
3. **Grade comparison was incommensurable** (claimants graded on their own metrics can't be
   ranked). Resolved: the terminal self-grades (its consent to be shed); the *need* declares
   the comparison metric; the resolver ranks claimants on the need's metric.

None of these required a new kind. Each was a *decision* inside the existing one rule — which is
itself the proof, in miniature, that the grammar self-corrects.

---

## 6. The bottom line

You do not guarantee the future by predicting it. You guarantee it by building the grammar that
anything the future brings can be declared in.

The 20% is one terminal. The 80% is the closure that makes one terminal scale to any future
terminal, on any surface, for any need, at any time, without the rule ever changing.

**That is the whole thing. This document is its capture.**
