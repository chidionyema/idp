# LATEST — session 2c88870e (.wt-vendor-probe, Kimi/aider lane)

## RESUME HERE

Kimi lane is blocked on the root itself: apply run 33711941272 (2026-09-03 03:42Z) proved
SEED_KIMI_API_KEY refused at all three Kimi homes and SEED_DEEPSEEK_API_KEY refused by DeepSeek.
PR 1201 (e7d2e684) merged: the seeder probes every Kimi home and writes MOONSHOT_API_BASE.
Waiting on the founder to re-set both repo secrets from his own tab (Telegram 21834) and say
"go"; then: gh workflow run oke-check.yml --ref main -f mode=apply, read the kimi seeder line,
wait ~10 min for the ExternalSecret, one router call with model kimi, report MEASURED.

Switching now (2026-09-03 04:1xZ) to record the founder's ruling "no agent can proceed without
the estate snapshot" as docs/founder/estate-snapshot-is-mandatory.md on branch
docs/founder-estate-snapshot-mandatory, then back to the Kimi wait.

## RESUME HERE — 2026-09-04T16:07Z (session 5f6f4e72)

Getting the research engine to produce, and its evidence into prospector.

- idp#1513 merged: the dagster and langfuse copies re-ran as `-r2` and both completed, which
  releases estate-db-migrate and the llm / research-engine rows that wait on it.
- prospector#814 merged: the tick generates from researched evidence. The prospector `strict`
  ruleset now requires only guard, python and ci-ok, because dotnet and nextjs report "skipping"
  on a path-filtered pull request and a skipped required context blocks the merge forever.
- research-engine#5 armed: a run records the embedding space the router resolved its lane to.
- claude-guards: the `--auto` refusal is deleted. Branch guard/automerge-on carries a whole-file
  reformat that trips the hand-rolled-policy ratchet (1452 -> 1812 lines), so the same deletion is
  being redone as a minimal diff on guard/auto-merge-is-armed and #243 will be closed.
- Next: the engine's hourly run at :23 writes its schema and its first claims; research_reader
  reconciles itself once the engine's DDL creates research_consumer.
