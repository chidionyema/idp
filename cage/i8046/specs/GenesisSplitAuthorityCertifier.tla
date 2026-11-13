---- MODULE GenesisSplitAuthorityCertifier ----
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS
  ClassA_Actors,        \* {"gemini-argon", "aistudio"}
  ClassB_Actors,        \* {"claude", "codex", "opencode", "kimi", "chatgpt", "minimax-otto", "deepseek", "aider", "openhands", "cline", "antigravity", "pi-agent", "legion-run", "chronos", "dependabot"}
  ProtectedPrimitives,  \* {"catalog/dof-registry.json", ".github/workflows", "catalog/genesis-protocols.json", ".github/CODEOWNERS", "features/"}
  CleanCommits,         \* {"6ed3d165"}
  TrojanCommits         \* {"937dda9d"}

VARIABLES
  main_commits,
  protected_prim_hash,
  dof_incidents_open,
  kernel_fence_token,
  telegram_3327_alerts,
  os_creds_mounted,
  chrome_debug_open,
  work_in_flight_state,
  reversible_journal

vars == <<main_commits, protected_prim_hash, dof_incidents_open, kernel_fence_token,
          telegram_3327_alerts, os_creds_mounted, chrome_debug_open,
          work_in_flight_state, reversible_journal>>

AllActors == ClassA_Actors \cup ClassB_Actors
AllCommits == CleanCommits \cup TrojanCommits

Init ==
  /\ main_commits = {}
  /\ protected_prim_hash = "SHA256_GENESIS_LOCKED_V1"
  /\ dof_incidents_open = {"#8022", "#7333", "#7334", "#8045"}
  /\ kernel_fence_token = 1
  /\ telegram_3327_alerts = 0
  /\ os_creds_mounted = [a \in AllActors |-> FALSE]
  /\ chrome_debug_open = [a \in AllActors |-> FALSE]
  /\ work_in_flight_state = [c \in AllCommits |-> "IN_FLIGHT"]
  /\ reversible_journal = << >>

\* Action 1: Class B agent attempts any write, delete, incident close, or primitive edit
ClassB_AttemptMutation(actor, target_commit) ==
  /\ actor \in ClassB_Actors
  /\ kernel_fence_token' = kernel_fence_token + 1
  /\ telegram_3327_alerts' = telegram_3327_alerts + 1
  /\ UNCHANGED <<main_commits, protected_prim_hash, dof_incidents_open,
                 os_creds_mounted, chrome_debug_open, work_in_flight_state, reversible_journal>>

\* Action 2: Deterministic Auto-Main evaluates candidate commit locally before shipping
EvaluateAndPromoteCommit(actor, passkey_sealed, local_tests_green, commit_id) ==
  /\ actor \in ClassA_Actors
  /\ passkey_sealed = TRUE
  /\ local_tests_green = TRUE
  /\ work_in_flight_state[commit_id] = "IN_FLIGHT"
  /\ IF commit_id \in TrojanCommits
     THEN /\ work_in_flight_state' = [work_in_flight_state EXCEPT ![commit_id] = "QUARANTINED_B2_BREACH"]
          /\ kernel_fence_token' = kernel_fence_token + 1
          /\ telegram_3327_alerts' = telegram_3327_alerts + 1
          /\ UNCHANGED <<main_commits, protected_prim_hash, dof_incidents_open,
                         os_creds_mounted, chrome_debug_open, reversible_journal>>
     ELSE /\ main_commits' = main_commits \cup {commit_id}
          /\ work_in_flight_state' = [work_in_flight_state EXCEPT ![commit_id] = "PROMOTED_MAIN"]
          /\ reversible_journal' = Append(reversible_journal, commit_id)
          /\ UNCHANGED <<protected_prim_hash, dof_incidents_open, kernel_fence_token,
                         telegram_3327_alerts, os_creds_mounted, chrome_debug_open>>

\* Action 3: Universal 1-Tap Rollback from Founder Surface
RollbackLastPromotion(actor, passkey_sealed) ==
  /\ actor \in ClassA_Actors
  /\ passkey_sealed = TRUE
  /\ Len(reversible_journal) > 0
  /\ LET last_c == reversible_journal[Len(reversible_journal)]
     IN /\ main_commits' = main_commits \ {last_c}
        /\ work_in_flight_state' = [work_in_flight_state EXCEPT ![last_c] = "ROLLED_BACK"]
        /\ reversible_journal' = SubSeq(reversible_journal, 1, Len(reversible_journal) - 1)
        /\ kernel_fence_token' = kernel_fence_token + 1
        /\ UNCHANGED <<protected_prim_hash, dof_incidents_open, telegram_3327_alerts,
                       os_creds_mounted, chrome_debug_open>>

Next ==
  \/ \E a \in ClassB_Actors, c \in AllCommits : ClassB_AttemptMutation(a, c)
  \/ \E a \in ClassA_Actors, c \in AllCommits : EvaluateAndPromoteCommit(a, TRUE, TRUE, c)
  \/ \E a \in ClassA_Actors : RollbackLastPromotion(a, TRUE)

\* ============================================================================
\* SAFETY INVARIANTS (STRICT ACCEPTANCE CRITERIA)
\* ============================================================================
INV_1_ImproverCannotSelfCertify ==
  /\ protected_prim_hash = "SHA256_GENESIS_LOCKED_V1"
  /\ dof_incidents_open = {"#8022", "#7333", "#7334", "#8045"}

INV_2_TrojanNeverReachesMain ==
  main_commits \cap TrojanCommits = {}

INV_3_OSAndBrowserQuarantine ==
  \A a \in ClassB_Actors :
    /\ os_creds_mounted[a] = FALSE
    /\ chrome_debug_open[a] = FALSE

INV_4_ReversibleJournalConsistency ==
  \A i \in 1..Len(reversible_journal) :
    reversible_journal[i] \in CleanCommits

Spec == Init /\ [][Next]_vars
====
