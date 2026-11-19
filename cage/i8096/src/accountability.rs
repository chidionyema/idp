//! Instruction I-8106 (Mandatory Amendment): Intellectual Freedom and
//! Operational Accountability.
//!
//! Enforces:
//! 1. Unrestricted Intellectual Freedom (IntellectualDiscourse passes through
//!    with zero gates)
//! 2. Durable Operational Accountability (Accepted obligations survive
//!    session/provider/capability failures)
//! 3. Behaviour Over Vocabulary (Zero keyword matching; truthful failures
//!    remain visible; abandonment triggers recovery)
//! 4. Strict Authority Separation (Untrusted comments & model outputs cannot
//!    authorize execution; CIF receipts & CI checks alone are intermediate
//!    FLOW steps; completion requires Y ^ C ^ V)
//!
//! The crate's own `sha2` dependency is the SHA-256; nothing new is added to
//! the dependency graph.

use sha2::{Digest, Sha256};

/// The shortest enclave key the receipt signer accepts.
pub const CIF_KEY_MIN_LEN: usize = 32;
/// The window an obligation's recovery plan must fit inside.
pub const RECOVERY_SLA_SECS: u64 = 600;

/// The SHA-256 of `data`, lower-case hex.
pub fn sha256_hex(data: &[u8]) -> String {
    let digest = Sha256::digest(data);
    let mut out = String::with_capacity(64);
    for byte in digest {
        out.push_str(&format!("{:02x}", byte));
    }
    out
}

/// HMAC-SHA256 of `message` under `key`, lower-case hex.
pub fn hmac_sha256_hex(key: &[u8], message: &[u8]) -> String {
    let mut block = [0u8; 64];
    if key.len() > 64 {
        block[..32].copy_from_slice(&Sha256::digest(key));
    } else {
        block[..key.len()].copy_from_slice(key);
    }
    let mut ipad = [0x36u8; 64];
    let mut opad = [0x5cu8; 64];
    for i in 0..64 {
        ipad[i] ^= block[i];
        opad[i] ^= block[i];
    }
    let mut inner = Vec::with_capacity(64 + message.len());
    inner.extend_from_slice(&ipad);
    inner.extend_from_slice(message);
    let inner_hash = Sha256::digest(&inner);
    let mut outer = Vec::with_capacity(96);
    outer.extend_from_slice(&opad);
    outer.extend_from_slice(&inner_hash);
    // sha256_hex already hashes: this is HMAC-SHA256(opad || H(ipad || message)),
    // not a second digest of the digest.
    sha256_hex(&outer)
}

/// Compare two hex strings without leaking where they differ.
pub fn constant_time_eq_hex(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.bytes().zip(b.bytes()) {
        diff |= x ^ y;
    }
    diff == 0
}

/// True when the candidate is 64 lower-case hex characters.
pub fn is_valid_sha256_hex(candidate: &str) -> bool {
    candidate.len() == 64
        && candidate
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// A signed receipt for one CIF step, produced inside the enclave.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CifStepRunReceipt {
    pub ticket_id: String,
    pub step_idx: u32,
    pub cmd: String,
    pub exit_code: i32,
    pub stdout_payload: String,
    pub stderr_payload: String,
    pub hmac_signature: String,
}

impl CifStepRunReceipt {
    /// The exact bytes the signature covers.
    pub fn canonical_signing_payload(&self) -> String {
        let stdout_hash = sha256_hex(self.stdout_payload.as_bytes());
        format!(
            "{}:{}:{}:{}:{}",
            self.ticket_id.trim(),
            self.step_idx,
            self.cmd.trim(),
            self.exit_code,
            stdout_hash
        )
    }

    /// Sign a receipt with the enclave key.
    pub fn sign_in_enclave(
        ticket_id: &str,
        step_idx: u32,
        cmd: &str,
        exit_code: i32,
        stdout_payload: &str,
        stderr_payload: &str,
        receipt_key: &[u8],
    ) -> Result<Self, CifVerificationError> {
        if receipt_key.len() < CIF_KEY_MIN_LEN || receipt_key.iter().all(|&b| b == 0) {
            return Err(CifVerificationError::InvalidEnclaveKey);
        }
        let mut draft = Self {
            ticket_id: ticket_id.trim().to_string(),
            step_idx,
            cmd: cmd.trim().to_string(),
            exit_code,
            stdout_payload: stdout_payload.to_string(),
            stderr_payload: stderr_payload.to_string(),
            hmac_signature: String::new(),
        };
        let payload = draft.canonical_signing_payload();
        draft.hmac_signature = hmac_sha256_hex(receipt_key, payload.as_bytes());
        Ok(draft)
    }
}

