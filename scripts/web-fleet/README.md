# Meridian Web Fleet: one live-evidence task contract

**Source-only, not a deployed browser agent.** The model-facing contract is
`platform/lifeboat/src/task-packet.js`'s **`MERIDIAN-TASK-V1` /
`MERIDIAN-PATCH-V1`**, under issue [#8430](https://github.com/chidionyema/idp/issues/8430).
The historical `MERIDIAN-TASK-V2` branch-level design is superseded; its CLI now
calls the canonical V1 hydrator and `patch-wire.mjs` delegates its data-only
validation to V1. No independent V2 acceptance authority remains.

## Live source → canonical task packet (read-only)

```sh
node scripts/web-fleet/task-packet.mjs --issue 8430 \
  --file platform/lifeboat/src/task-packet.js \
  --instruction FIR-07 --owner gemini-web-unverified \
  --task FIR-07-GEMINI-001 --out /tmp/meridian-task.json
```

The GitHub adapter `github-evidence.mjs` reads the **actual current** public IDP
`main`, exact Git tree/blob SHA, original executable mode, immutable source bytes
and an open issue. It rejects a moving main, missing or inaccessible source, an
unknown mode, a mismatched hash, private payloads, and an oversized packet.
The canonical V1 packet is capped at **12,288 bytes**, written as an exclusive
owner-only file (`0600`) when `--out` is used, and marked
`DATA_ONLY_UNTRUSTED`. A packet is never a worker lease or signature.

CI failure diagnostics must be read from an authorized job-log source using a
trusted caller's `readJobLog` callback. For the standalone CLI, `--run ID`
**refuses with BLIND** until that evidence reader is present; it never guesses
stderr from job names or treats GitHub's second-granularity timestamps as
certified milliseconds. Ordinary use without `--run` is valid and reports no
observed failed job. A changing repository or absent external transport is BLIND.

To validate an untrusted model proposal, call `validateProposal(packet, proposal)`
from `platform/lifeboat/src/task-packet.js` or its compatibility entry point
`validatePatch(proposal, packet)` in `patch-wire.mjs`. Both call **exactly the
same V1 validator**. A successfully shaped proposal stays
`PROPOSED_UNTRUSTED`; only existing authenticated submit gate → Greenlane →
independent outside-in proof may promote an effect. No model, browser userscript,
CLI or signed-in tab may mint that authority.

## Evidence and tests

```sh
node --check scripts/web-fleet/task-packet.mjs
node --check scripts/web-fleet/patch-wire.mjs
node --test \
  platform/lifeboat/test/task-packet.test.mjs \
  tests/web_fleet/github-evidence.test.mjs \
  tests/web_fleet/task-packet.test.mjs
```

This path consumes no paid inference, browser scraping or hidden API quota.
The private Gemini/AI Studio handoff lives in `chidionyema/gemini-sync` issue
[#3](https://github.com/chidionyema/gemini-sync/issues/3); a GitHub task commit
is **not** evidence that Gemini Web consumed the task or produced a patch.
`submit.meridianlabs.cloud` and the proposed browser/app bridges require separate
real DNS/TLS, authenticated client and deployment probes before they are called
operational. The quoted 70–85% zero-marginal-API-cost workload share is unmeasured.
