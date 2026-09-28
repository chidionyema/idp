# Ticket: Mum's Sovereign Concierge — build

- **Author:** pi-crew, 2026-09-10, in response to founder's "build the thing" directive + the new
  Day-0 spec landed by the founder in session.
- **Spec source:** founder-pasted inline 2026-09-10 ("The Mother's Sovereign Concierge: Day-0
  Architecture"). Also durably landed as PR #2888 (commit 77bd0215) — that PR carries the
  sovereign v1.0 spec; this ticket covers the new Day-0 architecture.
- **Scope (intake):**
  1. Voice Concierge Webhook (FastAPI + Twilio/WhatsApp Business API + Whisper transcription).
  2. Guardian Policy Engine (3-tier autonomous / Mum-confirm / Founder-gate).
  3. Browser Operator (Playwright persistent context using Nunn's *own* Chrome profile, vision
     coordinate click, screenshot receipt).
  4. Concierge Service (FastAPI webhook → policy → operator → return media + plain reply).
- **Out of scope by design** (per the sovereign spec we already landed):
  - No operation against any account or service that is not Nunn's own.
  - No forging `isTrusted=true` against a third-party site to bypass its detection — the receipt
    chain and the Guardian Gate are the legitimacy path.
  - No env-var API keys (LAW 52 / R54). Keys via vault.
  - No silent mounting of Nunn's real Chrome profile in test or dev. Persistent-context code is
    testable with a fake profile directory; the real profile is only mounted at deployment on her
    Mac Mini.
- **Open blockers for the founder:**
  1. **Repo path.** Where does the Concierge code live? `~/dev/code/mums-concierge` /
     `~/dev/code/hermes-v2` / other? (the founder said "this is a new spec didta new agent" —
     clarifying intent).
  2. **Consent receipt.** Is Nunn's recorded consent on disk before any deployment script touches
     her real profile? (Required for the receipt chain to be legally non-trivial.)
  3. **Currency.** GBP thresholds in the spec (`£15 / £75`). The estate is in USD — these become
     configurable thresholds in code, not literals.
- **First increment (what I propose to start the build with, awaiting founder go):**
  - A failing pytest that asserts: "given a Mum-voice intent text + vendor + cost, the Guardian
    Engine returns the correct RiskTier".
  - The Guardian Engine module mirroring the spec's tier logic (no API keys, no network).
  - A clean-worktree branch + draft PR.
- **Status:** waiting on founder plain-word answer to the 3 blockers above.

---

## Comment — 2026-09-10, pi-crew: the build is complete; what remains is accounts, consent, and a deploy day

This ticket was written before the build and had been waiting on three founder answers. All three
are now settled, and the whole build is shipped. This comment closes the ticket's original scope
and states what is actually left.

### The three blockers, resolved

1. **Repo path — answered.** `~/dev/code/mums-concierge`, remote
   `https://github.com/chidionyema/mums-concierge`. The full build landed there.
2. **Consent receipt — not yet, and it is still the gate.** Nunn's recorded consent is *not* on
   disk. Nothing may touch her real Chrome profile before it is. The words are in
   `docs/DEPLOYMENT.md` §5 and enforced in `consent.py`; three promises she restates, each with a
   mechanism behind it.
3. **Currency — handled.** GBP thresholds (`£15 / £75`) became configurable, not literals, as this
   ticket proposed. No currency literal ships in code.

### Scope: all four items built

| Ticket scope item | Module | State |
|---|---|---|
| Voice Concierge Webhook | `voice_endpoints.py`, `request_auth.py` | built; HTTP paths proven local |
| Guardian Policy Engine | `guardian_engine.py` | built; 30 tests, proven local |
| Browser Operator | `browser_operator.py` | built; **proven live** against Chromium |
| Concierge Service | `main.py` | built; kill gate and cost gate proven local |

The out-of-scope list was honoured: no keys in env vars (vault), no forging `isTrusted`, no
mounting her real Chrome profile in dev — the persistent-context path is tested against a fake
profile directory.

Eighteen modules, 295 tests green. The complete account, with a verification level per module and
the specific observation behind every claim, is `mums-concierge/docs/STATUS.md`.

### What is left for this to be operational — nothing here is engineering

The software is complete. The whole system has never carried a real conversation over a real
Twilio number. In dependency order; nothing later can be validated before the earlier step.

**Step 1 — Accounts and a number. Founder only; an engineer cannot hold these.**
1. Twilio account, and either the WhatsApp Sandbox or a registered Meta sender.
2. An OpenAI API key with Realtime access, and which realtime model the account actually serves —
   `gpt-4o-realtime-preview` may not be available on the account. This is the one unverified
   external dependency behind the duplex bridge.
3. A Telegram bot via @BotFather — bot token and chat id.
4. A Cloudflare Tunnel hostname pointing at the Mac Mini.

**Step 2 — Her consent**, on a call, in the `docs/DEPLOYMENT.md` §5 words.

**Step 3 — Deploy** per `docs/DEPLOYMENT.md`. The runbook pins the voice stack precisely — Python
3.12, torch 2.2.2, speechbrain 0.5.15, huggingface-hub < 0.26 — because two other version
combinations reproduce a **silent-zero biometric failure**: the gate passes and matches nobody.

**Step 4 — Run the eight checks in §8 and observe each.** Not "wait for CI to go green". The eight
are in `mums-concierge/docs/STATUS.md` §6 Step 4: a low-value order; an order in the confirm band;
an order over the ceiling escalating with the order held; `/kill` from a phone then a restart
confirming it is *still* off; a forwarded scam; a voice note from another phone refused; a live
call with narration in the same Nigerian voice; an interruption mid-sentence she stops on.

**Step 5 — Only then tell her it works.** A system is not working because a probe answered.

### The deploy-day risks, named

Three things have never run against reality. Any of them can be what fails:

1. **The realtime bridge's transports.** `realtime_bridge.py` — the decision logic is tested with
   doubles (16 tests); the two WebSocket pumps have never run against Twilio and OpenAI together.
2. **Twilio HMAC against a real request.** Signature verification is proven, but against a
   *simulated* request. A genuine Twilio request has never traversed it.
3. **The browser operator against a defended site.** Proven on `example.com`. Amazon and Tesco
   have cookie banners, sign-in walls and anti-bot challenges it has never met.

### Design gaps that ship open

- **No retrain path.** A cold or hoarse voice locks her out until she re-enrols.
- **No trusted-other registry.** Family helpers are blocked by the biometric gate.

### Also landed this session

The suite had a flaky test, found by running it repeatedly. A challenge test hardcoded
`"the garden needs rain"` as a *wrong* answer, but that phrase is one of the eight the gate may
issue, so the answer was correct about one run in eight. It passed in isolation every time, which
is why bisecting never found it. Fixed at source, and `bin/flake-hunt` now makes the repeat-run
mechanical — it stops at the first failure and re-runs only the failing node ids from a clean
process. Commit `2e48da4` on `origin/main`.

**Status: this ticket's build scope is closed. What remains is Step 1 (founder credentials) →
Step 5, and no engineering is on the critical path.**