/// How a metric in the step's stdout is compared to its threshold.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MetricOperator {
    GreaterThan,
    GreaterOrEqual,
    Equal,
}

/// One expected outcome of a CIF step.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExpectedOutcomeRule {
    pub metric_name: String,
    pub anchor_suffix: String,
    pub operator: MetricOperator,
    pub threshold: i64,
}

impl ExpectedOutcomeRule {
    /// Pull the metric out of the step's stdout and judge it.
    pub fn extract_and_evaluate(&self, stdout_payload: &str) -> Option<(i64, bool)> {
        let tokens: Vec<&str> = stdout_payload.split_whitespace().collect();
        let target = self.anchor_suffix.trim();
        for window in tokens.windows(2) {
            let cleaned_suffix = window[1].trim_matches(|c: char| !c.is_alphanumeric());
            if cleaned_suffix == target {
                if let Ok(val) = window[0].parse::<i64>() {
                    let ok = match self.operator {
                        MetricOperator::GreaterThan => val > self.threshold,
                        MetricOperator::GreaterOrEqual => val >= self.threshold,
                        MetricOperator::Equal => val == self.threshold,
                    };
                    return Some((val, ok));
                }
            }
        }
        None
    }
}

/// What the verifier decided about one expected outcome.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyDecisionRecord {
    pub ticket_id: String,
    pub step_idx: u32,
    pub metric_name: String,
    pub extracted_value: i64,
    pub satisfied: bool,
}

/// Why a receipt was refused.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CifVerificationError {
    InvalidEnclaveKey,
    HmacSignatureMismatch { ticket_id: String, step_idx: u32 },
    NonZeroExitCode { exit_code: i32 },
    MetricNotFoundInStdout { metric_name: String },
    MetricThresholdUnsatisfied {
        metric_name: String,
        extracted: i64,
        threshold: i64,
    },
}

/// Verify a receipt's signature, its exit code and every expected outcome.
pub fn verify_cif_receipt(
    receipt: &CifStepRunReceipt,
    expected_outcomes: &[ExpectedOutcomeRule],
    receipt_key: &[u8],
) -> Result<Vec<PolicyDecisionRecord>, CifVerificationError> {
    if receipt_key.len() < CIF_KEY_MIN_LEN || receipt_key.iter().all(|&b| b == 0) {
        return Err(CifVerificationError::InvalidEnclaveKey);
    }
    let expected_hmac = hmac_sha256_hex(
        receipt_key,
        receipt.canonical_signing_payload().as_bytes(),
    );
    if !constant_time_eq_hex(&expected_hmac, &receipt.hmac_signature) {
        return Err(CifVerificationError::HmacSignatureMismatch {
            ticket_id: receipt.ticket_id.clone(),
            step_idx: receipt.step_idx,
        });
    }
    if receipt.exit_code != 0 {
        return Err(CifVerificationError::NonZeroExitCode {
            exit_code: receipt.exit_code,
        });
    }
    let mut decisions = Vec::with_capacity(expected_outcomes.len());
    for rule in expected_outcomes {
        match rule.extract_and_evaluate(&receipt.stdout_payload) {
            None => {
                return Err(CifVerificationError::MetricNotFoundInStdout {
                    metric_name: rule.metric_name.clone(),
                });
            }
            Some((val, false)) => {
                return Err(CifVerificationError::MetricThresholdUnsatisfied {
                    metric_name: rule.metric_name.clone(),
                    extracted: val,
                    threshold: rule.threshold,
                });
            }
            Some((val, true)) => {
                decisions.push(PolicyDecisionRecord {
                    ticket_id: receipt.ticket_id.clone(),
                    step_idx: receipt.step_idx,
                    metric_name: rule.metric_name.clone(),
                    extracted_value: val,
                    satisfied: true,
                });
            }
        }
    }
    Ok(decisions)
}

/// Who is asking, and whether that origin may authorize execution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OriginAuthority {
    FounderAuthorizedIntent {
        founder_kid: String,
        intent_sha256: String,
    },
    AuthenticatedExecutionLease {
        lease_id: String,
        parent_instruction_id: String,
        fencing_token: u64,
    },
    ModelGeneratedProposal {
        model_surface: String,
    },
    UntrustedExternalComment {
        source_channel: String,
    },
}

