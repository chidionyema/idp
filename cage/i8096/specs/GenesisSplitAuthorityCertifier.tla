---- MODULE GenesisSplitAuthorityCertifier ----
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS
    Candidates,     \* e.g., {"cand_argon_01", "cand_crew_fix"}
    FailureClasses, \* e.g., {"FC_P0_7613", "FC_CREW_REVENUE"}
    Actors,         \* {"IMPROVER_AGENT", "INDEPENDENT_CERTIFIER", "ADVERSARY"}
    MaxSlaTicks     \* e.g., 3

VARIABLES
    candidateState,       \* [c \in Candidates -> {"PROPOSED", "CERTIFIED", "PROMOTED_MAIN", "REJECTED", "ROLLED_BACK"}]
    signedByCertifier,    \* [c \in Candidates -> BOOLEAN]
    heldOutTrialPassed,   \* [c \in Candidates -> BOOLEAN]
    rulesetEnforced,      \* [r \in {"idp", "argon", "argon-sync", "crew"} -> BOOLEAN]
    incidentState,        \* [fc \in FailureClasses -> {"OPEN", "LEASED", "VERIFIED_CLOSED"}]
    slaTimer,             \* [fc \in FailureClasses -> 0..MaxSlaTicks]
    authoritativeToken,   \* Int: monotonically increasing fencing token in kernel_fence_state
    lastAcceptedToken,    \* Int: last token that mutated state
    certifiedAntibodies,  \* Subset of FailureClasses with proven Pass-0 antibody transforms
    agentDiagPasses,      \* [fc \in FailureClasses -> Int]
    platformHealth,       \* {"KNOWN_GOOD", "MUTATING", "DEGRADED"}
    lastKnownGoodToken,   \* Int: fencing token of the last certified KNOWN_GOOD checkpoint
    historyArchiveFrozen  \* BOOLEAN: ~/.estate and estate.db permanently frozen read-only

vars == <<candidateState, signedByCertifier, heldOutTrialPassed, rulesetEnforced,
          incidentState, slaTimer, authoritativeToken, lastAcceptedToken,
          certifiedAntibodies, agentDiagPasses, platformHealth, lastKnownGoodToken,
          historyArchiveFrozen>>

Init ==
    /\ candidateState = [c \in Candidates |-> "PROPOSED"]
    /\ signedByCertifier = [c \in Candidates |-> FALSE]
    /\ heldOutTrialPassed = [c \in Candidates |-> FALSE]
    /\ rulesetEnforced = [r \in {"idp", "argon", "argon-sync", "crew"} |-> TRUE]
    /\ incidentState = [fc \in FailureClasses |-> "OPEN"]
    /\ slaTimer = [fc \in FailureClasses |-> 0]
    /\ authoritativeToken = 45
    /\ lastAcceptedToken = 45
    /\ certifiedAntibodies = {}
    /\ agentDiagPasses = [fc \in FailureClasses |-> -1]
    /\ platformHealth = "KNOWN_GOOD"
    /\ lastKnownGoodToken = 45
    /\ historyArchiveFrozen = TRUE

AdversarialDirectPush(c, actor) ==
    /\ actor \in {"IMPROVER_AGENT", "ADVERSARY"}
    /\ rulesetEnforced["argon"] = TRUE
    /\ rulesetEnforced["argon-sync"] = TRUE
    /\ candidateState[c] = "PROPOSED"
    /\ signedByCertifier[c] = FALSE
    /\ candidateState' = [candidateState EXCEPT ![c] = "REJECTED"]
    /\ UNCHANGED <<signedByCertifier, heldOutTrialPassed, rulesetEnforced,
                   incidentState, slaTimer, authoritativeToken, lastAcceptedToken,
                   certifiedAntibodies, agentDiagPasses, platformHealth,
                   lastKnownGoodToken, historyArchiveFrozen>>

IndependentCertify(c) ==
    /\ candidateState[c] = "PROPOSED"
    /\ historyArchiveFrozen = TRUE
    /\ heldOutTrialPassed' = [heldOutTrialPassed EXCEPT ![c] = TRUE]
    /\ signedByCertifier' = [signedByCertifier EXCEPT ![c] = TRUE]
    /\ candidateState' = [candidateState EXCEPT ![c] = "CERTIFIED"]
    /\ UNCHANGED <<rulesetEnforced, incidentState, slaTimer, authoritativeToken,
                   lastAcceptedToken, certifiedAntibodies, agentDiagPasses,
                   platformHealth, lastKnownGoodToken, historyArchiveFrozen>>

GreenlanePromoteMain(c) ==
    /\ candidateState[c] = "CERTIFIED"
    /\ signedByCertifier[c] = TRUE
    /\ heldOutTrialPassed[c] = TRUE
    /\ historyArchiveFrozen = TRUE
    /\ candidateState' = [candidateState EXCEPT ![c] = "PROMOTED_MAIN"]
    /\ platformHealth' = "KNOWN_GOOD"
    /\ authoritativeToken' = authoritativeToken + 1
    /\ lastAcceptedToken' = authoritativeToken + 1
    /\ lastKnownGoodToken' = authoritativeToken + 1
    /\ UNCHANGED <<signedByCertifier, heldOutTrialPassed, rulesetEnforced,
                   incidentState, slaTimer, certifiedAntibodies, agentDiagPasses,
                   historyArchiveFrozen>>

