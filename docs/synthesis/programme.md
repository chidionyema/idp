# The Programme — the spiral, the factory, and the direction that gives it lasting shape

**Document 2 of 2. Written 2026-09-23, from the programme director, for the consultant**
**architect. Companion: the Factory Inventory (document 1).**

If document 1 is the *map of the tree the seed has grown so far*, this document is the *why
that tree was grown at all, and where it is going*. The architect reads document 1 to know what
exists; they read this to know what **must** exist and why. This is a strategy document, not an
inventory — every claim in it is braced against the measured estate where it matters, but its
job is to state the problem and the direction, because that is what the inventory alone cannot
do.

---

## 1. The problem, stated plainly (this is not a solution looking for a problem)

The industry we live in moves fast, and it accelerates. That is not a threat we can manage by
being careful. It is a **spiral**:

1. The frontier moves, so we must build the bleeding edge to stay relevant.
2. The bleeding edge produces many overlapping things, because we are a research lab and
   overlap is how we discover what wins.
3. The overlap accumulates — many harnesses, many voice gates, many judges, many sandboxes,
   many memories — each one a thing that must be watched, maintained, and reconciled.
4. The cost of managing the overlap grows faster than the value the overlap creates.
5. So we spend our energy *managing what we have* instead of *building what's next*.
6. So we fall behind the frontier we were chasing — which restarts the cycle, harder.

The end state, if nothing constrains the spiral, is the one we refuse to write down idly:
**no coherence (nothing composes), no product (nothing ships), no moat (nothing is
defensible), and eternal chaos (the management cost is the product).**

This document exists because the spiral is real and the end state is unacceptable. The
question is not *whether* to fight it. The question is: **what shape can constrain a system
that fast-moving, without slowing it down — and still give it a lasting identity?**

---

## 2. The answer: the fractal factory

The only shape we have found that constrains the spiral **without resisting it** is this:

> **Every capability is produced by a factory. A factory is a thing that takes an order and
> produces a result. The result it produces is itself a factory. There is one kind of factory,
> recursing at every scale — the platform is that recursion, nothing more.**

This is not a component architecture with a theme. It is a **law**, and the law has one rule:

> **Produce. Grade. Shed.**

- **Produce** — every factory, given an order, births other factories (narrower, or rival).
  Staying bleeding-edge is *producing rival factories and letting the better one win*.
- **Grade** — every factory grades its own output against the order (the judge factory, the
  verifier, the red-team, the twin). Nothing ships on a green light alone; it ships on a
  measurement.
- **Shed** — every factory retires its obsolete output. Deprecation is not cleanup done later;
  it is a *first-class operation of the factory*, as fundamental as producing.

Why this is the **only** answer to the spiral — measured, not rhetorical:

1. **A component is finished; a factory is never finished.** A finished thing is obsolete the
   day the frontier moves. A factory's whole nature is change, so it *cannot* be made obsolete
   by change. It absorbs it.
2. **A layered architecture has a fixed number of kinds.** The future will demand a kind we
   did not predict, and the architecture will break. A fractal has **no fixed kinds** — it is
   one rule — so it cannot be out-evolved: robots, glasses, whatever comes, are *new branches
   of the same seed*, never a new layer the architecture must invent.
3. **The moat is the recursion, not any leaf.** Any competitor can copy a voice gate. No
   competitor can copy a platform where "the industry moved" is *input into the factory*
   rather than a threat to it. Our moat is that we are the ones who can stay bleeding-edge
   *forever without drowning* — because the factory sheds what no longer serves and births what
   does, and that capacity is not a product, it is the platform itself.

---

## 3. What the seed actually is (resolving the one ambiguity that matters)

The seed is **not `agent-foundry`.** `agent-foundry` is the rule's *first-grown expression* —
the first time we embodied "order → produce → grade → shed" in a repository. The seed is older
and outlives it:

> **The seed is the rule itself: a system that takes an order, produces instances that are
> themselves order-taking systems, grades them, and sheds them.**

