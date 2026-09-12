# The evidence layer, running

Every agent action on this estate can now be recorded as a signed receipt that a third party
verifies without trusting us. This page is what that looks like when it runs, with the real
output.

## Record a receipt and prove it verifies

```
$ python3 bin/idp-evidence-gate tests/fixtures/aevum-evidence/good/chain.json
ok    aevum-evidence tests/fixtures/aevum-evidence/good/chain.json: 1 receipt(s), every one
      chained and signed, and the chain verifies
```

## Break it, and watch verification refuse

The whole value of the layer is this one property. A record altered after it was signed must be
refused:

```
$ python3 bin/idp-evidence-gate tests/fixtures/aevum-evidence/bad/chain.json
FAIL  aevum-evidence tests/fixtures/aevum-evidence/bad/chain.json: the chain does not verify
exit=1
```

## The empty ledger is the case that matters most

Aevum's default store is in-memory and `verify_sigchain()` answers `True` about a chain with no
events at all. A misconfigured deployment therefore reports a clean bill while recording nothing —
worse than being down, because it looks present. So an empty chain is a fail-closed FAIL:

```
$ echo '{"chain": [], "verify_sigchain": true}' | python3 bin/idp-evidence-gate /dev/stdin
FAIL  aevum-evidence /dev/stdin: the chain is EMPTY. An empty ledger verifies trivially and
      proves nothing was recorded -- fail-closed, never a clean bill
exit=1
```

## Proved against a real Postgres, not asserted

The same factory the Deployment runs was driven end to end against a real database. All four
checks must pass for the rung to exit 0:

```
ok    records a signed receipt  urn:aevum:audit:01a09615-854f-79e9-a6b8-9a097e928ee4
ok    the receipt is persisted, not in memory  1 -> 2
ok    an untampered chain verifies
ok    a second connection sees the same chain and verifies it  3 event(s)
ok    a payload edited in the database breaks verification  mutated sequence 1
```

That third and fourth line are the point: a **second connection sharing only the database**
verifies the chain, and a payload **edited directly in Postgres** breaks it.

## Where to look

- `platform/observability/aevum.yaml` — the Deployment, its Service, and its ExternalSecret
- `platform/observability/aevum.Dockerfile` — the image the estate builds
- `bin/idp-evidence-gate` — the gate
- `docs/decisions/0028-aevum-replaces-popdd-as-the-evidence-layer.md` — why this and not POPDD
- `docs/how-to/onboarding/evidence.md` — what it costs and how to stop it
