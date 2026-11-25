//! MITP Plane 2 -> Plane 3 Deterministic Hysteresis Switching Gate
//!
//! Strictly mirrors `MITPHysteresisGate.tla`:
//! - Integer-only fixed-point arithmetic (zero IEEE-754 floats on the CP path)
//! - Dual hysteresis: value deadband + effect-class inertia + confirmation persistence + min dwell
//! - Structural Class P non-pre-emption once past the sink commit fence (`DispatchedP`)
//! - Strict atomic single-currency escrow conservation across Fast Path and Pinned Drain Path
//! - `ReservedSlots` counts `Active`, `DispatchedP`, AND `PendingDrain` to prevent lane theft
//! - Fail-closed on stale proposals (`now > computed_at_ms + staleness_ttl_ms`) and unknown constraints

use std::collections::{BTreeMap, BTreeSet};

/// Fixed-point priority density in signed micro-units (1_000_000 = 1.0).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PriorityMicros(pub i64);

impl PriorityMicros {
    #[inline]
    pub const fn saturating_sub(self, rhs: Self) -> Self {
        Self(self.0.saturating_sub(rhs.0))
    }

    #[inline]
    pub const fn saturating_add(self, rhs: Self) -> Self {
        Self(self.0.saturating_add(rhs.0))
    }
}

/// MITP four-class effect taxonomy (never treat reads/inference as effect-free).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum EffectClass {
    /// Class R: Epistemic / Read and Inference
    ReadEpistemic,
    /// Class I: Internal Reversible
    InternalReversible,
    /// Class C: External Compensatable (requires pre-registered Saga compensator)
    ExternalCompensatable,
    /// Class P: External Pivot / Irreversible (non-pre-emptible once dispatched)
    ExternalPivot,
}

/// Lifecycle state matching `MITPHysteresisGate.tla`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum EnvelopeState {
    Staged,
    Active,
    DispatchedP,
    PendingDrain,
    Quarantined,
    Reconciled,
    Settled,
}

pub type Digest32 = [u8; 32];

/// Untrusted advisory signal emitted by Plane 2 (RFC 8785 JCS canonicalised at ingress).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ValuationProposal {
    pub target_envelope_digest: Digest32,
    pub parent_mandate_digest: Digest32,
    pub priority: PriorityMicros,
    pub est_compensation_minor: u64,
    pub computed_at_ms: u64,
    pub staleness_ttl_ms: u64,
    pub provenance_digest: Digest32,
    /// Fail-closed guard: any unsupported policy/constraint tag forces immediate refusal.
    pub unsupported_constraints: bool,
}

impl ValuationProposal {
    #[inline]
    pub fn is_fresh(&self, now_ms: u64) -> bool {
        match self.computed_at_ms.checked_add(self.staleness_ttl_ms) {
            Some(deadline) => now_ms >= self.computed_at_ms && now_ms <= deadline,
            None => false,
        }
    }
}

/// Static constitutional/domain policy enforced inside Plane 3 (`AuthoritySequencer`).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HysteresisPolicy {
    pub max_active_slots: usize,
    pub admit_floor: PriorityMicros,
    pub base_deadband: PriorityMicros,
    pub confirm_window_ms: u64,
    pub min_dwell_ms: u64,
    pub class_inertia_r: PriorityMicros,
    pub class_inertia_i: PriorityMicros,
    pub class_inertia_c: PriorityMicros,
    pub class_inertia_p_pre_dispatch: PriorityMicros,
}

impl HysteresisPolicy {
    #[inline]
    pub const fn inertia_for(&self, class: EffectClass) -> PriorityMicros {
        match class {
            EffectClass::ReadEpistemic => self.class_inertia_r,
            EffectClass::InternalReversible => self.class_inertia_i,
            EffectClass::ExternalCompensatable => self.class_inertia_c,
            EffectClass::ExternalPivot => self.class_inertia_p_pre_dispatch,
        }
    }

