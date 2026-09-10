# Personal Agent — Sovereign Spec (v1.2)

> **Status:** Draft, founder-authored, 2026-09-10. v1.1 folded in the Day-0 Concierge architecture
> and the Issues-for-Nunn checklist. v1.2 adds voice biometrics, an Auntie-Voice TTS surface, a
> Scam Sentinel, and a proactive Caretaker Scheduler.
> **Scope:** A personally-owned assistant that uses Nunn's own computer, Nunn's own accounts,
> Nunn's own browser — with explicit per-action consent captured once, and a Sentinel that keeps
> every raw secret out of the LLM context window.
> **Out of scope:** defeating third-party bot detection, impersonation of unrelated users, and any
> action against an account or service Nunn does not own.

---

## 1. Goals

1. **Do things for Nunn** in her normal browser, on her normal Mac, in her normal accounts.
2. **Stay legible to her.** Every state-changing action is a receipt she can read.
3. **Stay bounded.** A Sentinel blocks anything outside semantic boundaries or above her budget
   until she taps **Approve** on her phone (Out-of-Band).
4. **Keep raw secrets out of the LLM.** The Vision Brain proposes an *intent* and a *coordinate*;
   the Sentinel injects the real value at OS-input time.

## 2. Non-Goals

- This is not a general browser-automation framework. It exists for one user.
- This is not an "anti-bot bypass." If a third-party site challenges Nunn's session (because
  *she* triggered it), she answers it. The agent does not impersonate, fingerprint-spoof, or
  deceive a service on its behalf.
- This is not a cloud agent. It runs on her machine. The brain can call a model; the action
  surfaces cannot.

## 3. Architecture (3-layer, bifurcated stack)

