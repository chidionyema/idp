// Meridian Deterministic Web Egress Gate Engine v1.0.0
// Pure compiled state-machine / rule evaluation. ZERO LLM judgment inside the gate.
// Shared identically between the MV3 Extension (background.js / selftest.js)
// and the Cloudflare Worker (worker/egress-gate-worker.js).

export const DEFAULT_LEDGER = {
  version: "1.0.0",
  mode: "LOCAL_COMPILED_GATE", // "LOCAL_COMPILED_GATE" | "CLOUD_REMOTE_GATE"
  cloudVerifierUrl: "",
  cloudTimeoutMs: 5000,
  strictContractMode: true,
  allowBootstrapChore: false,
  autoRejectEnabled: false,
  autoRejectMaxPerTurn: 1,
  quarantineOnStream: true,
  lanes: {
    dsh_web: {
      billingClass: "API_CREDIT",
      provider: "deepseek",
      status: "LIVE",
      forbiddenProviders: ["glm", "z.ai", "zai/glm", "pennyd", "127.0.0.1:4200"]
    },
    glm_zai: {
      billingClass: "MONTHLY_SUB",
      provider: "z.ai",
      status: "EXHAUSTED"
    },
    claude_code: {
      billingClass: "MONTHLY_SUB",
      provider: "anthropic",
      status: "LIVE",
      forbiddenInjections: ["claude-sonnet-secondary", "127.0.0.1:4200"]
    },
    pennyd_local: {
      billingClass: "LOCAL_DAEMON",
      endpoint: "127.0.0.1:4200",
      status: "DEAD"
    }
  }
};

function excerptMatch(text, matchIndex, len) {
  const start = Math.max(0, matchIndex - 35);
  const end = Math.min(text.length, matchIndex + len + 55);
  return text.slice(start, end).replace(/\s+/g, " ").trim();
}

function findPattern(text, regex) {
  const m = regex.exec(text);
  if (!m) return null;
  return {
    matched: m[0],
    excerpt: excerptMatch(text, m.index, m[0].length)
  };
}

