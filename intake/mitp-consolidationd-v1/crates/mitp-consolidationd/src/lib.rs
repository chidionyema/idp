//! mitp-consolidationd — the estate's sleep cycle.
//!
//! Design doc: Design_Proposal_TP-MEMORY_Consolidation_Dreaming_Rust.md (2026-11-28).
//! Fixes G1-G8 of the unified-memory-server audit and implements the staged
//! memory-promotion architecture from the grounded research memo (section 5):
//!
//!   raw episode -> STAGE -> evidence-gated PROMOTE -> SURVEIL (Brier/CUSUM)
//!                         \-> QUARANTINE            \-> demote + recalibrate
//!   DREAM: episodic clusters -> DISTILL (budget-gated, poison-scanned)
//!          -> new llm_derived semantic facts, provenance-linked, never superseding.
//!
//! Hard rules enforced in code, not comments:
//!  * E2: this crate never emits UPDATE/DELETE against `memories` or
//!    `memory_versions`. All bookkeeping lands in side tables. `sql.rs`
//!    statements are statically checked by tests.
//!  * E1: promotion requires at least one positive evidence row; MAPLE
//!    default scores (rho=1, tau=1, h=0) are explicitly inadmissible.
//!  * E4: the distiller never sets superseded_by (Anti-Ouroboros).
//!  * E8: model calls pass a hard budget ledger; zero budget means zero calls.
//!  * No `unsafe` anywhere.

pub mod config;
pub mod cycle;
pub mod distill;
pub mod evidence;
pub mod host;
pub mod json;
pub mod owasp;
pub mod quality;
pub mod receipts;
pub mod revalidate;
pub mod sql;
pub mod store;

/// Crate-wide result type.
pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    /// E3: a write that should have matched rows matched none — almost always
    /// a missing `app.tenant_id` GUC under FORCE ROW LEVEL SECURITY (idp#6507).
    RlsSilentNoOp { statement: &'static str, expected: u64 },
    /// Advisory lock held by another consolidator (E11). Not a failure of the
    /// cycle; the follower exits cleanly.
    NotLeader,
    /// Host envelope in crisis (E7); cycle skipped, zero side effects.
    HostInCrisis(String),
    /// Distillation budget exhausted (E8); abort with receipts written so far.
    BudgetExhausted { spent_micro: u64, floor_micro: u64 },
    /// Poisoned input refused (E6).
    PoisonDetected { memory_id: String, rule: &'static str },
    /// Store-layer failure propagated with context.
    Store(String),
    /// Configuration invalid; fail closed.
    Config(String),
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Error::RlsSilentNoOp { statement, expected } => write!(
                f,
                "RLS_SILENT_NOOP: {statement} expected >= {expected} rows, matched 0 (app.tenant_id unset?)"
            ),
            Error::NotLeader => write!(f, "NOT_LEADER: advisory lock held elsewhere"),
            Error::HostInCrisis(why) => write!(f, "HOST_IN_CRISIS: {why}"),
            Error::BudgetExhausted { spent_micro, floor_micro } => write!(
                f,
                "BUDGET_EXHAUSTED: spent {spent_micro} micro-units, floor {floor_micro}"
            ),
            Error::PoisonDetected { memory_id, rule } => {
                write!(f, "POISON_DETECTED: memory {memory_id} matched {rule}")
            }
            Error::Store(msg) => write!(f, "STORE: {msg}"),
            Error::Config(msg) => write!(f, "CONFIG: {msg}"),
        }
    }
}

impl std::error::Error for Error {}
