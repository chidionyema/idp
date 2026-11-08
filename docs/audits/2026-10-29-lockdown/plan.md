# Memory operational lockdown implementation plan

Goal: one founder instruction survives agents, sessions and outages, and the existing required
gates refuse unsupported operational claims across the estate.

Spec: `audit.md`, `contracts.json`, and existing ADR 0036 / whole-memory issue #6164.
Architecture: extend the existing memory, execution, evidence and CI layers. No parallel registry
of production truth. Use Python 3.9-compatible host tools, existing gateway authentication and
existing Aevum evidence. Work natively in an isolated sparse worktree; leave other claims alone.

## Global constraints

No hand kubectl apply, no direct main push, no hand-raised PR, no paid infrastructure, no secret
values in artifacts. Use intents, Greenlane and Flux. Production logs and founder-path behavior
decide operation. Routine action must not depend on the founder at a laptop. Do not call an
unknown or missing proof a pass. Preserve a governed repair path during lockdown.

## Review focus

- A later request never explicitly mentions the earlier directive: the applicable constraint still holds.
- A directive is superseded or revoked while an agent is already running: stale authority is refused.
- Memory or claim lookup fails: diagnosis/recovery can proceed within policy; unrelated writes cannot acquire implicit permission.
- The same display name is used by two agents: authenticated identity, session id and claim stay distinct.
- A submitted proof is valid but belongs to another SHA, image or caller: operational certification is refused.

## Tasks and acceptance

- [x] Capture current requests with verbatim transcript locators; compare shared checkout and main.
- [x] Reproduce shared-memory brief and real instruction publication; retain the failures.
- [x] Falsify the unmerged file-existence operational completion checks without changing their files.
- [ ] Reconcile the complete documentation/link corpus and recover the exact persistent-DNA source.
- [ ] Under #6156, extend the one runtime manifest/installer for every deployed harness, including Codex.
  Tests: missing integration refuses certification; fresh and running sessions retrieve the same directive version.
- [ ] Under #7397 and infrastructure recovery, restore the existing door and prove acknowledged-write durability,
  bounded fallback, heartbeat recomputation, isolated restore and idempotent replay.
- [ ] Under #6164, extend `bin/memory-gate` with the criteria in `contracts.json` using existing evidence verification.
  Tests must reject missing/empty/stale/wrong-subject evidence, skipped suites and falsified success; accepted
  evidence must describe an actual caller applying an instruction and a real violating action being refused.
- [ ] Coordinate #7443 and #7474 to make candidate-bound behavior proofs required through `ci-success`,
  including queue pushes and merge groups. Remove an existing suppression only after its wrong-subject bug is fixed.
- [ ] Exercise the constrained repair rollout; run exact-candidate checks, then real-caller verification.
  Re-run after session and router restart. Expire/revoke acceptance if continuous evidence is missing/red.
- [ ] Stream pass/refuse and service-level evidence to Fleet and expose it through the founder's normal voice path.
- [ ] Apply the same contract/evidence mechanism to routing, execution, context, identity, scheduling, secrets,
  verification, recovery and Fleet, one owner per capability. Do not declare blanket compliance from memory alone.

No unchecked task is implied complete by a merged document or a green diagnostic probe.
