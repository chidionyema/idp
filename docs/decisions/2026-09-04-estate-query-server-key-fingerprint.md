# The estate query server refused the key the estate hands out

2026-09-04. Record for the change on `platform/mcp/agentgateway.yaml`.

## What was measured

Every client that asks the estate's query server anything goes through one front door,
`agentgateway`, and that door checks the caller's key against a fingerprint written into its
configuration. From inside the `hermes-agent` pod, with the key the vault hands that pod:

```
/estate/mcp  -> 401
/github/mcp  -> 401
```

The fingerprint of the key the vault is handing out today is `sha256:a4f5939a…`. The
fingerprint in this file, and in the live configuration the cluster is running, was
`sha256:24a593ed…`, written on 2026-08-27. The keys were reseeded after that
(`bin/idp-estate-seed`, the `hex32` step) and this file was not moved with them.

So the door was checking last week's fingerprint against this week's key and refusing every
caller — including the agent sessions that read the estate's own state, which is why
`get_estate_state` has been answering BLIND.

## What changed

The two `keyHash` values now carry the fingerprint of the key in the vault.

## The class of mistake, not just this instance

A fingerprint copied into a manifest is a second copy of a secret's identity, and a second
copy goes stale silently: nothing failed loudly when the key was reseeded, the door simply
began saying no. The durable fix is for the door to read the fingerprint from the same secret
the clients read the key from, so a reseed moves both at once. That is a larger change than
this one and is not made here; this record exists so the next person finds the reason rather
than the symptom.
