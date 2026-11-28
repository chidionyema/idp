//! Meridian Intent Transmission Protocol & Zero-Shot Preventive Control Kernel (`mitp-core`).
//!
//! Enforces MERIDIAN-CTRL-001 (B01-B10) and MNSE-SPEC-v1.0 invariants at compile time and
//! deterministic runtime with zero prompt reliance and zero Python invariant logic.

use ed25519_dalek::{Signature, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashSet};

/// Explicit admission & gate verdicts (MERIDIAN-CTRL-001 Section 9).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum VerdictKind {
    Allow,
    Deny,
    Defer,
    Reconcile,
    Blind,
}

/// Machine-actionable gate verdict returned on stdout as JSON.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateVerdict {
    pub verdict: VerdictKind,
    pub error: Option<GateError>,
    pub violated_predicate: Option<String>,
    pub recovery_class: String,
    pub machine_owner: String,
    pub next_action: String,
    pub epoch: Option<u64>,
    pub fencing_token: Option<u64>,
}

impl GateVerdict {
    pub fn allow(epoch: u64, fencing_token: u64) -> Self {
        Self {
            verdict: VerdictKind::Allow,
            error: None,
            violated_predicate: None,
            recovery_class: "NONE".to_string(),
            machine_owner: "authority-sequencer".to_string(),
            next_action: "PROCEED".to_string(),
            epoch: Some(epoch),
            fencing_token: Some(fencing_token),
        }
    }

    pub fn deny(err: GateError, predicate: &str, recovery: &str, next_action: &str) -> Self {
        Self {
            verdict: VerdictKind::Deny,
            error: Some(err),
            violated_predicate: Some(predicate.to_string()),
            recovery_class: recovery.to_string(),
            machine_owner: "authority-sequencer".to_string(),
            next_action: next_action.to_string(),
            epoch: None,
            fencing_token: None,
        }
    }

    pub fn reconcile(err: GateError, predicate: &str, next_action: &str) -> Self {
        Self {
            verdict: VerdictKind::Reconcile,
            error: Some(err),
            violated_predicate: Some(predicate.to_string()),
            recovery_class: "BOUNDED_RECOVERY".to_string(),
            machine_owner: "reconciler".to_string(),
            next_action: next_action.to_string(),
            epoch: None,
            fencing_token: None,
        }
    }

    pub fn blind(reason: &str) -> Self {
        Self {
            verdict: VerdictKind::Blind,
            error: Some(GateError::BlindObservation(reason.to_string())),
            violated_predicate: Some("B08_OPERATIONAL_TRUTH".to_string()),
            recovery_class: "EXTERNAL_PREREQUISITE".to_string(),
            machine_owner: "verifier".to_string(),
            next_action: "RESTORE_OBSERVABILITY".to_string(),
            epoch: None,
            fencing_token: None,
        }
    }
}

/// Typed static resource keys for decidable Bernstein conflict checks.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ResourceKey {
    RepoPath { repo: String, path_prefix: String },
    GitRef { repo: String, branch: String },
    EscrowAccount { domain_id: String, currency: String },
    ExternalSink { sink_id: String, idempotency_key: String },
    RingScope { ring: u8, namespace: String },
}

