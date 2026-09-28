# Personal Agent — Sovereign Spec (v1.0)

> **Status:** Draft, founder-authored, 2026-09-10.
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
