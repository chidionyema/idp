# Resume a killed worker on another host

Spec: `ES-20261115-resume-a-killed-worker-on-another-host` | Type: `disaster_recovery` | Effect: `shared_infra` | Risk: `critical` | State: `DRAFT`

> This Markdown is a view of `spec.json`; edit JSON and regenerate with `spec_factory.py render`. Neither file grants permissions or certifies results.

## Work-class-specific decisions

Restore authoritative state and service after loss of a primary failure domain.

- [ ] What is the real RTO/RPO and most damaging credible common-mode failure?
- [ ] Which off-host backup, signing key and restore identity are available?
- [ ] How do corruption, stale snapshots, partial effects and authority revocation reconcile?
- [ ] Which cold-start drill measures time to safe user path?

## Work-class outputs

- [ ] Recovery topology and dependencies
- [ ] Backup/restore integrity records
- [ ] Cold-restore drill and measured RTO/RPO

## 1. Authority / provenance

### Canonical issue

https://github.com/chidionyema/idp/issues/7790

### Instruction id

idp#7790

### Issuer

existing issue owner FLOW; this packet grants nothing

### Mandate revision

UNKNOWN

### Governing protocols

- AGENTS.md
- IDP ADR 0048 (ARM k3s single node)
- Greenlane

### Permitted effects

- shared_infra (authoring only; no execution from this packet)

### Required approvals

- **UNRESOLVED**


## 2. Ownership / continuity

### Accountable owner

OpenCode

### Executor

OpenCode

### Independent verifier

UNASSIGNED

### Deadline utc

UNKNOWN

### Successor policy

Durable reassign via existing FLOW; no founder re-prompt


## 3. Outcome contract

### Problem statement

After the cloud migration a worker session can die (context exhaustion, host loss) and its mission is not durably resumable by a successor on another host.

### Desired outcome

A killed worker's mission is resumed by a successor on another host from a durable checkpoint and fenced lease, with no founder re-prompt.

### Why now

P0 continuity mission; session death is routine after the migration and the founder must not be the recovery procedure.

### In scope

- durable mission checkpoint
- lease and fencing
- successor takeover
- independent readback evidence

### Out of scope

- new scheduler
- new mission ledger
- new mandatory gate
- founder notification redesign

### Acceptance criteria

- a killed worker is resumed by a successor on another host
- a stale writer is refused by the fence
- the successor leaves an independent receipt of the resumed outcome

### Baseline evidence

- https://github.com/chidionyema/idp/issues/7790

### Target metrics

- successor resumes the mission without a founder prompt
- stale write refused with a typed failure
- independent receipt names the observed outcome

### Explicit non goals

- claiming production yield from a structural draft
- replacing FLOW or Greenlane


## 4. System map / first-principles baseline

### Primary system or repo

chidionyema/idp

### Existing capabilities

- existing FLOW mission ownership
- estate memory plan ledger
- Greenlane
- capability registry

### Interfaces and contracts

- GitHub issue as canonical mission owner
- SPEC/1 packet (this file)

### Data and privacy classes

- **UNRESOLVED**

### Dependencies

- durable checkpoint store
- lease and fencing primitive

### Trust boundaries

- agent host boundary
- shared infrastructure effect

### Failure domains

- host loss
- context exhaustion
- stale writer

### Blast radius

- shared_infra

### Alternatives considered

- a single long-lived session
- manual founder restart
- a new mission ledger (rejected: duplicate layer)


## 5. Execution / deterministic preflight

### Deterministic preflight

- confirm the issue is open and owned
- confirm the checkpoint store is reachable
- confirm a lease/fence primitive exists
- confirm no competing claim on the same paths

### Work packages

- checkpoint a live mission
- kill the worker
- acquire a fenced successor lease
- resume and read back
- record the independent receipt

### Sequencing and dependencies

- checkpoint -> lease -> successor resume -> independent readback

### External effects

- writes to the existing checkpoint store

### Idempotency and reconciliation

resume is idempotent; a stale fence is refused, not merged

### Rollback or compensation

drop the successor lease; the original checkpoint remains

### Resource budget

UNKNOWN


## 6. Assurance / failure map / falsifiers

### Mapped failure modes

- unrestorable-backup
- split-brain
- stale-recovery-authority
- orphaned-side-effect

### Required tests

- kill a worker mid-mission and resume on another host
- a stale writer is fenced
- no founder prompt appears in the recovery path

### Negative tests

- Destroy access to the primary host and prove recovery from off-host artifact.
- Restore an intentionally stale checkpoint and reject conflicting writes.

### Independent evidence

- **UNRESOLVED**

### Real caller canary

UNKNOWN

### Known residual risks

- **UNRESOLVED**


## 7. Recovery and succession

### Mission id

idp#7790

### Checkpoint store

UNKNOWN

### Checkpoint triggers

- initial acceptance
- before irreversible effect
- after durable milestone
- before likely context exhaustion

### Lease and fencing

UNKNOWN

### Takeover path

UNKNOWN

### Current branch or artifact

UNKNOWN

### Pending external effects

- **UNRESOLVED**


## 8. Finality / operational proof

### Source revision

UNKNOWN

### Promotion ref

UNKNOWN

### Production revision

UNKNOWN

### Independent receipt

UNKNOWN

### Observed outcome

UNKNOWN

### Verdict

UNVERIFIED

---

## Execution discipline

1. Reuse canonical authority: protocol/standards supersede this scaffold.
2. Persist mission and checkpoint before worker execution; never depend on a chat window.
3. Run deterministic checks before nondeterministic agent work; classify every failed assumption.
4. Use context-specific tests, negative controls and independent external outcomes.
5. Treat candidate, PR, CI, merge, deployment and verified yield as separate states.
6. Failed work keeps an owner, a checkpoint and a next admissible recovery transition.