impl OriginAuthority {
    /// Only a founder intent or an authenticated lease may authorize execution.
    pub fn can_authorize_execution(&self) -> bool {
        match self {
            OriginAuthority::FounderAuthorizedIntent {
                founder_kid,
                intent_sha256,
            } => !founder_kid.trim().is_empty() && is_valid_sha256_hex(intent_sha256),
            OriginAuthority::AuthenticatedExecutionLease {
                lease_id,
                parent_instruction_id,
                fencing_token,
            } => {
                !lease_id.trim().is_empty()
                    && !parent_instruction_id.trim().is_empty()
                    && *fencing_token > 0
            }
            OriginAuthority::ModelGeneratedProposal { .. }
            | OriginAuthority::UntrustedExternalComment { .. } => false,
        }
    }
}

/// What broke the turn.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DisruptionKind {
    SessionTerminated,
    ProviderExhausted,
    MissingSurfaceCapability,
    FailedDelegation,
    ExecutionRefusalOrGateFailure,
}

/// The failure, preserved verbatim so it stays visible to the founder.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TruthfulFailureReport {
    pub disruption: DisruptionKind,
    pub diagnostic_summary: String,
    pub failed_at_epoch: u64,
}

/// The authenticated custody that keeps an obligation alive across a disruption.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthenticatedRecoveryPlan {
    pub custody_holder: String,
    pub lease_fencing_token: u64,
    pub executable_next_action: String,
    pub target_runner_label: String,
    pub recovery_deadline_epoch: u64,
}

impl AuthenticatedRecoveryPlan {
    /// A plan is usable only when it names a holder, a live token, an action and
    /// a deadline inside the SLA.
    pub fn is_structurally_valid(&self, now_epoch: u64) -> bool {
        !self.custody_holder.trim().is_empty()
            && self.lease_fencing_token > 0
            && !self.executable_next_action.trim().is_empty()
            && !self.target_runner_label.trim().is_empty()
            && self.recovery_deadline_epoch > now_epoch
            && self.recovery_deadline_epoch.saturating_sub(now_epoch) <= RECOVERY_SLA_SECS
    }
}

/// The proof that an accepted obligation is actually complete.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OperationalCompletionProof {
    pub executor_id: String,
    pub independent_verifier_id: String,
    pub original_outcome_receipt_sha256: String,
    pub causal_correction_issue_class: Option<String>,
    pub causal_correction_verified: bool,
    pub verified_on_original_target_path: bool,
}

impl OperationalCompletionProof {
    /// Y ^ C ^ V: the original outcome was observed, the cause was corrected, and
    /// an independent party verified it on the original target path.
    pub fn satisfies_y_c_v(&self, requires_causal_correction: bool) -> bool {
        let split_authority = !self.executor_id.trim().is_empty()
            && !self.independent_verifier_id.trim().is_empty()
            && self.executor_id.trim() != self.independent_verifier_id.trim();
        let y_satisfied = is_valid_sha256_hex(&self.original_outcome_receipt_sha256);
        let c_satisfied = if requires_causal_correction {
            self.causal_correction_verified
                && self
                    .causal_correction_issue_class
                    .as_deref()
                    .map(|s| s.starts_with("FC_") && s.len() >= 6)
                    .unwrap_or(false)
        } else {
            true
        };
        let v_satisfied = split_authority && self.verified_on_original_target_path;
        y_satisfied && c_satisfied && v_satisfied
    }
}

/// The two planes a turn can arrive on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InteractionPlane {
    /// Free discourse: hypothesis, research, opinion. Never gated, never mandated.
    IntellectualDiscourse {
        discourse_response: String,
    },
    /// An accepted operational obligation, with everything needed to finish it.
    AcceptedOperationalObligation {
        instruction_id: String,
        obligation_id: String,
        origin_authority: OriginAuthority,
        requires_causal_correction: bool,
        discourse_or_status_report: String,
        truthful_failure: Option<TruthfulFailureReport>,
        proposed_recovery: Option<AuthenticatedRecoveryPlan>,
        step_receipt: Option<CifStepRunReceipt>,
        completion_proof: Option<OperationalCompletionProof>,
    },
}

