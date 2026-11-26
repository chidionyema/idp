// Capability selection is pure and shares the live routing DO's circuit state.
// It must reject output limits as well as context limits before paid dispatch.
export function selectCapabilities(pool, req, circuits, nowMs) {
  const effectiveOutputTokens = Math.max(req.requestedOutputTokens, pool.minOutputFloor || 2048);
  const requiredTotalTokens = req.estimatedInputTokens + effectiveOutputTokens;
  const excluded = new Set(req.excludeBackendIds ?? []);
  const eligible = [], rejected = [];
  for (const candidate of [...pool.candidates].sort((a, b) => a.priority - b.priority)) {
    const circuit = circuits[candidate.id];
    let reason = null;
    if (!candidate.enabled) reason = "disabled";
    else if (excluded.has(candidate.id)) reason = "excluded_by_caller";
    else if (req.requiresTools && !candidate.supportsTools) reason = "tools_unsupported";
    else if (!Number.isSafeInteger(candidate.maxOutputTokens) || candidate.maxOutputTokens < effectiveOutputTokens) {
      reason = "output_cap_exceeded";
    } else if (circuit && circuit.openUntilMs > nowMs) {
      reason = "circuit_open_until_" + circuit.openUntilMs + "_code_" + (circuit.lastErrorCode ?? 0);
    } else {
      const learnedCap = circuit?.learnedMaxContextTokens && (circuit.learnedMaxExpiresMs ?? 0) > nowMs
        ? circuit.learnedMaxContextTokens : Infinity;
      const effectiveMaxContext = Math.min(candidate.maxContextTokens, learnedCap);
      if (!Number.isSafeInteger(requiredTotalTokens) || requiredTotalTokens < 0 ||
          !Number.isSafeInteger(candidate.maxContextTokens) || requiredTotalTokens > effectiveMaxContext) {
        reason = "payload_exceeds_context:" + requiredTotalTokens + ">" + effectiveMaxContext;
      }
    }
    if (reason) rejected.push({id: candidate.id, reason});
    else eligible.push(candidate);
  }
  return {role: pool.role, effectiveOutputTokens, eligible, rejected};
}