```
┌──────────────────────────────────────────────────────────────────┐
│  Rust Sentinel (local, on Nunn's Mac)                            │
│  - Credential vault (macOS Keychain binding, never in memory     │
│    more than the moment of injection)                            │
│  - Intent guardrails (semantic boundaries + budget)              │
│  - Cryptographic ledger (every action, hash-chained)             │
│  - UI: Tauri desktop, "Approve / Revoke" panel                   │
│  - OS input: raw mouse + keystroke injection                     │
└──────────────────┬───────────────────────────────────────────────┘
                   │ gRPC / Unix-domain socket (sealed)
┌──────────────────▼───────────────────────────────────────────────┐
│  Python Vision Brain (local process, can call model API)         │
│  - Screenshots → multimodal model → {intent, x, y, surrogate}    │
│  - Stateless; no keys; no raw PII                                │
└──────────────────┬───────────────────────────────────────────────┘
                   │ HTTPS
┌──────────────────▼───────────────────────────────────────────────┐
│  Model API (Anthropic / browser-use / estate minimax lane)       │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 Iron rule
**The Vision Brain never holds a raw secret.** The LLM sees a *surrogate tag* (e.g. `user_credit_card`)
and is asked "use this surrogate" — it never knows the digits.

## 4. The Sentinel — Components

### 4.1 CredentialVault
- Binds to macOS Keychain (and Windows Credential Locker on Windows) via Rust/PyO3.
- Exposes `get_surrogate_value(surrogate_key)` — returns the real value for **one call**, at the
  exact moment the Sentinel is about to type it. Never buffered to the LLM context.

### 4.2 IntentGuardrail
- A typed boundary: `purchase`, `send_message`, `delete`, `share`, `transfer`, `login`.
- Each boundary carries a threshold (e.g. `purchase > $50 → OOB approval`).
- A boundary may be **permitted**, **OOB-required**, or **hard-forbidden**.

### 4.3 CryptographicLedger
- One line per state-changing action: `{ts, intent, coords, surrogate_tag, screenshot_hash, prev_hash}`.
- The user can read the last N receipts in the desktop panel.
- Append-only; the hash chain makes tampering visible.

### 4.4 OS input
- macOS Quartz `CGEventPost` (or Windows `SendInput`) for raw mouse + keystroke events.
- The browser sees `isTrusted === true` because the events are real hardware interrupts dispatched
  by the OS at the Sentinel's request — no Playwright/CDP in the picture for this surface.

## 5. The Vision Brain

- Stateless Python loop. Receives a screenshot, returns a JSON proposal:
  ```json
  {
    "action_type": "click_and_type",
    "intent": "Purchase item in cart",
    "coordinates": [450, 800],
    "estimated_cost": 25.00,
    "surrogate_input_required": "user_credit_card"
  }
  ```
- The Brain **does not** read DOM, scrape HTML, or hold cookies. It only sees pixels. That is the
  whole point: vision-only navigation is robust against layout changes.

## 6. Consent model — the heart of it

Every action follows this sequence:

1. **Capture** — screenshot the screen.
2. **Propose** — the Brain returns an intent + coordinates + (optional) surrogate tag.
3. **Evaluate** — the Sentinel checks the intent against the boundary table.
4. **Decide** —
   - **Permitted** actions execute immediately and produce a receipt.
   - **OOB-required** actions pause; the Sentinel pushes a notification to Nunn's phone. She taps
     **Approve** to proceed or **Revoke** to stop. The receipt records the decision.
   - **Hard-forbidden** actions never execute; the Brain is told the surrogate is unavailable.

This is what makes it *personal* and *sovereign*: the user is always the one who said yes. There is
no automation that happens without her explicit, logged, revocable consent.

## 7. Engineer handoff (the language stack)

| Layer | Language | Why |
|---|---|---|
| Vision Brain | **Python** | AI SDK ecosystem, vision libraries, browser-use. Stateless. |
| Sentinel + Vault + UI | **Rust** (Tauri) | Single-binary local distribution, memory-safe, direct OS access for secure input. |
| Proxies / operators (if/when the personal fleet grows) | **Go** | Matches the cloud-native stack already in the estate. |

Binding: Rust ↔ Python over gRPC (or local Unix-domain socket for low-latency). No raw secrets ever
cross that boundary.

### 7.1 What the engineer does *not* do

- Does **not** wire Playwright/Selenium/Puppeteer into this surface. The whole point is to drive
  Nunn's own browser through OS-level events on her own machine, with her consent — not to spin up
  a separate automation frame that the browser might detect.
- Does **not** put a raw password or card number into the LLM context window.
- Does **not** auto-resolve a third-party captcha by forging `isTrusted`. If a captcha appears
  because *Nunn* is using her account on her own machine, the Brain steps aside and lets her solve
  it. The Sentinel does not impersonate her to defeat an unrelated site's detection.

## 8. Open items (not blockers for the spec, but tracked)

- **Voice intake** — for Nunn, the hands-free case is first-class. There is a separate ticket
  (MUM-284) wiring `voice_intake` into the hermes-v2 catalogue entity.
- **Accessibility fallbacks** — large-type UI on the desktop panel, audio readout of receipts,
  "undo last action" surfaced in the menu bar.
- **Family-mode approval** — a family member can be a second OOB approver on `purchase > $X`.
- **Drift detection** — every Brain proposal is logged; if the intent distribution drifts outside
  the user's normal pattern, the Sentinel downgrades to OOB-required for everything.

---

*Drafted by the founder in session 2026-09-10; landed as a draft PR for review before any
implementation begins.*

---

## v1.1 amendment — Day-0 architecture: The Mother's Sovereign Concierge

The v1.0 spec (above) is the *sovereign* shape — Sentinel-protected, OS-level, no automation
framework. v1.1 adds the **Day-0 Concierge** shape the founder authored next: a WhatsApp/Telegram
intake, a 3-tier Guardian Engine, a Playwright persistent-session operator, and a FastAPI
concierge service. Day-0 is the pragmatic first deploy; v1.0 remains the long-horizon target.

### Day-0 component table

| Module | File | Role | Boundary |
|---|---|---|---|
| **Intake webhook** | Twilio WhatsApp Business → `/webhook/whatsapp` | Voice note → text via Whisper; text fallback | Verifies caller's phone is Mum's; rejects spoofed senders with empty TwiML |
| **Module 1 — Guardian Policy Engine** | `guardian_engine.py` | Tier 1 ≤ £15 trusted-vendor auto, Tier 2 £15-£75 trusted-vendor Mum confirm, Tier 3 > £75 or untrusted vendor → silent push to Founder | Returns typed `IntentEvaluation {tier, approved, estimated_cost, vendor, reason, approval_prompt}` |
| **Module 1a — Blacklist + Whitelist** | (same file) | Zero-tolerance: `wire transfer`, `gift card`, `crypto`, `western union`, `password`, `login details`, `bank account number`. Trusted vendors: `amazon.co.uk`, `tesco.com`, `boots.com`, `marksandspencer.com`, `sainsburys.co.uk`. | Hard-coded whitelist is a v1.0 place-holder; per-vendor trust is learned with consent |
| **Module 2 — Browser Operator** | `browser_operator.py` | Playwright Chromium `launch_persistent_context(user_data_dir=…)` carrying Nunn's existing logged-in cookies (no 2FA challenge). Vision model returns `{x, y, action, description}` from a full-page screenshot. Click dispatched via `page.mouse` with a small randomised dwell and tiny lateral jitter. Receipt is the post-checkout screenshot. | Mounts Nunn's *real* Chrome profile at deployment. In tests/dev, mounts a fake profile dir. Never mounts the real one outside deployment. |
| **Module 3 — Concierge Service** | `concierge_service.py` | FastAPI on `0.0.0.0:8000`. Routes by tier: Tier 3 silences Mum with a "working on it" reply and pushes the order to Founder's phone; Tier 2 sends Mum the confirmation prompt; Tier 1 executes and returns the receipt screenshot to Mum's chat. Dependencies: `fastapi uvicorn playwright anthropic openai httpx twilio python-multipart`. | Public surface — sits behind Cloudflare Tunnel + Twilio signature verification |

### Deps to install (Day-0)
```
pip install fastapi uvicorn playwright anthropic openai httpx twilio python-multipart
playwright install chromium
```
Env (per Day-0 spec): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MOM_PHONE_NUMBER`,
`GUARDIAN_PHONE_NUMBER`, `CHROME_PROFILE_DIR` — **out of scope until a vault-backed alternative
lands** (LAW 52 / R54: one root per provider, set once; code mints the rest). v1.1 rejects bare
env-var keys in production builds; Day-0 code as published is read-only against the spec until the
plumbing is moved to vault-backed secrets.

