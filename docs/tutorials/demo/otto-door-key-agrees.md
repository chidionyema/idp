# Demo: otto-door-key-agrees

`bin/idp-otto-door-key-agrees` grades one join that no single file owns: the key Otto's door
presents, against the key the lifeboat beside it can actually validate.

Otto's door pod runs three containers. `gateway` is Otto; `otto-brain` is a LiteLLM sidecar on
`127.0.0.1:4010` holding the three homes (the estate router, the direct vendor line, the
founder's laptop); `tailscale` is the road to the third. The door sends every model call to
`LITELLM_BASE_URL`, which is the sidecar. LiteLLM compares a *master* key in process, but a
*virtual* key is a row in a Postgres — and the sidecar is a lifeboat with no database. Present
a virtual key to it and it answers before any home is tried:

```
400 {"error":{"message":"No connected db.","type":"no_db_connection"}}
```

Run it against the deployment as it ships:

```
$ python3 bin/idp-otto-door-key-agrees
ok    door and lifeboat derive the same master key from Secret/otto-gateway-router
```

And against the shape that was live on 2026-09-10, kept as a fixture:

```
$ python3 bin/idp-otto-door-key-agrees tests/fixtures/otto-door-key/bad.yaml
FAIL  otto-brain derives its master key with sha256sum, but the door presents
      LITELLM_API_KEY unhashed. The sidecar has no database, so it cannot look up a
      virtual key: it answers 400 'No connected db.' to every turn, before any
      of the three homes is tried. Derive the same key in the door's entrypoint.
```

That fixture is not invented. For a day the three homes were merged, deployed, and reported
working, and had never carried one real turn. The door's own log, on a founder message rather
than a probe:

```
"component": "router", "event": "router.outcome",
"state": "needs_human", "lane": "judgment", "attempts": 2
```

Two attempts, two 400s, no model called, in two tenths of a second, on both replicas. The
answer-probe stayed green throughout — because it asked home 1 directly over the cluster
network and never presented a key to the lifeboat at all. A probe that goes around the door it
is meant to grade reports green through an outage, which is the failure THE EMPIRICAL PROOF
RULE exists to name.

The gate reads the parsed pod spec, never a git hunk. It resolves each container's
`LITELLM_API_KEY` back through its `volumeMounts` to the Kubernetes Secret it comes from, and
the two must land on the same Secret and the same derivation. It stays quiet when the door
points at the estate router instead of the sidecar, because a virtual key is the right key
there — a guard that refuses correct work is an outage (R38).

**Door (from the UI):** Backstage → Catalogue → `otto-gateway` → CI checks. The row is
`ottodoorkey` in the rules table; a red row names this file and the two fixtures.
