# Fractal engineering profile v1 — executable adoption

The architecture is **one shared component boundary**, not one repository layout forced onto Rust, .NET, Python and TypeScript. New reusable work uses `modules/<domain>/<module>/` where practical; existing code is adopted in place. The boundary file is `component.json`. Internals are private. Composites satisfy the same external contract as primitive components. No consumer may bind directly to another module's private `src`.

## Machine-verifiable boundary

A component declares an ID, implementation version, owner, lifecycle stage, provided capability + interface version + interface file, required capabilities + compatible versions, permitted effects, state semantics and contract tests. Stateful components declare a state contract. The checker flags duplicate IDs, missing contracts, unversioned dependencies, unauthorised effect names and locally resolvable dependency cycles.

For a genuinely new capability, start from a real interface contract, not a blank repository: `python3 bin/fractal-new-component --id memory/retrieval/lexical --capability memory/retrieval --owner memory-team --contract path/to/retrieval.interface.json`. The scaffold writes a versioned `component.json`, local contract and source/test boundaries, with `stage: experimental`. It deliberately does not manufacture a fake implementation or passing test.\n\nRun `python3 bin/fractal-shape scan --root .` and `python3 -m unittest discover -s tests -p test_fractal_shape.py -v`.

The existing `bin/capability-index` and `bin/registry-gate` remain the **single discovery and verification system of record**. This profile is an authored component contract to be projected into that registry, **not a second catalogue**. This initial checker establishes code-shape conformance; it does *not* prove a component operates in production, nor validate external contracts against a remote registry.

## Rules for all coding agents

1. Look up existing capabilities before design, implementation or refactor. Prefer reuse unchanged, then adapter, then minimal refactor, then new code for a demonstrated gap.
2. Expose only versioned public contracts. Private implementation imports are not stable interfaces. Language-specific code layouts stay internal.
3. Declare effects and state ownership. No cross-component database or secret access by implication.
4. Change public contracts, effects, state contracts, migrations and cross-boundary dependencies through an **independent architecture review**. A machine report must identify the exact changed contract and affected consumers; normal internal implementation changes need only automated checks.
5. Verify the whole composition, not just its pieces. An advertised working state requires independent operational receipts from the canonical registry.
6. Harvesting (experimental supply), component laboratory (continual prototypes), and assembly (qualified production reuse) are distinct execution lanes.
7. Deprecation requires reverse dependency lookup, migration or adapter compatibility, and rollback. Never automatically replace a stateful implementation merely because a different implementation scored better.
8. A broken conformance check returns specific filenames and remediation. No blanket gate is imposed on untouched legacy modules before the checker demonstrates operational yield.

## Promotion process

**Candidate → contract tests → integration test with a real consumer → independent reviewer → operational receipt → current.** There is no claim that writing `stage: current` establishes reality. Production binding must additionally consult the registry's observed health and evidence freshness.

This profile is intentionally narrow: no new framework, ORM, queue, agent runtime or catalogue. Iterate on the contract using real examples, then integrate it into the existing indexing and Greenlane remediation workflow. The architecture checker must first be able to fail on known-bad fixtures and pass on a real existing module.

## Review routing

`python3 bin/fractal-shape review --base origin/main` classifies structural changes for human or independent-agent review. This is an advisory classification at first; reviewer identity and protected branch rules remain the actual authorisation mechanism. A reviewer cannot be the agent whose design is under review.
