//! The falsifiers for the ingress door (issue #8302, claim #8345).
//!
//! Five assertions, each on the real store: no session 401, wrong ticket 403,
//! stale fence 409, replayed nonce 409, and a well-formed call opening once.
use genesis_ground_truth::ingress::{
    consume, sha256_hex, IngressDecision, IngressRefusal, IngressTicket,
};
use rusqlite::{params, Connection};

const FENCE: u64 = 7;
const TICKET: &str = "ticket-abc";

fn now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

fn db(status: &str, expires_in: i64) -> Connection {
    let conn = Connection::open_in_memory().unwrap();
    conn.execute_batch(include_str!("../migrations/001_ground_truth.sql"))
        .unwrap();
    conn.execute(
        "INSERT INTO gt_agent_leases
         (lease_id, agent_surface, role_id, repo_full_name, bound_seq_id,
          bound_fencing_token, admitted_paths_json, scope_sha256,
          expires_at_sec, status, created_at_ns)
         VALUES ('lease-1','web','architect','o/r',1,?1,'[]',?2,?3,?4,0)",
        params![FENCE as i64, sha256_hex(TICKET), now() + expires_in, status],
    )
    .unwrap();
    conn
}

fn ticket(nonce: &str) -> IngressTicket {
    IngressTicket {
        session_id: "lease-1".into(),
        ticket: TICKET.into(),
        nonce: nonce.into(),
        fencing_token: FENCE,
    }
}

#[test]
fn no_live_session_is_401() {
    let conn = db("ACTIVE", 3600);
    let mut t = ticket("n1");
    t.session_id = "lease-does-not-exist".into();
    assert_eq!(
        consume(&conn, FENCE, &t).unwrap(),
        IngressDecision::Shut(IngressRefusal::NoSession)
    );
}

#[test]
fn an_expired_lease_is_no_session() {
    let conn = db("ACTIVE", -60);
    assert_eq!(
        consume(&conn, FENCE, &ticket("n2")).unwrap(),
        IngressDecision::Shut(IngressRefusal::NoSession)
    );
}

#[test]
fn a_wrong_ticket_is_403() {
    let conn = db("ACTIVE", 3600);
    let mut t = ticket("n3");
    t.ticket = "not-the-ticket".into();
    assert_eq!(
        consume(&conn, FENCE, &t).unwrap(),
        IngressDecision::Shut(IngressRefusal::TicketRejected)
    );
}

#[test]
fn a_stale_fence_is_409() {
    let conn = db("ACTIVE", 3600);
    assert_eq!(
        consume(&conn, FENCE + 1, &ticket("n4")).unwrap(),
        IngressDecision::Shut(IngressRefusal::StaleFence)
    );
}

#[test]
fn a_replayed_nonce_is_409_and_the_first_call_opens() {
    let conn = db("ACTIVE", 3600);
    let t = ticket("once-1");
    assert_eq!(consume(&conn, FENCE, &t).unwrap(), IngressDecision::Open);
    assert_eq!(
        consume(&conn, FENCE, &t).unwrap(),
        IngressDecision::Shut(IngressRefusal::ReplayedNonce)
    );
}

#[test]
fn a_fresh_nonce_after_a_refusal_still_opens() {
    let conn = db("ACTIVE", 3600);
    let mut bad = ticket("n5");
    bad.fencing_token = FENCE + 1;
    assert!(matches!(
        consume(&conn, FENCE, &bad).unwrap(),
        IngressDecision::Shut(_)
    ));
    assert_eq!(
        consume(&conn, FENCE, &ticket("n6")).unwrap(),
        IngressDecision::Open
    );
}