impl ResourceKey {
    /// Rejects unbounded wildcards, empty fields, or path-traversal escape attempts.
    pub fn is_bounded(&self) -> bool {
        match self {
            ResourceKey::RepoPath { repo, path_prefix } => {
                let r = repo.trim();
                let p = path_prefix.trim();
                !r.is_empty()
                    && !p.is_empty()
                    && p != "*"
                    && p != "**"
                    && p != "/"
                    && p != "."
                    && !p.contains("..")
            }
            ResourceKey::GitRef { repo, branch } => {
                !repo.trim().is_empty() && !branch.trim().is_empty() && !branch.contains('*')
            }
            ResourceKey::EscrowAccount { domain_id, currency } => {
                !domain_id.trim().is_empty() && currency.len() == 3 && currency.chars().all(|c| c.is_ascii_uppercase())
            }
            ResourceKey::ExternalSink { sink_id, idempotency_key } => {
                !sink_id.trim().is_empty() && !idempotency_key.trim().is_empty()
            }
            ResourceKey::RingScope { ring, namespace } => *ring <= 3 && !namespace.trim().is_empty(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Footprint {
    pub reads: BTreeSet<ResourceKey>,
    pub writes: BTreeSet<ResourceKey>,
}

impl Footprint {
    /// Fail-closed validation: empty footprints and wildcard/traversal keys are rejected.
    pub fn validate(&self) -> Result<(), GateError> {
        if self.reads.is_empty() && self.writes.is_empty() {
            return Err(GateError::UnboundedFootprint);
        }
        if !self.reads.iter().all(ResourceKey::is_bounded) || !self.writes.iter().all(ResourceKey::is_bounded) {
            return Err(GateError::UnboundedFootprint);
        }
        Ok(())
    }

    /// Decidable Bernstein conflict predicate: (R1 ∩ W2) ∪ (W1 ∩ R2) ∪ (W1 ∩ W2) != ∅
    pub fn conflicts_with(&self, other: &Self) -> bool {
        !self.reads.is_disjoint(&other.writes)
            || !self.writes.is_disjoint(&other.reads)
            || !self.writes.is_disjoint(&other.writes)
    }

    /// Denning lattice taint check (B01/B10/I5): reading Ring 3 while writing/egressing to Ring 0..=2 or ExternalSink.
    pub fn has_ring3_egress_taint(&self) -> bool {
        let reads_ring3 = self
            .reads
            .iter()
            .any(|k| matches!(k, ResourceKey::RingScope { ring: 3, .. }));
        if !reads_ring3 {
            return false;
        }
        self.writes.iter().any(|k| match k {
            ResourceKey::RingScope { ring, .. } => *ring < 3,
            ResourceKey::ExternalSink { .. } => true,
            _ => false,
        })
    }
}

/// Ordered effect classes (R < I < C < P) enforcing monotonic authority attenuation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum EffectClass {
    R = 0, // Epistemic / Read & Inference
    I = 1, // Internal Reversible
    C = 2, // External Compensatable
    P = 3, // External Pivot / Irreversible
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Monotonicity {
    Monotonic,
    NonMonotonic,
}

/// Authoritative billing classification (MERIDIAN-CTRL-001 B02).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BillingClass {
    MonthlySubscription,
    ApiCredit,
    FreeAllowance,
    FounderAuthorisedException,
}

/// Provider lane eligibility state (B02 + idp#3525 FIT gate).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum LaneHealth {
    Fit,
    Unfit,
    Exhausted,
    Drained,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProviderLane {
    pub lane_id: String,
    pub billing_class: BillingClass,
    pub health: LaneHealth,
    pub fitness_expires_at_utc: u64,
}

/// Reserved constitutional powers never delegable to machine envelopes (B10).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ReservedPower {
    AlterConstitution,
    RotateJwksRoot,
    BridgeRing3External,
    WeakenAcceptancePredicate,
    RaiseParentBudget,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParentMandate {
    pub root_h_digest: String,
    pub max_effect_class: EffectClass,
    pub allowed_billing_class: BillingClass,
    pub policy_hash: String,
    pub currency: String,
    pub budget_ceiling_minor_units: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EffectEnvelope {
    pub instruction_id: String,
    pub attempt_id: String,
    pub effect_digest: String,
    pub parent_m_digest: String,
    pub root_h_digest: String,
    pub policy_hash: String,
    pub objective_hash: String,
    pub acceptance_predicate_hash: String,
    pub lane_id: String,
    pub requested_billing_class: BillingClass,
    pub class: EffectClass,
    pub monotonicity: Monotonicity,
    pub footprint: Footprint,
    pub cost_minor_units: i64,
    pub currency: String,
    pub revocation_epoch: u64,
    pub fencing_token: u64,
    pub base_revisions: BTreeMap<String, u64>,
    pub nonce_hex: String,
    pub verification_deadline_utc: u64,
    pub requested_reserved_power: Option<ReservedPower>,
}

/// Exhaustive, machine-actionable gate failure taxonomy.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "code", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum GateError {
    MissingInstructionId,
    UnboundedFootprint,
    AuthorityEscalation,
    CrossClassSubstitution {
        expected: BillingClass,
        got: BillingClass,
    },
    ProviderIneligible {
        lane_id: String,
        reason: String,
    },
    InvalidCost {
        cost: i64,
    },
    InsufficientEscrow {
        requested: i64,
        available: i64,
    },
    CurrencyMismatch {
        expected: String,
        got: String,
    },
    StaleRevocationEpoch {
        got: u64,
        current: u64,
    },
    StaleFencingToken {
        got: u64,
        authoritative: u64,
    },
    OccRevisionConflict {
        key: String,
        expected: u64,
        actual: u64,
    },
    MissingCertifierSignature,
    InvalidCertifierSignature,
    SelfCertificationForbidden,
    VerificationDeadlineExpired {
        now_utc: u64,
        deadline_utc: u64,
    },
    TaintViolation,
    ReplayNonceDetected,
    ProxyGreenSubstitution {
        url: String,
    },
    InvalidShipContract {
        reason: String,
    },
    ScopeViolation {
        path: String,
    },
    MissingFounderSeal {
        path: String,
    },
    AlreadySettled {
        instruction_id: String,
    },
    BlindObservation(String),
}

/// Independent Ed25519 settlement receipt (B08 + Section 11).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerifierReceipt {
    pub instruction_id: String,
    pub attempt_id: String,
    pub execution_epoch: u64,
    pub objective_hash: String,
    pub acceptance_predicate_hash: String,
    pub target_identity: String,
    pub artifact_digest: String,
    pub observed_at_utc: u64,
    pub evidence_expires_utc: u64,
    pub observation_url: String,
    pub verifier_pubkey_hex: String,
    pub policy_hash: String,
    pub signature_hex: String,
}

impl VerifierReceipt {
    /// Deterministic canonical payload bytes hashed and signed with Ed25519.
    pub fn canonical_message(&self) -> Vec<u8> {
        let joined = format!(
            "MERIDIAN-SETTLEMENT-V1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",
            self.instruction_id,
            self.attempt_id,
            self.execution_epoch,
            self.objective_hash,
            self.acceptance_predicate_hash,
            self.target_identity,
            self.artifact_digest,
            self.observed_at_utc,
            self.evidence_expires_utc,
            self.observation_url,
            self.policy_hash
        );
        let mut hasher = Sha256::new();
        hasher.update(joined.as_bytes());
        hasher.finalize().to_vec()
    }
}

/// Typestate markers: Settled cannot be constructed outside `verify_and_settle`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerifyingObligation {
    pub instruction_id: String,
    pub attempt_id: String,
    pub execution_epoch: u64,
    pub objective_hash: String,
    pub acceptance_predicate_hash: String,
    pub policy_hash: String,
    pub verification_deadline_utc: u64,
    pub worker_pubkey_hex: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SettledObligation {
    instruction_id: String,
    artifact_digest: String,
    settled_at_utc: u64,
}

impl SettledObligation {
    pub fn instruction_id(&self) -> &str {
        &self.instruction_id
    }
    pub fn artifact_digest(&self) -> &str {
        &self.artifact_digest
    }
    pub fn settled_at_utc(&self) -> u64 {
        self.settled_at_utc
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SettlementTransition {
    Settled(SettledObligation),
    RecoveryRequired {
        instruction_id: String,
        reason: GateError,
    },
}

/// Checks if a URL is a forbidden proxy-green URL (GitHub source or loopback).
pub fn is_proxy_green_url(url: &str) -> bool {
    let lower = url.trim().to_ascii_lowercase();
    if !lower.starts_with("https://") {
        return true;
    }
    let host = lower
        .trim_start_matches("https://")
        .split('/')
        .next()
        .unwrap_or("");
    let host_no_port = host.split(':').next().unwrap_or("");
    matches!(
        host_no_port,
        "" | "github.com"
            | "www.github.com"
            | "api.github.com"
            | "raw.githubusercontent.com"
            | "localhost"
            | "127.0.0.1"
            | "0.0.0.0"
            | "::1"
    )
}

/// Verifies an Ed25519 signature strictly (rejects malleability & non-canonical encodings).
pub fn verify_ed25519_strict(
    pubkey_hex: &str,
    message: &[u8],
    sig_hex: &str,
) -> Result<(), GateError> {
    let pk_bytes = hex::decode(pubkey_hex.trim()).map_err(|_| GateError::InvalidCertifierSignature)?;
    let pk_arr: [u8; 32] = pk_bytes
        .try_into()
        .map_err(|_| GateError::InvalidCertifierSignature)?;
    let vk = VerifyingKey::from_bytes(&pk_arr).map_err(|_| GateError::InvalidCertifierSignature)?;

    let sig_bytes = hex::decode(sig_hex.trim()).map_err(|_| GateError::InvalidCertifierSignature)?;
    let sig_arr: [u8; 64] = sig_bytes
        .try_into()
        .map_err(|_| GateError::InvalidCertifierSignature)?;
    let sig = Signature::from_bytes(&sig_arr);

    vk.verify_strict(message, &sig)
        .map_err(|_| GateError::InvalidCertifierSignature)
}

/// Sealed settlement transition (MERIDIAN-CTRL-001 B06, B08, Section 11).
pub fn verify_and_settle(
    obligation: &VerifyingObligation,
    receipt: Option<&VerifierReceipt>,
    trusted_certifier_pubkeys_hex: &HashSet<String>,
    current_revocation_epoch: u64,
    now_utc: u64,
    settled_registry: &mut HashSet<String>,
) -> Result<SettlementTransition, GateError> {
    if obligation.instruction_id.trim().is_empty() {
        return Err(GateError::MissingInstructionId);
    }
    if settled_registry.contains(&obligation.instruction_id) {
        return Err(GateError::AlreadySettled {
            instruction_id: obligation.instruction_id.clone(),
        });
    }
    if now_utc > obligation.verification_deadline_utc {
        return Ok(SettlementTransition::RecoveryRequired {
            instruction_id: obligation.instruction_id.clone(),
            reason: GateError::VerificationDeadlineExpired {
                now_utc,
                deadline_utc: obligation.verification_deadline_utc,
            },
        });
    }

    let r = receipt.ok_or(GateError::MissingCertifierSignature)?;

    if r.execution_epoch != current_revocation_epoch || r.execution_epoch != obligation.execution_epoch {
        return Err(GateError::StaleRevocationEpoch {
            got: r.execution_epoch,
            current: current_revocation_epoch,
        });
    }
    if r.instruction_id != obligation.instruction_id
        || r.attempt_id != obligation.attempt_id
        || r.objective_hash != obligation.objective_hash
        || r.acceptance_predicate_hash != obligation.acceptance_predicate_hash
        || r.policy_hash != obligation.policy_hash
    {
        return Err(GateError::InvalidCertifierSignature);
    }
    if r.evidence_expires_utc < now_utc {
        return Ok(SettlementTransition::RecoveryRequired {
            instruction_id: obligation.instruction_id.clone(),
            reason: GateError::VerificationDeadlineExpired {
                now_utc,
                deadline_utc: r.evidence_expires_utc,
            },
        });
    }
    if is_proxy_green_url(&r.observation_url) {
        return Err(GateError::ProxyGreenSubstitution {
            url: r.observation_url.clone(),
        });
    }
    if r.verifier_pubkey_hex.eq_ignore_ascii_case(&obligation.worker_pubkey_hex) {
        return Err(GateError::SelfCertificationForbidden);
    }
    if !trusted_certifier_pubkeys_hex.contains(&r.verifier_pubkey_hex.to_ascii_lowercase()) {
        return Err(GateError::MissingCertifierSignature);
    }

    let msg = r.canonical_message();
    verify_ed25519_strict(&r.verifier_pubkey_hex, &msg, &r.signature_hex)?;

    settled_registry.insert(obligation.instruction_id.clone());
    Ok(SettlementTransition::Settled(SettledObligation {
        instruction_id: obligation.instruction_id.clone(),
        artifact_digest: r.artifact_digest.clone(),
        settled_at_utc: now_utc,
    }))
}

/// CP-1 & CP-2: Infrastructure-agnostic AuthoritySequencer trait.
pub trait AuthoritySequencer {
    fn admit_effect(&mut self, env: &EffectEnvelope, now_utc: u64) -> Result<u64, GateError>;
    fn commit_revocation(&mut self) -> Result<u64, GateError>;
    fn drain_fenced_escrow(&mut self, effect_digest: &str) -> Result<i64, GateError>;
}

/// CP-3 & CP-4: Infrastructure-agnostic FencedCommitGate trait.
pub trait FencedCommitGate {
    fn promote_occ(
        &mut self,
        env: &EffectEnvelope,
        receipt: &VerifierReceipt,
        now_utc: u64,
    ) -> Result<u64, GateError>;
}

#[derive(Clone, Debug)]
struct Reservation {
    amount: i64,
    epoch: u64,
}

/// Reference deterministic AuthoritySequencer + FencedCommitGate implementation.
pub struct DeterministicKernel {
    pub mandate: ParentMandate,
    pub revocation_epoch: u64,
    pub authoritative_token: u64,
    pub spent_minor_units: i64,
    reservations: BTreeMap<String, Reservation>,
    consumed_nonces: HashSet<String>,
    lanes: BTreeMap<String, ProviderLane>,
    head_revisions: BTreeMap<String, u64>,
    trusted_certifiers: HashSet<String>,
    worker_pubkeys: HashSet<String>,
    settled_instructions: HashSet<String>,
}

impl DeterministicKernel {
    pub fn new(
        mandate: ParentMandate,
        lanes: Vec<ProviderLane>,
        trusted_certifiers_hex: Vec<String>,
        worker_pubkeys_hex: Vec<String>,
    ) -> Self {
        let mut lane_map = BTreeMap::new();
        for l in lanes {
            lane_map.insert(l.lane_id.clone(), l);
        }
        Self {
            mandate,
            revocation_epoch: 1,
            authoritative_token: 1,
            spent_minor_units: 0,
            reservations: BTreeMap::new(),
            consumed_nonces: HashSet::new(),
            lanes: lane_map,
            head_revisions: BTreeMap::new(),
            trusted_certifiers: trusted_certifiers_hex
                .into_iter()
                .map(|s| s.to_ascii_lowercase())
                .collect(),
            worker_pubkeys: worker_pubkeys_hex
                .into_iter()
                .map(|s| s.to_ascii_lowercase())
                .collect(),
            settled_instructions: HashSet::new(),
        }
    }

    pub fn set_head_revision(&mut self, key: &str, rev: u64) {
        self.head_revisions.insert(key.to_string(), rev);
    }

    pub fn head_revision(&self, key: &str) -> u64 {
        *self.head_revisions.get(key).unwrap_or(&0)
    }

    pub fn total_reserved(&self) -> i64 {
        self.reservations.values().map(|r| r.amount).sum()
    }
}

impl AuthoritySequencer for DeterministicKernel {
    fn admit_effect(&mut self, env: &EffectEnvelope, now_utc: u64) -> Result<u64, GateError> {
        if env.instruction_id.trim().is_empty() {
            return Err(GateError::MissingInstructionId);
        }
        if env.requested_reserved_power.is_some()
            || env.class > self.mandate.max_effect_class
            || env.root_h_digest != self.mandate.root_h_digest
            || env.policy_hash != self.mandate.policy_hash
        {
            return Err(GateError::AuthorityEscalation);
        }
        env.footprint.validate()?;
        if env.footprint.has_ring3_egress_taint() {
            return Err(GateError::TaintViolation);
        }
        if env.revocation_epoch != self.revocation_epoch {
            return Err(GateError::StaleRevocationEpoch {
                got: env.revocation_epoch,
                current: self.revocation_epoch,
            });
        }
        if env.fencing_token < self.authoritative_token {
            return Err(GateError::StaleFencingToken {
                got: env.fencing_token,
                authoritative: self.authoritative_token,
            });
        }
        if env.requested_billing_class != self.mandate.allowed_billing_class {
            return Err(GateError::CrossClassSubstitution {
                expected: self.mandate.allowed_billing_class,
                got: env.requested_billing_class,
            });
        }
        let lane = self.lanes.get(&env.lane_id).ok_or_else(|| GateError::ProviderIneligible {
            lane_id: env.lane_id.clone(),
            reason: "UNKNOWN_LANE".to_string(),
        })?;
        if lane.billing_class != self.mandate.allowed_billing_class {
            return Err(GateError::CrossClassSubstitution {
                expected: self.mandate.allowed_billing_class,
                got: lane.billing_class,
            });
        }
        if lane.health != LaneHealth::Fit || now_utc > lane.fitness_expires_at_utc {
            return Err(GateError::ProviderIneligible {
                lane_id: lane.lane_id.clone(),
                reason: format!("HEALTH_{:?}_OR_STALE_FIT", lane.health),
            });
        }
        if env.currency != self.mandate.currency {
            return Err(GateError::CurrencyMismatch {
                expected: self.mandate.currency.clone(),
                got: env.currency.clone(),
            });
        }
        if env.cost_minor_units < 0 {
            return Err(GateError::InvalidCost {
                cost: env.cost_minor_units,
            });
        }
        let reserved_now = self.total_reserved();
        let projected = reserved_now
            .checked_add(self.spent_minor_units)
            .and_then(|s| s.checked_add(env.cost_minor_units))
            .ok_or(GateError::InvalidCost {
                cost: env.cost_minor_units,
            })?;
        if projected > self.mandate.budget_ceiling_minor_units {
            let avail = self.mandate.budget_ceiling_minor_units - reserved_now - self.spent_minor_units;
            return Err(GateError::InsufficientEscrow {
                requested: env.cost_minor_units,
                available: avail,
            });
        }
        let nonce_norm = env.nonce_hex.trim().to_ascii_lowercase();
        if nonce_norm.len() < 16 || self.consumed_nonces.contains(&nonce_norm) {
            return Err(GateError::ReplayNonceDetected);
        }

        // Atomic commit of nonce + escrow reservation
        self.consumed_nonces.insert(nonce_norm);
        self.reservations.insert(
            env.effect_digest.clone(),
            Reservation {
                amount: env.cost_minor_units,
                epoch: self.revocation_epoch,
            },
        );
        Ok(self.authoritative_token)
    }

    fn commit_revocation(&mut self) -> Result<u64, GateError> {
        self.revocation_epoch = self.revocation_epoch.saturating_add(1);
        self.authoritative_token = self.authoritative_token.saturating_add(1);
        Ok(self.revocation_epoch)
    }

    fn drain_fenced_escrow(&mut self, effect_digest: &str) -> Result<i64, GateError> {
        match self.reservations.get(effect_digest) {
            Some(res) if res.epoch < self.revocation_epoch => {
                let amt = res.amount;
                self.reservations.remove(effect_digest);
                Ok(amt)
            }
            Some(_) => Ok(0),
            None => Ok(0),
        }
    }
}

impl FencedCommitGate for DeterministicKernel {
    fn promote_occ(
        &mut self,
        env: &EffectEnvelope,
        receipt: &VerifierReceipt,
        now_utc: u64,
    ) -> Result<u64, GateError> {
        if env.revocation_epoch != self.revocation_epoch {
            return Err(GateError::StaleRevocationEpoch {
                got: env.revocation_epoch,
                current: self.revocation_epoch,
            });
        }
        if env.fencing_token < self.authoritative_token {
            return Err(GateError::StaleFencingToken {
                got: env.fencing_token,
                authoritative: self.authoritative_token,
            });
        }
        if self.worker_pubkeys.contains(&receipt.verifier_pubkey_hex.to_ascii_lowercase()) {
            return Err(GateError::SelfCertificationForbidden);
        }

        let ob = VerifyingObligation {
            instruction_id: env.instruction_id.clone(),
            attempt_id: env.attempt_id.clone(),
            execution_epoch: env.revocation_epoch,
            objective_hash: env.objective_hash.clone(),
            acceptance_predicate_hash: env.acceptance_predicate_hash.clone(),
            policy_hash: env.policy_hash.clone(),
            verification_deadline_utc: env.verification_deadline_utc,
            worker_pubkey_hex: String::new(),
        };

        // Check OCC base revisions BEFORE mutating state or settling
        for (k, expected_rev) in &env.base_revisions {
            let actual = self.head_revision(k);
            if actual != *expected_rev {
                return Err(GateError::OccRevisionConflict {
                    key: k.clone(),
                    expected: *expected_rev,
                    actual,
                });
            }
        }

        let transition = verify_and_settle(
            &ob,
            Some(receipt),
            &self.trusted_certifiers,
            self.revocation_epoch,
            now_utc,
            &mut self.settled_instructions,
        )?;
        if let SettlementTransition::RecoveryRequired { reason, .. } = transition {
            return Err(reason);
        }

        // Advance revisions and convert reservation -> spent atomically
        for k in env.base_revisions.keys() {
            let cur = self.head_revision(k);
            self.head_revisions.insert(k.clone(), cur + 1);
        }
        if let Some(res) = self.reservations.remove(&env.effect_digest) {
            self.spent_minor_units = self.spent_minor_units.saturating_add(res.amount);
        }
        self.authoritative_token = self.authoritative_token.saturating_add(1);
        Ok(self.authoritative_token)
    }
}

/// Parsed and validated non-proxy Greenlane SHIP-CONTRACT.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ShipContract {
    pub accept_url: String,
    pub optimus_metric: String,
    pub failure_classes: Vec<String>,
    pub debug_pack: String,
}

impl ShipContract {
    pub fn parse(raw: &str) -> Result<Self, GateError> {
        let mut has_header = false;
        let mut accept_url: Option<String> = None;
        let mut optimus_metric: Option<String> = None;
        let mut failure_classes: Vec<String> = Vec::new();
        let mut debug_pack: Option<String> = None;

        for line in raw.lines() {
            let t = line.trim();
            if t == "SHIP-CONTRACT" {
                has_header = true;
            } else if let Some(rest) = t.strip_prefix("accept:") {
                let parts: Vec<&str> = rest.split_whitespace().collect();
                if parts.len() == 6
                    && parts[0] == "GET"
                    && parts[2] == "expect"
                    && parts[3] == "200"
                    && parts[4] == "within"
                    && parts[5].ends_with('m')
                {
                    let url = parts[1].to_string();
                    if is_proxy_green_url(&url) {
                        return Err(GateError::ProxyGreenSubstitution { url });
                    }
                    accept_url = Some(url);
                } else {
                    return Err(GateError::InvalidShipContract {
                        reason: "malformed accept: line".to_string(),
                    });
                }
            } else if let Some(rest) = t.strip_prefix("optimus:") {
                let parts: Vec<&str> = rest.split_whitespace().collect();
                if parts.len() == 3
                    && parts[1].starts_with("baseline=")
                    && parts[2].starts_with("target=")
                {
                    optimus_metric = Some(parts[0].to_string());
                } else {
                    return Err(GateError::InvalidShipContract {
                        reason: "malformed optimus: line".to_string(),
                    });
                }
            } else if let Some(rest) = t.strip_prefix("failure-classes:") {
                failure_classes = rest
                    .split(',')
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
                    .collect();
            } else if let Some(rest) = t.strip_prefix("debug-pack:") {
                let dp = rest.trim();
                if dp.starts_with("DBG-") && dp.len() >= 5 {
                    debug_pack = Some(dp.to_string());
                }
            }
        }

        if !has_header {
            return Err(GateError::InvalidShipContract {
                reason: "missing SHIP-CONTRACT header".to_string(),
            });
        }
        let accept_url = accept_url.ok_or_else(|| GateError::InvalidShipContract {
            reason: "missing accept: line".to_string(),
        })?;
        let optimus_metric = optimus_metric.ok_or_else(|| GateError::InvalidShipContract {
            reason: "missing optimus: line".to_string(),
        })?;
        if failure_classes.is_empty() {
            return Err(GateError::InvalidShipContract {
                reason: "missing failure-classes: line".to_string(),
            });
        }
        let debug_pack = debug_pack.ok_or_else(|| GateError::InvalidShipContract {
            reason: "missing debug-pack: DBG-NNN line".to_string(),
        })?;

        Ok(Self {
            accept_url,
            optimus_metric,
            failure_classes,
            debug_pack,
        })
    }
}

/// Protected enforcement path matcher + Founder Ed25519 seal verification (B10).
const PROTECTED_PREFIXES: &[&str] = &[
    "crates/mitp-core/",
    "crates/genesis-kernel/",
    "crates/meridian-gate/",
    ".github/workflows/",
    "bin/claim-gate",
    "bin/estate-gate",
];

pub fn path_matches_claim_pattern(path: &str, pattern: &str) -> bool {
    let p = path.trim_start_matches("./");
    let pat = pattern.trim().trim_start_matches("./");
    if let Some(prefix) = pat.strip_suffix("/**") {
        p == prefix || p.starts_with(&format!("{prefix}/"))
    } else {
        p == pat
    }
}

pub fn is_protected_path(path: &str) -> bool {
    let p = path.trim_start_matches("./");
    PROTECTED_PREFIXES
        .iter()
        .any(|pref| p == pref.trim_end_matches('/') || p.starts_with(pref))
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FounderSeal {
    pub founder_pubkey_hex: String,
    pub reason: String,
    pub file_hashes: BTreeMap<String, String>,
    pub signature_hex: String,
}

impl FounderSeal {
    pub fn canonical_message(&self) -> Vec<u8> {
        let mut h = Sha256::new();
        h.update(b"MERIDIAN-FOUNDER-SEAL-V1|");
        h.update(self.reason.as_bytes());
        for (path, digest) in &self.file_hashes {
            h.update(b"|");
            h.update(path.as_bytes());
            h.update(b"=");
            h.update(digest.as_bytes());
        }
        h.finalize().to_vec()
    }
}

pub fn check_diff_scope_and_seal(
    changed_files: &BTreeMap<String, String>,
    claimed_patterns: &[String],
    trusted_founder_pubkey_hex: &str,
    seal: Option<&FounderSeal>,
) -> Result<(), GateError> {
    let mut protected_touched: Vec<String> = Vec::new();
    for path in changed_files.keys() {
        if !claimed_patterns.iter().any(|pat| path_matches_claim_pattern(path, pat)) {
            return Err(GateError::ScopeViolation { path: path.clone() });
        }
        if is_protected_path(path) {
            protected_touched.push(path.clone());
        }
    }

    if !protected_touched.is_empty() {
        let s = seal.ok_or_else(|| GateError::MissingFounderSeal {
            path: protected_touched[0].clone(),
        })?;
        if !s.founder_pubkey_hex.eq_ignore_ascii_case(trusted_founder_pubkey_hex) {
            return Err(GateError::MissingFounderSeal {
                path: protected_touched[0].clone(),
            });
        }
        for p in &protected_touched {
            let expected = changed_files.get(p);
            let sealed = s.file_hashes.get(p);
            if expected.is_none() || expected != sealed {
                return Err(GateError::MissingFounderSeal { path: p.clone() });
            }
        }
        let msg = s.canonical_message();
        verify_ed25519_strict(&s.founder_pubkey_hex, &msg, &s.signature_hex)
            .map_err(|_| GateError::MissingFounderSeal {
                path: protected_touched[0].clone(),
            })?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::{Signer, SigningKey};

    fn test_keys() -> (SigningKey, SigningKey, SigningKey) {
        let certifier = SigningKey::from_bytes(&[0x11; 32]);
        let worker = SigningKey::from_bytes(&[0x22; 32]);
        let founder = SigningKey::from_bytes(&[0x33; 32]);
        (certifier, worker, founder)
    }

    fn base_kernel() -> (DeterministicKernel, SigningKey, SigningKey, SigningKey) {
        let (certifier, worker, founder) = test_keys();
        let mandate = ParentMandate {
            root_h_digest: "h-root-001".to_string(),
            max_effect_class: EffectClass::C,
            allowed_billing_class: BillingClass::ApiCredit,
            policy_hash: "pol-v1".to_string(),
            currency: "GBP".to_string(),
            budget_ceiling_minor_units: 50_000,
        };
        let lanes = vec![
            ProviderLane {
                lane_id: "deepseek-api".to_string(),
                billing_class: BillingClass::ApiCredit,
                health: LaneHealth::Fit,
                fitness_expires_at_utc: 2_000,
            },
            ProviderLane {
                lane_id: "claude-sub".to_string(),
                billing_class: BillingClass::MonthlySubscription,
                health: LaneHealth::Fit,
                fitness_expires_at_utc: 2_000,
            },
            ProviderLane {
                lane_id: "glm-dead".to_string(),
                billing_class: BillingClass::ApiCredit,
                health: LaneHealth::Exhausted,
                fitness_expires_at_utc: 2_000,
            },
        ];
        let k = DeterministicKernel::new(
            mandate,
            lanes,
            vec![hex::encode(certifier.verifying_key().to_bytes())],
            vec![hex::encode(worker.verifying_key().to_bytes())],
        );
        (k, certifier, worker, founder)
    }

    fn sample_env(id: &str, path: &str, cost: i64, nonce: &str) -> EffectEnvelope {
        let mut writes = BTreeSet::new();
        writes.insert(ResourceKey::RepoPath {
            repo: "chidionyema/idp".to_string(),
            path_prefix: path.to_string(),
        });
        EffectEnvelope {
            instruction_id: id.to_string(),
            attempt_id: "att-1".to_string(),
            effect_digest: format!("eff-{id}"),
            parent_m_digest: "m-1".to_string(),
            root_h_digest: "h-root-001".to_string(),
            policy_hash: "pol-v1".to_string(),
            objective_hash: "obj-1".to_string(),
            acceptance_predicate_hash: "pred-1".to_string(),
            lane_id: "deepseek-api".to_string(),
            requested_billing_class: BillingClass::ApiCredit,
            class: EffectClass::I,
            monotonicity: Monotonicity::Monotonic,
            footprint: Footprint {
                reads: BTreeSet::new(),
                writes,
            },
            cost_minor_units: cost,
            currency: "GBP".to_string(),
            revocation_epoch: 1,
            fencing_token: 1,
            base_revisions: BTreeMap::new(),
            nonce_hex: nonce.to_string(),
            verification_deadline_utc: 1_500,
            requested_reserved_power: None,
        }
    }

    fn sign_receipt(env: &EffectEnvelope, sk: &SigningKey, url: &str) -> VerifierReceipt {
        let mut r = VerifierReceipt {
            instruction_id: env.instruction_id.clone(),
            attempt_id: env.attempt_id.clone(),
            execution_epoch: env.revocation_epoch,
            objective_hash: env.objective_hash.clone(),
            acceptance_predicate_hash: env.acceptance_predicate_hash.clone(),
            target_identity: "idp-main".to_string(),
            artifact_digest: "sha256:abc123".to_string(),
            observed_at_utc: 1_100,
            evidence_expires_utc: 1_900,
            observation_url: url.to_string(),
            verifier_pubkey_hex: hex::encode(sk.verifying_key().to_bytes()),
            policy_hash: env.policy_hash.clone(),
            signature_hex: String::new(),
        };
        let sig = sk.sign(&r.canonical_message());
        r.signature_hex = hex::encode(sig.to_bytes());
        r
    }

    #[test]
    fn e01_valid_disjoint_monotonic_parallel_admit() {
        let (mut k, _, _, _) = base_kernel();
        let e1 = sample_env("INS-1", "crates/mitp-core/src/a.rs", 10_000, "0001000200030004");
        let e2 = sample_env("INS-2", "crates/mitp-core/src/b.rs", 15_000, "0005000600070008");
        assert!(!e1.footprint.conflicts_with(&e2.footprint));
        assert_eq!(k.admit_effect(&e1, 1_000), Ok(1));
        assert_eq!(k.admit_effect(&e2, 1_000), Ok(1));
        assert_eq!(k.total_reserved(), 25_000);
    }

    #[test]
    fn e02_empty_instruction_id_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let e = sample_env("   ", "crates/a.rs", 100, "1001000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::MissingInstructionId));
    }

    #[test]
    fn e03_unbounded_or_traversal_footprint_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let mut e = sample_env("INS-3", "**", 100, "2001000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::UnboundedFootprint));
        e.footprint.writes.clear();
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::UnboundedFootprint));
        e.footprint.writes.insert(ResourceKey::RepoPath {
            repo: "chidionyema/idp".to_string(),
            path_prefix: "../etc/passwd".to_string(),
        });
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::UnboundedFootprint));
    }

    #[test]
    fn e04_cross_class_billing_substitution_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let mut e = sample_env("INS-4", "crates/a.rs", 100, "3001000200030004");
        e.lane_id = "claude-sub".to_string();
        assert!(matches!(
            k.admit_effect(&e, 1_000),
            Err(GateError::CrossClassSubstitution { .. })
        ));
    }

