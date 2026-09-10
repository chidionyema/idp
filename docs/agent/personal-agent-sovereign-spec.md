# Personal Agent — Sovereign Spec (v1.1)

> **Status:** Draft, founder-authored, 2026-09-10. v1.1 folds in the Day-0 Concierge
> architecture and the Issues-for-Nunn checklist (Nunn is non-technical).
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

*Drafted by the founder in session 2026-09-10. v1.1 amendment landed on the same draft PR for
review. Implementation must wait for founder sign-off on the Issues-for-Nunn list and consent
receipt for the live deployment.*