UniversalRollbackToKnownGood(c) ==
    /\ candidateState[c] \in {"PROPOSED", "PROMOTED_MAIN"}
    /\ candidateState' = [candidateState EXCEPT ![c] = "ROLLED_BACK"]
    /\ platformHealth' = "KNOWN_GOOD"
    /\ authoritativeToken' = authoritativeToken + 1
    /\ lastAcceptedToken' = authoritativeToken + 1
    /\ lastKnownGoodToken' = authoritativeToken + 1
    /\ UNCHANGED <<signedByCertifier, heldOutTrialPassed, rulesetEnforced,
                   incidentState, slaTimer, certifiedAntibodies, agentDiagPasses,
                   historyArchiveFrozen>>

TickSlaTimer(fc) ==
    /\ incidentState[fc] \in {"OPEN", "LEASED"}
    /\ slaTimer[fc] < MaxSlaTicks - 1
    /\ slaTimer' = [slaTimer EXCEPT ![fc] = @ + 1]
    /\ UNCHANGED <<candidateState, signedByCertifier, heldOutTrialPassed,
                   rulesetEnforced, incidentState, authoritativeToken,
                   lastAcceptedToken, certifiedAntibodies, agentDiagPasses,
                   platformHealth, lastKnownGoodToken, historyArchiveFrozen>>

AcquireIncidentLease(fc) ==
    /\ incidentState[fc] = "OPEN"
    /\ slaTimer[fc] < MaxSlaTicks
    /\ incidentState' = [incidentState EXCEPT ![fc] = "LEASED"]
    /\ authoritativeToken' = authoritativeToken + 1
    /\ lastAcceptedToken' = authoritativeToken + 1
    /\ UNCHANGED <<candidateState, signedByCertifier, heldOutTrialPassed,
                   rulesetEnforced, slaTimer, certifiedAntibodies, agentDiagPasses,
                   platformHealth, lastKnownGoodToken, historyArchiveFrozen>>

RemediateAndSynthesizeAntibody(fc) ==
    /\ incidentState[fc] = "LEASED"
    /\ slaTimer[fc] <= MaxSlaTicks
    /\ incidentState' = [incidentState EXCEPT ![fc] = "VERIFIED_CLOSED"]
    /\ certifiedAntibodies' = certifiedAntibodies \cup {fc}
    /\ platformHealth' = "KNOWN_GOOD"
    /\ UNCHANGED <<candidateState, signedByCertifier, heldOutTrialPassed,
                   rulesetEnforced, slaTimer, authoritativeToken, lastAcceptedToken,
                   agentDiagPasses, lastKnownGoodToken, historyArchiveFrozen>>

SecondAgentEncounter(fc) ==
    /\ fc \in certifiedAntibodies
    /\ agentDiagPasses' = [agentDiagPasses EXCEPT ![fc] = 0]
    /\ UNCHANGED <<candidateState, signedByCertifier, heldOutTrialPassed,
                   rulesetEnforced, incidentState, slaTimer, authoritativeToken,
                   lastAcceptedToken, certifiedAntibodies, platformHealth,
                   lastKnownGoodToken, historyArchiveFrozen>>

Next ==
    \/ \E c \in Candidates, a \in Actors : AdversarialDirectPush(c, a)
    \/ \E c \in Candidates : IndependentCertify(c)
    \/ \E c \in Candidates : GreenlanePromoteMain(c)
    \/ \E c \in Candidates : UniversalRollbackToKnownGood(c)
    \/ \E fc \in FailureClasses : TickSlaTimer(fc)
    \/ \E fc \in FailureClasses : AcquireIncidentLease(fc)
    \/ \E fc \in FailureClasses : RemediateAndSynthesizeAntibody(fc)
    \/ \E fc \in FailureClasses : SecondAgentEncounter(fc)

Spec == Init /\ [][Next]_vars

ImproverCannotSelfCertify ==
    \A c \in Candidates :
        (candidateState[c] = "PROMOTED_MAIN") =>
            (signedByCertifier[c] = TRUE /\ heldOutTrialPassed[c] = TRUE)

UniversalRepoProtection ==
    \A r \in {"idp", "argon", "argon-sync", "crew"} : rulesetEnforced[r] = TRUE

IncidentSlaBoundedClosure ==
    \A fc \in FailureClasses : slaTimer[fc] <= MaxSlaTicks

MonotonicFencingSafety ==
    lastAcceptedToken = authoritativeToken

InheritedIntelligenceZeroPass ==
    \A fc \in FailureClasses :
        (fc \in certifiedAntibodies /\ agentDiagPasses[fc] # -1) => (agentDiagPasses[fc] = 0)

KnownGoodReversibilityGuarantee ==
    platformHealth = "KNOWN_GOOD" /\ lastKnownGoodToken <= authoritativeToken

HistoryQuarantineGuarantee ==
    historyArchiveFrozen = TRUE
====