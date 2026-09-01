# Onboarding: The deterministic estate compiler

## What it is for

Agents stop writing configuration files. They emit typed JSON intents — "I need a place to store
5GB of image data," "I need this container running behind a public host" — whose vocabulary
(`schema/intent/*.schema.json`) contains no estate name: no DNS zone, no registry, no cloud
provider, nowhere to hardcode one. `bin/intent-compile`, a plain non-AI script, merges each intent
with the founder's DNA (`clusters/*/estate-config.yaml`) and writes the manifests
deterministically. Change one DNA value and recompile: every compiled workload follows, the agents
never notice. Founder order 2026-09-01 ("Execute the Diamond Standard"), tracked in
[the estate compiler issue](https://github.com/chidionyema/crew/issues/804); decision record:
`docs/decisions/2026-09-01-diamond-standard-jit-compiler.md`.

## What it costs

Nothing to run: Python 3 with `jsonschema` and `yaml`, both already required by this repository.
No service, no daemon, no cluster component. Compile time is under a second per intent.

## Where it lives

- `schema/intent/` — the vocabulary (workload, storage).
- `bin/intent-compile` — intents in `intents/*.json` → manifests in `platform/compiled/<name>/`.
- `bin/intent-hydrate` — the reverse compiler: platform tree → draft intents in `intents/drafts/`.
- `tests/fixtures/intent/` — the both-ways proof; the `intent` rung in `bin/idp-ci` runs it.
- DNA keys: `ESTATE_ZONE`, `ESTATE_REGISTRY`, `ESTATE_STORAGE_PROVIDER` in
  `clusters/oke/estate-config.yaml`.

## How to use it

1. Write an intent: `intents/<name>.json` with a `capability` field (`workload` or `storage`).
2. `python3 bin/intent-compile` — refusals name the exact field or the DNA value spoken.
3. The output lands in `platform/compiled/<name>/`; it reaches the cluster only through a branch
   the founder merges and an apply he runs (permanent ruling, 2026-09-01).

## How to stop it

Delete the intent file and the matching `platform/compiled/<name>/` directory in one commit; the
founder's merge removes it. The compiler itself has no running state — not invoking it stops it.
To retire the whole lane, remove the `intent` rung from `bin/idp-ci` and the three files above;
nothing else references them.