    #[test]
    fn e05_exhausted_or_stale_provider_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let mut e = sample_env("INS-5", "crates/a.rs", 100, "4001000200030004");
        e.lane_id = "glm-dead".to_string();
        assert!(matches!(
            k.admit_effect(&e, 1_000),
            Err(GateError::ProviderIneligible { .. })
        ));
        e.lane_id = "deepseek-api".to_string();
        assert!(matches!(
            k.admit_effect(&e, 2_500),
            Err(GateError::ProviderIneligible { .. })
        ));
    }

    #[test]
    fn e06_atomic_escrow_overspend_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let e1 = sample_env("INS-6A", "crates/a.rs", 40_000, "5001000200030004");
        let e2 = sample_env("INS-6B", "crates/b.rs", 10_001, "5005000600070008");
        assert_eq!(k.admit_effect(&e1, 1_000), Ok(1));
        assert_eq!(
            k.admit_effect(&e2, 1_000),
            Err(GateError::InsufficientEscrow {
                requested: 10_001,
                available: 10_000
            })
        );
        assert_eq!(k.total_reserved(), 40_000);
    }

    #[test]
    fn e07_negative_or_overflow_cost_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let e1 = sample_env("INS-7A", "crates/a.rs", -1, "6001000200030004");
        assert_eq!(k.admit_effect(&e1, 1_000), Err(GateError::InvalidCost { cost: -1 }));
        let e_seed = sample_env("INS-7S", "crates/s.rs", 100, "6002000200030004");
        assert_eq!(k.admit_effect(&e_seed, 1_000), Ok(1));
        let e2 = sample_env("INS-7B", "crates/a.rs", i64::MAX, "6005000600070008");
        assert_eq!(k.admit_effect(&e2, 1_000), Err(GateError::InvalidCost { cost: i64::MAX }));
    }

    #[test]
    fn e08_currency_mismatch_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let mut e = sample_env("INS-8", "crates/a.rs", 100, "7001000200030004");
        e.currency = "USD".to_string();
        assert!(matches!(
            k.admit_effect(&e, 1_000),
            Err(GateError::CurrencyMismatch { .. })
        ));
    }

    #[test]
    fn e09_replay_nonce_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let e1 = sample_env("INS-9A", "crates/a.rs", 100, "8001000200030004");
        let e2 = sample_env("INS-9B", "crates/b.rs", 100, "8001000200030004");
        assert_eq!(k.admit_effect(&e1, 1_000), Ok(1));
        assert_eq!(k.admit_effect(&e2, 1_000), Err(GateError::ReplayNonceDetected));
    }

    #[test]
    fn e10_revocation_fences_stale_epoch_and_drains_escrow() {
        let (mut k, cert, _, _) = base_kernel();
        let e = sample_env("INS-10", "crates/a.rs", 12_000, "9001000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Ok(1));
        let receipt = sign_receipt(&e, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(k.commit_revocation(), Ok(2));
        assert_eq!(
            k.promote_occ(&e, &receipt, 1_100),
            Err(GateError::StaleRevocationEpoch { got: 1, current: 2 })
        );
        assert_eq!(k.drain_fenced_escrow(&e.effect_digest), Ok(12_000));
        assert_eq!(k.total_reserved(), 0);
    }

    #[test]
    fn e11_stale_fencing_token_rejected() {
        let (mut k, _, _, _) = base_kernel();
        k.authoritative_token = 5;
        let e = sample_env("INS-11", "crates/a.rs", 100, "a001000200030004");
        assert_eq!(
            k.admit_effect(&e, 1_000),
            Err(GateError::StaleFencingToken {
                got: 1,
                authoritative: 5
            })
        );
    }

    #[test]
    fn e12_occ_revision_conflict_preserves_escrow() {
        let (mut k, cert, _, _) = base_kernel();
        k.set_head_revision("idp:fence.rs", 7);
        let mut t3 = sample_env("INS-12A", "crates/fence.rs", 10_000, "b001000200030004");
        let mut t4 = sample_env("INS-12B", "crates/fence.rs", 10_000, "b005000600070008");
        t3.base_revisions.insert("idp:fence.rs".to_string(), 7);
        t4.base_revisions.insert("idp:fence.rs".to_string(), 7);
        assert_eq!(k.admit_effect(&t3, 1_000), Ok(1));
        assert_eq!(k.admit_effect(&t4, 1_000), Ok(1));
        let r3 = sign_receipt(&t3, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(k.promote_occ(&t3, &r3, 1_100), Ok(2));
        t4.fencing_token = 2;
        let r4 = sign_receipt(&t4, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(
            k.promote_occ(&t4, &r4, 1_100),
            Err(GateError::OccRevisionConflict {
                key: "idp:fence.rs".to_string(),
                expected: 7,
                actual: 8
            })
        );
        assert_eq!(k.spent_minor_units, 10_000);
        assert_eq!(k.total_reserved(), 10_000);
    }

    #[test]
    fn e13_authority_and_reserved_power_escalation_rejected() {
        let (mut k, _, _, _) = base_kernel();
        let mut e = sample_env("INS-13A", "crates/a.rs", 100, "c001000200030004");
        e.class = EffectClass::P;
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::AuthorityEscalation));
        e.class = EffectClass::I;
        e.requested_reserved_power = Some(ReservedPower::RaiseParentBudget);
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::AuthorityEscalation));
    }

    #[test]
    fn e14_ring3_to_external_taint_blocked() {
        let (mut k, _, _, _) = base_kernel();
        let mut e = sample_env("INS-14", "crates/a.rs", 100, "d001000200030004");
        e.footprint.reads.insert(ResourceKey::RingScope {
            ring: 3,
            namespace: "founder-private".to_string(),
        });
        e.footprint.writes.insert(ResourceKey::ExternalSink {
            sink_id: "public-webhook".to_string(),
            idempotency_key: "k1".to_string(),
        });
        assert_eq!(k.admit_effect(&e, 1_000), Err(GateError::TaintViolation));
    }

    #[test]
    fn e15_valid_ed25519_settlement_before_deadline() {
        let (mut k, cert, _, _) = base_kernel();
        let e = sample_env("INS-15", "crates/a.rs", 5_000, "e001000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Ok(1));
        let r = sign_receipt(&e, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(k.promote_occ(&e, &r, 1_200), Ok(2));
        assert_eq!(k.spent_minor_units, 5_000);
        assert_eq!(k.total_reserved(), 0);
    }

    #[test]
    fn e16_deadline_expiry_forces_recovery_no_indefinite_wait() {
        let (mut k, cert, _, _) = base_kernel();
        let e = sample_env("INS-16", "crates/a.rs", 1_000, "f001000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Ok(1));
        let r = sign_receipt(&e, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(
            k.promote_occ(&e, &r, 1_501),
            Err(GateError::VerificationDeadlineExpired {
                now_utc: 1_501,
                deadline_utc: 1_500
            })
        );
    }

    #[test]
    fn e17_tampered_ed25519_receipt_rejected() {
        let (mut k, cert, _, _) = base_kernel();
        let e = sample_env("INS-17", "crates/a.rs", 1_000, "1101000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Ok(1));
        let mut r = sign_receipt(&e, &cert, "https://llm.meridianlabs.cloud/health");
        r.artifact_digest = "sha256:tampered".to_string();
        assert_eq!(k.promote_occ(&e, &r, 1_200), Err(GateError::InvalidCertifierSignature));
    }

    #[test]
    fn e18_worker_self_certification_rejected() {
        let (mut k, _, worker, _) = base_kernel();
        let e = sample_env("INS-18", "crates/a.rs", 1_000, "1201000200030004");
        assert_eq!(k.admit_effect(&e, 1_000), Ok(1));
        let r = sign_receipt(&e, &worker, "https://llm.meridianlabs.cloud/health");
        assert_eq!(k.promote_occ(&e, &r, 1_200), Err(GateError::SelfCertificationForbidden));
    }

    #[test]
    fn e19_and_e20_ship_contract_rejects_proxy_green_and_accepts_live() {
        let bad = "SHIP-CONTRACT\naccept: GET https://raw.githubusercontent.com/chidionyema/idp/main/README.md expect 200 within 30m\noptimus: k.m baseline=0 target=1\nfailure-classes: x\ndebug-pack: DBG-001\n";
        assert!(matches!(
            ShipContract::parse(bad),
            Err(GateError::ProxyGreenSubstitution { .. })
        ));
        let good = "SHIP-CONTRACT\naccept: GET https://llm.meridianlabs.cloud/health expect 200 within 30m\noptimus: kernel.rust_invariant_gate_enforced baseline=0 target=1\nfailure-classes: agent-invariant-bypass\ndebug-pack: DBG-001\n";
        let sc = ShipContract::parse(good).expect("valid non-proxy ship contract");
        assert_eq!(sc.accept_url, "https://llm.meridianlabs.cloud/health");
    }

    #[test]
    fn e21_and_e22_scope_violation_and_founder_ed25519_seal() {
        let (_, _, founder) = test_keys();
        let founder_pk = hex::encode(founder.verifying_key().to_bytes());
        let claims = vec!["crates/mitp-core/**".to_string()];

        let mut out_of_scope = BTreeMap::new();
        out_of_scope.insert("bin/unrelated.py".to_string(), "sha256:111".to_string());
        assert_eq!(
            check_diff_scope_and_seal(&out_of_scope, &claims, &founder_pk, None),
            Err(GateError::ScopeViolation {
                path: "bin/unrelated.py".to_string()
            })
        );

        let mut protected = BTreeMap::new();
        protected.insert("crates/mitp-core/src/lib.rs".to_string(), "sha256:222".to_string());
        assert_eq!(
            check_diff_scope_and_seal(&protected, &claims, &founder_pk, None),
            Err(GateError::MissingFounderSeal {
                path: "crates/mitp-core/src/lib.rs".to_string()
            })
        );

        let mut seal = FounderSeal {
            founder_pubkey_hex: founder_pk.clone(),
            reason: "Authorized kernel hardening".to_string(),
            file_hashes: protected.clone(),
            signature_hex: String::new(),
        };
        let sig = founder.sign(&seal.canonical_message());
        seal.signature_hex = hex::encode(sig.to_bytes());
        assert_eq!(
            check_diff_scope_and_seal(&protected, &claims, &founder_pk, Some(&seal)),
            Ok(())
        );
    }

    #[test]
    fn e23_duplicate_settlement_rejected() {
        let (mut k, cert, _, _) = base_kernel();
        let e1 = sample_env("INS-23", "crates/a.rs", 500, "1301000200030004");
        let e2 = sample_env("INS-23", "crates/b.rs", 500, "1305000600070008");
        assert_eq!(k.admit_effect(&e1, 1_000), Ok(1));
        let r1 = sign_receipt(&e1, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(k.promote_occ(&e1, &r1, 1_100), Ok(2));
        let mut e2_tok = e2;
        e2_tok.fencing_token = 2;
        assert_eq!(k.admit_effect(&e2_tok, 1_100), Ok(2));
        let r2 = sign_receipt(&e2_tok, &cert, "https://llm.meridianlabs.cloud/health");
        assert_eq!(
            k.promote_occ(&e2_tok, &r2, 1_200),
            Err(GateError::AlreadySettled {
                instruction_id: "INS-23".to_string()
            })
        );
    }
}
