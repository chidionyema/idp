import {
  DEFAULT_LEDGER,
  evaluateEgress,
  buildRejectionPrompt,
  buildIngressEnvelope
} from "./gate-engine.js";

const STORAGE_KEYS = {
  LEDGER: "meridian_ledger_v1",
  AUDIT: "meridian_audit_log_v1",
  STATS: "meridian_stats_v1"
};

const DEFAULT_STATS = {
  inspected: 0,
  passed: 0,
  blocked: 0,
  blind: 0,
  bypasses: 0
};

async function sha256Hex(str) {
  const bytes = new TextEncoder().encode(str);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function getLedger() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.LEDGER);
  const saved = data[STORAGE_KEYS.LEDGER];
  if (!saved) {
    await chrome.storage.local.set({ [STORAGE_KEYS.LEDGER]: DEFAULT_LEDGER });
    return structuredClone(DEFAULT_LEDGER);
  }
  return {
    ...DEFAULT_LEDGER,
    ...saved,
    lanes: {
      ...DEFAULT_LEDGER.lanes,
      ...(saved.lanes || {})
    }
  };
}

async function getStats() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.STATS);
  return { ...DEFAULT_STATS, ...(data[STORAGE_KEYS.STATS] || {}) };
}

async function appendAudit(entry) {
  const data = await chrome.storage.local.get(STORAGE_KEYS.AUDIT);
  const log = Array.isArray(data[STORAGE_KEYS.AUDIT]) ? data[STORAGE_KEYS.AUDIT] : [];
  log.push(entry);
  // Bounded ring buffer (Anti-Windup Law: cap at 1000 records so storage never bloats)
  const bounded = log.length > 1000 ? log.slice(log.length - 1000) : log;
  await chrome.storage.local.set({ [STORAGE_KEYS.AUDIT]: bounded });
}

async function updateBadge(stats) {
  const total = stats.passed + stats.blocked + stats.blind;
  const fpy = total > 0 ? Math.round((stats.passed / total) * 100) : 0;
  const text = total === 0 ? "ARM" : `${fpy}%`;
  const color = stats.blind > 0 ? "#d97706" : (fpy >= 80 || total === 0 ? "#16a34a" : "#dc2626");
  try {
    await chrome.action.setBadgeText({ text });
    await chrome.action.setBadgeBackgroundColor({ color });
  } catch (_) {}
}