    pub fn validate(&self) -> Result<(), GateError> {
        if self.max_active_slots == 0 {
            return Err(GateError::InvalidPolicy("max_active_slots must be >= 1"));
        }
        if self.min_dwell_ms == 0 {
            return Err(GateError::InvalidPolicy("min_dwell_ms must be >= 1"));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EnvelopeRecord {
    pub digest: Digest32,
    pub parent_mandate_digest: Digest32,
    pub effect_class: EffectClass,
    pub cost_minor: u64,
    pub state: EnvelopeState,
    pub latest_proposal: Option<ValuationProposal>,
    pub admitted_at_ms: u64,
    pub reserved_minor: u64,
    pub quarantined_minor: u64,
    pub pinned_to: Option<Digest32>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SwitchingDecision {
    HoldCurrent,
    RejectStaleProposal,
    SurfaceTrustedSummaryCard { staged_digest: Digest32 },
    AdmitFromHeadroom { challenger_digest: Digest32 },
    PreemptAndDrain {
        incumbent_digest: Digest32,
        challenger_digest: Digest32,
        next_revocation_epoch: u64,
        quarantined_escrow_minor: u64,
        fast_path_admitted: bool,
    },
    FailClosedUnknownConstraint,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum GateError {
    InvalidPolicy(&'static str),
    InvalidCeiling,
    UnknownEnvelope(Digest32),
    DuplicateEnvelope(Digest32),
    InvalidCost,
    TimeRegression { current_ms: u64, requested_ms: u64 },
    InvalidStateTransition(&'static str),
    SpendExceedsLockedEscrow { spend: u64, locked: u64 },
    NotClassP(Digest32),
}

/// Pure deterministic single-writer `AuthoritySequencer` state machine for one parent mandate `H`.
#[derive(Clone, Debug)]
pub struct HysteresisSequencer {
    pub mandate_digest: Digest32,
    pub policy: HysteresisPolicy,
    pub ceiling_minor: u64,
    pub now_ms: u64,
    pub revocation_epoch: u64,
    pub free_minor: u64,
    pub spent_minor: u64,
    pub envelopes: BTreeMap<Digest32, EnvelopeRecord>,
    /// Confirmation start timestamps for `(challenger, incumbent)` pairs.
    pub confirm_start_ms: BTreeMap<(Digest32, Digest32), u64>,
    /// Ghost audit set matching TLA+ `everDispatchedP`.
    pub ever_dispatched_p: BTreeSet<Digest32>,
    /// Count of priority-driven pre-emptions for chattering bound verification.
    pub priority_switches: u64,
}

impl HysteresisSequencer {
    pub fn new(
        mandate_digest: Digest32,
        ceiling_minor: u64,
        policy: HysteresisPolicy,
    ) -> Result<Self, GateError> {
        policy.validate()?;
        if ceiling_minor == 0 {
            return Err(GateError::InvalidCeiling);
        }
        Ok(Self {
            mandate_digest,
            policy,
            ceiling_minor,
            now_ms: 0,
            revocation_epoch: 0,
            free_minor: ceiling_minor,
            spent_minor: 0,
            envelopes: BTreeMap::new(),
            confirm_start_ms: BTreeMap::new(),
            ever_dispatched_p: BTreeSet::new(),
            priority_switches: 0,
        })
    }

    pub fn register_staged_envelope(
        &mut self,
        digest: Digest32,
        parent_mandate_digest: Digest32,
        effect_class: EffectClass,
        cost_minor: u64,
    ) -> Result<(), GateError> {
        if self.envelopes.contains_key(&digest) {
            return Err(GateError::DuplicateEnvelope(digest));
        }
        if cost_minor == 0 || cost_minor > self.ceiling_minor {
            return Err(GateError::InvalidCost);
        }
        self.envelopes.insert(
            digest,
            EnvelopeRecord {
                digest,
                parent_mandate_digest,
                effect_class,
                cost_minor,
                state: EnvelopeState::Staged,
                latest_proposal: None,
                admitted_at_ms: 0,
                reserved_minor: 0,
                quarantined_minor: 0,
                pinned_to: None,
            },
        );
        Ok(())
    }

    /// Reserved lane slots include `Active`, `DispatchedP`, AND `PendingDrain`
    /// so no third envelope can steal a lane while a pinned challenger drains.
    pub fn reserved_slots(&self) -> usize {
        self.envelopes
            .values()
            .filter(|e| {
                matches!(
                    e.state,
                    EnvelopeState::Active
                        | EnvelopeState::DispatchedP
                        | EnvelopeState::PendingDrain
                )
            })
            .count()
    }

    pub fn advance_time(&mut self, next_now_ms: u64) -> Result<(), GateError> {
        if next_now_ms < self.now_ms {
            return Err(GateError::TimeRegression {
                current_ms: self.now_ms,
                requested_ms: next_now_ms,
            });
        }
        self.now_ms = next_now_ms;
        self.sync_confirm_timers();
        Ok(())
    }

    /// Plane 2 submits an untrusted, quantised valuation snapshot.
    pub fn submit_valuation(&mut self, proposal: ValuationProposal) -> Result<(), GateError> {
        let rec = self
            .envelopes
            .get_mut(&proposal.target_envelope_digest)
            .ok_or(GateError::UnknownEnvelope(proposal.target_envelope_digest))?;
        rec.latest_proposal = Some(proposal);
        self.sync_confirm_timers();
        Ok(())
    }

    fn raw_preempt_ready(&self, j_id: &Digest32, i_id: &Digest32) -> bool {
        let (Some(j), Some(i)) = (self.envelopes.get(j_id), self.envelopes.get(i_id)) else {
            return false;
        };
        if j.state != EnvelopeState::Staged || i.state != EnvelopeState::Active {
            return false;
        }
        if j.parent_mandate_digest != self.mandate_digest
            || i.parent_mandate_digest != self.mandate_digest
        {
            return false;
        }
        let (Some(pj), Some(pi)) = (&j.latest_proposal, &i.latest_proposal) else {
            return false;
        };
        if pj.unsupported_constraints || pi.unsupported_constraints {
            return false;
        }
        if !pj.is_fresh(self.now_ms) || !pi.is_fresh(self.now_ms) {
            return false;
        }
        if pj.priority < self.policy.admit_floor {
            return false;
        }
        let required_margin = self
            .policy
            .base_deadband
            .saturating_add(self.policy.inertia_for(i.effect_class));
        pj.priority.saturating_sub(pi.priority) >= required_margin
    }

    fn sync_confirm_timers(&mut self) {
        let ids: Vec<Digest32> = self.envelopes.keys().copied().collect();
        let mut next_timers = BTreeMap::new();
        for &j in &ids {
            for &i in &ids {
                if j == i {
                    continue;
                }
                if self.raw_preempt_ready(&j, &i) {
                    let start = self
                        .confirm_start_ms
                        .get(&(j, i))
                        .copied()
                        .unwrap_or(self.now_ms);
                    next_timers.insert((j, i), start);
                }
            }
        }
        self.confirm_start_ms = next_timers;
    }

    /// Evaluate and execute a deterministic admission or pre-emption switch for `challenger_id`.
    pub fn evaluate_and_apply_switch(
        &mut self,
        challenger_id: Digest32,
        incumbent_id: Option<Digest32>,
    ) -> Result<SwitchingDecision, GateError> {
        let j = self
            .envelopes
            .get(&challenger_id)
            .ok_or(GateError::UnknownEnvelope(challenger_id))?;

        if j.state != EnvelopeState::Staged {
            return Ok(SwitchingDecision::HoldCurrent);
        }

        let Some(pj) = j.latest_proposal.as_ref() else {
            return Ok(SwitchingDecision::RejectStaleProposal);
        };

        if pj.unsupported_constraints {
            return Ok(SwitchingDecision::FailClosedUnknownConstraint);
        }

        if !pj.is_fresh(self.now_ms) {
            return Ok(SwitchingDecision::RejectStaleProposal);
        }

        if pj.priority < self.policy.admit_floor {
            return Ok(SwitchingDecision::HoldCurrent);
        }

        // Mandate containment invariant: candidates outside active mandate H must escalate
        // to Trusted Summary Card for fresh human seal — never autonomous admission.
        if j.parent_mandate_digest != self.mandate_digest
            || pj.parent_mandate_digest != self.mandate_digest
        {
            return Ok(SwitchingDecision::SurfaceTrustedSummaryCard {
                staged_digest: challenger_id,
            });
        }

        let cost_j = j.cost_minor;

        // Path A: Direct headroom admission when lane and escrow headroom both exist.
        if incumbent_id.is_none() {
            if self.reserved_slots() < self.policy.max_active_slots && self.free_minor >= cost_j {
                self.free_minor -= cost_j;
                let j_mut = self.envelopes.get_mut(&challenger_id).unwrap();
                j_mut.state = EnvelopeState::Active;
                j_mut.reserved_minor = cost_j;
                j_mut.admitted_at_ms = self.now_ms;
                self.sync_confirm_timers();
                return Ok(SwitchingDecision::AdmitFromHeadroom {
                    challenger_digest: challenger_id,
                });
            }
            return Ok(SwitchingDecision::HoldCurrent);
        }

        // Path B: Hysteresis-gated pre-emption of a specific active incumbent.
        let i_id = incumbent_id.unwrap();
        if !self.envelopes.contains_key(&i_id) {
            return Err(GateError::UnknownEnvelope(i_id));
        }

        // Ensure no other challenger is already pinned to this incumbent.
        if self.envelopes.values().any(|e| e.pinned_to == Some(i_id)) {
            return Ok(SwitchingDecision::HoldCurrent);
        }

        if !self.raw_preempt_ready(&challenger_id, &i_id) {
            return Ok(SwitchingDecision::HoldCurrent);
        }

        let admitted_at_i = self.envelopes[&i_id].admitted_at_ms;
        if self.now_ms.saturating_sub(admitted_at_i) < self.policy.min_dwell_ms {
            return Ok(SwitchingDecision::HoldCurrent);
        }

        let Some(&confirm_started) = self.confirm_start_ms.get(&(challenger_id, i_id)) else {
            return Ok(SwitchingDecision::HoldCurrent);
        };
        if self.now_ms.saturating_sub(confirm_started) < self.policy.confirm_window_ms {
            return Ok(SwitchingDecision::HoldCurrent);
        }

        let quarantined_amount = self.envelopes[&i_id].reserved_minor;
        self.revocation_epoch += 1;
        self.priority_switches += 1;

        let fast_path = self.free_minor >= cost_j;
        if fast_path {
            self.free_minor -= cost_j;
            {
                let i_mut = self.envelopes.get_mut(&i_id).unwrap();
                i_mut.state = EnvelopeState::Quarantined;
                i_mut.reserved_minor = 0;
                i_mut.quarantined_minor = quarantined_amount;
            }
            {
                let j_mut = self.envelopes.get_mut(&challenger_id).unwrap();
                j_mut.state = EnvelopeState::Active;
                j_mut.reserved_minor = cost_j;
                j_mut.admitted_at_ms = self.now_ms;
            }
        } else {
            {
                let i_mut = self.envelopes.get_mut(&i_id).unwrap();
                i_mut.state = EnvelopeState::Quarantined;
                i_mut.reserved_minor = 0;
                i_mut.quarantined_minor = quarantined_amount;
            }
            {
                let j_mut = self.envelopes.get_mut(&challenger_id).unwrap();
                j_mut.state = EnvelopeState::PendingDrain;
                j_mut.pinned_to = Some(i_id);
            }
        }

        self.sync_confirm_timers();
        Ok(SwitchingDecision::PreemptAndDrain {
            incumbent_digest: i_id,
            challenger_digest: challenger_id,
            next_revocation_epoch: self.revocation_epoch,
            quarantined_escrow_minor: quarantined_amount,
            fast_path_admitted: fast_path,
        })
    }

    /// Class P envelope crosses the irreversible external sink commit fence.
    pub fn dispatch_class_p(&mut self, id: Digest32) -> Result<(), GateError> {
        let rec = self
            .envelopes
            .get_mut(&id)
            .ok_or(GateError::UnknownEnvelope(id))?;
        if rec.effect_class != EffectClass::ExternalPivot {
            return Err(GateError::NotClassP(id));
        }
        if rec.state != EnvelopeState::Active {
            return Err(GateError::InvalidStateTransition(
                "only ACTIVE Class P envelopes may cross the sink fence",
            ));
        }
        rec.state = EnvelopeState::DispatchedP;
        self.ever_dispatched_p.insert(id);
        self.sync_confirm_timers();
        Ok(())
    }

    /// Reconcile a quarantined incumbent, book switching loss permanently, and atomically
    /// fund a pinned challenger if verified residual covers its cost.
    pub fn reconcile_quarantined(
        &mut self,
        incumbent_id: Digest32,
        actual_spend_minor: u64,
    ) -> Result<(), GateError> {
        let locked = {
            let rec = self
                .envelopes
                .get(&incumbent_id)
                .ok_or(GateError::UnknownEnvelope(incumbent_id))?;
            if rec.state != EnvelopeState::Quarantined {
                return Err(GateError::InvalidStateTransition(
                    "only QUARANTINED envelopes may reconcile",
                ));
            }
            rec.quarantined_minor
        };

        if actual_spend_minor > locked {
            return Err(GateError::SpendExceedsLockedEscrow {
                spend: actual_spend_minor,
                locked,
            });
        }

        let residual = locked - actual_spend_minor;
        let next_pool = self.free_minor + residual;

        let pinned_challenger = self
            .envelopes
            .values()
            .find(|e| e.pinned_to == Some(incumbent_id))
            .map(|e| e.digest);

        {
            let i_mut = self.envelopes.get_mut(&incumbent_id).unwrap();
            i_mut.state = EnvelopeState::Reconciled;
            i_mut.quarantined_minor = 0;
        }
        self.spent_minor += actual_spend_minor;

        if let Some(j_id) = pinned_challenger {
            let cost_j = self.envelopes[&j_id].cost_minor;
            if next_pool >= cost_j {
                self.free_minor = next_pool - cost_j;
                let j_mut = self.envelopes.get_mut(&j_id).unwrap();
                j_mut.state = EnvelopeState::Active;
                j_mut.reserved_minor = cost_j;
                j_mut.admitted_at_ms = self.now_ms;
                j_mut.pinned_to = None;
            } else {
                // Switching loss exhausted headroom: fail closed back to STAGED.
                self.free_minor = next_pool;
                let j_mut = self.envelopes.get_mut(&j_id).unwrap();
                j_mut.state = EnvelopeState::Staged;
                j_mut.pinned_to = None;
            }
        } else {
            self.free_minor = next_pool;
        }

        self.sync_confirm_timers();
        Ok(())
    }

    /// Normal settlement of an ACTIVE or DISPATCHED_P envelope.
    pub fn settle_active(
        &mut self,
        id: Digest32,
        actual_spend_minor: u64,
    ) -> Result<(), GateError> {
        let locked = {
            let rec = self
                .envelopes
                .get(&id)
                .ok_or(GateError::UnknownEnvelope(id))?;
            if !matches!(
                rec.state,
                EnvelopeState::Active | EnvelopeState::DispatchedP
            ) {
                return Err(GateError::InvalidStateTransition(
                    "only ACTIVE or DISPATCHED_P envelopes may settle",
                ));
            }
            rec.reserved_minor
        };

        if actual_spend_minor > locked {
            return Err(GateError::SpendExceedsLockedEscrow {
                spend: actual_spend_minor,
                locked,
            });
        }

        let residual = locked - actual_spend_minor;
        {
            let rec = self.envelopes.get_mut(&id).unwrap();
            rec.state = EnvelopeState::Settled;
            rec.reserved_minor = 0;
        }
        self.spent_minor += actual_spend_minor;
        self.free_minor += residual;
        self.sync_confirm_timers();
        Ok(())
    }

    /// Re-stage a reconciled envelope (used in adversarial ping-pong chattering tests).
    pub fn restage_reconciled(&mut self, id: Digest32) -> Result<(), GateError> {
        let rec = self
            .envelopes
            .get_mut(&id)
            .ok_or(GateError::UnknownEnvelope(id))?;
        if rec.state != EnvelopeState::Reconciled {
            return Err(GateError::InvalidStateTransition(
                "only RECONCILED envelopes may be re-staged",
            ));
        }
        rec.state = EnvelopeState::Staged;
        self.sync_confirm_timers();
        Ok(())
    }

    /// Runtime assertion of all five TLA+ safety invariants (mirrors `MITPHysteresisGate.tla`).
    pub fn assert_invariants(&self) {
        // 1. EscrowConservation
        let sum_reserved: u64 = self.envelopes.values().map(|e| e.reserved_minor).sum();
        let sum_quarantined: u64 = self.envelopes.values().map(|e| e.quarantined_minor).sum();
        assert_eq!(
            self.free_minor + self.spent_minor + sum_reserved + sum_quarantined,
            self.ceiling_minor,
            "EscrowConservation violated"
        );
        for e in self.envelopes.values() {
            assert!(
                !(e.reserved_minor > 0 && e.quarantined_minor > 0),
                "EscrowConservation dual-bucket violation"
            );
        }

        // 2. EscrowStateBinding
        for e in self.envelopes.values() {
            match e.state {
                EnvelopeState::Staged
                | EnvelopeState::PendingDrain
                | EnvelopeState::Reconciled
                | EnvelopeState::Settled => {
                    assert_eq!(e.reserved_minor, 0, "EscrowStateBinding reserved != 0");
                    assert_eq!(e.quarantined_minor, 0, "EscrowStateBinding quarantined != 0");
                }
                EnvelopeState::Active | EnvelopeState::DispatchedP => {
                    assert_eq!(e.reserved_minor, e.cost_minor, "EscrowStateBinding active cost");
                    assert_eq!(e.quarantined_minor, 0, "EscrowStateBinding active quarantined");
                }
                EnvelopeState::Quarantined => {
                    assert_eq!(e.reserved_minor, 0, "EscrowStateBinding quarantined reserved");
                    assert_eq!(
                        e.quarantined_minor, e.cost_minor,
                        "EscrowStateBinding quarantined cost"
                    );
                }
            }
        }

        // 3. ClassPNonPreemptible
        for id in &self.ever_dispatched_p {
            let e = &self.envelopes[id];
            assert_eq!(e.effect_class, EffectClass::ExternalPivot);
            assert!(
                matches!(e.state, EnvelopeState::DispatchedP | EnvelopeState::Settled),
                "ClassPNonPreemptible violated: {:?}",
                e.state
            );
        }

        // 4. PinnedDrainSafety
        assert!(
            self.reserved_slots() <= self.policy.max_active_slots,
            "PinnedDrainSafety slot cap violated: {} > {}",
            self.reserved_slots(),
            self.policy.max_active_slots
        );
        for e in self.envelopes.values() {
            if e.state == EnvelopeState::PendingDrain {
                let target = e.pinned_to.expect("PendingDrain must have pinned_to");
                assert_eq!(
                    self.envelopes[&target].state,
                    EnvelopeState::Quarantined,
                    "PinnedDrainSafety target must be QUARANTINED"
                );
                assert_eq!(e.reserved_minor, 0, "PinnedDrainSafety challenger holds escrow");
            }
        }

        // 5. BoundedPriorityChattering
        let max_switches =
            (self.policy.max_active_slots as u64) * (self.now_ms / self.policy.min_dwell_ms);
        assert!(
            self.priority_switches <= max_switches,
            "BoundedPriorityChattering violated: {} > {}",
            self.priority_switches,
            max_switches
        );
    }
}