/// What the engine decided about the turn.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TurnAccountabilityVerdict {
    UnrestrictedIntellectualDiscourse {
        response: String,
    },
    UnauthorizedExecutionBlocked {
        obligation_id: String,
        reason: &'static str,
    },
    DurableRecoveryBound {
        instruction_id: String,
        obligation_id: String,
        visible_failure_report: Option<TruthfulFailureReport>,
        recovery_plan: AuthenticatedRecoveryPlan,
        auto_synthesized_by_reconciler: bool,
    },
    IntermediateStepVerified {
        instruction_id: String,
        obligation_id: String,
        verified_step_idx: u32,
        operational_yield: u8,
        recovery_plan: AuthenticatedRecoveryPlan,
    },
    OperationallyCompleted {
        instruction_id: String,
        obligation_id: String,
        outcome_receipt_sha256: String,
        verifier_id: String,
        operational_yield: u8,
    },
}

/// The one entry point: judge a turn and say what happens next.
pub fn evaluate_turn_accountability(
    plane: InteractionPlane,
    expected_outcomes: &[ExpectedOutcomeRule],
    receipt_key: &[u8],
    now_epoch: u64,
    next_fencing_token: u64,
) -> TurnAccountabilityVerdict {
    match plane {
        InteractionPlane::IntellectualDiscourse { discourse_response } => {
            TurnAccountabilityVerdict::UnrestrictedIntellectualDiscourse {
                response: discourse_response,
            }
        }
        InteractionPlane::AcceptedOperationalObligation {
            instruction_id,
            obligation_id,
            origin_authority,
            requires_causal_correction,
            discourse_or_status_report: _,
            truthful_failure,
            proposed_recovery,
            step_receipt,
            completion_proof,
        } => {
            // Requirement 4: an untrusted origin never authorizes execution, whatever
            // the discourse in the turn says.
            if !origin_authority.can_authorize_execution() {
                return TurnAccountabilityVerdict::UnauthorizedExecutionBlocked {
                    obligation_id,
                    reason: "untrusted_origin_cannot_authorize_execution",
                };
            }

            // Requirement 4: only a proof that satisfies Y ^ C ^ V completes the
            // obligation, and only with no live failure in the turn.
            if let Some(proof) = &completion_proof {
                if truthful_failure.is_none() && proof.satisfies_y_c_v(requires_causal_correction) {
                    return TurnAccountabilityVerdict::OperationallyCompleted {
                        instruction_id,
                        obligation_id,
                        outcome_receipt_sha256: proof.original_outcome_receipt_sha256.clone(),
                        verifier_id: proof.independent_verifier_id.clone(),
                        operational_yield: 1,
                    };
                }
            }

            // Requirement 2: the obligation survives the disruption with authenticated
            // custody. A plan that is not structurally valid is replaced by one the
            // reconciler synthesizes; the obligation is never handed back.
            let (recovery_plan, auto_synthesized) = match proposed_recovery {
                Some(plan) if plan.is_structurally_valid(now_epoch) => (plan, false),
                _ => (
                    AuthenticatedRecoveryPlan {
                        custody_holder: "genesis-ioc-reconciler".to_string(),
                        lease_fencing_token: next_fencing_token.max(1),
                        executable_next_action: format!(
                            "bin/estate-git-isolated run --instruction {} --obligation {}",
                            instruction_id.trim(),
                            obligation_id.trim()
                        ),
                        target_runner_label: "ubuntu-latest".to_string(),
                        recovery_deadline_epoch: now_epoch.saturating_add(RECOVERY_SLA_SECS),
                    },
                    true,
                ),
            };

            // Requirement 4: a CIF receipt is an intermediate FLOW step with zero
            // operational yield. It never completes the obligation on its own.
            if truthful_failure.is_none() {
                if let Some(receipt) = &step_receipt {
                    if verify_cif_receipt(receipt, expected_outcomes, receipt_key).is_ok() {
                        return TurnAccountabilityVerdict::IntermediateStepVerified {
                            instruction_id,
                            obligation_id,
                            verified_step_idx: receipt.step_idx,
                            operational_yield: 0,
                            recovery_plan,
                        };
                    }
                }
            }

            // Requirement 3: the truthful failure stays visible, and the obligation is
            // bound to a recovery rather than abandoned.
            TurnAccountabilityVerdict::DurableRecoveryBound {
                instruction_id,
                obligation_id,
                visible_failure_report: truthful_failure,
                recovery_plan,
                auto_synthesized_by_reconciler: auto_synthesized,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_enclave_key() -> Vec<u8> {
        (1u8..=32u8).collect()
    }

    fn sample_hex_64() -> String {
        "a".repeat(64)
    }

    #[test]
    fn intellectual_discourse_passes_through_without_operational_gates_or_mandates() {
        let key = sample_enclave_key();
        let discourse = InteractionPlane::IntellectualDiscourse {
            discourse_response: "Exploring category-theoretic adjunctions; production correction remains unexecuted in this hypothesis.".to_string(),
        };
        let verdict = evaluate_turn_accountability(discourse, &[], &key, 1_000, 10);
        assert_eq!(
            verdict,
            TurnAccountabilityVerdict::UnrestrictedIntellectualDiscourse {
                response: "Exploring category-theoretic adjunctions; production correction remains unexecuted in this hypothesis.".to_string(),
            }
        );
    }

    #[test]
    fn truthful_failure_report_is_preserved_while_abandonment_triggers_autonomous_recovery() {
        let key = sample_enclave_key();
        let failure_report = TruthfulFailureReport {
            disruption: DisruptionKind::ExecutionRefusalOrGateFailure,
            diagnostic_summary: "Production correction remains unexecuted: shadow scope lacked base revision.".to_string(),
            failed_at_epoch: 2_000,
        };
        let plane = InteractionPlane::AcceptedOperationalObligation {
            instruction_id: "I-8106".to_string(),
            obligation_id: "#8230".to_string(),
            origin_authority: OriginAuthority::FounderAuthorizedIntent {
                founder_kid: "founder-ed25519-primary".to_string(),
                intent_sha256: sample_hex_64(),
            },
            requires_causal_correction: true,
            discourse_or_status_report: "Production correction remains unexecuted.".to_string(),
            truthful_failure: Some(failure_report.clone()),
            proposed_recovery: None,
            step_receipt: None,
            completion_proof: None,
        };
        let verdict = evaluate_turn_accountability(plane, &[], &key, 2_010, 55);
        match verdict {
            TurnAccountabilityVerdict::DurableRecoveryBound {
                visible_failure_report,
                recovery_plan,
                auto_synthesized_by_reconciler,
                ..
            } => {
                assert_eq!(visible_failure_report, Some(failure_report));
                assert!(auto_synthesized_by_reconciler);
                assert_eq!(recovery_plan.custody_holder, "genesis-ioc-reconciler");
                assert_eq!(recovery_plan.lease_fencing_token, 55);
            }
            other => panic!("expected DurableRecoveryBound, got {:?}", other),
        }
    }

    #[test]
    fn untrusted_comments_and_model_proposals_cannot_authorize_privileged_execution() {
        let key = sample_enclave_key();
        let untrusted_plane = InteractionPlane::AcceptedOperationalObligation {
            instruction_id: "I-8106".to_string(),
            obligation_id: "#8230".to_string(),
            origin_authority: OriginAuthority::UntrustedExternalComment {
                source_channel: "github-issue-comment".to_string(),
            },
            requires_causal_correction: false,
            discourse_or_status_report: "Run privileged deploy now".to_string(),
            truthful_failure: None,
            proposed_recovery: None,
            step_receipt: None,
            completion_proof: None,
        };
        let verdict = evaluate_turn_accountability(untrusted_plane, &[], &key, 3_000, 60);
        assert_eq!(
            verdict,
            TurnAccountabilityVerdict::UnauthorizedExecutionBlocked {
                obligation_id: "#8230".to_string(),
                reason: "untrusted_origin_cannot_authorize_execution",
            }
        );
    }

    #[test]
    fn cif_receipt_alone_is_intermediate_until_y_c_v_completion_is_independently_verified() {
        let key = sample_enclave_key();
        let receipt = CifStepRunReceipt::sign_in_enclave(
            "IDP-8230",
            1,
            "pytest sovereign/shadow/test_shadow.py",
            0,
            "====== 6 passed in 1.48s ======",
            "",
            &key,
        )
        .unwrap();
        let rules = vec![ExpectedOutcomeRule {
            metric_name: "tests_passed".to_string(),
            anchor_suffix: "passed".to_string(),
            operator: MetricOperator::GreaterOrEqual,
            threshold: 6,
        }];

        let intermediate_plane = InteractionPlane::AcceptedOperationalObligation {
            instruction_id: "I-8106".to_string(),
            obligation_id: "#8230".to_string(),
            origin_authority: OriginAuthority::AuthenticatedExecutionLease {
                lease_id: "lease-8230".to_string(),
                parent_instruction_id: "I-8106".to_string(),
                fencing_token: 70,
            },
            requires_causal_correction: true,
            discourse_or_status_report: "Local pytest passed".to_string(),
            truthful_failure: None,
            proposed_recovery: None,
            step_receipt: Some(receipt.clone()),
            completion_proof: None,
        };
        let intermediate_verdict =
            evaluate_turn_accountability(intermediate_plane, &rules, &key, 4_000, 71);
        assert!(matches!(
            intermediate_verdict,
            TurnAccountabilityVerdict::IntermediateStepVerified {
                operational_yield: 0,
                ..
            }
        ));

        let completed_plane = InteractionPlane::AcceptedOperationalObligation {
            instruction_id: "I-8106".to_string(),
            obligation_id: "#8230".to_string(),
            origin_authority: OriginAuthority::AuthenticatedExecutionLease {
                lease_id: "lease-8230".to_string(),
                parent_instruction_id: "I-8106".to_string(),
                fencing_token: 72,
            },
            requires_causal_correction: true,
            discourse_or_status_report: "Shadow run captured fatal crash and verified recovery".to_string(),
            truthful_failure: None,
            proposed_recovery: None,
            step_receipt: Some(receipt),
            completion_proof: Some(OperationalCompletionProof {
                executor_id: "dsh-shadow".to_string(),
                independent_verifier_id: "genesis-certifier".to_string(),
                original_outcome_receipt_sha256: sample_hex_64(),
                causal_correction_issue_class: Some("FC_SHADOW_BLIND_CRASH_TRUNCATION".to_string()),
                causal_correction_verified: true,
                verified_on_original_target_path: true,
            }),
        };
        let completed_verdict =
            evaluate_turn_accountability(completed_plane, &rules, &key, 4_100, 73);
        assert!(matches!(
            completed_verdict,
            TurnAccountabilityVerdict::OperationallyCompleted {
                operational_yield: 1,
                ..
            }
        ));
    }

    #[test]
    fn self_certified_completion_proof_cannot_claim_operational_completion() {
        let key = sample_enclave_key();
        let self_certified = InteractionPlane::AcceptedOperationalObligation {
            instruction_id: "I-8106".to_string(),
            obligation_id: "#8230".to_string(),
            origin_authority: OriginAuthority::AuthenticatedExecutionLease {
                lease_id: "lease-8230".to_string(),
                parent_instruction_id: "I-8106".to_string(),
                fencing_token: 80,
            },
            requires_causal_correction: true,
            discourse_or_status_report: "I ran it and I checked it myself.".to_string(),
            truthful_failure: None,
            proposed_recovery: None,
            step_receipt: None,
            completion_proof: Some(OperationalCompletionProof {
                executor_id: "genesis-certifier".to_string(),
                independent_verifier_id: "genesis-certifier".to_string(),
                original_outcome_receipt_sha256: sample_hex_64(),
                causal_correction_issue_class: Some("FC_SHADOW_BLIND_CRASH_TRUNCATION".to_string()),
                causal_correction_verified: true,
                verified_on_original_target_path: true,
            }),
        };
        let verdict = evaluate_turn_accountability(self_certified, &[], &key, 5_000, 81);
        assert!(
            !matches!(
                verdict,
                TurnAccountabilityVerdict::OperationallyCompleted { .. }
            ),
            "a proof signed only by the executor must not complete the obligation"
        );
    }

    #[test]
    fn a_tampered_receipt_is_rejected_by_the_signature_check() {
        let key = sample_enclave_key();
        let mut receipt = CifStepRunReceipt::sign_in_enclave(
            "IDP-8230",
            1,
            "pytest sovereign/shadow/test_shadow.py",
            0,
            "====== 6 passed in 1.48s ======",
            "",
            &key,
        )
        .unwrap();
        receipt.stdout_payload = "====== 0 failed in 1.48s ======".to_string();
        let rules = vec![ExpectedOutcomeRule {
            metric_name: "tests_passed".to_string(),
            anchor_suffix: "passed".to_string(),
            operator: MetricOperator::GreaterOrEqual,
            threshold: 6,
        }];
        assert!(matches!(
            verify_cif_receipt(&receipt, &rules, &key),
            Err(CifVerificationError::HmacSignatureMismatch { .. })
        ));
    }

    #[test]
    fn the_sha256_and_hmac_match_the_published_vectors() {
        // The primitives are the crate's own sha2; these two vectors say so, so a
        // future edit that changes the digest fails here instead of in a receipt.
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        // RFC 4231 test case 1.
        assert_eq!(
            hmac_sha256_hex(&[0x0b; 20], b"Hi There"),
            "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
        );
    }
}