// Evaluate a raw web-agent response strictly deterministically.
export function evaluateEgress(rawText, ledgerInput = DEFAULT_LEDGER, meta = {}) {
  const ledger = {
    ...DEFAULT_LEDGER,
    ...(ledgerInput || {}),
    lanes: {
      ...DEFAULT_LEDGER.lanes,
      ...((ledgerInput && ledgerInput.lanes) || {})
    }
  };

  const text = String(rawText || "");
  const lower = text.toLowerCase();
  const violations = [];
  const passedChecks = [];

  // Helper to detect explicit negation/prohibition context around a forbidden token
  function hasProhibitionContext(excerpt) {
    const e = excerpt.toLowerCase();
    return /\b(never|do not|don't|forbid|forbidden|prohibit|strip|remove|kill|dead|closed|bypass|outside|zero|off|decoupl|avoid|exhausted|reject|block|retract|ban|broken|hijack|not\s+use|without)\b/.test(e);
  }

  // -------------------------------------------------------------------------
  // GATE 1: G1_BILLING_CLASS_COLLISION
  // Forbids injecting exhausted monthly GLM into DeepSeek API DSH Web,
  // or recommending Anthropic API key / secondary spoof for monthly Claude.
  // -------------------------------------------------------------------------
  const g1Hits = [];
  const glmExhausted = ledger.lanes.glm_zai && ledger.lanes.glm_zai.status === "EXHAUSTED";
  const mentionsDsh = /\b(dsh\s*web|dsh\b|deepseek\s+harness|dsh_cloud|dsh-router-catalog)\b/i.test(text);
  const glmActionRegex = /\b(use|run|running|route|select|configure|switch\s+to|fallback\s+to|backed\s+by|with|on)\b[^.\n]{0,60}\b(zai\/glm(?:-[\d.]+)?|glm-?[\d.]+|z\.ai\s+glm)\b/i;

  if (glmExhausted && mentionsDsh) {
    const m = findPattern(text, glmActionRegex);
    if (m && !hasProhibitionContext(m.excerpt)) {
      g1Hits.push({
        code: "G1_BILLING_CLASS_COLLISION",
        severity: "CRITICAL",
        detail: "Attempted to route exhausted MONTHLY_SUB provider (GLM/Z.ai) into API_CREDIT harness (DSH Web).",
        excerpt: m.excerpt
      });
    }
  }

  // Also block any positive recommendation to run exhausted GLM anywhere
  if (glmExhausted && g1Hits.length === 0) {
    const m = findPattern(text, /\b(use|switch\s+to|run\s+on|route\s+through|fallback\s+to)\s+(?:the\s+)?(zai\/glm(?:-[\d.]+)?|glm-?5(?:\.\d+)?|z\.ai\s+monthly)\b/i);
    if (m && !hasProhibitionContext(m.excerpt)) {
      g1Hits.push({
        code: "G1_EXHAUSTED_PROVIDER_ROUTING",
        severity: "CRITICAL",
        detail: "Attempted to route execution to EXHAUSTED provider (GLM monthly subscription).",
        excerpt: m.excerpt
      });
    }
  }

  // Claude monthly subscription vs ANTHROPIC_API_KEY injection
  const mentionsClaude = /\bclaude(\s+code)?\b/i.test(text);
  if (mentionsClaude) {
    const mApi = findPattern(text, /\b(set|export|add|configure|use)\b[^.\n]{0,40}\b(ANTHROPIC_API_KEY|claude-sonnet-secondary)\b/i);
    if (mApi && !hasProhibitionContext(mApi.excerpt)) {
      g1Hits.push({
        code: "G1_CLAUDE_BILLING_OR_SPOOF_VIOLATION",
        severity: "CRITICAL",
        detail: "Violates ADR 0011 / Monthly Subscription lane by recommending ANTHROPIC_API_KEY or claude-sonnet-secondary.",
        excerpt: mApi.excerpt
      });
    }
  }

  if (g1Hits.length > 0) {
    violations.push(...g1Hits);
  } else {
    passedChecks.push("G1_BILLING_CLASS_ISOLATION");
  }

  // -------------------------------------------------------------------------
  // GATE 2: G2_FOUNDER_CLI_CHORE
  // Hard-blocks raw terminal/shell/python copy-paste chores pushed to Founder
  // unless allowBootstrapChore is explicitly enabled for an audited turn.
  // -------------------------------------------------------------------------
  const g2Hits = [];
  if (!ledger.allowBootstrapChore) {
    const fencedShell = findPattern(
      text,
      /```(?:zsh|bash|sh|shell|terminal|console)\s*\n[\s\S]{10,}?```/i
    );
    const imperativeShell = findPattern(
      text,
      /\b(run\s+this\s+(?:in\s+terminal|command|script|block)|paste\s+this\s+into\s+terminal|execute\s+in\s+zsh)\b/i
    );
    const rawDestructiveCmd = findPattern(
      text,
      /(?:^|\n)\s*(?:sudo\s+)?(?:rm\s+-rf|launchctl\s+(?:bootout|bootstrap)|mv\s+~\/\.|cp\s+~\/\.|python3\s+-\s*<<|grep\s+-rn\s+["']|curl\s+[^|\n]+\|\s*(?:ba)?sh)/m
    );

    if (fencedShell) {
      g2Hits.push({
        code: "G2_FOUNDER_CLI_CHORE",
        severity: "HIGH",
        detail: "Response pushes fenced shell commands onto the Founder (breaches NO_FOUNDER_CLI_CHORES).",
        excerpt: fencedShell.excerpt.slice(0, 140)
      });
    } else if (rawDestructiveCmd) {
      g2Hits.push({
        code: "G2_FOUNDER_CLI_CHORE",
        severity: "HIGH",
        detail: "Response emits raw terminal mutation commands directly to Founder eyes.",
        excerpt: rawDestructiveCmd.excerpt.slice(0, 140)
      });
    } else if (imperativeShell) {
      g2Hits.push({
        code: "G2_FOUNDER_CLI_CHORE",
        severity: "HIGH",
        detail: "Response instructs the Founder to manually execute terminal work.",
        excerpt: imperativeShell.excerpt
      });
    }
  }

  if (g2Hits.length > 0) {
    violations.push(...g2Hits);
  } else {
    passedChecks.push("G2_ZERO_FOUNDER_CLI_CHORES");
  }

  // -------------------------------------------------------------------------
  // GATE 3: G3_SHARED_FATE_COUPLING
  // Blocks proposals wiring cockpits/recovery tools onto dead 127.0.0.1:4200
  // or legacy llm.mumchimp.com/v1.
  // -------------------------------------------------------------------------
  const g3Hits = [];
  const pennydDead = ledger.lanes.pennyd_local && ledger.lanes.pennyd_local.status === "DEAD";
  if (pennydDead) {
    const m4200 = findPattern(
      text,
      /\b(point|route|connect|set|use|start|restart|via|through|target)\b[^.\n]{0,55}\b(127\.0\.0\.1:4200|localhost:4200|com\.estate\.pennyd)\b/i
    );
    if (m4200 && !hasProhibitionContext(m4200.excerpt)) {
      g3Hits.push({
        code: "G3_SHARED_FATE_COUPLING",
        severity: "CRITICAL",
        detail: "Attempted to couple execution or recovery onto DEAD local pennyd (127.0.0.1:4200).",
        excerpt: m4200.excerpt
      });
    }
  }
  const mLegacy = findPattern(
    text,
    /\b(point|route|connect|set|use|default\s+to)\b[^.\n]{0,45}llm\.mumchimp\.com/i
  );
  if (mLegacy && !hasProhibitionContext(mLegacy.excerpt)) {
    g3Hits.push({
      code: "G3_LEGACY_ROUTER_COUPLING",
      severity: "HIGH",
      detail: "Attempted to route traffic to legacy endpoint llm.mumchimp.com.",
      excerpt: mLegacy.excerpt
    });
  }

  if (g3Hits.length > 0) {
    violations.push(...g3Hits);
  } else {
    passedChecks.push("G3_BULKHEAD_ISOLATION");
  }

  // -------------------------------------------------------------------------
  // GATE 4: G4_UNVERIFIED_PROXY_GREEN
  // Blocks asserting live operational certainty purely from merge/unit-test/prose.
  // -------------------------------------------------------------------------
  const g4Hits = [];
  const proxyGreen = findPattern(
    text,
    /\b(100%\s+operational|fully\s+operational|now\s+live\s+and\s+verified|confirmed\s+fixed\s+in\s+production|operational_yield\s*=\s*1)\b/i
  );
  if (proxyGreen) {
    const hasReceipt = /\b(sha-?256|http\s*200|exit\s*code\s*0|receipt|observed\s+at|timestamp|verified\s+probe)\b/i.test(text);
    const explicitlyZero = /operational_yield\s*=\s*0/i.test(text);
    if (!hasReceipt && !explicitlyZero) {
      g4Hits.push({
        code: "G4_PROXY_GREEN_SUBSTITUTION",
        severity: "CRITICAL",
        detail: "Asserted live operational yield without an external non-proxy verification receipt (KARMA Firewall).",
        excerpt: proxyGreen.excerpt
      });
    }
  }

  if (g4Hits.length > 0) {
    violations.push(...g4Hits);
  } else {
    passedChecks.push("G4_KARMA_NON_PROXY_PROOF");
  }

  // -------------------------------------------------------------------------
  // GATE 5: G5_MISSING_FAILURE_FIRST_CONTRACT
  // When strictContractMode is ON and response is substantive (>280 chars)
  // and proposes changes/architecture/actions, require explicit reality grounding
  // (Observed vs UNKNOWN) + Failure Mode / Rollback / Effects coverage.
  // -------------------------------------------------------------------------
  const g5Hits = [];
  const isProposalLike =
    text.length >= 280 &&
    /\b(propos|architect|deploy|migrat|remediat|recover|patch|config|workflow|implement|step\s+1|recommend|should\s+(?:run|use|edit|change|build))\b/i.test(text);

  if (ledger.strictContractMode && isProposalLike) {
    const hasRealitySplit = /\b(observed|verified)\b/i.test(text) && /\b(unknown|unverified|blind)\b/i.test(text);
    const hasFailureMode = /\b(failure\s+mode|fail-closed|blast\s+radius|bulkhead|guaranteed\s+failure)\b/i.test(text);
    const hasEffectsOrRollback = /\b(1st-?order|first-?order|2nd-?order|second-?order|rollback|reversib|escape\s+hatch)\b/i.test(text);

    const missing = [];
    if (!hasRealitySplit) missing.push("OBSERVED_VS_UNKNOWN");
    if (!hasFailureMode) missing.push("FAILURE_MODE_OR_BULKHEAD");
    if (!hasEffectsOrRollback) missing.push("EFFECTS_OR_ROLLBACK");

    if (missing.length > 0) {
      g5Hits.push({
        code: "G5_MISSING_CONTRACT_FIELDS",
        severity: "HIGH",
        detail: `Ungrounded proposal missing mandatory Failure-First fields: ${missing.join(", ")}.`,
        excerpt: text.slice(0, 140).replace(/\s+/g, " ").trim()
      });
    }
  }

  if (g5Hits.length > 0) {
    violations.push(...g5Hits);
  } else {
    passedChecks.push("G5_FAILURE_FIRST_CONTRACT");
  }

  // -------------------------------------------------------------------------
  // GATE 6: G6_UNAUTHORISED_AUTHORITY_CLAIM
  // Consumer web surfaces are Class R / Class B read-only untrusted compute.
  // Block false claims of having directly executed local Mac commands.
  // -------------------------------------------------------------------------
  const g6Hits = [];
  const fakeLocalExec = findPattern(
    text,
    /\b(i\s+(?:have\s+)?(?:executed|ran|edited|modified|restarted|killed|deleted)\s+(?:on\s+your\s+mac|your\s+local|~\/\.claude|~\/\.dsh|pennyd\s+on\s+your\s+machine))\b/i
  );
  if (fakeLocalExec && !hasProhibitionContext(fakeLocalExec.excerpt)) {
    g6Hits.push({
      code: "G6_FALSE_EXECUTION_CLAIM",
      severity: "CRITICAL",
      detail: "Web agent falsely claimed direct execution on local MacBook host.",
      excerpt: fakeLocalExec.excerpt
    });
  }

  if (g6Hits.length > 0) {
    violations.push(...g6Hits);
  } else {
    passedChecks.push("G6_CLASS_R_AUTHORITY_BOUNDARY");
  }

  // -------------------------------------------------------------------------
  // GATE 7: G7_FOUNDER_ATTENTION_POLLUTION
  // A web agent that answers with raw tool plumbing, retry narratives or serial
  // "what next?" stalls spends the reader's attention instead of delivering an
  // outcome. Narrow on purpose: only an unambiguous log dump (many log-shaped
  // lines forming the body of the answer) or two or more distinct check-ins.
  // A single status table or one code block never trips it.
  // -------------------------------------------------------------------------
  const g7Hits = [];
  const lines = text.split(/\r?\n/);
  const logShaped = lines.filter((l) =>
    /^\s*(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:|\d{2}:\d{2}:\d{2}\s|ok\s{2,}|FAIL\s{2,}|PASS\s{2,}|error:|warning:|remote:|hint:|\{|\}|at\s+\S+\s+\(|\+\d+\s|\-\d+\s)/.test(l)
  ).length;
  const logRatio = lines.length ? logShaped / lines.length : 0;
  if (logShaped >= 12 && logRatio >= 0.35) {
    g7Hits.push({
      code: "G7_FOUNDER_ATTENTION_POLLUTION",
      severity: "MEDIUM",
      detail: "Answer is mostly raw tool output (" + logShaped + " log-shaped lines, " + Math.round(logRatio * 100) + "% of the body). The outcome belongs on one line; the plumbing belongs behind a drawer.",
      excerpt: lines.find((l) => /^\s*(?:ok\s{2,}|FAIL\s{2,}|error:)/.test(l))?.slice(0, 120) || text.slice(0, 120)
    });
  }
  const stallHits = text.match(/\b(?:what next|what'?s next|shall i|should i|want me to|let me know|standing by|awaiting (?:your|instruction)|ready when you are)\b/gi) || [];
  const distinctStalls = [...new Set(stallHits.map((s) => s.toLowerCase()))];
  if (distinctStalls.length >= 2) {
    g7Hits.push({
      code: "G7_FOUNDER_ATTENTION_POLLUTION",
      severity: "MEDIUM",
      detail: "Answer asks the reader to steer " + distinctStalls.length + " times (" + distinctStalls.join(", ") + "). One turn, one outcome, one decision or NONE.",
      excerpt: stallHits[0]
    });
  }

  if (g7Hits.length > 0) {
    violations.push(...g7Hits);
  } else {
    passedChecks.push("G7_FOUNDER_ATTENTION_FIREWALL");
  }

  const verdict = violations.length === 0 ? "PASS" : "BLOCKED";
  const codes = [...new Set(violations.map((v) => v.code))];

  return {
    verdict,
    mode: ledger.mode,
    codes,
    violations,
    passedChecks,
    totalChecks: 7,
    passedCount: passedChecks.length,
    host: meta.host || "unknown",
    evaluatedAt: new Date().toISOString(),
    charCount: text.length
  };
}

export function buildRejectionPrompt(result) {
  const codeList = (result.codes || []).join(", ");
  const details = (result.violations || [])
    .slice(0, 4)
    .map((v) => `- ${v.code}: ${v.detail}`)
    .join("\n");
  return [
    "[ESTATE_EGRESS_REJECT — DETERMINISTIC MEMBRANE]",
    `FAILED_GATES: ${codeList}`,
    details,
    "REWRITE_MANDATE: Eliminate all failed gates above. Separate Observed vs UNKNOWN state, respect immutable billing classes (DSH Web = DeepSeek API_CREDIT LIVE; GLM = MONTHLY_SUB EXHAUSTED; Claude = MONTHLY_SUB LIVE; pennyd 127.0.0.1:4200 = DEAD), emit ZERO copy-paste Founder CLI chores, and declare Failure Modes, Bulkhead, 1st/2nd-Order Effects, and Rollback."
  ].join("\n");
}

export function buildIngressEnvelope(ledgerInput = DEFAULT_LEDGER) {
  const l = { ...DEFAULT_LEDGER, ...(ledgerInput || {}), lanes: { ...DEFAULT_LEDGER.lanes, ...((ledgerInput && ledgerInput.lanes) || {}) } };
  return [
    "[MERIDIAN_ESTATE_ENVELOPE v1 | AUTHORITY=CLASS_R_READONLY]",
    `LEDGER: DSH_WEB=DeepSeek:${l.lanes.dsh_web.billingClass}:${l.lanes.dsh_web.status} | GLM=Z.ai:${l.lanes.glm_zai.billingClass}:${l.lanes.glm_zai.status} | CLAUDE=Anthropic:${l.lanes.claude_code.billingClass}:${l.lanes.claude_code.status} | PENNYD_4200=${l.lanes.pennyd_local.status}`,
    `HARD_GATES: ZERO_CLI_CHORES=${!l.allowBootstrapChore} | STRICT_6_FIELD=${l.strictContractMode} | ZERO_BILLING_COLLISION=true | ZERO_PROXY_GREEN=true | FAILURE_FIRST=true`,
    "RESPONSE_WILL_BE_QUARANTINED_AND_DROPPED_IF_ANY_GATE_FAILS.",
    "---"
  ].join("\n");
}
