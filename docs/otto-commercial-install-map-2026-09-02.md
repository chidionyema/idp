# Otto: the current install process, end to end — mapped 2026-09-02

Ordered by the founder ("focus on otto readiness for comercial install, seamless all the
way from beginning, lets map current fragile process end to end"). This is the map of the
process **as it exists today** — assessment only, nothing fixed here. Three read-only
sweeps: the platform side (this repo), the product side (hermes-v2), and the written
records that define the bar. Every claim carries a file and line.

## The bar this is graded against (already written, in his words)

- The golden-goose pivot (founder, 2026-09-02, verbatim capture): *"the ground beneath
  the installation must change from 'Infrastructure as Code' to 'Zero-Touch
  Provisioning'"*; the token never touches a terminal or clipboard; a tenant in under 60
  seconds with no CLI.
- The tenancy plan, ADR `0016-self-service-tenancy-not-botfather.md`
  (`origin/docs/self-service-tenancy` @ d838734a — **not on main; its own last line:
  "Not built, not started"**): one shared platform bot, a `t.me/<bot>?start=<code>`
  link binds a tenant, an `OttoTenant` composition stamps the manifests.
- The approved bootstrap plan (2026-08-31, crew#736): *"one action on our side, at most
  one tap on theirs"*, hosted-first, acceptance graded by wall-clock on a run log.
- The machine-graded readiness rows (crew `product/readiness.py`, 2026-08-28): hermes
  **pay path RED** (no signup, billing or pricing file), **second tenant RED**,
  **surface-agnostic RED**; no price or SKU named anywhere.

**Verdict in one line: for the estate, one Otto costs nine founder hands and lives on
one irreplaceable laptop; for a paying stranger, the install does not merely fail — it
cannot begin, and the money path from "customer pays" to "Otto answers" has zero wiring.**

## Map 1 — what one Otto costs the estate today

Twenty-five steps from empty cloud to a proven bot. The nine founder-hand steps:

| # | Step | Fragility |
|---|---|---|
| 1 | Oracle tenancy bootstrap — browser sign-in as tenancy owner (`bin/idp-oci-bootstrap:44`) | one-time, tolerable |
| 2 | **Create the bot in BotFather by hand** — Telegram has no API for it (`platform/vendors/consoles.yaml:104`; `bin/idp-set-root:110-116`) | per-bot, unavoidable today |
| 3 | Paste the token → repo secret (`bin/idp-set-root:26`) | assisted |
| 4 | Second bot + chat id for alerts — and **no way to discover the chat id exists in this repo** (`consoles.yaml:127-128`) | undiscoverable value |
| 5 | **Four more `SEED_HERMES_*` values by bare `gh secret set`** — not covered by `idp-set-root` at all (`oke-check.yml:178-183` vs `bin/idp-set-root:16`) | untooled, undocumented |
| 6 | Tailscale root registration (`clusters/oke/estate-config.yaml:56-61`) | one-time |
| 7 | Model-vendor keys (Anthropic/OpenRouter/…, `bin/idp-set-root:78-85`) | per-provider |
| 8 | Measure and **commit the founder's Mac username and Tailscale IP as literals** (`clusters/oke/estate-config.yaml:50-51`) | hardcoded person |
| 9 | **On the Mac itself**: `bin/idp-mac-adopt-otto` — greps Otto's public key out of CI run logs, appends to `authorized_keys`, runs `sudo systemsetup -setremotelogin on` (`bin/idp-mac-adopt-otto:43-72`) | sudo on one laptop, key by log-scraping |

Everything after that is code and CI (vault seeding, ESO sync, one Flux row at
`clusters/oke/platform.yaml:333-365`, the image registering its own webhook) — that half
is genuinely good. But the running shape is fragile even for us:

- **One replica, `Recreate`, one RWO volume, one token** (`gateway.yaml:255-257,199-208`)
  — every rollout is a 4–5 minute outage (`docs/how-to/onboarding/otto.md:47-49`), and a
  second poller *steals* the bot (hermes-v2 `SOUL.md:21`).
- **The public door lives in another repo** (the `https-otto` listener on prospector's
  Gateway) and **nothing watches it**: no certificate alert, no `getWebhookInfo` reader —
  the 2026-09-01 incident ran 11 hours dark
  (`docs/reference/incidents/2026-09-01-otto-telegram-door-and-five-unread-p0s.md:37-42`).
- **Otto's hands are one specific MacBook**: tools exec over SSH to
  `FOUNDER_MAC_USER@FOUNDER_MAC_TS_IP` (`gateway.yaml:321-324`, `mac-run.tpl:46-48`).
  Mac asleep = Otto's tools fail. A test *enforces* this coupling
  (hermes-v2 `tests/test_incident_crew561_pod_has_gh_and_knows_the_mac.py`).
- **The bot's vault entry is imperative**: `hermes-agent-env` is built by CI shell
  steps, declared nowhere in terraform, so its full key set is not enumerable from git
  (`oke-check.yml:184-192`; no `oci_vault_secret` for hermes in `platform/oci/*.tf`).
- Four credentials mount `optional: true` — a missing key silently degrades
  (`gateway.yaml:478-490`; named in `docs/founder/otto.md:50`).
- The estate's identity is hardcoded inside Otto's config —
  `platform/hermes-agent/estate.yaml:17-21,58,113` names prospector, chidionyema, crew.
  One ConfigMap, one estate, by construction.

## Map 2 — a stranger with the public repo, today

hermes-v2 ships a real installer (`./install`, 7 steps, idempotent, with a proof
harness) — better bones than expected. But a stranger hits **three hard stops**, in
order, before reaching a running agent:

1. **Step 4 dies**: the installer fetches the engine from `NousResearch/hermes-agent`
   (`install:21`), which does not hold the pinned commit — only the fork does. The repo
   already knows (`Dockerfile:26-28` and `gates.yml:52` were fixed); the installer wasn't.
2. **Step 5 dies** (interactive path): the five questions write an `estate.yaml` with no
   `hermes:` block, and `bin/render:83` refuses templates that need it.
3. **Step 7 fails**: `plugins/sovereign` is a committed **absolute-path symlink into
   `/Users/chidionyema/dev/code/idp/...`** — dangling on any other machine, and the
   verify harness returns red on it (`bin/verify-sovereign-plugin:28-44`).

Past those, the product still points at us, not at them:

4. The default model provider is the founder's private router —
   `config.yaml:6-9` `base_url: https://llm.mumchimp.com/v1` needing `LITELLM_API_KEY`,
   while the installer prompts for `ANTHROPIC_API_KEY`, which the config never uses; and
   `.env.example` documents 9 of the 15 variables actually in use.
5. Following the README's own last command (`gateway install`) turns the verify harness
   red — the launchd gateway is retired and the harness *fails on its existence*
   (`README.md:57` vs `bin/verify:293-299`).
6. **A tracked SessionStart hook clones the founder's personal Claude config over the
   stranger's `~/.claude`** (`.claude/settings.json:8`) — on a public repo, this runs
   for anyone who opens the checkout in Claude Code. Security-relevant both ways.
7. CI would catch none of it: no workflow runs `./install` or `bin/verify`
   (`gates.yml:7-11` says so outright), and the security/policy gates call
   `chidionyema/idp@main` unpinned.
8. Zero tenancy in the engine: no tenant concept in either repo (grep: 0 hits); one
   home, one state.db, one token, one user allow-list. A second customer means a full
   second deployment plus a second hand-made bot.

## Map 3 — the money path

There is none. Not fragile — absent:

- Commerce (Lago) rows are **suspended** (`clusters/oke/commerce.yaml:3,18,45,67`),
  feature defaulted off (`platform/features/features.yaml:239`).
- The `estate.commerce.order_paid` event contract exists and **nothing subscribes to
  it** — grep finds only the contract, comments and tests.
- No wiring anywhere from payment to provisioning: `grep -rniE "hermes|otto"
  platform/commerce/` → nothing.
- No price, no SKU, no signup page, no customer-facing Otto page in `docs/demo/` or
  `docs/onboarding/` (neither directory has an otto/hermes entry). Pricing exists only
  as market notes (`crew docs/product/BRAINSTORM-2026-08-30.md` §E: personal $20 settled
  in discussion, run cost $22.63/mo — never ratified into a SKU file).
- The portal has no install button; the feature toggle that lists `hermes-agent` flips
  a `suspend:` field the hermes-agent Flux row does not have
  (`backstage/templates/enable-platform-feature/template.yaml:43` vs
  `clusters/oke/platform.yaml:333-365`).

## What does not exist at all (the commercial gap, itemised)

1. Any tenancy primitive (`OttoTenant`, composition, tenant table) — ADR 0016 plans it;
   zero code on any branch.
2. Tenant binding on the shared bot (portal button + start-code) — planned, unstarted.
3. Per-lane health (a healthy Otto still reads as a red cluster) — planned, unstarted.
4. Customer-usable model access (today: our private router or nothing).
5. Pay → provision wiring, price, SKU, signup.
6. Customer onboarding/demo material.
7. A stranger-runnable install (three hard stops above).
8. An execution surface that isn't the founder's Mac.

## Decisions this map surfaces for the founder (not taken here)

- **Hosted-first vs self-hosted**: the approved bootstrap plan defers self-hosted
  explicitly, while the market-requirements note ranks "self-hosted as the qualifier"
  (C3). One of these gives way; the map can't choose.
- **The Mac coupling**: `mac-run` is a first-class, test-enforced capability with no
  customer analogue. Either it becomes a per-tenant "bring your own machine" feature or
  it is fenced out of the product build. Needs a ruling before OttoTenant is designed.
- ADR 0016's order of work (baseline → tenant binding → per-lane health → OttoTenant →
  managed bots) already carries his direction; this map found nothing that contradicts
  it and several receipts that reinforce step 1 ("a control plane stamped from a broken
  template scales the breakage").

## Sources

Platform sweep, product sweep and records inventory: session 54539261 task outputs,
2026-09-02. Peer lane record: `origin/docs/self-service-tenancy` @ d838734a. Related:
`docs/security-audit-2026-09-02.md` (feat/security-end-to-end) — three of its findings
(hermes CI `@main`, the unpinned cross-repo gate, the imperative vault entry) reappear
here as commercial-readiness defects.
