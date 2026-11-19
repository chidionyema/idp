//! Instruction I-8106 (Mandatory Amendment): Intellectual Freedom and Operational Accountability.
//!
//! Enforces:
//! 1. Unrestricted Intellectual Freedom (IntellectualDiscourse passes through with zero gates)
//! 2. Durable Operational Accountability (obligations survive session/provider/capability failures)
//! 3. Behaviour Over Vocabulary (zero keyword matching; truthful failures stay visible)
//! 4. Strict Authority Separation (untrusted comments and model outputs cannot authorize
//!    execution; a CIF receipt or CI check is an intermediate step; completion requires Y ^ C ^ V)

pub const CIF_KEY_MIN_LEN: usize = 32;
pub const RECOVERY_SLA_SECS: u64 = 600;

const K256: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

pub fn sha256_digest(data: &[u8]) -> [u8; 32] {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut padded = data.to_vec();
    padded.push(0x80);
    while (padded.len() % 64) != 56 {
        padded.push(0x00);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in padded.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (i, word) in w.iter_mut().take(16).enumerate() {
            let offset = i * 4;
            *word = u32::from_be_bytes([
                chunk[offset],
                chunk[offset + 1],
                chunk[offset + 2],
                chunk[offset + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K256[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut out = [0u8; 32];
    for (i, word) in h.iter().enumerate() {
        out[i * 4..(i + 1) * 4].copy_from_slice(&word.to_be_bytes());
    }
    out
}

pub fn bytes_to_lower_hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut s = String::with_capacity(bytes.len() * 2);
    for &b in bytes {
        let _ = write!(&mut s, "{:02x}", b);
    }
    s
}

pub fn sha256_hex(data: &[u8]) -> String {
    bytes_to_lower_hex(&sha256_digest(data))
}

pub fn hmac_sha256(key: &[u8], message: &[u8]) -> [u8; 32] {
    let mut k_block = [0u8; 64];
    if key.len() > 64 {
        let hashed = sha256_digest(key);
        k_block[..32].copy_from_slice(&hashed);
    } else {
        k_block[..key.len()].copy_from_slice(key);
    }
    let mut ipad = [0x36u8; 64];
    let mut opad = [0x5cu8; 64];
    for i in 0..64 {
        ipad[i] ^= k_block[i];
        opad[i] ^= k_block[i];
    }
    let mut inner = Vec::with_capacity(64 + message.len());
    inner.extend_from_slice(&ipad);
    inner.extend_from_slice(message);
    let inner_hash = sha256_digest(&inner);

    let mut outer = Vec::with_capacity(64 + 32);
    outer.extend_from_slice(&opad);
    outer.extend_from_slice(&inner_hash);
    sha256_digest(&outer)
}

pub fn hmac_sha256_hex(key: &[u8], message: &[u8]) -> String {
    bytes_to_lower_hex(&hmac_sha256(key, message))
}

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

pub fn is_valid_sha256_hex(candidate: &str) -> bool {
    candidate.len() == 64
        && candidate
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MetricOperator {
    GreaterThan,
    GreaterOrEqual,
    Equal,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExpectedOutcomeRule {
    pub metric_name: String,
    pub anchor_suffix: String,
    pub operator: MetricOperator,
    pub threshold: i64,
}

impl ExpectedOutcomeRule {
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

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyDecisionRecord {
    pub ticket_id: String,
    pub step_idx: u32,
    pub metric_name: String,
    pub extracted_value: i64,
    pub satisfied: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CifVerificationError {
    InvalidEnclaveKey,
    HmacSignatureMismatch {
        ticket_id: String,
        step_idx: u32,
    },
    NonZeroExitCode {
        exit_code: i32,
    },
    MetricNotFoundInStdout {
        metric_name: String,
    },
    MetricThresholdUnsatisfied {
        metric_name: String,
        extracted: i64,
        threshold: i64,
    },
}

pub fn verify_cif_receipt(
    receipt: &CifStepRunReceipt,
    expected_outcomes: &[ExpectedOutcomeRule],
    receipt_key: &[u8],
) -> Result<Vec<PolicyDecisionRecord>, CifVerificationError> {
    if receipt_key.len() < CIF_KEY_MIN_LEN || receipt_key.iter().all(|&b| b == 0) {
        return Err(CifVerificationError::InvalidEnclaveKey);
    }
    let expected_hmac = hmac_sha256_hex(receipt_key, receipt.canonical_signing_payload().as_bytes());
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DisruptionKind {
    SessionTerminated,
    ProviderExhausted,
    MissingSurfaceCapability,
    FailedDelegation,
    ExecutionRefusalOrGateFailure,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TruthfulFailureReport {
    pub disruption: DisruptionKind,
    pub diagnostic_summary: String,
    pub failed_at_epoch: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthenticatedRecoveryPlan {
    pub custody_holder: String,
    pub lease_fencing_token: u64,
    pub executable_next_action: String,
    pub target_runner_label: String,
    pub recovery_deadline_epoch: u64,
}

impl AuthenticatedRecoveryPlan {
    pub fn is_structurally_valid(&self, now_epoch: u64) -> bool {
        !self.custody_holder.trim().is_empty()
            && self.lease_fencing_token > 0
            && !self.executable_next_action.trim().is_empty()
            && !self.target_runner_label.trim().is_empty()
            && self.recovery_deadline_epoch > now_epoch
            && self.recovery_deadline_epoch.saturating_sub(now_epoch) <= RECOVERY_SLA_SECS
    }
}

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

// The obligation variant carries the whole evidence bundle (receipt, failure report, recovery
// plan, completion proof) while discourse carries one string. The difference is intentional and
// harmless here: a plane is constructed once per turn and never stored in a collection or moved
// in bulk, so boxing the obligation would buy indirection on the accountability path and nothing
// else. Measured: this is the only clippy finding in this module.
#[allow(clippy::large_enum_variant)]
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InteractionPlane {
    IntellectualDiscourse {
        discourse_response: String,
    },
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

pub fn evaluate_turn_accountability(
    plane: InteractionPlane,
    expected_outcomes: &[ExpectedOutcomeRule],
    receipt_key: &[u8],
    now_epoch: u64,
    next_fencing_token: u64,
) -> TurnAccountabilityVerdict {
    match plane {
        InteractionPlane::IntellectualDiscourse {
            discourse_response,
        } => TurnAccountabilityVerdict::UnrestrictedIntellectualDiscourse {
            response: discourse_response,
        },
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
            if !origin_authority.can_authorize_execution() {
                return TurnAccountabilityVerdict::UnauthorizedExecutionBlocked {
                    obligation_id,
                    reason: "untrusted_origin_cannot_authorize_execution",
                };
            }

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
            discourse_or_status_report: "Shadow run captured fatal crash and verified recovery"
                .to_string(),
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

    /// FALSIFIER: a tampered receipt must not advance the obligation. Without this, an agent
    /// could sign nothing and still reach IntermediateStepVerified.
    #[test]
    fn tampered_receipt_does_not_advance_the_obligation() {
        let key = sample_enclave_key();
        let mut receipt = CifStepRunReceipt::sign_in_enclave(
            "I-8106", 1, "cargo test", 0, "====== 10 passed in 0.01s ======", "", &key,
        )
        .unwrap();
        // Flip one character of the signed payload: the HMAC must no longer match.
        receipt.stdout_payload = "====== 11 passed in 0.01s ======".to_string();

        let rules = vec![ExpectedOutcomeRule {
            metric_name: "tests_passed".to_string(),
            anchor_suffix: "passed".to_string(),
            operator: MetricOperator::GreaterOrEqual,
            threshold: 10,
        }];
        assert!(verify_cif_receipt(&receipt, &rules, &key).is_err());

        let verdict = evaluate_turn_accountability(
            InteractionPlane::AcceptedOperationalObligation {
                instruction_id: "I-8106".to_string(),
                obligation_id: "#8244".to_string(),
                origin_authority: OriginAuthority::AuthenticatedExecutionLease {
                    lease_id: "lease-8244".to_string(),
                    parent_instruction_id: "I-8106".to_string(),
                    fencing_token: 40,
                },
                requires_causal_correction: true,
                discourse_or_status_report: "tests pass".to_string(),
                truthful_failure: None,
                proposed_recovery: None,
                step_receipt: Some(receipt),
                completion_proof: None,
            },
            &rules,
            &key,
            5_000,
            40,
        );
        assert!(
            matches!(verdict, TurnAccountabilityVerdict::DurableRecoveryBound { .. }),
            "a tampered receipt must bind recovery, got {:?}",
            verdict
        );
    }

    /// FALSIFIER: a stale or already-expired recovery plan must be replaced, not honoured.
    /// Without this, custody could be bound to a deadline that has already passed.
    #[test]
    fn expired_recovery_plan_is_replaced_not_honoured() {
        let key = sample_enclave_key();
        let stale = AuthenticatedRecoveryPlan {
            custody_holder: "someone-else".to_string(),
            lease_fencing_token: 1,
            executable_next_action: "echo noop".to_string(),
            target_runner_label: "ubuntu-latest".to_string(),
            recovery_deadline_epoch: 1_000, // already past when now = 9_000
        };
        let verdict = evaluate_turn_accountability(
            InteractionPlane::AcceptedOperationalObligation {
                instruction_id: "I-8106".to_string(),
                obligation_id: "#8244".to_string(),
                origin_authority: OriginAuthority::FounderAuthorizedIntent {
                    founder_kid: "founder-ed25519-primary".to_string(),
                    intent_sha256: sample_hex_64(),
                },
                requires_causal_correction: false,
                discourse_or_status_report: "blocked".to_string(),
                truthful_failure: Some(TruthfulFailureReport {
                    disruption: DisruptionKind::ExecutionRefusalOrGateFailure,
                    diagnostic_summary: "gate refused".to_string(),
                    failed_at_epoch: 8_000,
                }),
                proposed_recovery: Some(stale),
                step_receipt: None,
                completion_proof: None,
            },
            &[],
            &key,
            9_000,
            77,
        );
        match verdict {
            TurnAccountabilityVerdict::DurableRecoveryBound {
                recovery_plan,
                auto_synthesized_by_reconciler,
                ..
            } => {
                assert!(auto_synthesized_by_reconciler, "stale plan must be replaced");
                assert_eq!(recovery_plan.lease_fencing_token, 77);
                assert!(recovery_plan.recovery_deadline_epoch > 9_000);
            }
            other => panic!("expected recovery bound, got {:?}", other),
        }
    }

    /// FALSIFIER: a completion proof whose executor and verifier are the same actor must NOT
    /// complete. Without this, an agent can self-certify and reach yield=1.
    #[test]
    fn completion_requires_split_authority() {
        let key = sample_enclave_key();
        let self_certified = OperationalCompletionProof {
            executor_id: "dsh-i8106-cage-20261119".to_string(),
            independent_verifier_id: "dsh-i8106-cage-20261119".to_string(),
            original_outcome_receipt_sha256: sample_hex_64(),
            causal_correction_issue_class: Some("FC_SELF_CERTIFICATION".to_string()),
            causal_correction_verified: true,
            verified_on_original_target_path: true,
        };
        assert!(!self_certified.satisfies_y_c_v(true));

        let verdict = evaluate_turn_accountability(
            InteractionPlane::AcceptedOperationalObligation {
                instruction_id: "I-8106".to_string(),
                obligation_id: "#8244".to_string(),
                origin_authority: OriginAuthority::FounderAuthorizedIntent {
                    founder_kid: "founder-ed25519-primary".to_string(),
                    intent_sha256: sample_hex_64(),
                },
                requires_causal_correction: true,
                discourse_or_status_report: "done".to_string(),
                truthful_failure: None,
                proposed_recovery: None,
                step_receipt: None,
                completion_proof: Some(self_certified),
            },
            &[],
            &key,
            6_000,
            50,
        );
        assert!(
            !matches!(verdict, TurnAccountabilityVerdict::OperationallyCompleted { .. }),
            "self-certification must not complete, got {:?}",
            verdict
        );
    }
}