`agent-foundry` gets deprecated the moment a better embodiment of the rule wins — and when that
happens, the platform does not lose its anchor, because the anchor was never a repo; it was the
rule the repo demonstrated. This is why the fractal framing is not vanity: **it is the one
architecture whose anchor cannot be deprecated.**

Document 1 already shows this is not abstract. The estate has grown — without ever naming the
rule — exactly the branches the rule predicts: harness, voice, web, evals, sandbox, trace,
memory, compute, workforce, platform, products. They are not eleven layers we designed; they
are **eleven places the one seed has chosen to grow**, and the overlap the map records is not
debt — it is the seed *producing rivals and letting them compete*, exactly as the rule says.

---

## 4. What this means for the product (the direction, for the architect)

The product we are building is not "a personal agent." It is not "a concierge." It is not "a
swarm platform." Those are all **orders against the factory** — and they matter, but they are
*instances*, not the thing itself.

**The product is the factory.** Concretely, the product is:

1. **One order language** — a single way to ask the factory for anything: an agent, a swarm, a
   concierge, a robot, a pair of glasses. (Document 1 named the seed of this: `agent-foundry`'s
   order object, which still lacks the `capabilities: [...]` grant field — the architect's job.)
2. **One recursion** — every produced thing is itself an order-taking factory, so an agent can
   produce a sub-agent, a swarm can produce a specialist, a robot can produce a skill, with the
   *same mechanism* at every scale.
3. **One shed operation** — deprecation is a primitive. Old voice gates, old judges, old
   sandboxes don't linger; they are *shed on a schedule*, and the factory records that they were
   shed (the trace branch is the memory of every shed).
4. **One self-description** — the factory produces its **own description**. Every repo declares
   its branch and outputs (the `capability.yaml` schema from document 1 §4), and a collector
   rolls them into a living registry, so the map of the tree is *produced*, hourly, not
   maintained by hand. (This is the single most important move: once the platform can describe
   itself, "exhaustive inventory" stops being a document someone writes and becomes a fact the
   factory emits.)

Serving **corporate and personal clients** is then not two products — it is the *same* factory
issued two kinds of order (a corporate swarm vs. a private, consent-gated concierge), which is
exactly the `make-to-order` (private) vs `make-to-stock` (marketplace) split `agent-foundry`'s
ORDER.md already describes. The builder's "grant any capability" surface — the thing that lets a
founder assemble an agent in real time — is just **placing an order against the factory and
letting it resolve each capability to a branch's current output.**

---

## 5. The long-term direction (where this matures)

The same rule, extended across time, is the roadmap — and it needs no redesign, only growth:

- **Today**: the factory produces *agents* — Claude/pi harnesses, the Concierge, swarms, the
  Architect. The branches are software running on laptops and a cluster.
- **Near**: the factory produces *first-class surfaces* — voice, web, telegram — and the
  corporate/personal split becomes a running multi-tenant fact, not a description.
- **Later**: the factory produces *embodied agents* — a robot is not a new architecture; it is
  the same order language issued against an *actuation* branch (the OS-input injection and
  computer-use branches document 1 already records are the first buds of it). A pair of glasses
  is the same order language issued against a *perception + display* branch.
- **Enduring**: the factory produces *itself* — new factories that produce factories, at finer
  and finer grain, until the platform *is* the recursion and the inventory *is* a fact the
  recursion emits.

None of these are speculative moon-shots bolted on later. Each is the **same rule applied to a
new order**, and document 1 already shows the estate has quietly grown the first branches of
every one of them (actuation, perception, vision, voice, memory) without anyone having named the
rule they were obeying.

---

## 6. The one-line brief for the architect

> **Design the platform as one fractal factory: a single order language, a single recursion
> (every produced thing is itself a factory), a single shed primitive, and a self-describing
> registry — so that the entire estate, today's agents through tomorrow's robots and glasses,
> is the same rule applied to successive orders, and the moat is the recursion itself, not any
> leaf it has yet grown.**

Document 1 is the measured tree the seed has grown. This document is the rule that explains the
tree and the direction it is growing in. Together they are the brief: **shape the product from
the tree, and constrain it with the rule.**

---

*End of document 2 of 2.*
