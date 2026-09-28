# Onboarding: the evidence recorder

## What it is for

It writes one signed, hash-chained receipt into the estate's ledger for each agent action worth
remembering. Until 2026-09-13 the ledger held only the evidence layer's own heartbeat — 92 rows, all
`session.start` — so nothing an agent did was recorded anywhere tamper-evident.

## Use it

```bash
kubectl -n observability exec deploy/aevum -c aevum -- sh -c '
  export AEVUM_SIGNING_KEY="$(cat /run/secrets/aevum/signing-key)"
  export AEVUM_POSTGRES_DSN="postgresql://aevum_evidence:$(cat /run/secrets/aevum/postgres-password)@estate-rw.estate-db.svc.cluster.local:5432/aevum_evidence"
  cd /tmp && python3 /tmp/recorder.py'
```

From Python, in the pod:

```python
import sys; sys.path.insert(0, "/tmp")
import recorder
rec = recorder.from_env()
audit_id = rec.record(event_type="mcp.tools/call", actor="agentgateway",
                      payload={"tool": "get_estate_state", "route": "/estate/mcp", "status": 200})
assert rec.verify()
```

`record()` returns the receipt's audit id (`urn:aevum:audit:<uuid7>`). `verify()` walks the whole
chain. **If `verify()` is not `True`, nothing is recorded as far as anyone should be concerned.**

## The two environment variables, and why they are assembled by hand

The Deployment's entrypoint builds them from the mounted Secret:

```sh
export AEVUM_SIGNING_KEY="$(cat /run/secrets/aevum/signing-key)"
export AEVUM_POSTGRES_DSN="postgresql://aevum_evidence:$(cat /run/secrets/aevum/postgres-password)@estate-rw.estate-db.svc.cluster.local:5432/aevum_evidence"
```

No `${...}` appears anywhere in that file, **comments included**. Flux substitutes dollar-brace names
in a reconciled manifest before the pod runs it, and its `--strict` mode treats an unknown name as
fatal — so a comment containing one is enough to break the apply.

## What it costs

One Postgres insert and one Ed25519 signature per recorded action. Both are sub-millisecond; the
ledger holds 94 rows and a full `verify()` over the chain returns in well under a second. No new
Secret, no new credential, no new workload — the recorder runs inside the pod that already holds the
key.

## How to stop it

Delete `platform/observability/recorder/recorder.py` and stop calling it. Nothing schedules it, and
no resident process depends on it; the Aevum server never imports it. **Do not stop it by revoking
the key** — that invalidates verification of every receipt already written.

## What to watch

- **A receipt that verifies but whose `prior_hash` is not the previous receipt's `payload_hash`.**
  That is a fork, not a chain, and it means two writers. There must be one.
- **`audit_id` returning `<bound method ...>`.** `AuditEvent.audit_id` is a plain method, not a
  property; call it. A `getattr(receipt, "audit_id")` returns the bound getter.
- **Where a person goes next:** `docs/tutorials/demo/evidence-recorder.md` shows the ledger rows.
