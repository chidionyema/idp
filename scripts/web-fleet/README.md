# Meridian Web Fleet: bounded ChatGPT Web / Gemini AI Studio source packets

This is source-only; not a consumer browser automator, operational Cloudflare door, active Drive Outbox or new GitHub merge authority.

`node scripts/web-fleet/task-packet.mjs --issue 7760 --file scripts/web-fleet/patch-wire.mjs` produces a model-neutral `MERIDIAN-TASK-V2` payload from public idp at an exact observed main SHA. Only caller-declared paths can be read. Files over 3400 bytes, an issue over 1500 body bytes, or a CI run at another SHA are marked BLIND rather than silently truncated. The complete packet is capped at 12KiB.

`node --test tests/web_fleet/task-packet.test.mjs` exercises nine grounded negative/positive cases.

Use `validatePatch(candidate, packet)` from `scripts/web-fleet/patch-wire.mjs` for strictly local `MERIDIAN-PATCH-V1` shape checks. A SCHEMA_VALID_ONLY verdict never grants QUAD mandate, source commit permission, CI approval or independent operational yield. The existing authenticated submit/**, fast gate and Greenlane must independently re-check exact main/base SHA, source bytes, paths, modes, owner claim, and all credentials before taking any effect.

Gemini Web / AI Studio's role: generate a source patch or adversarial review from a task packet; do not invent tool output or GitHub commit. ChatGPT Web's role: claim, verify, submit, inspect independent job receipts and hand back only verified results to the instruction ledger. Coordination uses the existing public OMNIFLOW #8133 for non-sensitive references; all private AI Studio sources continue through the existing private source-intake #7760.

The separate companion ZIP includes a manually invoked Chrome MV3 local validator and an iOS Shortcut bridge spec. No scraping, headless consumer-account login, evasion of provider quotas/CAPTCHAs, or secret in public GitHub is authorised. Consumer tier free capacity and 70-85% workload coverage remain unmeasured hypotheses, not guarantees.

Current source acceptance issue: https://github.com/chidionyema/idp/issues/7760; source SHIP-CONTRACT is not a deployed capability certificate.
