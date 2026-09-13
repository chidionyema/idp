# Recording a real agent action in the evidence ledger

## The problem this solved

On 2026-09-13 the Aevum ledger held 92 receipts and every one was `session.start` from
`aevum-core` — the layer's own heartbeat. The estate had a tamper-evident ledger with nothing in it
worth tampering with. It was up, and telling the truth about an empty file.

A door proved it could serve fourteen tools. Nothing recorded that it had.

## What it looks like now

```
$ python3 -c "import recorder; rec = recorder.from_env();
              print(rec.record(event_type='mcp.tools/call', actor='agentgateway',
                    payload={'tool':'get_estate_inventory','route':'/estate/mcp','status':200}))"
urn:aevum:audit:01a09979-e8a2-7b1d-b578-1cc1c773fad1

$ python3 -c "import recorder; print(recorder.from_env().verify())"
True
```

In the ledger:

```
sequence | event_type      | actor         | payload_hash | prior_hash
       93 | mcp.tools/call | agentgateway  | 80f4566a4c19 | 0f2bdba0ef
       94 | mcp.tools/call | agentgateway  | e9b693620fa7 | fd243b957c
```

A `prior_hash` pointing at the receipt before it is what makes it a chain rather than a list. Change
one byte of either payload and `verify()` stops returning `True`.

## Which primitive, and which one it is not

`PostgresLedger.append(event_type=, payload=, actor=, ...)` signs with the estate's Ed25519 key,
links to its predecessor and writes one row. It does **not** touch the governed knowledge graph —
that is `/v1/ingest`, a different membrane.

Recording that an action happened and asserting that a fact is true are not the same act. This only
ever does the first.

## Why it lives inside the Aevum pod

A signature is worth exactly what the key's exclusivity is worth. A separate recorder workload would
hold a second copy of the signing key, unreviewed; a receipt minted from that copy verifies against
the estate's public key and nothing in the chain would show it. One key holder, one writer.

## Run it yourself

```bash
kubectl -n observability exec deploy/aevum -c aevum -- sh -c '
  export AEVUM_SIGNING_KEY="$(cat /run/secrets/aevum/signing-key)"
  export AEVUM_POSTGRES_DSN="postgresql://aevum_evidence:$(cat /run/secrets/aevum/postgres-password)@estate-rw.estate-db.svc.cluster.local:5432/aevum_evidence"
  cd /tmp && python3 /tmp/recorder.py'
```

## What to watch

- **`verify()` returning `False` on a ledger you just wrote.** The `Engine` and the `PostgresLedger`
  must share ONE `Sigchain` object. An `Engine` built without `sigchain=` mints its own random one
  and verifies every stored event against the wrong key — it does not raise, it just reports the
  chain invalid.
- **`UndefinedTable: relation "aevum_ledger" does not exist`.** The store does not create its own
  table; `initialize_ledger_schema(conn)` must be called first.
- **A green verdict on an empty ledger.** Aevum's in-memory store reports a *valid* empty chain.
  A recorder that cannot reach Postgres must refuse, never fall back to memory.
