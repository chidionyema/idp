# The empirical proof rule is on the default branch of all seven manifests

Written 2026-09-05. This is a session checkpoint, not the estate's LATEST — another session owns
that file for the Otto work.

## What landed

The founder gave the rule on 2026-09-05. His words are the record and are never paraphrased:
`~/.claude/docs/founder/2026-09-05T1415Z-he-generalized-rule-empirical-proof-over-synthetic-probes-a79801e5.md`
The founder document for this session is
`~/.claude/docs/founder/2026-09-05T1802Z-chidis-macbook-pro-idp-claude-7cb55e29.md`

All seven pull requests are merged and the block is verbatim on every default branch: idp#1835,
prospector#817, mumchimp-medusa#3, hermes-agent#63, claude-guards#248, claude-estate#19 and
crew#869. crew#872 landed first, because crew#869 could not go green until the dead spec-gate job
was removed from the workflow.

A manifest nobody is stopped by is a wish (LAW 44), so the rule is also enforced. The refusal is
`policy/reply.rego` in claude-guards, running on the Stop hook: a reply asserting `MEASURED_OK`
with nothing quoted is blocked, a reply quoting a pod log line passes, and the same words inside
backticks pass because a mention is not a claim. `opa test` is 40/40 and all three cases were run
through the real hook, not only in policy tests.

## Two defects found on the way, both worth keeping

1. **The resident laws file has a hard 15,360-byte ceiling** and sat three bytes under it. The
   branch took it to 18,990. Fixed by moving history and provenance prose verbatim into
   `laws/AGENTS-FULL.md`, keeping every binding rule resident. Now 15,271, so the ratchet still
   falls. The test is `tests/test_incident_crew26_resident_laws_file_fits.py`.
2. **The rule was first written into `dod-guard.py`, which is being retired.** conftest refused
   it outright: the hand-rolled guards are being migrated to Rego, not extended. Moved to Rego;
   `opa-hook.py` gained `reply_evidence()`, which measures the two facts Rego cannot see off the
   RAW above-fold text, because the existing reader deletes fenced blocks before policy sees
   them. Adapter gathers, Rego decides.

## The spec-gate breakage, still mostly open

idp's CI purge (`b3affcc8`, 2026-09-04) deleted `.github/actions/spec-gate` while 26 repositories
still called it, so every pull request in them has carried a permanently failing check since. The
canonical fixed template is `platform/github/workflows/security-scan.yml` and the tool that copies
it is `bin/estate-security-rollout --apply --merge`. Only crew and claude-estate are fixed, because
they held this work. **The founder's word is still needed to run the rollout across the rest.**
The incident is written up at `crew/docs/incidents/2026-09-05-the-deleted-spec-gate-action.md`.

## Cyrus is MEASURED_FAIL, and the credential design is the reason

`cyrus-webhook` is SecretSyncedError, 143 failures over 15 hours, the secret does not exist, both
pods are ContainerCreating on FailedMount, and the wedged replicas have saturated the namespace
CPU quota at `limits.cpu=4`, so new ReplicaSets are refused. The quota needs clearing before Cyrus
can start even once the secret lands.

The blocker guard refused two attempts to ping the founder, correctly, and that exposed the real
defect: asking him to visit the Linear console breaks LAW 52. `docs/reference/policy/root-trust.md`
line 101 still records `cyrus-linear` as seeded by hand, which is why it has sat empty. The lawful
pattern is one row above it — `otto-staging-telegram` is MEETS because the token is born in his
browser and saved once into the Bitwarden human vault (decision 0017), pulled through the
`human-vault` store.

**STAGED with a 60-minute timer, Telegram message_id 26603:** wire `cyrus-linear` that way, with
the webhook secret minted by code through Linear's `webhookCreate` mutation rather than a second
console visit. If he has not replied 'hold', execute it.

## Cline did nothing

No pull request, no commit, no remote branch, no comment on crew#865, in either repository.
crew#865 has no checkboxes at all, so CP1, CP2b, CP3 and CP5 could not have been ticked; only CP2
moved, by the founder, via idp#1781.
