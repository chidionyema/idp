# Estate stack controller contract, v1.0.0

Status: implemented; live verification currently **OPEN** because the real
user path is not healthy.

## Purpose

`bin/estate-stack-controller` is the one commanded loop from an approved stack
intent to a signed receipt. It exists to stop an agent, a workflow, a review or
an HTTP 200 from standing in for an operational stack.

The controller composes existing doors. It is not a second scheduler, receipt
ledger, router, Kubernetes control plane or infrastructure provider.

## Versioned artifacts

- Intent schema:
  `catalog/schemas/estate.stack-intent.v1.schema.json`
- Receipt schema:
  `catalog/schemas/estate.stack-receipt.v1.schema.json`
- Executable BDD contract:
  `tests/bdd/estate_stack_controller.feature`
- Falsifiers:
  `tests/test_estate_stack_controller.py`
- Pinned receipt signer:
  `docs/keys/estate-agent.pub`

An incompatible change to a schema requires a new version. An existing receipt
retains the contract hash under which it was signed and can be verified without
trusting the current working tree.

## The required stage order

```text
gate
-> plan
-> lease
-> cost
-> policy
-> apply
-> publish
-> router-deploy
-> dsh-deploy
-> verify-router
-> verify-dsh
-> verify-doors
-> publish-receipt
```

Verify mode omits `apply`, `router-deploy` and `dsh-deploy`; it never converts an
omitted mutation into a pass. The contract's canonical digest is carried in every
receipt.

## Admission

### Live claim lease

The intent names an open GitHub claim. The controller reads the newest
`CLAIM agent=... paths=... heartbeat=...` comment and derives:

```text
fencing_token = sha256(repo#issue, comment_id, agent, heartbeat, paths)
```

The fencing token is derived before the intent digest. The intent then binds it
with `intent_sha256`. The lease expires two hours after the heartbeat. A changed
comment, a newer claim, an expired heartbeat or a mismatched token is refused.

### Founder approval

Apply mode requires `approval.scheme = ed25519-founder` and an Ed25519 signature
over `intent_sha256` verified against `docs/keys/founder.pub`. Verify mode does
not need that signature because it cannot mutate.

### Cloud-only mutation

Apply mode refuses unless `GITHUB_ACTIONS=true`. It never creates a Mac-bound
execution path. The signed plan is applied from the same cloud execution, and
router and DSH deployment run through their existing cloud workflows.

### Idempotency

Apply mode checks both the local execution state and the claim issue for the same
idempotency key. A replay is refused before the capability handler. Verify mode
is repeatable because it has no mutation.

### Cost and degree of freedom

`budget_usd` is bounded by the estate ceiling. `bin/dof-gate --lease` is read on
every run. While an incident is open, apply must resolve at least one live repair
scope; verify remains read-only.

## Planning and apply

The plan is an OpenTofu saved plan containing only the addresses declared in
`targets.opentofu_targets`. The retired OKE door is not invoked.

Before apply, the controller runs the estate state guard and recreate guard
against those same targets. The apply stage consumes the saved plan; it does not
silently plan a different change.

Router and DSH deployment are dispatched only after the substrate apply measured
success. A failed or BLIND substrate stage leaves cloud yield open.

## Real user-path proof

A stage is `MEASURED_OK` only when its own primitive returns a measurement.
Failure is `FAILED`; inability to measure is `BLIND`. BLIND is never a pass.

The controller requires all of the following:

- router liveliness;
- a non-empty `/v1/models` catalogue;
- an authenticated router completion when `LITELLM_API_KEY` is available;
- DSH health and release-contract metadata;
- DSH's authentication boundary;
- an authenticated DSH entry when `DSH_LAUNCH_TOKEN` is available;
- exactly 14 `estate-doors` lanes, all `MEASURED_OK`;
- successful durable receipt publication on the claim issue.

An absent credential makes the corresponding user path BLIND, not green.

## Signed receipt

The receipt contains, for every stage:

- name and command;
- exit status;
- last measured line;
- SHA-256 of the redacted output;
- whether the stage was measured;
- `MEASURED_OK`, `FAILED` or `BLIND`.

It also binds the intent hash, claim, fencing token, idempotency key, contract
hash, targeted door count, final yield and durable publication result. Credential-
shaped output is redacted before hashing.

The payload is signed with Ed25519 when a local estate key exists. In GitHub
Actions the controller requests a short-lived GitHub OIDC token whose audience is
`estate-stack-receipt:<payload-sha256>`; the receipt carries that token as proof
bound to the exact payload and the pinned controller workflow. No private key is
copied to the runner. Verification checks the signer, audience, payload hash,
signature and receipt semantics. A correctly signed receipt that claims CLOSED
with a missing stage, non-OK stage, out-of-order stage or partial door board is
rejected.

```bash
bin/estate-stack-controller --verify-receipt <receipt.json>
```

## Yield rule

Yield is `CLOSED` only when all required stages are measured, all 14 doors answer,
the router and DSH real-user paths are measured, durable publication succeeded and
the signed receipt verifies. Anything else is `OPEN`, with the measured refusal
recorded in the receipt.

## Current measured state

The final live verify-only run published receipt
`11207e895baec518be9fdae0e3ce3ada02876368cfb99d72248ebfe5adefd9eb`;
the receipt file SHA-256 is
`440e9f563f03faa52e3ee172d0ee1c2d3cbda62129d01e1faf401f385bc6c0da`.
It reported:

- claim lease, degree of freedom, zero cost, policy fit and receipt publication:
  measured;
- OpenTofu identity: BLIND outside GitHub Actions;
- router catalogue: 13 models, authenticated completion BLIND without a caller key;
- DSH health and auth boundary: measured, authenticated entry BLIND without its
  launch credential;
- estate doors: 1/14 measured healthy;
- final yield: OPEN.

This is an operational proof of the controller's refusal path, not a claim that
the estate stack is operating.
