//! The single ingress door for a web agent (issue #8302, claim #8345).
//!
//! Three facts bind a caller before any handler body runs, and each refusal has
//! its own status so a caller can tell them apart without reading prose:
//!   401 no live session, 403 a ticket that does not open this session,
//!   409 a replayed nonce or a stale fencing token.
use anyhow::Result;
use axum::http::StatusCode;
use rusqlite::{params, Connection, OptionalExtension};
use sha2::{Digest, Sha256};

pub fn sha256_hex(s: &str) -> String {
    hex::encode(Sha256::digest(s.as_bytes()))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IngressRefusal {
    NoSession,
    TicketRejected,
    ReplayedNonce,
    StaleFence,
}

impl IngressRefusal {
    pub fn status(self) -> StatusCode {
        match self {
            Self::NoSession => StatusCode::UNAUTHORIZED,
            Self::TicketRejected => StatusCode::FORBIDDEN,
            Self::ReplayedNonce | Self::StaleFence => StatusCode::CONFLICT,
        }
    }

    pub fn code(self) -> &'static str {
        match self {
            Self::NoSession => "NO_LIVE_SESSION",
            Self::TicketRejected => "TICKET_REJECTED",
            Self::ReplayedNonce => "NONCE_REPLAYED",
            Self::StaleFence => "STALE_FENCING_TOKEN",
        }
    }
}

/// What a caller presents. Every field is required: an absent field is a
/// refusal, never a default, because a default is a session nobody granted.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct IngressTicket {
    pub session_id: String,
    pub ticket: String,
    pub nonce: String,
    pub fencing_token: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IngressDecision {
    Open,
    Shut(IngressRefusal),
}

fn now_sec() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

/// The door. Order matters: identity, then ticket, then fence, then nonce --
/// so a replayed nonce can never be mistaken for a bad ticket, and a stale
/// fence is reported before the nonce is burned.
pub fn consume(
    conn: &Connection,
    live_fence: u64,
    t: &IngressTicket,
) -> Result<IngressDecision> {
    if t.session_id.trim().is_empty() || t.ticket.trim().is_empty() || t.nonce.trim().is_empty() {
        return Ok(IngressDecision::Shut(IngressRefusal::NoSession));
    }
    let row: Option<(String, i64, String)> = conn
        .query_row(
            "SELECT scope_sha256, expires_at_sec, status FROM gt_agent_leases WHERE lease_id = ?1",
            params![t.session_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .optional()?;
    let Some((scope_sha256, expires_at_sec, status)) = row else {
        return Ok(IngressDecision::Shut(IngressRefusal::NoSession));
    };
    if status != "ACTIVE" || expires_at_sec <= now_sec() {
        return Ok(IngressDecision::Shut(IngressRefusal::NoSession));
    }
    if sha256_hex(&t.ticket) != scope_sha256 {
        return Ok(IngressDecision::Shut(IngressRefusal::TicketRejected));
    }
    if t.fencing_token != live_fence {
        return Ok(IngressDecision::Shut(IngressRefusal::StaleFence));
    }
    let inserted = conn.execute(
        "INSERT INTO gt_ingress_nonces (nonce, session_id, ticket_sha256, fencing_token, consumed_at_ns)
         VALUES (?1, ?2, ?3, ?4, ?5)",
        params![
            t.nonce,
            t.session_id,
            sha256_hex(&t.ticket),
            t.fencing_token as i64,
            now_sec() as i64
        ],
    );
    match inserted {
        Ok(_) => Ok(IngressDecision::Open),
        // The PRIMARY KEY on nonce is the single-use guarantee: a second
        // presentation cannot insert, so replay is refused by the store.
        Err(rusqlite::Error::SqliteFailure(e, _))
            if e.code == rusqlite::ErrorCode::ConstraintViolation =>
        {
            Ok(IngressDecision::Shut(IngressRefusal::ReplayedNonce))
        }
        Err(e) => Err(e.into()),
    }
}

use crate::store::GroundTruthEngine;

impl GroundTruthEngine {
    pub fn check_ingress(&self, t: &IngressTicket) -> Result<IngressDecision> {
        let conn = self.write_conn.lock().expect("write conn poisoned");
        consume(&conn, self.current_fencing_token(), t)
    }
}
