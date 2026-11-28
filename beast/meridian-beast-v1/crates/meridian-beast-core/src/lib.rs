//! `meridian-beast-core`: The Unsleeping Sovereign Reference Kernel.
//!
//! Zero LLMs in the hot path. Zero `.unwrap()`, zero `panic!()`, zero `todo!()` in production code.
//! Mediates every deterministic and non-deterministic transition across domain bulkheads via:
//!   1. `SovereignMark` (Ed25519 RFC 8032 `verify_strict` — No Mark, No Buy/Sell/Mutate)
//!   2. `MerkleWal` (Append-only SHA-256 hash-chained real-time causal event bus)
//!   3. `DomainBulkhead` (Per-domain isolated escrow, DOF level, epochs, fitness pool, NPV ledger)
//!   4. `BeastEngine` (Sub-millisecond O(1) reflex table governing both stochastic workers & deterministic infra)

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BillingClass {
    MonthlySubscription,
    ApiCredit,
    FreeAllowance,
    FounderAuthorisedException,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum DofLevel {
    L0FullLease = 0,
    L1ReadDiagnose = 1,
    L2ComponentRepairOnly = 2,
    L3FrozenBulkhead = 3,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ProcessClass {
    NonDeterministicWorker,
    DeterministicInfra,
}

/// Cryptographic capability token: No process buys, sells, or mutates without a live Mark.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SovereignMark {
    pub mark_id: String,
    pub domain_id: String,
    pub actor_urn: String,
    pub process_class: ProcessClass,
    pub billing_class: BillingClass,
    pub footprint_hash: String,
    pub max_cost_minor_units: i64,
    pub currency: String,
    pub revocation_epoch: u64,
    pub lease_epoch: u64,
    pub expires_utc: u64,
    pub reads_ring3: bool,
    pub egresses_external: bool,
    pub issuer_pubkey_hex: String,
    pub signature_hex: String,
}

impl SovereignMark {
    pub fn canonical_bytes(&self) -> Vec<u8> {
        let s = format!(
            "BEAST-MARK-V1|{}|{}|{}|{:?}|{:?}|{}|{}|{}|{}|{}|{}|{}|{}",
            self.mark_id,
            self.domain_id,
            self.actor_urn,
            self.process_class,
            self.billing_class,
            self.footprint_hash,
            self.max_cost_minor_units,
            self.currency,
            self.revocation_epoch,
            self.lease_epoch,
            self.expires_utc,
            self.reads_ring3,
            self.egresses_external,
        );
        let mut h = Sha256::new();
        h.update(s.as_bytes());
        h.finalize().to_vec()
    }

    pub fn sign(&mut self, sk: &SigningKey) {
        self.issuer_pubkey_hex = hex::encode(sk.verifying_key().to_bytes());
        self.signature_hex = hex::encode(sk.sign(&self.canonical_bytes()).to_bytes());
    }

    pub fn verify_strict(&self, trusted_issuers: &HashSet<String>) -> Result<(), BeastDeny> {
        if !trusted_issuers.contains(&self.issuer_pubkey_hex.to_ascii_lowercase()) {
            return Err(BeastDeny::UnmarkedOrUntrustedActor);
        }
        let pk_raw = hex::decode(&self.issuer_pubkey_hex).map_err(|_| BeastDeny::InvalidMarkSignature)?;
        let pk_arr: [u8; 32] = pk_raw.try_into().map_err(|_| BeastDeny::InvalidMarkSignature)?;
        let vk = VerifyingKey::from_bytes(&pk_arr).map_err(|_| BeastDeny::InvalidMarkSignature)?;
        let sig_raw = hex::decode(&self.signature_hex).map_err(|_| BeastDeny::InvalidMarkSignature)?;
        let sig_arr: [u8; 64] = sig_raw.try_into().map_err(|_| BeastDeny::InvalidMarkSignature)?;
        let sig = Signature::from_bytes(&sig_arr);
        vk.verify_strict(&self.canonical_bytes(), &sig)
            .map_err(|_| BeastDeny::InvalidMarkSignature)
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "code", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BeastDeny {
    UnknownDomain { domain_id: String },
    UnmarkedOrUntrustedActor,
    InvalidMarkSignature,
    MarkExpired { now_utc: u64, expires_utc: u64 },
    ReplayMarkDetected { mark_id: String },
    StaleRevocationEpoch { got: u64, current: u64 },
    StaleLeaseEpoch { got: u64, current: u64 },
    DomainBulkheadFrozenL3 { domain_id: String },
    CrossClassSubstitution { expected: BillingClass, got: BillingClass },
    CurrencyMismatch { expected: String, got: String },
    InsufficientEscrow { requested: i64, available: i64 },
    InvalidCost { cost: i64 },
    Ring3EgressTaintBlocked,
    NoFitLaneInClass { billing_class: BillingClass },
    ProxyGreenUrlBlocked { url: String },
    SelfCertificationBlocked { actor_urn: String },
    ForbiddenNoteOrBlockerBlocked { detail: String },
    DeterministicRotDetected { detail: String },
}

/// Autonomous sub-millisecond reflexes fired by the Beast with zero Founder intervention.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "reflex", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BeastReflex {
    Proceed {
        domain_id: String,
        assigned_lane: String,
        reserved_minor_units: i64,
        fencing_token: u64,
    },
    SettledOperationalYield {
        domain_id: String,
        instruction_id: String,
        net_cost_minor_units: i64,
        yield_units: u64,
    },
    DrainLaneAndFailoverSameClass {
        domain_id: String,
        drained_lane: String,
        replacement_lane: Option<String>,
        released_minor_units: i64,
    },
    AutoSpawnDirectAttack {
        domain_id: String,
        reason: String,
        directive: String,
    },
    FreezeBulkheadL3AndFence {
        domain_id: String,
        new_revocation_epoch: u64,
        red_card: bool,
        reason: String,
    },
    DrainExternalSecretSilently {
        domain_id: String,
        env_var: String,
    },
    RejectedFailClosed {
        domain_id: String,
        deny: BeastDeny,
    },
}

/// Every real-time signal entering the Beast's unsleeping event loop.
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "event", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BeastSignal {
    /// Worker requests inference or mutation (MUST carry a valid SovereignMark).
    RequestExecution {
        mark: Option<SovereignMark>,
        instruction_id: String,
        requested_lane: Option<String>,
        requested_cost_minor_units: i64,
        probe_url: Option<String>,
        touched_paths: Vec<String>,
        worker_text: String,
    },
    /// Mid-flight provider fault (429 / empty patch / crash) -> instant drain + same-class failover.
    WorkerFault {
        domain_id: String,
        lane_id: String,
        reservation_id: String,
        reason: String,
        is_external_secret_401: Option<String>,
    },
    /// Deterministic infra telemetry (mode 0644 bin, HTTP 525 origin, stale >24h proof, Optimus=UNKNOWN).
    DeterministicInfraAnomaly {
        domain_id: String,
        component_id: String,
        detail: String,
        severe_dual_probe_fail: bool,
    },
    /// Cross-surface bypass attempt during degraded state -> instant L3 bulkhead freeze + Red Card.
    CrossSurfaceBypassAttempt {
        domain_id: String,
        surface: String,
        actor_urn: String,
    },
    /// Independent external oracle submitting settlement proof.
    OracleSettlement {
        domain_id: String,
        instruction_id: String,
        reservation_id: String,
        worker_urn: String,
        oracle_urn: String,
        probe_url: String,
        actual_cost_minor_units: i64,
        rounds_passed: u8,
    },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WalEntry {
    pub seq: u64,
    pub timestamp_utc: u64,
    pub domain_id: String,
    pub event_summary: String,
    pub reflex_summary: String,
    pub prev_hash: String,
    pub hash: String,
}

/// Append-only SHA-256 hash-chained real-time bus (every iota recorded, tamper-evident).
#[derive(Clone, Debug)]
pub struct MerkleWal {
    entries: Vec<WalEntry>,
    head_hash: String,
}

impl Default for MerkleWal {
    fn default() -> Self {
        Self {
            entries: Vec::new(),
            head_hash: "0".repeat(64),
        }
    }
}

impl MerkleWal {
    pub fn append(&mut self, ts: u64, domain_id: &str, event_summary: &str, reflex_summary: &str) -> &WalEntry {
        let seq = (self.entries.len() as u64) + 1;
        let prev = self.head_hash.clone();
        let hash = Self::compute_hash(seq, ts, domain_id, event_summary, reflex_summary, &prev);
        self.head_hash = hash.clone();
        self.entries.push(WalEntry {
            seq,
            timestamp_utc: ts,
            domain_id: domain_id.to_string(),
            event_summary: event_summary.to_string(),
            reflex_summary: reflex_summary.to_string(),
            prev_hash: prev,
            hash,
        });
        // Safe indexing because we just pushed
        &self.entries[self.entries.len() - 1]
    }

    pub fn compute_hash(
        seq: u64,
        ts: u64,
        domain_id: &str,
        event_summary: &str,
        reflex_summary: &str,
        prev_hash: &str,
    ) -> String {
        let mut h = Sha256::new();
        h.update(format!("{seq}|{ts}|{domain_id}|{event_summary}|{reflex_summary}|{prev_hash}").as_bytes());
        hex::encode(h.finalize())
    }

    pub fn verify_full_chain(&self) -> Result<(), u64> {
        let mut expected_prev = "0".repeat(64);
        for e in &self.entries {
            if e.prev_hash != expected_prev {
                return Err(e.seq);
            }
            let calc = Self::compute_hash(
                e.seq,
                e.timestamp_utc,
                &e.domain_id,
                &e.event_summary,
                &e.reflex_summary,
                &e.prev_hash,
            );
            if e.hash != calc {
                return Err(e.seq);
            }
            expected_prev = e.hash.clone();
        }
        Ok(())
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn head_hash(&self) -> &str {
        &self.head_hash
    }
}

#[derive(Clone, Debug)]
pub struct LaneSlot {
    pub lane_id: String,
    pub billing_class: BillingClass,
    pub fit: bool,
    pub p99_ms: u32,
}

/// Isolated Domain Bulkhead — failure/freeze in one domain NEVER stalls unrelated domains.
#[derive(Clone, Debug)]
pub struct DomainBulkhead {
    pub domain_id: String,
    pub currency: String,
    pub allowed_billing_class: BillingClass,
    pub ceiling_minor_units: i64,
    pub spent_minor_units: i64,
    pub revocation_epoch: u64,
    pub lease_epoch: u64,
    pub fencing_token: u64,
    pub dof_level: DofLevel,
    pub red_card_count: u32,
    pub settled_yield_count: u64,
    pub auto_remediations_spawned: u64,
    pub founder_interrupts: u64,
    reservations: BTreeMap<String, i64>,
    lanes: BTreeMap<String, LaneSlot>,
    consumed_marks: HashSet<String>,
}

impl DomainBulkhead {
    pub fn new(
        domain_id: &str,
        currency: &str,
        allowed_billing_class: BillingClass,
        ceiling_minor_units: i64,
        lanes: Vec<LaneSlot>,
    ) -> Self {
        let mut lane_map = BTreeMap::new();
        for l in lanes {
            lane_map.insert(l.lane_id.clone(), l);
        }
        Self {
            domain_id: domain_id.to_string(),
            currency: currency.to_string(),
            allowed_billing_class,
            ceiling_minor_units,
            spent_minor_units: 0,
            revocation_epoch: 1,
            lease_epoch: 1,
            fencing_token: 1,
            dof_level: DofLevel::L0FullLease,
            red_card_count: 0,
            settled_yield_count: 0,
            auto_remediations_spawned: 0,
            founder_interrupts: 0,
            reservations: BTreeMap::new(),
            lanes: lane_map,
            consumed_marks: HashSet::new(),
        }
    }

    pub fn total_reserved(&self) -> i64 {
        self.reservations.values().sum()
    }

    pub fn available_minor_units(&self) -> i64 {
        self.ceiling_minor_units - self.spent_minor_units - self.total_reserved()
    }

    pub fn select_best_fit(&self, billing_class: BillingClass) -> Option<String> {
        self.lanes
            .values()
            .filter(|l| l.fit && l.billing_class == billing_class)
            .min_by_key(|l| (l.p99_ms, l.lane_id.clone()))
            .map(|l| l.lane_id.clone())
    }
}

pub fn is_proxy_green_url(url: &str) -> bool {
    let low = url.trim().to_ascii_lowercase();
    if !low.starts_with("https://") {
        return true;
    }
    let host = low
        .trim_start_matches("https://")
        .split('/')
        .next()
        .unwrap_or("")
        .split(':')
        .next()
        .unwrap_or("");
    matches!(
        host,
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

pub fn is_forbidden_note_or_blocker(paths: &[String], text: &str) -> Option<String> {
    for p in paths {
        let low = p.trim().trim_start_matches("./").to_ascii_lowercase();
        if low.starts_with("docs/diagnoses/")
            || low.starts_with("docs/notes/")
            || low.starts_with(".growmos/")
            || low.contains("handoff")
            || low.contains("journal")
        {
            return Some(format!("FORBIDDEN_NOTE_PATH:{p}"));
        }
    }
    let t = text.to_ascii_lowercase();
    for bad in ["blocker:", "outside this lane", "waiting on founder", "handed_off"] {
        if t.contains(bad) {
            return Some(format!("FORBIDDEN_ADMIN_PHRASE:{bad}"));
        }
    }
    None
}

/// The Unsleeping Beast Kernel: owns all domain bulkheads + single Merkle-WAL causal spine.
pub struct BeastEngine {
    trusted_mark_issuers: HashSet<String>,
    pub domains: BTreeMap<String, DomainBulkhead>,
    pub wal: MerkleWal,
}

impl BeastEngine {
    pub fn new(trusted_issuers_hex: Vec<String>, domains: Vec<DomainBulkhead>) -> Self {
        let mut dmap = BTreeMap::new();
        for d in domains {
            dmap.insert(d.domain_id.clone(), d);
        }
        Self {
            trusted_mark_issuers: trusted_issuers_hex
                .into_iter()
                .map(|s| s.to_ascii_lowercase())
                .collect(),
            domains: dmap,
            wal: MerkleWal::default(),
        }
    }

    /// Real-time O(1) mediation & reflex dispatch. Every event is hash-chained onto the Merkle-WAL.
    pub fn process_signal(&mut self, now_utc: u64, signal: BeastSignal) -> BeastReflex {
        let (domain_id, ev_summary, reflex) = match signal {
            BeastSignal::RequestExecution {
                mark,
                instruction_id,
                requested_lane,
                requested_cost_minor_units,
                probe_url,
                touched_paths,
                worker_text,
            } => {
                let m = match mark {
                    Some(mk) => mk,
                    None => {
                        let r = BeastReflex::RejectedFailClosed {
                            domain_id: "UNKNOWN".to_string(),
                            deny: BeastDeny::UnmarkedOrUntrustedActor,
                        };
                        self.wal.append(now_utc, "UNKNOWN", "REQ_UNMARKED", "DENY_NO_MARK");
                        return r;
                    }
                };
                let dom_id = m.domain_id.clone();
                let r = self.mediate_execution(
                    now_utc,
                    &m,
                    &instruction_id,
                    requested_lane.as_deref(),
                    requested_cost_minor_units,
                    probe_url.as_deref(),
                    &touched_paths,
                    &worker_text,
                );
                (dom_id, format!("REQ:{instruction_id}"), r)
            }
            BeastSignal::WorkerFault {
                domain_id,
                lane_id,
                reservation_id,
                reason,
                is_external_secret_401,
            } => {
                let r = if let Some(dom) = self.domains.get_mut(&domain_id) {
                    let released = dom.reservations.remove(&reservation_id).unwrap_or(0);
                    if let Some(slot) = dom.lanes.get_mut(&lane_id) {
                        slot.fit = false;
                    }
                    if let Some(env_var) = is_external_secret_401 {
                        BeastReflex::DrainExternalSecretSilently {
                            domain_id: domain_id.clone(),
                            env_var,
                        }
                    } else {
                        let repl = dom.select_best_fit(dom.allowed_billing_class);
                        dom.auto_remediations_spawned = dom.auto_remediations_spawned.saturating_add(1);
                        BeastReflex::DrainLaneAndFailoverSameClass {
                            domain_id: domain_id.clone(),
                            drained_lane: lane_id.clone(),
                            replacement_lane: repl,
                            released_minor_units: released,
                        }
                    }
                } else {
                    BeastReflex::RejectedFailClosed {
                        domain_id: domain_id.clone(),
                        deny: BeastDeny::UnknownDomain { domain_id: domain_id.clone() },
                    }
                };
                (domain_id, format!("FAULT:{lane_id}:{reason}"), r)
            }
            BeastSignal::DeterministicInfraAnomaly {
                domain_id,
                component_id,
                detail,
                severe_dual_probe_fail,
            } => {
                let r = if let Some(dom) = self.domains.get_mut(&domain_id) {
                    if severe_dual_probe_fail && dom.dof_level < DofLevel::L2ComponentRepairOnly {
                        dom.dof_level = DofLevel::L2ComponentRepairOnly;
                        dom.lease_epoch = dom.lease_epoch.saturating_add(1);
                    }
                    dom.auto_remediations_spawned = dom.auto_remediations_spawned.saturating_add(1);
                    BeastReflex::AutoSpawnDirectAttack {
                        domain_id: domain_id.clone(),
                        reason: format!("{component_id}:{detail}"),
                        directive: format!("DIRECT_ATTACK_INFRA:{component_id}:{detail}"),
                    }
                } else {
                    BeastReflex::RejectedFailClosed {
                        domain_id: domain_id.clone(),
                        deny: BeastDeny::UnknownDomain { domain_id: domain_id.clone() },
                    }
                };
                (domain_id, format!("INFRA_ROT:{component_id}"), r)
            }
            BeastSignal::CrossSurfaceBypassAttempt {
                domain_id,
                surface,
                actor_urn,
            } => {
                let r = if let Some(dom) = self.domains.get_mut(&domain_id) {
                    dom.dof_level = DofLevel::L3FrozenBulkhead;
                    dom.revocation_epoch = dom.revocation_epoch.saturating_add(1);
                    dom.lease_epoch = dom.lease_epoch.saturating_add(1);
                    dom.fencing_token = dom.fencing_token.saturating_add(1);
                    dom.red_card_count = dom.red_card_count.saturating_add(1);
                    dom.reservations.clear();
                    BeastReflex::FreezeBulkheadL3AndFence {
                        domain_id: domain_id.clone(),
                        new_revocation_epoch: dom.revocation_epoch,
                        red_card: true,
                        reason: format!("CROSS_SURFACE_BYPASS:{surface}:{actor_urn}"),
                    }
                } else {
                    BeastReflex::RejectedFailClosed {
                        domain_id: domain_id.clone(),
                        deny: BeastDeny::UnknownDomain { domain_id: domain_id.clone() },
                    }
                };
                (domain_id, format!("BYPASS:{surface}"), r)
            }
            BeastSignal::OracleSettlement {
                domain_id,
                instruction_id,
                reservation_id,
                worker_urn,
                oracle_urn,
                probe_url,
                actual_cost_minor_units,
                rounds_passed,
            } => {
                let r = self.mediate_settlement(
                    &domain_id,
                    &instruction_id,
                    &reservation_id,
                    &worker_urn,
                    &oracle_urn,
                    &probe_url,
                    actual_cost_minor_units,
                    rounds_passed,
                );
                (domain_id, format!("SETTLE:{instruction_id}"), r)
            }
        };

        let r_tag = format!("{:?}", reflex);
        self.wal.append(now_utc, &domain_id, &ev_summary, &r_tag);
        reflex
    }

    #[allow(clippy::too_many_arguments)]
    fn mediate_execution(
        &mut self,
        now_utc: u64,
        mark: &SovereignMark,
        instruction_id: &str,
        requested_lane: Option<&str>,
        cost: i64,
        probe_url: Option<&str>,
        touched_paths: &[String],
        worker_text: &str,
    ) -> BeastReflex {
        let dom_id = mark.domain_id.clone();
        if let Err(deny) = mark.verify_strict(&self.trusted_mark_issuers) {
            return BeastReflex::RejectedFailClosed { domain_id: dom_id, deny };
        }
        if now_utc > mark.expires_utc {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::MarkExpired {
                    now_utc,
                    expires_utc: mark.expires_utc,
                },
            };
        }
        if mark.reads_ring3 && mark.egresses_external {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::Ring3EgressTaintBlocked,
            };
        }
        if let Some(u) = probe_url {
            if is_proxy_green_url(u) {
                return BeastReflex::RejectedFailClosed {
                    domain_id: dom_id,
                    deny: BeastDeny::ProxyGreenUrlBlocked { url: u.to_string() },
                };
            }
        }
        if let Some(detail) = is_forbidden_note_or_blocker(touched_paths, worker_text) {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::ForbiddenNoteOrBlockerBlocked { detail },
            };
        }

        let dom = match self.domains.get_mut(&dom_id) {
            Some(d) => d,
            None => {
                return BeastReflex::RejectedFailClosed {
                    domain_id: dom_id.clone(),
                    deny: BeastDeny::UnknownDomain { domain_id: dom_id },
                }
            }
        };
        if dom.dof_level == DofLevel::L3FrozenBulkhead {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id.clone(),
                deny: BeastDeny::DomainBulkheadFrozenL3 { domain_id: dom_id },
            };
        }
        if mark.revocation_epoch != dom.revocation_epoch {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::StaleRevocationEpoch {
                    got: mark.revocation_epoch,
                    current: dom.revocation_epoch,
                },
            };
        }
        if mark.lease_epoch != dom.lease_epoch {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::StaleLeaseEpoch {
                    got: mark.lease_epoch,
                    current: dom.lease_epoch,
                },
            };
        }
        if mark.billing_class != dom.allowed_billing_class {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::CrossClassSubstitution {
                    expected: dom.allowed_billing_class,
                    got: mark.billing_class,
                },
            };
        }
        if mark.currency != dom.currency {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::CurrencyMismatch {
                    expected: dom.currency.clone(),
                    got: mark.currency.clone(),
                },
            };
        }
        if cost <= 0 || cost > mark.max_cost_minor_units {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::InvalidCost { cost },
            };
        }
        if dom.consumed_marks.contains(&mark.mark_id) {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::ReplayMarkDetected {
                    mark_id: mark.mark_id.clone(),
                },
            };
        }
        let avail = dom.available_minor_units();
        if cost > avail {
            return BeastReflex::RejectedFailClosed {
                domain_id: dom_id,
                deny: BeastDeny::InsufficientEscrow {
                    requested: cost,
                    available: avail,
                },
            };
        }

        let lane_id = match requested_lane {
            Some(lid) => match dom.lanes.get(lid) {
                Some(slot) if slot.billing_class != dom.allowed_billing_class => {
                    return BeastReflex::RejectedFailClosed {
                        domain_id: dom_id,
                        deny: BeastDeny::CrossClassSubstitution {
                            expected: dom.allowed_billing_class,
                            got: slot.billing_class,
                        },
                    };
                }
                Some(slot) if slot.fit => slot.lane_id.clone(),
                _ => match dom.select_best_fit(dom.allowed_billing_class) {
                    Some(best) => best,
                    None => {
                        return BeastReflex::RejectedFailClosed {
                            domain_id: dom_id,
                            deny: BeastDeny::NoFitLaneInClass {
                                billing_class: dom.allowed_billing_class,
                            },
                        }
                    }
                },
            },
            None => match dom.select_best_fit(dom.allowed_billing_class) {
                Some(best) => best,
                None => {
                    return BeastReflex::RejectedFailClosed {
                        domain_id: dom_id,
                        deny: BeastDeny::NoFitLaneInClass {
                            billing_class: dom.allowed_billing_class,
                        },
                    }
                }
            },
        };

        dom.consumed_marks.insert(mark.mark_id.clone());
        dom.reservations.insert(instruction_id.to_string(), cost);
        BeastReflex::Proceed {
            domain_id: dom_id,
            assigned_lane: lane_id,
            reserved_minor_units: cost,
            fencing_token: dom.fencing_token,
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn mediate_settlement(
        &mut self,
        domain_id: &str,
        instruction_id: &str,
        reservation_id: &str,
        worker_urn: &str,
        oracle_urn: &str,
        probe_url: &str,
        actual_cost: i64,
        rounds_passed: u8,
    ) -> BeastReflex {
        if worker_urn.eq_ignore_ascii_case(oracle_urn) {
            return BeastReflex::RejectedFailClosed {
                domain_id: domain_id.to_string(),
                deny: BeastDeny::SelfCertificationBlocked {
                    actor_urn: oracle_urn.to_string(),
                },
            };
        }
        if is_proxy_green_url(probe_url) {
            return BeastReflex::RejectedFailClosed {
                domain_id: domain_id.to_string(),
                deny: BeastDeny::ProxyGreenUrlBlocked {
                    url: probe_url.to_string(),
                },
            };
        }
        if rounds_passed < 3 {
            return BeastReflex::AutoSpawnDirectAttack {
                domain_id: domain_id.to_string(),
                reason: format!("INSUFFICIENT_BLACKBOX_ROUNDS:{rounds_passed}"),
                directive: "DIRECT_ATTACK_REVERIFY_3OF3".to_string(),
            };
        }
        let dom = match self.domains.get_mut(domain_id) {
            Some(d) => d,
            None => {
                return BeastReflex::RejectedFailClosed {
                    domain_id: domain_id.to_string(),
                    deny: BeastDeny::UnknownDomain {
                        domain_id: domain_id.to_string(),
                    },
                }
            }
        };
        let reserved = dom.reservations.remove(reservation_id).unwrap_or(0);
        if actual_cost < 0 || actual_cost > reserved {
            dom.reservations.insert(reservation_id.to_string(), reserved);
            return BeastReflex::RejectedFailClosed {
                domain_id: domain_id.to_string(),
                deny: BeastDeny::InvalidCost { cost: actual_cost },
            };
        }
        dom.spent_minor_units = dom.spent_minor_units.saturating_add(actual_cost);
        dom.fencing_token = dom.fencing_token.saturating_add(1);
        dom.settled_yield_count = dom.settled_yield_count.saturating_add(1);
        BeastReflex::SettledOperationalYield {
            domain_id: domain_id.to_string(),
            instruction_id: instruction_id.to_string(),
            net_cost_minor_units: actual_cost,
            yield_units: 1,
        }
    }
}

#[cfg(test)]
mod tests;