async function evaluateViaCloud(text, ledger, meta) {
  const url = (ledger.cloudVerifierUrl || "").trim();
  if (!url) {
    return {
      verdict: "BLIND",
      mode: "CLOUD_REMOTE_GATE",
      codes: ["LAW50_NO_CLOUD_URL_CONFIGURED"],
      violations: [{
        code: "LAW50_NO_CLOUD_URL_CONFIGURED",
        severity: "CRITICAL",
        detail: "CLOUD_REMOTE_GATE mode is active but no remote Cloudflare Worker URL is configured. Failing closed per LAW 50.",
        excerpt: "cloudVerifierUrl=<empty>"
      }],
      passedChecks: [],
      totalChecks: 6,
      passedCount: 0,
      host: meta.host || "unknown",
      evaluatedAt: new Date().toISOString()
    };
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ledger.cloudTimeoutMs || 5000);
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, ledger, meta }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (!resp.ok) {
      throw new Error(`HTTP_${resp.status}`);
    }
    const parsed = await resp.json();
    if (!parsed || !["PASS", "BLOCKED", "BLIND"].includes(parsed.verdict)) {
      throw new Error("MALFORMED_VERIFIER_ENVELOPE");
    }
    return parsed;
  } catch (err) {
    clearTimeout(timeoutId);
    // LAW 50: Fail closed into visible BLIND quarantine. NEVER pass through silently.
    return {
      verdict: "BLIND",
      mode: "CLOUD_REMOTE_GATE",
      codes: ["LAW50_VERIFIER_UNREACHABLE"],
      violations: [{
        code: "LAW50_VERIFIER_UNREACHABLE",
        severity: "CRITICAL",
        detail: `Remote verifier (${url}) failed (${err.message}). Failing closed per LAW 50 — raw output quarantined.`,
        excerpt: String(err.message)
      }],
      passedChecks: [],
      totalChecks: 6,
      passedCount: 0,
      host: meta.host || "unknown",
      evaluatedAt: new Date().toISOString()
    };
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  const ledger = await getLedger();
  const stats = await getStats();
  await updateBadge(stats);
  await appendAudit({
    event: "MEMBRANE_INSTALLED",
    mode: ledger.mode,
    ts: new Date().toISOString()
  });
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === "GET_STATE") {
        const [ledger, stats, auditWrap] = await Promise.all([
          getLedger(),
          getStats(),
          chrome.storage.local.get(STORAGE_KEYS.AUDIT)
        ]);
        sendResponse({
          ok: true,
          ledger,
          stats,
          auditCount: (auditWrap[STORAGE_KEYS.AUDIT] || []).length,
          ingressEnvelope: buildIngressEnvelope(ledger)
        });
        return;
      }

      if (msg.type === "SAVE_LEDGER") {
        const merged = {
          ...DEFAULT_LEDGER,
          ...(msg.ledger || {}),
          lanes: {
            ...DEFAULT_LEDGER.lanes,
            ...((msg.ledger && msg.ledger.lanes) || {})
          }
        };
        await chrome.storage.local.set({ [STORAGE_KEYS.LEDGER]: merged });
        await appendAudit({
          event: "LEDGER_UPDATED",
          mode: merged.mode,
          strictContractMode: merged.strictContractMode,
          allowBootstrapChore: merged.allowBootstrapChore,
          ts: new Date().toISOString()
        });
        sendResponse({ ok: true, ledger: merged, ingressEnvelope: buildIngressEnvelope(merged) });
        return;
      }

      if (msg.type === "EVALUATE_EGRESS") {
        const ledger = await getLedger();
        const meta = {
          host: msg.host || (sender.tab && sender.tab.url ? new URL(sender.tab.url).hostname : "unknown"),
          turnId: msg.turnId || "unknown",
          isHistorical: Boolean(msg.isHistorical)
        };

        const result =
          ledger.mode === "CLOUD_REMOTE_GATE"
            ? await evaluateViaCloud(msg.text, ledger, meta)
            : evaluateEgress(msg.text, ledger, meta);

        const receiptHash = await sha256Hex(
          JSON.stringify({
            verdict: result.verdict,
            codes: result.codes,
            host: meta.host,
            len: (msg.text || "").length,
            ts: result.evaluatedAt
          })
        );
        result.receiptHash = receiptHash.slice(0, 16);
        result.rejectionPrompt = result.verdict === "BLOCKED" ? buildRejectionPrompt(result) : "";

        const stats = await getStats();
        stats.inspected += 1;
        if (result.verdict === "PASS") stats.passed += 1;
        else if (result.verdict === "BLOCKED") stats.blocked += 1;
        else stats.blind += 1;
        await chrome.storage.local.set({ [STORAGE_KEYS.STATS]: stats });
        await updateBadge(stats);

        await appendAudit({
          event: "EGRESS_EVALUATED",
          verdict: result.verdict,
          codes: result.codes,
          host: meta.host,
          turnId: meta.turnId,
          receiptHash: result.receiptHash,
          mode: result.mode,
          ts: result.evaluatedAt
        });

        sendResponse({ ok: true, result, ledger, stats });
        return;
      }

      if (msg.type === "LOG_BYPASS") {
        const stats = await getStats();
        stats.bypasses += 1;
        await chrome.storage.local.set({ [STORAGE_KEYS.STATS]: stats });
        await appendAudit({
          event: "UNVERIFIED_BYPASS",
          host: msg.host || "unknown",
          turnId: msg.turnId || "unknown",
          codes: msg.codes || [],
          receiptHash: msg.receiptHash || "",
          ts: new Date().toISOString()
        });
        sendResponse({ ok: true, stats });
        return;
      }

      if (msg.type === "EXPORT_AUDIT") {
        const data = await chrome.storage.local.get(STORAGE_KEYS.AUDIT);
        const log = Array.isArray(data[STORAGE_KEYS.AUDIT]) ? data[STORAGE_KEYS.AUDIT] : [];
        const jsonl = log.map((r) => JSON.stringify(r)).join("\n") + (log.length ? "\n" : "");
        sendResponse({ ok: true, jsonl, count: log.length });
        return;
      }

      if (msg.type === "RESET_STATS") {
        await chrome.storage.local.set({ [STORAGE_KEYS.STATS]: DEFAULT_STATS });
        await updateBadge(DEFAULT_STATS);
        sendResponse({ ok: true, stats: DEFAULT_STATS });
        return;
      }

      sendResponse({ ok: false, error: "UNKNOWN_MESSAGE_TYPE" });
    } catch (err) {
      sendResponse({ ok: false, error: String(err && err.message ? err.message : err) });
    }
  })();
  return true;
});
