# Rotating a vendor key

You change the key in Bitwarden Secrets Manager. Nothing else. This page exists for the one
thing the platform genuinely cannot do for you: deciding when it is safe to delete the old key
at the vendor.

## The two vaults, and which one this is about

The estate keeps credentials in two places, and the split is deliberate:

- **The estate vault** holds what the platform mints for itself — the Postgres password LiteLLM
  uses, the Langfuse keys, the SSO secret, database roles. You never see these and you never
  rotate them by hand.
- **Bitwarden Secrets Manager** holds the keys that are *yours*: the vendor accounts you pay
  for. This page is only about those.

## What happens on its own

1. You save the new value in Bitwarden.
2. External Secrets re-reads it within 60 seconds (`refreshInterval: 1m` on every
   `human-*` ExternalSecret) and rewrites the Kubernetes Secret.
3. Reloader sees the Secret change and rolls the Deployment that mounts it.
4. The rollout is `replicas: 2`, `maxUnavailable: 0`, `maxSurge: 1` — a new pod is ready before
   an old one goes, so no request is dropped.

Roughly two minutes end to end. There is no command for you to run and nothing to tell an agent.

## The one thing you have to get right

Between step 1 and the end of step 4 there is a window where **old pods still hold the old key**.
If you delete the old key at the vendor as soon as you have made the new one, those pods start
answering 401 until the roll finishes.

So rotate in this order:

1. **At the vendor**, create a *second* key alongside the existing one. Do not touch the old one.
2. **In Bitwarden**, replace the value with the new key.
3. **Wait about two minutes**, and check the workload is serving.
4. **At the vendor**, now delete the old key.

Both old and new pods serve successfully throughout, because both keys were valid the whole time.

## Which workloads this is true of today

`llm` — the model router. Gemini, MiniMax, Moonshot and OpenRouter are read from your Bitwarden
copy there, proved in the running pod on 2026-09-07: the estate's copy of the MiniMax key
fingerprints `54000bd4c1ef`, yours `ba6afa3e735c`, and what the process held was `ba6afa3e735c`.

`prospector`, `hermes-agent`, `flux-system` and `notify` receive your key into the namespace but
their workloads still read the estate vault's copy, so a rotation does not reach them yet. Each
reads secrets in a different shape — a projected volume, a product-side directory, a Secret
named by a Flux `Provider`, channel files — and each is wired separately. Until a namespace is
wired, rotating its key in Bitwarden changes nothing on that pod.

## When it does not land in 60 seconds

A key that was **missing** and is being added for the first time is different from one being
changed. External Secrets backs off after a failed lookup, so the first sync of a brand-new name
can take a few minutes rather than one. A key that already exists and is being changed — the
case this page is about — goes on the normal 60-second cycle.

## What to read if it does not happen

The ExternalSecret carries the verdict:

    bin/idp-kube get externalsecret -n llm

`SecretSynced` with a recent `LAST SYNC` means the new value is in the cluster and the question
is the rollout; `SecretSyncedError` means Bitwarden did not answer with that name, which is
almost always a name that does not match. The names are generated from
`platform/vendors/consoles.yaml`, and each key has its own ExternalSecret precisely so that one
bad name cannot take its neighbours down with it.
