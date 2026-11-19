package estate.beast

# ==============================================================================
# MERIDIAN AUTONOMOUS ESTATE — CANONICAL DECLARATIVE CONSTITUTION (estate.rego)
# Replaces scattered imperative checks across IDP, Pi-extensions, FLOW, Legion,
# Bitwarden secret brokers, Greenlane CI, and Omega Robotics HALs.
# Every threshold binds dynamically to `data.dials` for instant founder control.
# ==============================================================================

default allow := false

# 1. HARD RESEARCH-LAB INVARIANT: ZERO UNEVALUATED SESSIONS
deny contains msg if {
  data.dials.requireRealtimeEvalOnEverySession == true
  input.session.realtimeEvalAttached != true
  msg := "ZERO_UNEVALUATED_SESSIONS: Session cannot execute without live 5-gate real-time evaluation attached."
}

# 2. PERSISTENT REAL-NAME IDENTITY & LINE-1 ESTATE-SESSION
deny contains msg if {
  data.dials.enforceLine1EstateSession == true
  not startswith(input.session.actorDid, "did:estate:")
  msg := "ESTATE_SESSION_REQUIRED: Unowned or anonymous actor DID rejected by Line-1 Constitution."
}

# 3. PI-EXTENSION & HARNESS TEST COLLECTION FLOOR (BLOCKS FALSE-GREEN 0-TEST EXITS)
deny contains msg if {
  input.action.kind == "CI_OR_PREPUSH_GATE"
  input.metrics.collectedTests < data.dials.minTestCollectionCount
  msg := sprintf("TEST_COLLECTION_FLOOR_BREACH: Collected %d tests < dial floor %d.", [
    input.metrics.collectedTests,
    data.dials.minTestCollectionCount,
  ])
}

# 4. EPISTEMIC CONFIDENCE & ANTI-HALLUCINATION FLOOR
deny contains msg if {
  input.metrics.epistemicConfidencePct < data.dials.minEpistemicConfidencePct
  msg := sprintf("EPISTEMIC_CONFIDENCE_BELOW_DIAL: Observed %d%% < required %d%%.", [
    input.metrics.epistemicConfidencePct,
    data.dials.minEpistemicConfidencePct,
  ])
}

# 5. BITWARDEN & VAULT LEASE BOUNDARY (ZERO UNSCOPED SECRET READS)
deny contains msg if {
  data.dials.bitwardenStrictLeaseRequired == true
  input.action.requiresVaultSecret == true
  input.vault.bitwardenLeaseValid != true
  msg := "BITWARDEN_LEASE_REQUIRED: Secret-touching task blocked until scoped Bitwarden/OCI lease is verified."
}

# 6. BRANCH PROTECTION (GOVERNED LANE/* ONLY UNLESS DIAL EXPLICITLY LOOSENED)
deny contains msg if {
  data.dials.allowDirectMainPush == false
  input.git.targetBranch == "main"
  msg := "DIRECT_MAIN_PUSH_FORBIDDEN: Mutations must land via governed lane/* branch and Greenlane proof."
}

# 7. TOKEN BUDGET & AUTOMATIC FREE-LANE REROUTING
route_to_free_lane if {
  input.tokens.sessionUsedTokens >= data.dials.maxSessionTokenBudget
}

# 8. MILLISECOND INCIDENT WAKE-UP CASCADE SELECTION
wakeup_target := "WEB_BROWSER_SYMBIONT" if {
  input.incident.domain == "UI_OR_DOM_SURFACE"
  input.availability.webBrowserPoolOnline == true
} else := "LOCAL_MAC_CONSOLE" if {
  input.availability.localMacHeartbeatMs <= data.dials.incidentWakeupSlaMs * 20
  input.availability.localMacOnline == true
} else := "CLOUD_ALWAYS_ON_LEGION"

# 9. FINAL AUTHORIZATION VERDICT
allow if {
  count(deny) == 0
}
