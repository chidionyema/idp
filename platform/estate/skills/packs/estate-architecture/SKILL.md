---
name: estate-architecture
description: "Architecture inside the estate: one of each layer, a spec before the build, a decision record for every fork, and the gates that prove the shape is right."
license: see NOTICE.md
metadata:
  estate-category: architecture
  estate-upstream: estate-native
---

# Estate architecture -- how a decision gets written down

Architecture inside the estate: one of each layer, a spec before the build, a decision record for every fork, and the gates that prove the shape is right.

## When to use this

When the question is what shape to build, not what to type. The estate's own rules
for shape: one of each layer, a spec before the build, a decision doc per fork, and
the gates that prove the shape.

## How to use it

1. **One of each layer.** Routing, traces, identity, secrets, scheduling, catalog,
   execution boundary, evidence, verification, memory. A product may live outside
   `idp`; a duplicate layer never does.
2. **Spec before build.** The spec names the shape, the boundaries, the failure
   modes and the proof. Then the build.
3. **One fork, one decision doc.** `docs/decisions/` holds the record: the options
   considered, the one chosen, and what would make it wrong.
4. **Placement is a decision too.** The free tier decides where a workload lives
   (decision 0034): delete, GitHub Actions schedule, Grafana Cloud free, Cloudflare
   Workers free, laptop just in time, KEDA scale-to-zero, always-on.
5. **The shape must be provable.** A gate that cannot fail is not a gate; a test that
   executes nothing is not a test. Say which gate proves the shape.

## Estate rules that bind this pack

- **Tokens, not literals.** Colours, spacing, type scale and radii come from
  `packages/estate-ui-kit/tokens.json`. `ui.review` grades token purity and can fail
  the work; a pack never overrides it.
- **Voice first.** A surface the founder cannot speak to and watch live is not
  finished, however good it looks.
- **Proof, not assertion.** A claim about how a design looks is a screenshot or a
  graded `ui.review` run, never a description of what it would look like.
- **Budgets are budgets.** The JS and page budgets in `ui.review` are the caps.
  Motion and 3D packs earn their weight or they do not ship.
- **One of each layer.** If the estate already owns a component, a token or a
  pattern, this pack informs it; it does not become a second copy of it.
