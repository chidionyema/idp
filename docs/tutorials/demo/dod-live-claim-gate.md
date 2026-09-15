# Demo: dod-live-claim-gate

## What you see

Open a ticket, spec, or audit doc under `docs/{tickets,specs,audits}/` that opens with a line
like:

```
**Status:** built, smoke-tested, and doored, 2026-09-15
```

and later in the body names a capability path such as `backstage/plugins/fleetview-backend/`.
Run the gate by hand against it:

```
python3 bin/dod-live-claim-gate docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md
```

If that path has no `Dockerfile` and no `kind: Deployment` manifest anywhere under
`platform/` or `clusters/` naming it, and the doc has no `**Not done:**` line, the gate refuses:

```
FAIL  dod-live-claim docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md: **Status:**
claims built/done/doored and names `backstage/plugins/fleetview-backend`, but that path has no
Dockerfile + `kind: Deployment` manifest, and the doc has no `**Not done:**` line naming the gap
```

Add either a real manifest for the path, or an honest line —

```
**Not done:** backstage/plugins/fleetview-backend has no Deployment yet, tracked at <link>
```

— and the same run passes:

```
ok    dod-live-claim 1 doc(s) graded, no unverified live claim
```

The same check runs unattended on every push (`rules.yaml` row `dod-v3-verified-not-asserted`,
CI plane) and against files a session hook hands it (session plane), so the pass above is not a
one-time run — it is the same check the estate keeps making.

## Why it exists

Founder, 2026-09-15: "let the environment decide when it is done," and "done means commercially
ready and viable" — not proven against a local daemon on someone's laptop. The same day, a ticket
declared "built, smoke-tested, and doored" on a BDD suite that only ever ran against a local
daemon, while the Backstage door it named had no Dockerfile, no Deployment, nothing running under
that name anywhere reachable. Nothing on the repository plane read the doc closely enough to
disagree with its own claim. This gate is that disagreement, made mechanical: a `**Status:**`
line that claims built/done/doored while naming a real capability path must be backed by a real
manifest, or must say plainly what is not done yet.
