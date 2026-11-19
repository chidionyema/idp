//! Bound web ingress and a read-only projection of independently signed FLOW receipts.
//! Issuer/acceptance/verifier keys are external trust anchors. No model holds those keys.
//! This module neither executes mutations nor grants itself a signer identity.
use crate::{crypto::FounderVerifier, GroundTruthEngine};
use axum::{
    extract::{Extension, Request, State},
    http::{header, HeaderMap, HeaderValue, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use rusqlite::{params, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{collections::HashSet, sync::Arc, time::{SystemTime, UNIX_EPOCH}};

pub const SQL: &str = r#"
CREATE TABLE IF NOT EXISTS gt_web_sessions (
    session_id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    grant_json TEXT NOT NULL,
    expires INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1))
);
CREATE TABLE IF NOT EXISTS gt_web_nonces (
    session_id TEXT NOT NULL, nonce TEXT NOT NULL,
    PRIMARY KEY(session_id,nonce)
);
CREATE TABLE IF NOT EXISTS gt_web_lease_binding (
    lease_id TEXT PRIMARY KEY, session_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gt_flow_acceptances (
    instruction_id TEXT PRIMARY KEY, contract_hash TEXT NOT NULL, contract_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gt_flow_artifacts (
    artifact_id TEXT PRIMARY KEY, instruction_id TEXT NOT NULL,
    producer TEXT NOT NULL, artifact_json TEXT NOT NULL, submitted_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS gt_external_yield_observations (
    artifact_id TEXT NOT NULL, criterion_id TEXT NOT NULL,
    observation_hash TEXT NOT NULL UNIQUE, observation_json TEXT NOT NULL,
    signature TEXT NOT NULL, sequence INTEGER NOT NULL, verdict TEXT NOT NULL,
    observed_at INTEGER NOT NULL, valid_until INTEGER NOT NULL,
    PRIMARY KEY(artifact_id,criterion_id)
);
"#;

type WebResult<T> = Result<T, WebError>;
#[derive(Debug)]
pub struct WebError(StatusCode, &'static str);
impl IntoResponse for WebError {
    fn into_response(self) -> Response {
        (self.0, Json(serde_json::json!({"ok":false,"error":self.1}))).into_response()
    }
}
impl From<rusqlite::Error> for WebError {
    fn from(_: rusqlite::Error) -> Self { err(StatusCode::SERVICE_UNAVAILABLE, "LEDGER_UNAVAILABLE") }
}
impl From<serde_json::Error> for WebError {
    fn from(_: serde_json::Error) -> Self { err(StatusCode::UNPROCESSABLE_ENTITY, "INVALID_TYPED_RECORD") }
}
fn err(code: StatusCode, why: &'static str) -> WebError { WebError(code, why) }
fn forbidden(why: &'static str) -> WebError { err(StatusCode::FORBIDDEN, why) }
fn conflict(why: &'static str) -> WebError { err(StatusCode::CONFLICT, why) }
fn invalid(why: &'static str) -> WebError { err(StatusCode::UNPROCESSABLE_ENTITY, why) }
fn unavailable() -> WebError { err(StatusCode::SERVICE_UNAVAILABLE, "AUTHORITY_UNAVAILABLE") }
fn now() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() as i64
}
pub fn hash(bytes: &[u8]) -> String { hex::encode(Sha256::digest(bytes)) }
fn hex_len(s:&str, len:usize) -> bool {
    s.len()==len && s.bytes().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
}
fn name(s:&str) -> bool {
    !s.is_empty() && s.len()<=128 && s.bytes().all(|c| c.is_ascii_alphanumeric() || b"-_.:/#".contains(&c))
}
pub fn path_ok(p:&str) -> bool {
    !p.is_empty() && p.len()<=512 && !p.starts_with('/') &&
    !p.bytes().any(|c| c.is_ascii_control() || c.is_ascii_whitespace() || b"\\*?[]{}:".contains(&c)) &&
    p.split('/').all(|x| !x.is_empty() && x!="." && x!="..")
}
fn head<'a>(h:&'a HeaderMap,k:&str) -> Option<&'a str> { h.get(k).and_then(|v|v.to_str().ok()) }
fn key(env:&str) -> WebResult<FounderVerifier> {
    let raw=std::env::var(env).map_err(|_|unavailable())?;
    FounderVerifier::from_hex(&raw).map_err(|_|unavailable())
}
fn authentic(v:&FounderVerifier,h:&HeaderMap,path:&str,body:&str)->WebResult<String>{
    let ts=head(h,"x-genesis-timestamp").and_then(|x|x.parse::<i64>().ok())
        .ok_or_else(||err(StatusCode::UNAUTHORIZED,"SIGNED_AUTHORITY_REQUIRED"))?;
    if now().abs_diff(ts)>60 { return Err(err(StatusCode::UNAUTHORIZED,"STALE_SIGNATURE")); }
    let sig=head(h,"x-genesis-signature").ok_or_else(||err(StatusCode::UNAUTHORIZED,"SIGNED_AUTHORITY_REQUIRED"))?;
    v.verify_signed_request("POST",path,head(h,"x-genesis-timestamp"),Some(sig),body)
        .map_err(|_|err(StatusCode::UNAUTHORIZED,"SIGNATURE_INVALID"))?;
    Ok(sig.to_string())
}
fn distinct(a:&FounderVerifier,b:&FounderVerifier)->bool {
    a.verifying_key.to_bytes()!=b.verifying_key.to_bytes()
}

#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Grant {
    pub session_id:String, pub token_sha256:String, pub principal:String,
    pub instruction_id:String, pub role_id:String, pub repo_full_name:String,
    pub paths:Vec<String>, pub read_only:bool, pub expires_at:i64,
    pub operations:Vec<String>,
}
impl Grant {
    fn validate(&self)->WebResult<()> {
        let ops=["live","stream","admit","verify","flow","yield","chat"];
        if !hex_len(&self.session_id,32) || !hex_len(&self.token_sha256,64) ||
           !name(&self.principal) || self.principal.to_ascii_lowercase().starts_with("founder") ||
           !name(&self.instruction_id) || !name(&self.role_id) ||
           !crate::types::TRACKED_REPOS.contains(&self.repo_full_name.as_str()) ||
           self.expires_at<=now() || self.expires_at>now()+600 ||
           self.paths.len()>crate::types::MAX_FILES_PER_CHANGE ||
           self.paths.iter().any(|p|!path_ok(p)||crate::classifier::is_guarded_path(p)||crate::classifier::is_zone_a_forbidden_path(p)) ||
           self.paths.iter().collect::<HashSet<_>>().len()!=self.paths.len() ||
           self.operations.is_empty() ||
           self.operations.iter().any(|o|!ops.contains(&o.as_str())) ||
           self.operations.iter().collect::<HashSet<_>>().len()!=self.operations.len() ||
           (self.read_only && (!self.paths.is_empty()||self.operations.iter().any(|o|o=="verify"))) ||
           (!self.read_only && self.paths.is_empty()) {
            return Err(invalid("INVALID_SESSION_GRANT"));
        }
        Ok(())
    }
}
#[derive(Clone)]
pub struct Bound { pub grant:Grant, pub fence:Option<u64> }
pub async fn register(State(e):State<Arc<GroundTruthEngine>>,h:HeaderMap,body:String)->WebResult<Json<serde_json::Value>> {
    let issuer=key("GENESIS_SESSION_ISSUER_PUBLIC_KEY")?;
    authentic(&issuer,&h,"/api/truth/session",&body)?;
    let grant:Grant=serde_json::from_str(&body)?;
    grant.validate()?;
    let conn=e.write_conn.lock().map_err(|_|unavailable())?;
    let n=conn.execute("INSERT OR IGNORE INTO gt_web_sessions(session_id,token_hash,grant_json,expires) VALUES(?1,?2,?3,?4)",
        params![grant.session_id,grant.token_sha256,serde_json::to_string(&grant)?,grant.expires_at])?;
    if n!=1 {return Err(conflict("SESSION_ALREADY_USED"));}
    Ok(Json(serde_json::json!({"ok":true,"session_id":grant.session_id,"expires_at":grant.expires_at})))
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Revocation { session_id:String }
pub async fn revoke(State(e):State<Arc<GroundTruthEngine>>,h:HeaderMap,body:String)->WebResult<Json<serde_json::Value>> {
    authentic(&key("GENESIS_SESSION_ISSUER_PUBLIC_KEY")?,&h,"/api/truth/session/revoke",&body)?;
    let req:Revocation=serde_json::from_str(&body)?;
    if !hex_len(&req.session_id,32){return Err(invalid("INVALID_SESSION_ID"));}
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    c.execute("UPDATE gt_web_sessions SET revoked=1 WHERE session_id=?1",params![req.session_id])?;
    Ok(Json(serde_json::json!({"ok":true})))
}
fn op(method:&str,path:&str)->Option<(&'static str,bool)>{
    match (method,path) {
        ("GET","/api/truth/live")|("GET","/api/truth/live.md")=>Some(("live",false)),
        ("GET","/api/realtime/ws")|("GET","/api/realtime/sse")=>Some(("stream",true)),
        ("POST","/api/truth/admit")=>Some(("admit",true)),
        ("POST","/api/truth/verify-fence")=>Some(("verify",true)),
        ("POST","/api/truth/flow")=>Some(("flow",true)),
        ("POST","/api/truth/yield")|("POST","/api/truth/yield/status")=>Some(("yield",true)),
        ("POST","/v1/role/chat")=>Some(("chat",true)),
        _=>None
    }
}
fn bind(e:&GroundTruthEngine,h:&HeaderMap,method:&str,path:&str)->WebResult<Bound>{
    let (operation,requires_fence)=op(method,path).ok_or_else(||forbidden("OPERATION_NOT_ADMITTED"))?;
    let raw=head(h,"authorization").and_then(|s|s.strip_prefix("Bearer "))
        .filter(|s|hex_len(s,64)).ok_or_else(||err(StatusCode::UNAUTHORIZED,"NO_SESSION"))?;
    let mut conn=e.write_conn.lock().map_err(|_|unavailable())?;
    let tx=conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row:Option<(String,i64,i64)>=tx.query_row(
        "SELECT grant_json,expires,revoked FROM gt_web_sessions WHERE token_hash=?1",
        params![hash(raw.as_bytes())],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let (raw_grant,expires,revoked)=row.ok_or_else(||err(StatusCode::UNAUTHORIZED,"NO_SESSION"))?;
    let grant:Grant=serde_json::from_str(&raw_grant)?;
    if expires<=now() || revoked!=0 {return Err(forbidden("EXPIRED_OR_REVOKED_SESSION"));}
    if head(h,"x-estate-ticket")!=Some(grant.instruction_id.as_str()) {return Err(forbidden("WRONG_TICKET"));}
    if !grant.operations.iter().any(|x|x==operation){return Err(forbidden("UNADMITTED_OPERATION"));}
    let fence=if requires_fence {
        let presented=head(h,"x-genesis-fence").and_then(|s|s.parse::<u64>().ok()).ok_or_else(||conflict("FENCE_REQUIRED"))?;
        let persisted:i64=tx.query_row("SELECT authoritative_token FROM kernel_fence_state WHERE singleton_id=1",[],|r|r.get(0))?;
        if persisted<0 || presented!=persisted as u64 {return Err(conflict("STALE_FENCING_TOKEN"));}
        Some(presented)
    } else {None};
    let nonce=head(h,"x-estate-nonce").filter(|s|hex_len(s,32)||hex_len(s,64)).ok_or_else(||conflict("NONCE_REQUIRED"))?;
    let n=tx.execute("INSERT OR IGNORE INTO gt_web_nonces(session_id,nonce) VALUES(?1,?2)",params![grant.session_id,nonce])?;
    if n!=1 {return Err(conflict("REPLAY"));}
    tx.commit()?;
    Ok(Bound{grant,fence})
}
pub async fn gate(State(e):State<Arc<GroundTruthEngine>>,mut req:Request,next:Next)->Response {
    match bind(&e,req.headers(),req.method().as_str(),req.uri().path()) {
        Ok(bound)=>{
            req.extensions_mut().insert(bound);
            let mut response=next.run(req).await;
            response.headers_mut().insert(header::CACHE_CONTROL,HeaderValue::from_static("private, no-store"));
            response
        }
        Err(why)=>why.into_response()
    }
}
pub fn bind_admission(bound:&Bound,req:&mut crate::types::PrerequisiteGateRequest)->WebResult<()> {
    let g=&bound.grant;
    let mut actual=req.planned_paths.clone();actual.sort();
    let mut allowed=g.paths.clone();allowed.sort();
    if req.role_id!=g.role_id || req.repo_full_name!=g.repo_full_name ||
       actual!=allowed || req.read_only_recon!=g.read_only || req.is_atomic_ic_bundle {
        return Err(forbidden("UNADMITTED_SCOPE_OR_ROLE"));
    }
    if Some(req.seen_fencing_token)!=bound.fence {return Err(conflict("STALE_FENCING_TOKEN"));}
    req.agent_surface=g.principal.clone();
    let ttl=(g.expires_at-now()).max(0) as u64;
    if ttl==0 {return Err(forbidden("SESSION_EXPIRED"));}
    req.ttl_seconds=Some(req.ttl_seconds.unwrap_or(300).min(ttl));
    Ok(())
}
pub fn still_live(e:&GroundTruthEngine,b:&Bound)->WebResult<()> {
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    let active:i64=c.query_row("SELECT count(*) FROM gt_web_sessions WHERE session_id=?1 AND revoked=0 AND expires>?2",
        params![b.grant.session_id,now()],|r|r.get(0))?;
    if active!=1{return Err(forbidden("SESSION_EXPIRED_OR_REVOKED"));}
    if let Some(f)=b.fence {
        let n:i64=c.query_row("SELECT authoritative_token FROM kernel_fence_state WHERE singleton_id=1",[],|r|r.get(0))?;
        if n<0 || n as u64!=f {return Err(conflict("STALE_FENCING_TOKEN"));}
    }
    Ok(())
}
pub fn bind_lease(e:&GroundTruthEngine,b:&Bound,id:&str)->WebResult<()> {
    still_live(e,b)?;
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    c.execute("INSERT INTO gt_web_lease_binding(lease_id,session_id) VALUES(?1,?2)",params![id,b.grant.session_id])?;
    Ok(())
}
pub fn verify_lease(e:&GroundTruthEngine,b:&Bound,req:&crate::types::VerifyFenceRequest)->WebResult<()> {
    still_live(e,b)?;
    if b.grant.read_only || Some(req.presented_fencing_token)!=b.fence ||
       req.touched_paths.is_empty() || req.touched_paths.iter().any(|p|!b.grant.paths.contains(p)) {
        return Err(forbidden("UNADMITTED_SCOPE"));
    }
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    let stored:Option<String>=c.query_row("SELECT session_id FROM gt_web_lease_binding WHERE lease_id=?1",params![req.lease_id],|r|r.get(0)).optional()?;
    if stored.as_deref()!=Some(b.grant.session_id.as_str()){return Err(forbidden("FOREIGN_LEASE"));}
    Ok(())
}

// Signed, immutable acceptance contracts are projections of the existing FLOW instruction.
// An agent cannot issue acceptance, register a verifier, or set a yield amount.
#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Criterion {
    pub criterion_id:String, pub predicate_sha256:String,
    pub verifier_principal:String, pub verifier_public_key:String
}
#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Acceptance {
    pub instruction_id:String, pub accepted_event_id:String, pub expected_outcome_digest:String,
    pub producer_principal:String, pub repo_full_name:String,
    pub accepted_at:i64, pub criteria:Vec<Criterion>,
}
impl Acceptance {
    fn validate(&self,authority:&FounderVerifier,issuer:&FounderVerifier)->WebResult<()> {
        if !name(&self.instruction_id)||!name(&self.accepted_event_id)||!hex_len(&self.expected_outcome_digest,64)||
           !name(&self.producer_principal)||!crate::types::TRACKED_REPOS.contains(&self.repo_full_name.as_str())||
           self.accepted_at<=0||self.accepted_at>now()||self.criteria.is_empty()||self.criteria.len()>32||
           self.criteria.iter().map(|x|&x.criterion_id).collect::<HashSet<_>>().len()!=self.criteria.len() {
            return Err(invalid("INVALID_ACCEPTANCE"));
        }
        for c in &self.criteria {
            let v=FounderVerifier::from_hex(&c.verifier_public_key).map_err(|_|invalid("INVALID_VERIFIER_KEY"))?;
            if !name(&c.criterion_id)||!name(&c.verifier_principal)||c.verifier_principal==self.producer_principal||
               !hex_len(&c.predicate_sha256,64)||!distinct(&v,authority)||!distinct(&v,issuer) {
                return Err(invalid("INDEPENDENT_VERIFIER_REQUIRED"));
            }
        }
        Ok(())
    }
}
pub async fn accept(State(e):State<Arc<GroundTruthEngine>>,h:HeaderMap,body:String)->WebResult<Json<serde_json::Value>>{
    let authority=key("GENESIS_ACCEPTANCE_AUTHORITY_PUBLIC_KEY")?;
    let issuer=key("GENESIS_SESSION_ISSUER_PUBLIC_KEY")?;
    if !distinct(&authority,&issuer){return Err(unavailable());}
    authentic(&authority,&h,"/api/truth/acceptance",&body)?;
    let a:Acceptance=serde_json::from_str(&body)?;
    a.validate(&authority,&issuer)?;
    let canonical=serde_json::to_string(&a)?;
    let digest=hash(canonical.as_bytes());
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    let n=c.execute("INSERT OR IGNORE INTO gt_flow_acceptances(instruction_id,contract_hash,contract_json) VALUES(?1,?2,?3)",
        params![a.instruction_id,digest,canonical])?;
    if n!=1{return Err(conflict("ACCEPTANCE_IMMUTABLE"));}
    Ok(Json(serde_json::json!({"ok":true,"instruction_id":a.instruction_id,"contract_sha256":digest})))
}
#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FlowArtifact {
    pub contract_sha256:String, pub release_sha:String, pub artifact_sha256:String,
    pub flow_event_id:String,
}
fn acceptance(c:&rusqlite::Connection,instruction:&str)->WebResult<(String,Acceptance)>{
    let row:Option<(String,String)>=c.query_row("SELECT contract_hash,contract_json FROM gt_flow_acceptances WHERE instruction_id=?1",
        params![instruction],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    let (h,s)=row.ok_or_else(||invalid("NO_AUTHENTIC_ACCEPTANCE"))?;
    if hash(s.as_bytes())!=h{return Err(unavailable());}
    Ok((h,serde_json::from_str(&s)?))
}
fn record_artifact(e:&GroundTruthEngine,b:&Bound,a:&FlowArtifact)->WebResult<serde_json::Value>{
    still_live(e,b)?;
    if !hex_len(&a.contract_sha256,64)||!hex_len(&a.release_sha,40)||!hex_len(&a.artifact_sha256,64)||!name(&a.flow_event_id){
        return Err(invalid("INVALID_FLOW_ARTIFACT"));
    }
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    let (digest,contract)=acceptance(&c,&b.grant.instruction_id)?;
    if digest!=a.contract_sha256 || contract.producer_principal!=b.grant.principal || contract.repo_full_name!=b.grant.repo_full_name {
        return Err(forbidden("ARTIFACT_NOT_BOUND_TO_INSTRUCTION"));
    }
    let raw=serde_json::to_string(&a)?;
    let id=hash(serde_json::to_vec(&(&b.grant.instruction_id,&b.grant.principal,&a))?.as_slice());
    c.execute("INSERT OR IGNORE INTO gt_flow_artifacts(artifact_id,instruction_id,producer,artifact_json,submitted_at) VALUES(?1,?2,?3,?4,?5)",
        params![id,b.grant.instruction_id,b.grant.principal,raw,now()])?;
    // No yield/status field is writable by the model.
    Ok(serde_json::json!({"accepted_artifact_id":id,"instruction_id":b.grant.instruction_id}))
}
pub async fn flow(State(e):State<Arc<GroundTruthEngine>>,Extension(b):Extension<Bound>,Json(a):Json<FlowArtifact>)->WebResult<Json<serde_json::Value>>{
    Ok(Json(record_artifact(&e,&b,&a)?))
}
#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observation {
    pub instruction_id:String, pub accepted_event_id:String, pub contract_sha256:String,
    pub expected_outcome_digest:String, pub producer_principal:String,
    pub artifact_id:String, pub release_sha:String, pub criterion_id:String,
    pub predicate_sha256:String, pub verifier_principal:String,
    pub evidence_sha256:String, pub source_receipt_id:String, pub sequence:i64,
    pub observed_at:i64, pub valid_until:i64, pub verdict:String,
}
pub async fn observe(State(e):State<Arc<GroundTruthEngine>>,h:HeaderMap,body:String)->WebResult<Json<serde_json::Value>>{
    let o:Observation=serde_json::from_str(&body)?;
    if !name(&o.source_receipt_id)||!hex_len(&o.evidence_sha256,64)||o.sequence<=0||
       o.observed_at<=0||o.observed_at>now()||o.valid_until<=o.observed_at||
       o.valid_until>o.observed_at.saturating_add(86_400)||!matches!(o.verdict.as_str(),"PASS"|"FAIL") {
        return Err(invalid("INVALID_OBSERVATION"));
    }
    let c=e.write_conn.lock().map_err(|_|unavailable())?;
    let (digest,a)=acceptance(&c,&o.instruction_id)?;
    let criterion=a.criteria.iter().find(|x|x.criterion_id==o.criterion_id).ok_or_else(||forbidden("UNKNOWN_CRITERION"))?;
    let v=FounderVerifier::from_hex(&criterion.verifier_public_key).map_err(|_|unavailable())?;
    let sig=authentic(&v,&h,"/api/truth/observation",&body)?;
    if o.accepted_event_id!=a.accepted_event_id||o.contract_sha256!=digest||o.expected_outcome_digest!=a.expected_outcome_digest||
       o.producer_principal!=a.producer_principal||o.verifier_principal!=criterion.verifier_principal||
       o.verifier_principal==o.producer_principal||o.predicate_sha256!=criterion.predicate_sha256 {
        return Err(forbidden("UNLINKED_OR_SELF_VERIFIED_OBSERVATION"));
    }
    let row:Option<(String,String,i64)>=c.query_row(
        "SELECT producer,artifact_json,submitted_at FROM gt_flow_artifacts WHERE artifact_id=?1 AND instruction_id=?2",
        params![o.artifact_id,o.instruction_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let (producer,raw,submitted)=row.ok_or_else(||invalid("UNKNOWN_FLOW_ARTIFACT"))?;
    let artifact:FlowArtifact=serde_json::from_str(&raw)?;
    if producer!=o.producer_principal||artifact.release_sha!=o.release_sha||artifact.contract_sha256!=digest||
       o.observed_at<submitted||o.observed_at<a.accepted_at {
        return Err(forbidden("OBSERVATION_TARGET_MISMATCH"));
    }
    let observation_hash=hash(body.as_bytes());
    let n=c.execute("INSERT INTO gt_external_yield_observations(artifact_id,criterion_id,observation_hash,observation_json,signature,sequence,verdict,observed_at,valid_until)
        VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)
        ON CONFLICT(artifact_id,criterion_id) DO UPDATE SET observation_hash=excluded.observation_hash,observation_json=excluded.observation_json,signature=excluded.signature,sequence=excluded.sequence,verdict=excluded.verdict,observed_at=excluded.observed_at,valid_until=excluded.valid_until
        WHERE excluded.sequence>gt_external_yield_observations.sequence AND excluded.observed_at>=gt_external_yield_observations.observed_at",
        params![o.artifact_id,o.criterion_id,observation_hash,body,sig,o.sequence,o.verdict,o.observed_at,o.valid_until])?;
    if n!=1{return Err(conflict("STALE_OR_REPLAYED_OBSERVATION"));}
    Ok(Json(serde_json::json!({"ok":true,"observation_id":observation_hash})))
}
#[derive(Debug,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StatusRequest { pub artifact_id:String }
#[derive(Debug,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReportRequest { pub artifact_id:String,pub yield_receipt_id:String }
fn projection(e:&GroundTruthEngine,b:&Bound,id:&str)->WebResult<serde_json::Value>{
    still_live(e,b)?;
    let mut c=e.write_conn.lock().map_err(|_|unavailable())?;
    let tx=c.transaction_with_behavior(TransactionBehavior::Deferred)?;
    let (digest,a)=acceptance(&tx,&b.grant.instruction_id)?;
    let row:Option<String>=tx.query_row("SELECT artifact_json FROM gt_flow_artifacts WHERE instruction_id=?1 AND artifact_id=?2",
        params![b.grant.instruction_id,id],|r|r.get(0)).optional()?;
    let artifact:FlowArtifact=serde_json::from_str(&row.ok_or_else(||invalid("ARTIFACT_NOT_FOUND"))?)?;
    if artifact.contract_sha256!=digest{return Err(invalid("ACCEPTANCE_MISMATCH"));}
    let mut hashes=Vec::new();
    let mut until=i64::MAX;
    for criterion in &a.criteria{
        let r:Option<(String,String,i64)>=tx.query_row("SELECT observation_hash,verdict,valid_until FROM gt_external_yield_observations WHERE artifact_id=?1 AND criterion_id=?2",
            params![id,criterion.criterion_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
        if let Some((h,v,t))=r {
            if v=="PASS" && t>now(){hashes.push(h);until=until.min(t);}
        }
    }
    let verified=hashes.len()==a.criteria.len();
    hashes.sort();
    let receipt=if verified {Some(hash(&serde_json::to_vec(&("GENESIS_YIELD_V1",&digest,id,&hashes))?))}else{None};
    let result=serde_json::json!({
        "instruction_id":a.instruction_id,"accepted_event_id":a.accepted_event_id,
        "expected_outcome_digest":a.expected_outcome_digest,"contract_sha256":digest,
        "artifact_id":id,"release_sha":artifact.release_sha,"verified_yield":if verified {1}else{0},
        "yield_receipt_id":receipt,"independent_observation_ids":hashes,
        "required_observations":a.criteria.len(),"valid_until":if verified{Some(until)}else{None}
    });
    tx.commit()?;
    Ok(result)
}
pub async fn status(State(e):State<Arc<GroundTruthEngine>>,Extension(b):Extension<Bound>,Json(r):Json<StatusRequest>)->WebResult<Json<serde_json::Value>>{
    Ok(Json(projection(&e,&b,&r.artifact_id)?))
}
fn report(e:&GroundTruthEngine,b:&Bound,r:&ReportRequest)->WebResult<serde_json::Value>{
    let p=projection(e,b,&r.artifact_id)?;
    if !hex_len(&r.yield_receipt_id,64)||p["verified_yield"]!=1||p["yield_receipt_id"].as_str()!=Some(r.yield_receipt_id.as_str()){
        return Err(invalid("INDEPENDENT_YIELD_RECEIPT_REQUIRED"));
    }
    Ok(p)
}
pub async fn render_yield(State(e):State<Arc<GroundTruthEngine>>,Extension(b):Extension<Bound>,Json(r):Json<ReportRequest>)->WebResult<Json<serde_json::Value>>{
    Ok(Json(report(&e,&b,&r)?))
}
