//! Engine 4: Linearizable Edge Authority (`BudgetLedgerDO` + `RoutingStateDO`).
//!
//! Replaces split-brain local `pennyd` (`budgets.json` seq races + broken WAL) with one
//! single-writer minor-unit escrow ledger and signed `estate.lane-fitness.v1` routing table.

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BillingClass {
    MonthlySubscription,
    ApiCredit,
    FreeAllowance,
    FounderAuthorisedException,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum LaneStatus {
    Fit,
    Unfit,
    Drained,
}

/// Signed `estate.lane-fitness.v1` record stored in `RoutingStateDO` and exported to `--fitness-dir`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct LaneFitnessRecord {
    pub schema: String,
    pub lane_id: String,
    pub provider: String,
    pub model: String,
    pub secret_env: String,
    pub billing_class: BillingClass,
    pub status: LaneStatus,
    pub checked_at_utc: u64,
    pub expires_at_utc: u64,
    pub p99_ms: u32,
    pub golden_pass: bool,
    pub reason: String,
    pub signer_pubkey_hex: String,
    pub signature_hex: String,
}

impl LaneFitnessRecord {
    pub const SCHEMA_V1: &'static str = "estate.lane-fitness.v1";

    pub fn canonical_bytes(&self) -> Vec<u8> {
        let payload = format!(
            "{}|{}|{}|{}|{}|{:?}|{:?}|{}|{}|{}|{}|{}",
            self.schema,
            self.lane_id,
            self.provider,
            self.model,
            self.secret_env,
            self.billing_class,
            self.status,
            self.checked_at_utc,
            self.expires_at_utc,
            self.p99_ms,
            self.golden_pass,
            self.reason,
        );
        let mut h = Sha256::new();
        h.update(payload.as_bytes());
        h.finalize().to_vec()
    }

    pub fn sign(&mut self, sk: &SigningKey) {
        self.signer_pubkey_hex = hex::encode(sk.verifying_key().to_bytes());
        let sig = sk.sign(&self.canonical_bytes());
        self.signature_hex = hex::encode(sig.to_bytes());
    }

    pub fn verify_strict(&self, trusted_pubkeys_hex: &HashSet<String>) -> Result<(), LedgerError> {
        if self.schema != Self::SCHEMA_V1 {
            return Err(LedgerError::InvalidFitnessSignature);
        }
        if !trusted_pubkeys_hex.contains(&self.signer_pubkey_hex.to_ascii_lowercase()) {
            return Err(LedgerError::UntrustedFitnessSigner);
        }
        let pk_raw = hex::decode(&self.signer_pubkey_hex).map_err(|_| LedgerError::InvalidFitnessSignature)?;
        let pk_arr: [u8; 32] = pk_raw.try_into().map_err(|_| LedgerError::InvalidFitnessSignature)?;
        let vk = VerifyingKey::from_bytes(&pk_arr).map_err(|_| LedgerError::InvalidFitnessSignature)?;

        let sig_raw = hex::decode(&self.signature_hex).map_err(|_| LedgerError::InvalidFitnessSignature)?;
        let sig_arr: [u8; 64] = sig_raw.try_into().map_err(|_| LedgerError::InvalidFitnessSignature)?;
        let sig = Signature::from_bytes(&sig_arr);
        vk.verify_strict(&self.canonical_bytes(), &sig)
            .map_err(|_| LedgerError::InvalidFitnessSignature)
    }