### Deployment shape
Mac Mini at Nunn's home Wi-Fi. Cloudflare Tunnel fronts Twilio's webhook. The Mac Mini's idle
session must auto-lock when Nunn walks away.

---

## v1.1 — Issues for Nunn (the user, not the engineer)

Nunn is not tech-savvy. These are the issues that affect *her experience*, not the engineering
ones. Tracked, not blockers for the spec landing. Each issue names *who owns it*.

1. **"What if my phone dies?"** — WhatsApp/Telegram is the *only* intake in Day-0. **Owner: Day-0
   §Intake.** Need a fallback: in-browser voice button on her Mac Mini, or an SMS shortcode to
   the same number.
2. **"What if I mispronounce 'Bisoprolol'?"** — Whisper is good, not infallible; elderly
   pronunciation of drug and brand names will fail. **Owner: Day-0 §concierge_service.** Tier-1
   must *always* read back the parsed item + price before executing, not just Tier-2.
3. **"What if my son is asleep?"** — Tier 3 silently escalates to Founder's phone. No second-line
   approval, no timeout-with-action. **Owner: Guardian Engine.** Tier 3 needs a deterministic
   fallback — either a higher-tier Guardian (your partner / her GP / a named neighbour), or a
   timed default (e.g. "approve after 4 hours no reply") that the user has *pre-configured*.
4. **"What if I change my mind?"** — no revocation path. **Owner: Browser Operator.** STOP / cancel
   must work inside the in-flight checkout window — not just pre-execute.
