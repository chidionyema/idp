# Intercloud failure modes

Every row names a test that runs in the Intercloud crate. A new failure mode
without a test is refused by `bin/failure-mode-gate`.

| ID | Failure | Expected response | Test |
|---|---|---|---|
| F-IC-1 | SHA-256 implementation drifts | published vectors fail | `sha256_vectors` |
| F-IC-2 | A paid lane wins ahead of a free lane | free-first placement | `free_first_and_capacity` |
| F-IC-3 | Approval arrives over a non-Telegram channel | approval refused | `telegram_gate_refuses_other_channels` |
| F-IC-4 | Free capacity appears and work is reclaimed immediately | three stable ticks required before reclaim | `hysteresis_reclaim` |
| F-IC-5 | Provider churn leaves a workload without a home | GAP_VERDICT receipt emitted | `churn_drill_finds_gaps` |
| F-IC-6 | Receipt is edited after placement | chain verification refuses | `receipt_tamper_detected` |
| F-IC-7 | Malformed or ambiguous lane registry | loud validation refusal | `registry_loud_validation` |
| F-IC-8 | One cloud is the only recovery home | DR check names the violation | `dr_check_flags_single_cloud` |
| F-IC-9 | Caller unlocks paid placement without the engine gate | paid placement remains denied | `approval_only_via_engine_gate` |
| F-IC-10 | The Mac is selected as a placement lane | forbidden lane never wins | `forbidden_lane_never_placed` |
| F-IC-11 | Free workload is placed but receipt is minted before readiness | receipt waits for observed Ready=true | `ctl_free_probe_placed_then_receipt_on_ready` |
| F-IC-12 | Paid workload has no approval | denied instead of silently overspending | `ctl_paid_denied_without_approval` |
| F-IC-13 | Approval signature is forged | claim is not created | `ctl_bad_hmac_refused` |
| F-IC-14 | Valid Telegram approval is ignored | paid claim is created and receipted | `ctl_valid_hmac_paid_claim` |
| F-IC-15 | Down provider leaves its claim behind | stale claim is deleted | `ctl_churn_deletes_down_lane_claims` |
| F-IC-16 | Failure loops flood the primary receipt ledger | configured cap spills overflow and preserves a record | `ctl_receipt_budget_spills` |
| F-IC-17 | Free-first policy ordering drifts | policy lists free lanes first | `ctl_policy_ordering_free_first` |
| F-IC-18 | Filesystem receipt chain is edited | chain verification refuses | `ctl_receipt_chain_detects_tamper` |