    pub fn is_live_fit(&self, now_utc: u64) -> bool {
        self.status == LaneStatus::Fit && self.golden_pass && now_utc <= self.expires_at_utc
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ReservationState {
    Reserved,
    Committed,
    Released,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EscrowReservation {
    pub reservation_id: String,
    pub lane_id: String,
    pub billing_class: BillingClass,
    pub amount_minor_units: i64,
    pub currency: String,
    pub epoch: u64,
    pub fencing_token: u64,
    pub state: ReservationState,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "code", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum LedgerError {
    InvalidCost { cost: i64 },
    CurrencyMismatch { expected: String, got: String },
    CrossClassSubstitution { expected: BillingClass, got: BillingClass },
    InsufficientEscrow { requested: i64, available: i64 },
    ReplayNonceDetected { nonce: String },
    StaleEpoch { got: u64, current: u64 },
    StaleFencingToken { got: u64, authoritative: u64 },
    UnknownReservation { id: String },
    DuplicateReservation { id: String },
    InvalidStateTransition { id: String },
    UntrustedFitnessSigner,
    InvalidFitnessSignature,
}

/// Linearizable single-writer BudgetLedger (`BudgetLedgerDO` core).
#[derive(Clone, Debug)]
pub struct BudgetLedger {
    pub currency: String,
    pub allowed_billing_class: BillingClass,
    pub ceiling_minor_units: i64,
    pub spent_minor_units: i64,
    pub revocation_epoch: u64,
    pub fencing_token: u64,
    reservations: BTreeMap<String, EscrowReservation>,
    nonces: HashSet<String>,
}

impl BudgetLedger {
    pub fn new(currency: &str, allowed_billing_class: BillingClass, ceiling_minor_units: i64) -> Self {
        Self {
            currency: currency.to_string(),
            allowed_billing_class,
            ceiling_minor_units,
            spent_minor_units: 0,
            revocation_epoch: 1,
            fencing_token: 1,
            reservations: BTreeMap::new(),
            nonces: HashSet::new(),
        }
    }

    pub fn total_reserved(&self) -> i64 {
        self.reservations
            .values()
            .filter(|r| r.state == ReservationState::Reserved)
            .map(|r| r.amount_minor_units)
            .sum()
    }

    pub fn available_minor_units(&self) -> i64 {
        self.ceiling_minor_units - self.spent_minor_units - self.total_reserved()
    }

    pub fn reserve(
        &mut self,
        reservation_id: &str,
        lane_id: &str,
        billing_class: BillingClass,
        amount_minor_units: i64,
        currency: &str,
        nonce: &str,
        epoch: u64,
        fencing_token: u64,
    ) -> Result<EscrowReservation, LedgerError> {
        if epoch != self.revocation_epoch {
            return Err(LedgerError::StaleEpoch {
                got: epoch,
                current: self.revocation_epoch,
            });
        }
        if fencing_token < self.fencing_token {
            return Err(LedgerError::StaleFencingToken {
                got: fencing_token,
                authoritative: self.fencing_token,
            });
        }
        if billing_class != self.allowed_billing_class {
            return Err(LedgerError::CrossClassSubstitution {
                expected: self.allowed_billing_class,
                got: billing_class,
            });
        }
        if currency != self.currency {
            return Err(LedgerError::CurrencyMismatch {
                expected: self.currency.clone(),
                got: currency.to_string(),
            });
        }
        if amount_minor_units <= 0 {
            return Err(LedgerError::InvalidCost {
                cost: amount_minor_units,
            });
        }
        if self.reservations.contains_key(reservation_id) {
            return Err(LedgerError::DuplicateReservation {
                id: reservation_id.to_string(),
            });
        }
        let norm_nonce = nonce.trim().to_ascii_lowercase();
        if norm_nonce.len() < 8 || self.nonces.contains(&norm_nonce) {
            return Err(LedgerError::ReplayNonceDetected { nonce: norm_nonce });
        }
        let reserved_now = self.total_reserved();
        let projected = reserved_now
            .checked_add(self.spent_minor_units)
            .and_then(|s| s.checked_add(amount_minor_units))
            .ok_or(LedgerError::InvalidCost {
                cost: amount_minor_units,
            })?;
        if projected > self.ceiling_minor_units {
            return Err(LedgerError::InsufficientEscrow {
                requested: amount_minor_units,
                available: self.ceiling_minor_units - reserved_now - self.spent_minor_units,
            });
        }

        self.nonces.insert(norm_nonce);
        let res = EscrowReservation {
            reservation_id: reservation_id.to_string(),
            lane_id: lane_id.to_string(),
            billing_class,
            amount_minor_units,
            currency: self.currency.clone(),
            epoch: self.revocation_epoch,
            fencing_token: self.fencing_token,
            state: ReservationState::Reserved,
        };
        self.reservations.insert(reservation_id.to_string(), res.clone());
        Ok(res)
    }

    pub fn commit(&mut self, reservation_id: &str, actual_minor_units: i64) -> Result<u64, LedgerError> {
        let res = self
            .reservations
            .get_mut(reservation_id)
            .ok_or_else(|| LedgerError::UnknownReservation {
                id: reservation_id.to_string(),
            })?;
        if res.state != ReservationState::Reserved {
            return Err(LedgerError::InvalidStateTransition {
                id: reservation_id.to_string(),
            });
        }
        if res.epoch != self.revocation_epoch {
            return Err(LedgerError::StaleEpoch {
                got: res.epoch,
                current: self.revocation_epoch,
            });
        }
        if actual_minor_units < 0 || actual_minor_units > res.amount_minor_units {
            return Err(LedgerError::InvalidCost {
                cost: actual_minor_units,
            });
        }
        res.state = ReservationState::Committed;
        self.spent_minor_units = self.spent_minor_units.saturating_add(actual_minor_units);
        self.fencing_token = self.fencing_token.saturating_add(1);
        Ok(self.fencing_token)
    }

    pub fn release(&mut self, reservation_id: &str) -> Result<i64, LedgerError> {
        let res = self
            .reservations
            .get_mut(reservation_id)
            .ok_or_else(|| LedgerError::UnknownReservation {
                id: reservation_id.to_string(),
            })?;
        if res.state != ReservationState::Reserved {
            return Err(LedgerError::InvalidStateTransition {
                id: reservation_id.to_string(),
            });
        }
        res.state = ReservationState::Released;
        Ok(res.amount_minor_units)
    }

    pub fn bump_revocation_epoch(&mut self) -> u64 {
        self.revocation_epoch = self.revocation_epoch.saturating_add(1);
        self.fencing_token = self.fencing_token.saturating_add(1);
        self.revocation_epoch
    }
}

/// Linearizable routing & fitness lease registry (`RoutingStateDO` core).
#[derive(Clone, Debug)]
pub struct RoutingState {
    trusted_pubkeys: HashSet<String>,
    records: BTreeMap<String, LaneFitnessRecord>,
}

impl RoutingState {
    pub fn new(trusted_pubkeys_hex: Vec<String>) -> Self {
        Self {
            trusted_pubkeys: trusted_pubkeys_hex
                .into_iter()
                .map(|s| s.to_ascii_lowercase())
                .collect(),
            records: BTreeMap::new(),
        }
    }

    pub fn upsert_signed(&mut self, rec: LaneFitnessRecord) -> Result<(), LedgerError> {
        rec.verify_strict(&self.trusted_pubkeys)?;
        self.records.insert(rec.lane_id.clone(), rec);
        Ok(())
    }

    pub fn drain_lane(&mut self, lane_id: &str, reason: &str) {
        if let Some(rec) = self.records.get_mut(lane_id) {
            rec.status = LaneStatus::Drained;
            rec.golden_pass = false;
            rec.reason = reason.to_string();
        }
    }

    /// Selects the lowest-latency live FIT lane strictly within `billing_class`.
    pub fn select_best_fit(
        &self,
        billing_class: BillingClass,
        now_utc: u64,
        excluded: &HashSet<String>,
    ) -> Option<&LaneFitnessRecord> {
        self.records
            .values()
            .filter(|r| {
                r.billing_class == billing_class
                    && r.is_live_fit(now_utc)
                    && !excluded.contains(&r.lane_id)
            })
            .min_by_key(|r| (r.p99_ms, r.lane_id.clone()))
    }

    pub fn all_records(&self) -> Vec<&LaneFitnessRecord> {
        self.records.values().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ledger_atomic_reserve_commit_release_and_no_overspend() {
        let mut l = BudgetLedger::new("GBP", BillingClass::ApiCredit, 1_000);
        assert!(l.reserve("r1", "deepseek", BillingClass::ApiCredit, 600, "GBP", "nonce-0001", 1, 1).is_ok());
        assert_eq!(
            l.reserve("r2", "minimax", BillingClass::ApiCredit, 401, "GBP", "nonce-0002", 1, 1),
            Err(LedgerError::InsufficientEscrow { requested: 401, available: 400 })
        );
        assert_eq!(
            l.reserve("r3", "claude-sub", BillingClass::MonthlySubscription, 100, "GBP", "nonce-0003", 1, 1),
            Err(LedgerError::CrossClassSubstitution {
                expected: BillingClass::ApiCredit,
                got: BillingClass::MonthlySubscription
            })
        );
        assert_eq!(l.commit("r1", 450), Ok(2));
        assert_eq!(l.spent_minor_units, 450);
        assert_eq!(l.available_minor_units(), 550);
    }

    #[test]
    fn routing_state_verifies_ed25519_and_picks_lowest_p99_same_class() {
        let sk = SigningKey::from_bytes(&[0x55; 32]);
        let pk = hex::encode(sk.verifying_key().to_bytes());
        let mut rs = RoutingState::new(vec![pk]);

        let mut slow = LaneFitnessRecord {
            schema: LaneFitnessRecord::SCHEMA_V1.to_string(),
            lane_id: "minimax-m3".to_string(),
            provider: "minimax".to_string(),
            model: "MiniMax-M3".to_string(),
            secret_env: "SEED_MINIMAX_API_KEY".to_string(),
            billing_class: BillingClass::ApiCredit,
            status: LaneStatus::Fit,
            checked_at_utc: 1_000,
            expires_at_utc: 2_000,
            p99_ms: 950,
            golden_pass: true,
            reason: "PRE_EDIT_RED->FIX_GREEN".to_string(),
            signer_pubkey_hex: String::new(),
            signature_hex: String::new(),
        };
        slow.sign(&sk);
        assert!(rs.upsert_signed(slow).is_ok());

        let mut fast = LaneFitnessRecord {
            schema: LaneFitnessRecord::SCHEMA_V1.to_string(),
            lane_id: "deepseek-v4".to_string(),
            provider: "deepseek".to_string(),
            model: "deepseek-chat".to_string(),
            secret_env: "SEED_DEEPSEEK_API_KEY".to_string(),
            billing_class: BillingClass::ApiCredit,
            status: LaneStatus::Fit,
            checked_at_utc: 1_000,
            expires_at_utc: 2_000,
            p99_ms: 420,
            golden_pass: true,
            reason: "PRE_EDIT_RED->FIX_GREEN".to_string(),
            signer_pubkey_hex: String::new(),
            signature_hex: String::new(),
        };
        fast.sign(&sk);
        assert!(rs.upsert_signed(fast).is_ok());

        let chosen = rs.select_best_fit(BillingClass::ApiCredit, 1_100, &HashSet::new());
        assert_eq!(chosen.map(|r| r.lane_id.as_str()), Some("deepseek-v4"));
    }
}