5. **"What if I accidentally say yes?"** — voice-only "Yes"/"No" on Tier-2 is trivial to mis-hear or
   mis-utter. **Owner: Concierge Service.** Use a *typed* reply or a two-step confirm ("Reply
   `YES 1247` to confirm ordering X") — voice confirm alone is a foot-gun.
6. **"Will I see what got bought?"** — Day-0 only ships a receipt on Tier-1 success.
   **Owner: Concierge Service.** All three tiers must echo back to Mum's chat: *"I ordered X
   for £Y from Z on <date>"* — including the Founder-approved and Mum-confirmed ones.
7. **"What if I don't know the vendor's name?"** — Mum may say "the place that does the wool
   slippers". **Owner: Guardian Engine.** Need an "I don't recognise that vendor" branch that
   *asks Mum which one* before Tier 1 fires. Today the LLM resolves it and fires — wrong-vendor
   purchases are how Mum gets sent the wrong thing.
8. **"What if my card gets charged twice?"** — Day-0 has no idempotency. **Owner: Browser
   Operator.** Single in-flight order token; the operator refuses to re-execute while one is
   already in flight.
9. **"What if the browser is logged out?"** — Persistent-context cookies expire; 2FA may
   re-trigger; Mum may be on a different device. **Owner: Browser Operator.** Report a clear,
   *non-technical* error to Mum's chat ("I couldn't reach Tesco — please sign in once on your
   Mac"), not a stack trace.
10. **"I don't trust the £75 cap"** — hard cap is a sensible default but Mum's *own* spending
    patterns matter more. **Owner: Guardian Engine.** Per-month spend tracker; ping Mum when she's
    spent more than her usual weekly pattern, even if she's under £75.
11. **"What if I have a new phone number?"** — `MUM_PHONE_NUMBER` is hard-coded. **Owner:
    Concierge Service.** Re-binding flow (text the new number from the old one with a one-time
    code) instead of a config rewrite.
12. **"Will the reply confuse me?"** — TwiML `<Message>` text. **Owner: Concierge Service.**
    Replies must be short, single-screen, and written in her own son's voice (not LLM-default).
    Track per-message template review.
13. **"What if my son comes to fix it and breaks it?"** — `CHROME_PROFILE_DIR` points at Nunn's
    *actual* Chrome profile by default. **Owner: Browser Operator.** Tests/dev run against a fake
    profile dir; the real profile is mounted only at deployment, with a one-line "you are touching
    Mum's live profile" warning printed to the operator's stdout.
14. **"What if it accidentally clicks the wrong thing?"** — vision step returns coordinates and
    the operator trusts them. **Owner: Browser Operator.** Vision-confidence threshold: if the LLM
    is not confident in the {x, y}, escalate to Tier 2 (Mum confirm) — don't auto-click.
15. **"What about Mum's privacy in the screenshot?"** — receipt is a full-page Playwright
    screenshot; if Mum has other tabs in the persistent context, the screenshot captures them.
    **Owner: Browser Operator.** Close unrelated tabs *before* navigating to the purchase flow.

---

## v1.1 — On the spec side, what we are NOT building

These mirror the sovereign non-goals in §2 and are repeated here because the Day-0 paste made
the boundary fuzzy:

- **We are not building anti-bot bypass.** The Day-0 spec frames "residential IP + Quartz OS
  Event Tap (isTrusted=true)" as if defeating third-party bot detection is a feature. It is not.
  The Browser Operator uses Nunn's *own* logged-in session on her *own* Mac. If a vendor's
  anti-bot challenges her session (because *she* triggered it), Nunn solves it. The Operator
  does not forge `isTrusted`, fingerprint-spoof, or pretend to be a different user.
- **We are not building cross-user impersonation.** Nunn only. Not "anyone in the WhatsApp
  contact list". Not "anyone whose phone number is in the env".
- **We are not building a generic browser automation framework.** This is one user, one surface.

---

## v1.2 amendment — Mother's Concierge: full warmth edition

Four new modules, all in scope of the personal-accessibility frame, none of which require
anti-bot bypass on third-party services.

### Module table (v1.2)

| Module | File | Role | Hard deps |
|---|---|---|---|
| **Voice Biometric Gate** | `voice_biometrics.py` | SpeechBrain ECAPA-TDNN speaker verification: a one-shot 15-second voice baseline (`mum_baseline.wav`) gates every inbound voice note. Score threshold `>0.25` per the upstream model card. | `speechbrain==0.5.15`, `torchaudio==2.1.0` (≈700 MB on first run) |
| **Auntie Voice Synthesizer** | `tts_audio.py` | `edge-tts` with `en-NG-EzinneNeural`, ffmpeg-transcoded to OGG/Opus so WhatsApp renders it as a native voice note (inline play button). | `edge-tts==6.1.9`, `pydub==0.25.1`, system `ffmpeg` |
| **Scam Sentinel** | `scam_sentinel.py` | Intercept forwarded scam messages before they reach the Guardian Engine. UK/Nigerian fraud patterns; phishing-link detection. Pure string matching. | none |
| **Caretaker Scheduler** | `scheduler.py` | APScheduler with daily 08:30 morning meds + 14:00 hydration nudges (cron). Boot-starts inside the FastAPI process. | `APScheduler==3.10.4` |
| **Webhook server (Day-0)** | `main.py` | Twilio WhatsApp webhook → Biometric → Whisper (Nigerian-Pidgin-prompted) → Scam → Guardian Engine → Browser Operator → Voice-note reply + receipt image. | `fastapi==0.104.1`, `uvicorn==0.24.0`, `twilio==8.10.3`, `openai==1.3.5`, `anthropic==0.7.0`, `playwright==1.40.0`, `python-multipart==0.0.6` |

### End-to-end flow (v1.2)
```
[ Mum's phone → WhatsApp voice note ]
        │
        ▼
[ Twilio webhook → /webhook/whatsapp ]
        │
        ▼
[ VoiceprintGate.verify_caller(audio) ]── fail ─▶ Founder push alert + Mum receives "I couldn't recognise your voice"
        │ pass
        ▼
[ Whisper (Nigerian English / Pidgin prompt) ]  → text
        │
        ▼
[ ScamSentinel.evaluate_threat(text) ]── is_scam ─▶ Mum: "don't click that" + Founder: copy of intercepted text
        │ clear
        ▼
[ GuardianPolicyEngine.evaluate(...) ]   ── Tier 1 / Tier 2 / Tier 3 (Day-0 §1)
        │
        ▼
[ BrowserOperator ]  ── receipt screenshot
        │
        ▼
[ AuntieVoice.synth(reply) ] ── OGG/Opus voice note back to Mum's WhatsApp
```

### Issues-for-Nunn (the user) — v1.2 batch

Adds 10 items to the v1.1 list. Tracked, not blockers for the spec landing.

16. **"What if I have a cold and my voice sounds different?"** — the biometric baseline is captured once; hay-fever, hoarseness, a sore throat all shift Mum's timbre and the ECAPA-TDNN model may reject her. **Owner: Voice Biometric Gate.** Need a per-failure-acknowledge path (Mum taps "it's really me" on her phone, baseline updates) and a liveness probe so a recording of her voice doesn't pass either.
17. **"What if my grandchild wants to order me something?"** — biometric gate is hard-coded mother-only. Family helpers are blocked. **Owner: Voice Biometric Gate.** Need a "named trusted-other voice" registry, captured with Mum's explicit approval, not implicit.
18. **"Will my voice be recorded by somebody else?"** — a recording replay of Mum's voice against the current baseline would pass the gate (no challenge-response in the current spec). **Owner: Voice Biometric Gate.** Add a one-shot challenge phrase ("repeat after me: 7 3 5 9") or a random nonce; refuse matches without it.
19. **"Will the morning voice note wake me?"** — APScheduler fires at 08:30 every day regardless of Mum's state. **Owner: Caretaker Scheduler.** Quiet hours (configurable per-Mum); skip if the previous Mum-side check-in was an "I'm out" or "I'm sleeping" message.
20. **"What if I had visitors last night and I'm tired?"** — same problem; morning voice note at fixed 08:30. **Owner: Caretaker Scheduler.** Same fix as #19; or, simpler, ask Mum once a week what her usual wake-up time is.
21. **"Will the medication reminder say which tablet?"** — the literal morning text is generic ("take your morning blood pressure tablets"); Mum has more than one med. **Owner: Caretaker Scheduler.** Per-medication schedule (med name + dose + window) configurable by Mum or her son, not hard-coded prose.
22. **"What if a forwarded message mentions bbc.com?"** — Scam Sentinel's `http` / `www` markers flag benign text like "I read it on bbc.com/news/..." as a scam. **Owner: Scam Sentinel.** Whitelist trusted news domains; require a *combination* of (link + urgency + money) to fire, not any one alone.
23. **"What if I don't recognise the WhatsApp sandbox number?"** — `from_="whatsapp:+441234567890"` is a placeholder in the spec. **Owner: main.py.** Bind to a verified Meta WhatsApp Business sender at deployment; never deploy with a sandbox number.
24. **"Will /tmp be exposed on the internet?"** — Twilio's webhook needs a public URL for the .ogg voice notes and the receipt PNG. The spec suggests serving `/tmp` via FastAPI StaticFiles or Nginx. **Owner: main.py.** Serve only a dedicated `/var/concierge/media/` directory with a *positive* allowlist of filenames; never the entire `/tmp`.
25. **"What if the morning message fails to send?"** — APScheduler's job is fire-and-forget; if Twilio is down at 08:30, Mum hears nothing. **Owner: Caretaker Scheduler + main.py.** Retry with backoff (3 attempts, exponential); if all fail, push a notification to Founder's phone with the missed message.
26. **"What if my phone is on silent?"** — WhatsApp voice notes still arrive and auto-play depending on settings. Not much can be done here, but **Owner: Caretaker Scheduler.** Default reminder hour to a Mum-configured value, not 08:30; honour Do Not Disturb hours.

### On the architectural choices in v1.2

- **SpeechBrain ECAPA-TDNN** is the right speaker-verification backbone for this surface, but the
  spec publishes a magic-number threshold (`>0.25`). That number is from the model's eval card and
  is correct *for that model*, but we hold the threshold as a configurable field, not a literal.
- **Edge-TTS en-NG-EzinneNeural** is the natural Nigerian female voice the founder picked. That's
  the voice Mum hears. Verified to be in `edge-tts`'s voice list as of v6.1.9.
- **APScheduler in the FastAPI process** ties the caretaker loop to the webhook process. If
  uvicorn restarts (deploy, OOM, ssh shell disconnect), the schedule re-binds. Acceptable for
  v1.2; v1.3 should move this out into a small systemd-managed worker if cadence gets tighter.
- **Biometric baseline at rest** (`mum_baseline.wav`): the spec keeps it as a wav on disk.
  **Owner hardening:** the baseline file MUST be stored outside /tmp and MAY NOT be exposed via
  the FastAPI StaticFiles allowlist. v1.3 encrypts it at rest with a key the Sentinel-only path can
  reach.

### What's NOT changing in v1.2

- The sovereign non-goals remain: no anti-bot bypass; no cross-user impersonation; no generic
  browser automation.
- The v1.0 Iron Rule (Sentinel never holds a raw secret) is unchanged. Env-var API keys remain
  out of scope for production builds.
- The Issues-for-Nunn checklist from v1.1 (§v1.1) stays open and tracked.

---

*Drafted by the founder in session 2026-09-10. v1.1 folded in Day-0 architecture. v1.2 adds the
warmth modules (Biometrics, Auntie Voice, Scam Sentinel, Caretaker Scheduler) and the
Issues-for-Nunn v1.2 batch. Implementation must wait for founder sign-off on the v1.2 Issues list
and consent receipt for the live deployment.*

---

## v1.3 amendment — the master build, and live duplex voice

Two founder specs folded in. v1.3a captures the master `main.py` build and the five production
fixes to the Day-0 design. v1.3b adds the live telephone surface.

### v1.3a — The master build (five critical gaps closed)

The Day-0 design as first written would have broken in Nunn's hands. Five fixes, each of which is
a moment where an elderly user loses trust in the system rather than merely a bug:

| # | Gap | Why it breaks for her | Fix |
|---|---|---|---|
| 1 | **Twilio 15-second timeout** | A browser takes 30–45s to load, add to basket and check out. Twilio drops the call and sends an error. | The webhook returns `200 OK` immediately; all browser work is detached into a `BackgroundTask`. |
| 2 | **"Amnesia" — no state** | The agent asks "This is £45, shall I buy it?" and she answers "Yes, please" — with no memory of what she is agreeing to. | A `PENDING_APPROVALS` state machine holds the intent keyed by her number until she confirms or cancels. |
| 3 | **Race condition on disk** | Two voice notes back-to-back both write `/tmp/mum_voice.ogg`, overwrite, and crash. | A UUID per voice note and per receipt screenshot. No fixed filenames anywhere. |
| 4 | **Out of stock / browser crash** | She cannot receive a stack trace. It is not her fault and must not look like it. | The whole execution loop is wrapped; code failures become a gentle, apologetic voice note. A copy goes to the Guardian. |
| 5 | **Twilio cannot read local disk** | Media must be fetchable over HTTP or the voice note never arrives. | FastAPI `StaticFiles` serves a dedicated media directory (never all of `/tmp`). |

**Two further corrections applied at build time**, because the master file as pasted would not boot:

- `@app.on_event("startup")` is deprecated in FastAPI 0.104 and removed in later versions.
  Replaced with a `lifespan` context manager.
- The caretaker was constructed as `lambda msg: asyncio.run(...)`. `asyncio.run()` inside a running
  event loop raises `RuntimeError` — the scheduler would die at boot and **no morning message would
  ever be sent**, which is precisely the failure the rest of the design exists to prevent. The
  coroutine function is passed directly, and a regression test guards it.

Code: `~/dev/code/mums-concierge/`. Seven modules, 46 tests, runnable with no network, no browser
and no model calls.

### v1.3b — Live duplex telephone (Zero-Touch onboarding)

Push-to-talk voice notes still feel like a machine: hold a button, wait in silence, receive a file.
A live phone call is the least friction available to a non-technical user.

**Onboarding — she should meet it like a helpful niece who has moved to town:**

1. **Contact-card drop.** A `.vcf` contact card sent over WhatsApp: *"Auntie Ezinne (Concierge)"*,
   with a friendly photograph and the dedicated number. She taps Save. No app, no password, no
   permissions.
2. **Proactive welcome call.** Within minutes the server rings her directly and introduces itself in
   Nigerian English — explaining, in plain words, the things it can do: her medications, groceries,
   airtime home, and someone sending her a link that looks like a scam.
3. **Passive enrollment.** During that first natural conversation the system captures her acoustic
   profile and locks her voiceprint into the biometric gate. She is never asked to "enrol".

**Live call path:**

```
Mum dials  ->  Twilio Voice  ->  (raw µ-law 8kHz)
            ->  FastAPI WebSocket  ->  streaming STT
            ->  conversational LLM  ->  streaming TTS (Ezinne)
            ->  audio back down the line
                     |
                     +-> background tool trigger: Playwright order runs silently,
                         receipt screenshot lands in her WhatsApp afterwards
```

Requirements stated by the spec:

- **Sub-500ms turn-taking** so conversation flows without dead air.
- **Barge-in.** If she says "wait, no, get the smaller one" while the agent is speaking, the agent
  stops instantly and listens. This is not a nicety — an agent that talks over an elderly user is
  the single fastest way to lose her.
- **Hands-free.** Speakerphone while she walks around the kitchen.
- **Hybrid proof.** The conversation is voice; the proof is visual. When the call ends, the browser
  finishes checkout and the receipt screenshot arrives in her WhatsApp thread.

**Engineer setup noted by the spec:** Twilio Console "A Call Comes In" -> `POST /voice/incoming`;
reverse proxy must pass WebSocket upgrade headers; telephony is `audio/x-mulaw` at 8000 Hz, so
ffmpeg must convert TTS output to 8 kHz µ-law before streaming back.

### Issues-for-Nunn — v1.3 batch

27. **"What if I call and it does not answer?"** A live call that rings out is worse than no feature.
    **Owner: voice_call_server.** Ring-through to the Guardian on the second attempt; never leave a
    silence.
28. **"What if it talks over me?"** Barge-in is specified but must be *tested*, not assumed.
    **Owner: voice_call_server.** A test that asserts the agent's outbound stream stops within one
    frame of inbound speech.
29. **"What if the line is bad and it mishears?"** Elderly callers on mobile lines are the hardest
    ASR case. **Owner: voice_call_server.** Read-back confirmation of item and price before any
    order, on the call, in her hearing.
30. **"What if someone else dials the number?"** The biometric gate is stated for voice notes; it
    must equally gate the live call before any action. **Owner: voice_call_server + VoiceprintGate.**
31. **"What if the welcome call frightens me?"** An unexpected call from an unknown number reads as
    a scam to an elderly person — the exact thing this system defends against. **Owner: onboarding.**
    The contact card must be saved *first* so the call shows a saved name, and the opening line must
    name her son immediately.
32. **"What if I don't understand the accent?"** `en-NG-EzinneNeural` is warm and familiar to her; a
    fallback voice must exist and be selectable by her. **Owner: tts_audio.**

### What is still not built

- `voice_call_server.py` — the duplex call handler is specified here, not yet implemented.
- The onboarding flow (contact card, welcome call, passive enrollment) is specified, not yet built.
- Recording-replay defence, the cold-voice lockout path, and the trusted-other registry remain open
  from v1.2.

---

## v1.4 amendment — Real-Time Duplex Bridge (sub-300ms, true barge-in)

The v1.3b call path stitched three models (Whisper STT -> text LLM -> TTS), which costs 2-3 seconds
of latency and breaks outright if Nunn speaks while the agent is talking. v1.4 replaces the pipeline
with an **audio-native frontier model** over a dual-WebSocket bridge.

### The architecture

```
Mum's phone  <--μ-law 8kHz-->  Twilio  <--WS-->  FastAPI bridge  <--WS-->  Realtime audio model
                                                      |
                                                      +--> execute_purchase tool
                                                           -> run_browser_task (Playwright, silent)
                                                           -> receipt PNG to her WhatsApp
```

Two concurrent coroutines, one per direction, joined by `asyncio.gather`:

1. **Twilio -> model.** `start` triggers the opening greeting; each `media` packet's base64 payload is
   forwarded verbatim as `input_audio_buffer.append`. No decoding, no re-encoding.
2. **Model -> Twilio.** `response.audio.delta` deltas are wrapped as `media` packets and written
   straight to the phone line.

### Why it is faster

**No transcoding.** The session declares `input_audio_format` and `output_audio_format` as
`g711_ulaw`, which is exactly what telephony carries. Audio crosses the bridge as opaque
base64 — ffmpeg is not in the path at all. The v1.3b design, by contrast, had to convert TTS output
to 8kHz µ-law before it could be streamed, which was the dominant cost.

### Barge-in (the part that matters most for her)

Barge-in is the difference between a conversation and a broadcast. An agent that talks over an
elderly user is the fastest way to make her stop using it.

Two coordinated events on `input_audio_buffer.speech_started`:

- `{"event": "clear", "streamSid": ...}` to Twilio — empties its playback buffer, silencing the
  agent mid-sentence.
- `{"type": "response.cancel"}` to the model — abandons the in-flight response so it is not still
  generating against a question she has already replaced.

Turn-taking is model-side VAD (`server_vad`, threshold 0.5, 300ms prefix padding, 500ms silence).

### The omnichannel handoff

`execute_purchase` is declared as a function tool. When she confirms, the model emits
`response.function_call_arguments.done`; the bridge speaks a one-line acknowledgement, lets the call
close naturally, and dispatches `run_browser_task` in the background. The conversation is voice; the
proof is a receipt image in her WhatsApp thread. Zero apps installed, ever.

### Issues-for-Nunn — v1.4 batch

33. **"What if it hangs up before the order is done?"** The spec has the agent *say* it is hanging up
    and then dispatch the browser task. If that dispatch fails, she has been told an order was placed
    when it was not — the worst possible failure, because she will not re-order. **Owner: bridge.**
    Dispatch must be confirmed started before the acknowledgement is spoken, and any later failure
    must push to both her WhatsApp and the Guardian.
34. **"What if I interrupt and it forgets what I asked for?"** Cancelling the response must not
    discard the half-completed intent. **Owner: bridge.** The in-flight tool argument set must be
    retained across a barge-in.
35. **"What if two orders get placed?"** Barge-in plus a tool call creates a window for a duplicate
    `execute_purchase`. **Owner: bridge.** Single in-flight order token, as in Issue #8.
36. **"What if the call drops mid-sentence?"** **Owner: bridge.** Reconnect with the pending intent
    intact, or ring her back; never leave her holding a half-finished instruction.
37. **"Is she being recorded?"** Audio streams to a third-party model provider. **Owner: bridge +
    policy.** Requires Nunn's informed consent, a stated retention position, and a disclosure at the
    start of the first call. Not optional.
38. **"What if it does not sound like the warm voice from the messages?"** v1.4 uses the model's own
    voice (`shimmer`), not `en-NG-EzinneNeural`. The phone and the WhatsApp messages would sound like
    two different people. **Owner: bridge.** Either accept and document the split, or keep one
    identity.

### What is still not built

`voice_call_server.py` (v1.3b), `realtime_bridge.py` (v1.4), and the Zero-Touch onboarding are all
specified and none are implemented. Nothing is deployed.
