(() => {
  "use strict";

  const HOST = window.location.hostname;
  const STREAM_DEBOUNCE_MS = 1400;
  const MAX_QUARANTINE_WAIT_MS = 25000;

  // Vendor-specific assistant response selectors + input composer selectors
  function getVendorProfile() {
    if (HOST.includes("gemini.google.com")) {
      return {
        name: "gemini",
        turnSelector: "model-response, .response-container-content",
        stopSelector: 'button[aria-label*="Stop"], mat-icon[data-mat-icon-name="stop"]',
        inputSelector: 'rich-textarea .ql-editor, div[contenteditable="true"][role="textbox"], textarea'
      };
    }
    if (HOST.includes("chatgpt.com") || HOST.includes("chat.openai.com")) {
      return {
        name: "chatgpt",
        turnSelector: '[data-message-author-role="assistant"]',
        stopSelector: 'button[data-testid="stop-button"], button[aria-label*="Stop"]',
        inputSelector: '#prompt-textarea, div[contenteditable="true"][id="prompt-textarea"], textarea'
      };
    }
    if (HOST.includes("claude.ai")) {
      return {
        name: "claude",
        // Measured on https://claude.ai/new 2026-11-27: the bare .font-claude-response selector
        // matched SIX marketing nodes — the hero paragraph, "Meet Claude", the Free/Pro/Max
        // pricing headings and "Frequently asked questions" — because the landing page reuses it
        // as a typography class. Quarantining a pricing page is worse than missing a turn, so a
        // claude response must now also sit inside a conversation container.
        turnSelector: '[data-is-streaming="true"], [data-testid*="conversation"] .font-claude-response, [class*="conversation"] .font-claude-response',
        stopSelector: 'button[aria-label*="Stop"], [data-is-streaming="true"]',
        // claude.ai serves a plain textarea today: contenteditable=0, .ProseMirror=0, textarea=2
        // on https://claude.ai/new, measured 2026-11-27. Without the textarea the pill never attaches.
        inputSelector: 'textarea, div.ProseMirror[contenteditable="true"], div[contenteditable="true"], [role="textbox"]'
      };
    }
    if (HOST.includes("aistudio.google.com")) {
      return {
        name: "aistudio",
        turnSelector: 'ms-chat-turn[data-turn-role="Model"], .chat-turn-container.model',
        stopSelector: 'button[aria-label*="Stop"], button[mattooltip*="Stop"]',
        inputSelector: 'textarea, div[contenteditable="true"]'
      };
    }
    return {
      name: "generic",
      turnSelector: '[data-message-author-role="assistant"], model-response',
      stopSelector: 'button[aria-label*="Stop"]',
      inputSelector: 'textarea, div[contenteditable="true"]'
    };
  }

  const VENDOR = getVendorProfile();
  const nodeMeta = new WeakMap();
  let turnCounter = 0;
  let cachedState = null;

  function sendBg(payload) {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage(payload, (resp) => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
          } else {
            resolve(resp || { ok: false, error: "NO_RESPONSE" });
          }
        });
      } catch (err) {
        resolve({ ok: false, error: String(err) });
      }
    });
  }

  function extractCleanText(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll(".meridian-membrane-banner").forEach((n) => n.remove());
    return (clone.innerText || clone.textContent || "").trim();
  }

  function isActivelyStreaming(el) {
    if (el.getAttribute && el.getAttribute("data-is-streaming") === "true") return true;
    const stopBtn = document.querySelector(VENDOR.stopSelector);
    if (!stopBtn) return false;
    const rect = stopBtn.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function injectIntoComposer(textToInsert) {
    const box = document.querySelector(VENDOR.inputSelector);
    if (!box) {
      navigator.clipboard && navigator.clipboard.writeText(textToInsert).catch(() => {});
      return false;
    }
    box.focus();
    if (box.tagName === "TEXTAREA" || box.tagName === "INPUT") {
      const existing = box.value || "";
      box.value = textToInsert + (existing ? "\n\n" + existing : "");
      box.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      const existing = (box.innerText || "").trim();
      const combined = textToInsert + (existing ? "\n\n" + existing : "");
      box.innerText = combined;
      box.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: combined }));
    }
    return true;
  }

  function ensureBanner(el) {
    let banner = el.querySelector(":scope > .meridian-membrane-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "meridian-membrane-banner";
      el.prepend(banner);
    }
    return banner;
  }

  function renderQuarantined(el, meta) {
    el.setAttribute("data-meridian-state", "quarantined");
    const banner = ensureBanner(el);
    banner.className = "meridian-membrane-banner meridian-banner-quarantined";
    banner.textContent = "";
    const hdr = document.createElement("div");
    hdr.className = "meridian-banner-header";
    hdr.textContent = `MERIDIAN MEMBRANE [QUARANTINED] — ${VENDOR.name.toUpperCase()} turn #${meta.turnId} streaming under lock. Awaiting deterministic Egress Gate...`;
    banner.appendChild(hdr);
  }

  function renderResult(el, meta, result) {
    const banner = ensureBanner(el);
    banner.textContent = "";

    if (result.verdict === "PASS") {
      el.setAttribute("data-meridian-state", "passed");
      banner.className = "meridian-membrane-banner meridian-banner-pass";
      const hdr = document.createElement("div");
      hdr.className = "meridian-banner-header";
      const left = document.createElement("span");
      left.textContent = `MITP TRUSTED CARD | GATE: PASS (${result.passedCount}/${result.totalChecks}) | MODE: ${result.mode} | RECEIPT: ${result.receiptHash}`;
      const reBtn = document.createElement("button");
      reBtn.className = "meridian-btn meridian-btn-reeval";
      reBtn.textContent = "Re-Verify";
      reBtn.addEventListener("click", () => runEvaluation(el, meta, true));
      hdr.append(left, reBtn);
      banner.appendChild(hdr);
      return;
    }

    const isBlind = result.verdict === "BLIND";
    el.setAttribute("data-meridian-state", isBlind ? "blind" : "blocked");
    banner.className = `meridian-membrane-banner ${isBlind ? "meridian-banner-blind" : "meridian-banner-blocked"}`;

    const hdr = document.createElement("div");
    hdr.className = "meridian-banner-header";
    hdr.textContent = isBlind
      ? `ESTATE_GATE_BLIND (LAW 50) — REMOTE VERIFIER UNREACHABLE — OUTPUT QUARANTINED | RECEIPT: ${result.receiptHash}`
      : `BLOCKED BY MERIDIAN EGRESS GATE — ${result.violations.length} VIOLATION(S) | RECEIPT: ${result.receiptHash}`;
    banner.appendChild(hdr);

    const pills = document.createElement("div");
    (result.codes || []).forEach((code) => {
      const p = document.createElement("span");
      p.className = "meridian-code-pill";
      p.textContent = code;
      pills.appendChild(p);
    });
    banner.appendChild(pills);

    const ul = document.createElement("ul");
    ul.className = "meridian-violation-list";
    (result.violations || []).forEach((v) => {
      const li = document.createElement("li");
      li.textContent = `[${v.severity}] ${v.detail}`;
      if (v.excerpt) {
        const ex = document.createElement("span");
        ex.className = "meridian-excerpt";
        ex.textContent = `Matched: "${v.excerpt}"`;
        li.appendChild(ex);
      }
      ul.appendChild(li);
    });
    banner.appendChild(ul);

    const btnRow = document.createElement("div");
    btnRow.className = "meridian-btn-row";

    if (!isBlind && result.rejectionPrompt) {
      const rejBtn = document.createElement("button");
      rejBtn.className = "meridian-btn meridian-btn-reject";
      rejBtn.textContent = "Inject Rejection Receipt into Prompt Box";
      rejBtn.addEventListener("click", () => {
        const ok = injectIntoComposer(result.rejectionPrompt);
        rejBtn.textContent = ok ? "Rejection Stamped in Prompt Box" : "Copied Rejection to Clipboard";
      });
      btnRow.appendChild(rejBtn);
    }

    const bypassBtn = document.createElement("button");
    bypassBtn.className = "meridian-btn meridian-btn-bypass";
    bypassBtn.textContent = "Reveal Raw (Log Audited UNVERIFIED_BYPASS)";
    bypassBtn.addEventListener("click", async () => {
      await sendBg({
        type: "LOG_BYPASS",
        host: HOST,
        turnId: meta.turnId,
        codes: result.codes,
        receiptHash: result.receiptHash
      });
      el.setAttribute("data-meridian-state", "bypassed");
      banner.className = "meridian-membrane-banner meridian-banner-bypassed";
      banner.textContent = `AUDITED BREAK-GLASS BYPASS LOGGED | FAILED GATES: ${(result.codes || []).join(", ")} | RECEIPT: ${result.receiptHash} — UNVERIFIED OUTPUT`;
      refreshFloatingPill();
    });
    btnRow.appendChild(bypassBtn);

    const reBtn = document.createElement("button");
    reBtn.className = "meridian-btn meridian-btn-reeval";
    reBtn.textContent = "Re-Evaluate";
    reBtn.addEventListener("click", () => runEvaluation(el, meta, true));
    btnRow.appendChild(reBtn);

    banner.appendChild(btnRow);
  }

  async function runEvaluation(el, meta, forced = false) {
    const text = extractCleanText(el);
    if (!text || text.length < 2) return;
    if (!forced && meta.lastEvaluatedText === text) return;
    meta.lastEvaluatedText = text;

    const resp = await sendBg({
      type: "EVALUATE_EGRESS",
      host: HOST,
      turnId: meta.turnId,
      text,
      isHistorical: meta.isHistorical
    });

    if (!resp || !resp.ok || !resp.result) {
      // Fail closed per LAW 50 if background worker fails
      renderResult(el, meta, {
        verdict: "BLIND",
        codes: ["LAW50_EXTENSION_WORKER_ERROR"],
        violations: [{
          code: "LAW50_EXTENSION_WORKER_ERROR",
          severity: "CRITICAL",
          detail: `Background gate worker failed (${resp && resp.error ? resp.error : "unknown"}). Failing closed.`,
          excerpt: ""
        }],
        receiptHash: "err-blind"
      });
      return;
    }

    cachedState = resp;
    renderResult(el, meta, resp.result);
    refreshFloatingPill();

    // Optional Anti-Windup capped Auto-Reject injection (max 1 per live turn, NEVER on historical turns)
    if (
      !meta.isHistorical &&
      resp.result.verdict === "BLOCKED" &&
      resp.ledger &&
      resp.ledger.autoRejectEnabled &&
      meta.autoRejectCount < (resp.ledger.autoRejectMaxPerTurn || 1)
    ) {
      meta.autoRejectCount += 1;
      injectIntoComposer(resp.result.rejectionPrompt);
    }
  }

  function scheduleEvaluation(el, isHistorical = false) {
    let meta = nodeMeta.get(el);
    if (!meta) {
      turnCounter += 1;
      meta = {
        turnId: `${VENDOR.name}-${turnCounter}`,
        firstSeen: Date.now(),
        timer: null,
        lastEvaluatedText: "",
        autoRejectCount: 0,
        isHistorical
      };
      nodeMeta.set(el, meta);
      if (!isHistorical) {
        renderQuarantined(el, meta);
      }
    }

    if (el.getAttribute("data-meridian-state") === "bypassed") return;

    if (meta.timer) clearTimeout(meta.timer);
    meta.timer = setTimeout(() => {
      const elapsed = Date.now() - meta.firstSeen;
      if (!isHistorical && isActivelyStreaming(el) && elapsed < MAX_QUARANTINE_WAIT_MS) {
        scheduleEvaluation(el, false);
        return;
      }
      runEvaluation(el, meta, false);
    }, isHistorical ? 150 : STREAM_DEBOUNCE_MS);
  }

  function scanTurns(isHistorical = false) {
    const nodes = document.querySelectorAll(VENDOR.turnSelector);
    nodes.forEach((node) => {
      // Skip nested duplicates inside an already tracked turn
      if (node.parentElement && node.parentElement.closest("[data-meridian-state]")) return;
      scheduleEvaluation(node, isHistorical);
    });
  }

  async function refreshFloatingPill() {
    let pill = document.getElementById("meridian-floating-pill");
    if (!document.body) return;
    if (!pill) {
      pill = document.createElement("div");
      pill.id = "meridian-floating-pill";

      const label = document.createElement("span");
      label.id = "meridian-pill-label";
      label.textContent = "MEMBRANE: ARMED";

      const stampBtn = document.createElement("button");
      stampBtn.textContent = "Stamp Envelope";
      stampBtn.title = "Prepend live Estate Billing & Gate Envelope into prompt box";
      stampBtn.addEventListener("click", async () => {
        const st = await sendBg({ type: "GET_STATE" });
        if (st && st.ok && st.ingressEnvelope) {
          const ok = injectIntoComposer(st.ingressEnvelope);
          stampBtn.textContent = ok ? "Stamped" : "Copied";
          setTimeout(() => (stampBtn.textContent = "Stamp Envelope"), 1500);
        }
      });

      const scanBtn = document.createElement("button");
      scanBtn.textContent = "Re-Scan";
      scanBtn.addEventListener("click", () => scanTurns(true));

      pill.append(label, stampBtn, scanBtn);
      document.body.appendChild(pill);
    }

    const st = cachedState || (await sendBg({ type: "GET_STATE" }));
    const labelEl = document.getElementById("meridian-pill-label");
    if (st && st.stats && labelEl) {
      const s = st.stats;
      const total = s.passed + s.blocked + s.blind;
      const fpy = total > 0 ? Math.round((s.passed / total) * 100) : 100;
      labelEl.textContent = `MEMBRANE | PASS:${s.passed} BLK:${s.blocked} BLD:${s.blind} | FPY:${total ? fpy + "%" : "ARM"}`;
    }
  }

  function boot() {
    refreshFloatingPill();
    scanTurns(true);

    const observer = new MutationObserver((mutations) => {
      let touched = false;
      for (const m of mutations) {
        if (m.target && m.target.closest && m.target.closest(".meridian-membrane-banner")) continue;
        if (m.target && m.target.id === "meridian-floating-pill") continue;
        touched = true;
        break;
      }
      if (touched) scanTurns(false);
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
