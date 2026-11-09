# Candidate Fractal Engineering Standard

Status: experimental, not yet enforced. Owner: architecture.

Existing libraries and services retain their own physical source structure. The shared engineering interface is the versioned capability boundary, not one forced framework.

- One component provides a stable versioned capability with contract, owner, explicit permissions, state semantics, tests, adapters and implementation-specific code.
- New features resolve existing capabilities before generating code. Reuse without modification first; adapt next; refactor when necessary; author new code only for a demonstrated gap.
- A composite is itself a component with the same boundary and recursively named child dependencies.
- Imports of another component's private implementation are not permitted. Public interfaces and contract versions are the only stable dependencies.
- Changes to public contracts, effects, state format, cross-component dependencies or authority require an independently owned architecture review. Internal refactors with unchanged contracts need standard automated checks only.
- Never confuse component declaration with operational proof. Existing canonical capability registry remains authoritative; no second catalogue or memory layer.
- Harvesting and permanent experimentation are separate from production assembly. Admission requires independent evidence.
- Version each component and public contract; changes to contracts are explicit and consumer compatibility is tested. Stateful implementations require state migration and rollback strategy.
- Enforce incrementally on newly created or materially changed boundaries. Report legacy drift without blocking the estate. Every failed rule must return actionable remediation.
