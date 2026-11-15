# Resolution notes — idp#7790 SPEC/1 canary

`spec.json` is the source of truth; `SPEC.md` is the generator's projection of it. This note
records what was filled from evidence and what deliberately stayed `UNKNOWN`.

## Filled from evidence

| Field | Source |
|---|---|
| `authority.canonical_issue` | `gh issue view 7790` → open, title "P0 SPECIAL PROJECT: Agent continuity, cross-surface heartbeats and capacity-aware takeover after cloud migration" |
| `authority.governing_protocols` | `AGENTS.md`, ADR 0048, Greenlane |
| `ownership.accountable_owner` | the executing agent (OpenCode) |
| `outcome.*` | the issue title and the estate's continuity objective |
| `system_map.primary_system_or_repo` | `chidionyema/idp` |
| `continuity.mission_id` | `idp#7790` |

## Deliberately UNKNOWN

- `continuity.checkpoint_store` — not independently verified on this host.
- `assurance.real_caller_canary`, `assurance.independent_evidence` — no real caller has run.
- every `finality.*` field — `source_revision`, `promotion_ref`, `production_revision`,
  `independent_receipt`, `observed_outcome`, `verdict`.

`validate --stage verified` refuses this draft (23 unresolved fields). That refusal is the point:
the packet is structurally valid and operationally unproven.

## How to resolve it

1. Pick the real checkpoint store and lease/fence primitive.
2. Kill a worker mid-mission and resume it on another host.
3. Record the independent receipt and observed outcome in the existing issue, then re-validate at
   `--stage verified`.

Do not copy this file as proof of yield.
