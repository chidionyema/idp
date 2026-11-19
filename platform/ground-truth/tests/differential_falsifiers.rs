use axum::body::Body;
use axum::http::{Request, StatusCode};
use ed25519_dalek::SigningKey;
use genesis_ground_truth::classifier::scan_idp_counterexamples;
use genesis_ground_truth::crypto::{
    compute_github_webhook_hmac, sign_canonical_request, FounderVerifier,
};
use genesis_ground_truth::types::{
    PrerequisiteGateRequest, ProviderEventRequest, RoleAllocationUpdateRequest, VerifyFenceRequest,
};
use genesis_ground_truth::{ground_truth_router, GroundTruthEngine};
use std::collections::BTreeMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tempfile::{NamedTempFile, TempDir};
use tower::ServiceExt;

fn setup_engine() -> (NamedTempFile, [u8; 32], std::sync::Arc<GroundTruthEngine>) {
    let tmp = NamedTempFile::new().expect("temp sqlite");
    let seed = [42u8; 32];
    let signing_key = SigningKey::from_bytes(&seed);
    let pub_hex = hex::encode(signing_key.verifying_key().to_bytes());
    let verifier = FounderVerifier::from_hex(&pub_hex).expect("valid pubkey");
    let engine = GroundTruthEngine::open(
        tmp.path(),
        10,
        Some("super-secret-webhook-key".into()),
        Some(verifier),
    )
    .expect("open engine");
    (tmp, seed, engine)
}

#[test]
fn falsifier_rejects_zone_a_legacy_estate_path() {
    let err = GroundTruthEngine::open("/tmp/.estate/estate.db", 1, None, None);
    assert!(err.is_err());
    let msg = err.err().unwrap().to_string();
    assert!(
        msg.contains("HISTORY_QUARANTINE_VIOLATION"),
        "expected quarantine violation, got {msg}"
    );
}

#[tokio::test]
async fn falsifier_rejects_forged_github_webhook_and_streams_valid_push_under_50ms() {
    let (_tmp, _seed, engine) = setup_engine();
    let mut rx = engine.tx.subscribe();
    let app = ground_truth_router(engine.clone());

    let body = serde_json::json!({
        "repository": { "full_name": "chidionyema/argon", "default_branch": "main" },
        "workflow_run": {
            "id": 99001,
            "name": "Genesis provenance gate",
            "head_branch": "main",
            "head_sha": "deadbeef1234",
            "event": "push",
            "status": "completed",
            "conclusion": "failure",
            "failing_step": "Verify provenance and protected paths",
            "updated_at": "2026-11-19T12:40:00Z"
        }
    })
    .to_string();

    // 1. Forged signature -> 401 UNAUTHORIZED
    let bad_req = Request::builder()
        .method("POST")
        .uri("/api/webhooks/github")
        .header("x-github-delivery", "deliv-1")
        .header("x-github-event", "workflow_run")
        .header("x-hub-signature-256", "sha256=0000")
        .body(Body::from(body.clone()))
        .unwrap();
    let bad_resp = app.clone().oneshot(bad_req).await.unwrap();
    assert_eq!(bad_resp.status(), StatusCode::UNAUTHORIZED);

    // 2. Valid HMAC -> 200 OK, fence bumps 10 -> 11, WS broadcast < 50ms
    let sig = compute_github_webhook_hmac("super-secret-webhook-key", body.as_bytes()).unwrap();
    let good_req = Request::builder()
        .method("POST")
        .uri("/api/webhooks/github")
        .header("x-github-delivery", "deliv-1")
        .header("x-github-event", "workflow_run")
        .header("x-hub-signature-256", sig)
        .body(Body::from(body))
        .unwrap();
    let good_resp = app.oneshot(good_req).await.unwrap();
    assert_eq!(good_resp.status(), StatusCode::OK);

    let env = tokio::time::timeout(Duration::from_millis(50), rx.recv())
        .await
        .expect("broadcast within 50ms")
        .expect("valid envelope");
    assert_eq!(env.fencing_token, 11);
    assert_eq!(env.merkle_root.len(), 64);

    let proj = engine.read_live_projection().unwrap();
    assert_eq!(proj.block1_fleet_kpis.argon_ci_fail_pct, 100.0);
    assert_eq!(proj.block4_failure_taxonomy[0].failure_class, "GATE-ALWAYS-RED");
}

#[tokio::test]
async fn falsifier_blocks_stale_fence_and_429_provider_exhaustion_before_inference() {
    let (_tmp, _seed, engine) = setup_engine();

    // 1. Stale fence rejected before inference
    let stale = engine
        .admit_agent_turn(&PrerequisiteGateRequest {
            agent_surface: "opencode".into(),
            role_id: "coder".into(),
            repo_full_name: "chidionyema/idp".into(),
            seen_fencing_token: 9,
            planned_paths: vec!["src/main.rs".into()],
            is_atomic_ic_bundle: false,
            read_only_recon: false,
            ttl_seconds: Some(300),
        })
        .unwrap();
    assert!(!stale.admitted);
    assert!(stale.reason.starts_with("STALE_FENCING_TOKEN"));

    // 2. Valid admission gets lease + scope_sha256
    let ok = engine
        .admit_agent_turn(&PrerequisiteGateRequest {
            agent_surface: "opencode".into(),
            role_id: "coder".into(),
            repo_full_name: "chidionyema/idp".into(),
            seen_fencing_token: 10,
            planned_paths: vec!["src/main.rs".into()],
            is_atomic_ic_bundle: false,
            read_only_recon: false,
            ttl_seconds: Some(300),
        })
        .unwrap();
    assert!(ok.admitted);
    let lease_id = ok.lease_id.clone().unwrap();
    let scope_sha = ok.scope_sha256.clone().unwrap();

    // 3. Touching an unadmitted path is refused at submit
    let scope_breach = engine
        .verify_fence(&VerifyFenceRequest {
            lease_id: lease_id.clone(),
            presented_fencing_token: 10,
            touched_paths: vec!["src/main.rs".into(), ".github/workflows/greenlane.yml".into()],
            presented_scope_sha256: scope_sha.clone(),
        })
        .unwrap();
    assert!(!scope_breach.valid);
    assert_eq!(scope_breach.code, "UNADMITTED_PATH_TOUCHED");

    // 4. Provider 429 flips circuit breaker, bumps fence 10 -> 11, invalidates old lease & blocks new admission
    engine
        .ingest_provider_signal(&ProviderEventRequest {
            provider_id: "minimax".into(),
            http_status: 429,
            circuit_open_seconds: Some(120),
            detail: Some("rate_limit_error".into()),
        })
        .unwrap();

    let fenced_submit = engine
        .verify_fence(&VerifyFenceRequest {
            lease_id,
            presented_fencing_token: 10,
            touched_paths: vec!["src/main.rs".into()],
            presented_scope_sha256: scope_sha,
        })
        .unwrap();
    assert!(!fenced_submit.valid);
    assert_eq!(fenced_submit.code, "STALE_FENCING_TOKEN");

    let blocked_429 = engine
        .admit_agent_turn(&PrerequisiteGateRequest {
            agent_surface: "opencode".into(),
            role_id: "coder".into(),
            repo_full_name: "chidionyema/idp".into(),
            seen_fencing_token: 11,
            planned_paths: vec!["src/main.rs".into()],
            is_atomic_ic_bundle: false,
            read_only_recon: false,
            ttl_seconds: Some(300),
        })
        .unwrap();
    assert!(!blocked_429.admitted);
    assert!(blocked_429.reason.starts_with("PROVIDER_CAPACITY_EXHAUSTED"));
}

#[tokio::test]
async fn falsifier_founder_signed_role_allocation_rejects_unsigned_and_single_vendor() {
    let (_tmp, seed, engine) = setup_engine();
    let app = ground_truth_router(engine.clone());

    let multi_body = serde_json::to_string(&RoleAllocationUpdateRequest {
        role_id: "coder".into(),
        ordered_pool: vec!["deepseek".into(), "zai".into(), "minimax".into()],
        weights: BTreeMap::new(),
        budget_cap_usd: 5.0,
        max_tokens_cap: 2048,
        circuit_breaker_policy: None,
        founder_override_single_vendor: false,
    })
    .unwrap();

    // 1. Unsigned -> 401 UNAUTHORIZED
    let unsigned = Request::builder()
        .method("POST")
        .uri("/api/truth/roles")
        .body(Body::from(multi_body.clone()))
        .unwrap();
    assert_eq!(
        app.clone().oneshot(unsigned).await.unwrap().status(),
        StatusCode::UNAUTHORIZED
    );

    // 2. Signed single-vendor without override -> 422 UNPROCESSABLE_ENTITY
    let single_body = serde_json::to_string(&RoleAllocationUpdateRequest {
        role_id: "coder".into(),
        ordered_pool: vec!["gemini".into()],
        weights: BTreeMap::new(),
        budget_cap_usd: 5.0,
        max_tokens_cap: 2048,
        circuit_breaker_policy: None,
        founder_override_single_vendor: false,
    })
    .unwrap();
    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let (ts1, sig1) = sign_canonical_request(&seed, "POST", "/api/truth/roles", now, &single_body);
    let single_req = Request::builder()
        .method("POST")
        .uri("/api/truth/roles")
        .header("x-genesis-timestamp", ts1)
        .header("x-genesis-signature", sig1)
        .body(Body::from(single_body))
        .unwrap();
    assert_eq!(
        app.clone().oneshot(single_req).await.unwrap().status(),
        StatusCode::UNPROCESSABLE_ENTITY
    );

    // 3. Signed multi-vendor -> 200 OK and reflected immediately in live projection
    let (ts2, sig2) = sign_canonical_request(&seed, "POST", "/api/truth/roles", now, &multi_body);
    let ok_req = Request::builder()
        .method("POST")
        .uri("/api/truth/roles")
        .header("x-genesis-timestamp", ts2)
        .header("x-genesis-signature", sig2)
        .body(Body::from(multi_body))
        .unwrap();
    assert_eq!(app.oneshot(ok_req).await.unwrap().status(), StatusCode::OK);

    let proj = engine.read_live_projection().unwrap();
    assert_eq!(proj.block6_role_allocations.len(), 1);
    assert_eq!(proj.block6_role_allocations[0].ordered_pool, vec!["deepseek", "zai", "minimax"]);
}

#[test]
fn falsifier_counterexample_scanner_catches_and_clears_all_5_terminus_defects() {
    let dir = TempDir::new().unwrap();
    std::fs::create_dir_all(dir.path().join("bin")).unwrap();
    std::fs::create_dir_all(dir.path().join(".github/workflows")).unwrap();

    // Broken state matching TERMINUS counterexamples
    std::fs::write(
        dir.path().join("bin/verify_three_proofs.py"),
        "parser.add_argument('--founder-seal', action='store_true')\ndef check(has_founder_seal: bool): pass\n",
    )
    .unwrap();
    std::fs::write(
        dir.path().join("bin/idp-shadow"),
        "def stand_in_database():\n    pass\n",
    )
    .unwrap();
    std::fs::write(
        dir.path().join(".github/workflows/agent-sandbox.yml"),
        "env:\n  CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}\nrun: python3 bin/idp-agent-base-apply.py --base-file a --patch b\n",
    )
    .unwrap();
    std::fs::write(
        dir.path().join(".github/workflows/estate-state.yml"),
        "on:\n  # - cron: '*/15 * * * *'\n",
    )
    .unwrap();

    let broken = scan_idp_counterexamples(dir.path(), "d5d9d74");
    assert_eq!(broken.len(), 5);
    assert!(
        broken.iter().all(|c| c.verdict == "CONFIRMED_DEFECT"),
        "all 5 TERMINUS defects must trip CONFIRMED_DEFECT: {broken:?}"
    );

    // Remediated state -> all 5 CLEARED
    std::fs::write(
        dir.path().join("bin/verify_three_proofs.py"),
        "def check(auth_trailer: str): return verify_ed25519(auth_trailer)\n",
    )
    .unwrap();
    std::fs::write(
        dir.path().join("bin/idp-shadow"),
        "def stand_in_database():\n    pass\nstand_in_database()\n",
    )
    .unwrap();
    std::fs::write(
        dir.path().join(".github/workflows/agent-sandbox.yml"),
        "run: python3 bin/idp-agent-base-apply.py --base-file a --patch b --scope-file s --scope-sha256 h\n",
    )
    .unwrap();
    std::fs::write(
        dir.path().join(".github/workflows/estate-state.yml"),
        "on:\n  workflow_dispatch:\n",
    )
    .unwrap();

    let fixed = scan_idp_counterexamples(dir.path(), "fixed123");
    assert_eq!(fixed.len(), 5);
    assert!(
        fixed.iter().all(|c| c.verdict == "CLEARED"),
        "all 5 remediated checks must report CLEARED: {fixed:?}"
    );
}


#[tokio::test]
async fn web_ingress_refuses_unauthenticated_truth_admission_and_completion() {
    let (_tmp,_seed,engine)=setup_engine();
    let app=ground_truth_router(engine);
    for (method,path) in [
        ("GET","/api/truth/live"),("GET","/api/truth/live.md"),
        ("POST","/api/truth/admit"),("POST","/api/truth/verify-fence"),
        ("POST","/api/truth/flow"),("POST","/api/truth/yield"),("POST","/api/truth/yield/status")
    ] {
        let req=Request::builder().method(method).uri(path)
            .header("content-type","application/json").body(Body::from("{}")).unwrap();
        assert_eq!(app.clone().oneshot(req).await.unwrap().status(),StatusCode::UNAUTHORIZED,"{path}");
    }
}
#[tokio::test]
async fn web_ingress_consumes_nonce_and_refuses_wrong_ticket_stale_fence_and_fake_yield() {
    use genesis_ground_truth::web::{Grant,hash};
    let (_tmp,_seed,engine)=setup_engine();
    let token="b".repeat(64);
    let now=SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let grant=Grant{session_id:"a".repeat(32),token_sha256:hash(token.as_bytes()),
        principal:"quad:web:test".into(),instruction_id:"idp#8068".into(),role_id:"coder".into(),
        repo_full_name:"chidionyema/idp".into(),paths:vec!["src/main.rs".into()],read_only:false,
        expires_at:now+300,operations:vec!["live".into(),"admit".into(),"verify".into(),"yield".into(),"flow".into()]};
    engine.write_conn.lock().unwrap().execute(
        "INSERT INTO gt_web_sessions(session_id,token_hash,grant_json,expires) VALUES(?1,?2,?3,?4)",
        rusqlite::params![grant.session_id,grant.token_sha256,serde_json::to_string(&grant).unwrap(),grant.expires_at]).unwrap();
    let app=ground_truth_router(engine);
    let call=|ticket:&str,fence:&str,nonce:&str,method:&str,path:&str,body:&str|{
        Request::builder().method(method).uri(path).header("authorization",format!("Bearer {token}"))
            .header("x-estate-ticket",ticket).header("x-genesis-fence",fence)
            .header("x-estate-nonce",nonce).header("content-type","application/json").body(Body::from(body.to_owned())).unwrap()
    };
    assert_eq!(app.clone().oneshot(call("","10",&"1".repeat(32),"POST","/api/truth/yield","{}")).await.unwrap().status(),StatusCode::FORBIDDEN);
    assert_eq!(app.clone().oneshot(call("idp#8068","9",&"2".repeat(32),"POST","/api/truth/yield","{}")).await.unwrap().status(),StatusCode::CONFLICT);
    assert_eq!(app.clone().oneshot(call("idp#8068","10",&"3".repeat(32),"GET","/api/truth/live","")).await.unwrap().status(),StatusCode::OK);
    assert_eq!(app.clone().oneshot(call("idp#8068","10",&"3".repeat(32),"GET","/api/truth/live","")).await.unwrap().status(),StatusCode::CONFLICT);
    assert_eq!(app.clone().oneshot(call("idp#8068","10",&"4".repeat(32),"POST","/api/truth/yield",
        r#"{"artifact_id":"a","yield_receipt_id":"made-up","verified_yield":1}"#)).await.unwrap().status(),StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(app.oneshot(call("idp#8068","10",&"5".repeat(32),"POST","/api/truth/yield",
        r#"{"artifact_id":"a","yield_receipt_id":"made-up"}"#)).await.unwrap().status(),StatusCode::UNPROCESSABLE_ENTITY);
}


// Synthetic signing keys are fixture-only. No test is a production receipt.
#[tokio::test]
async fn only_independent_exact_criteria_can_produce_yield_and_a_failure_revokes_it() {
    use genesis_ground_truth::web::{Acceptance,Criterion,FlowArtifact,Grant,Observation,hash};
    use axum::body::to_bytes;
    use serde_json::Value;
    let (_tmp,_seed,engine)=setup_engine();
    let issuer=[43u8;32];
    let authority=[44u8;32];
    let verifiers=[[45u8;32],[46u8;32],[47u8;32]];
    let pubkey=|seed:&[u8;32]|hex::encode(SigningKey::from_bytes(seed).verifying_key().to_bytes());
    std::env::set_var("GENESIS_SESSION_ISSUER_PUBLIC_KEY",pubkey(&issuer));
    std::env::set_var("GENESIS_ACCEPTANCE_AUTHORITY_PUBLIC_KEY",pubkey(&authority));
    let now=||SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let app=ground_truth_router(engine.clone());
    let signed=|path:&str,body:String,seed:&[u8;32]|{
        let (ts,sig)=sign_canonical_request(seed,"POST",path,now(),&body);
        Request::builder().method("POST").uri(path).header("content-type","application/json")
            .header("x-genesis-timestamp",ts).header("x-genesis-signature",sig).body(Body::from(body)).unwrap()
    };
    let body_json=|response:axum::response::Response|async move{
        serde_json::from_slice::<Value>(&to_bytes(response.into_body(),65_536).await.unwrap()).unwrap()
    };
    let principal="quad:web:fixture";
    let ticket="idp#8068";
    let token="c".repeat(64);
    let grant=Grant{session_id:"d".repeat(32),token_sha256:hash(token.as_bytes()),
        principal:principal.into(),instruction_id:ticket.into(),role_id:"coder".into(),
        repo_full_name:"chidionyema/idp".into(),paths:vec!["src/main.rs".into()],read_only:false,
        expires_at:now()+300,operations:vec!["live".into(),"admit".into(),"verify".into(),"flow".into(),"yield".into(),"chat".into()]};
    let grant_body=serde_json::to_string(&grant).unwrap();
    assert_eq!(app.clone().oneshot(signed("/api/truth/session",grant_body.clone(),&authority)).await.unwrap().status(),StatusCode::UNAUTHORIZED);
    assert_eq!(app.clone().oneshot(signed("/api/truth/session",grant_body.clone(),&issuer)).await.unwrap().status(),StatusCode::OK);
    assert_eq!(app.clone().oneshot(signed("/api/truth/session",grant_body,&issuer)).await.unwrap().status(),StatusCode::CONFLICT);
    let acceptance=Acceptance{instruction_id:ticket.into(),accepted_event_id:"flow:accept:8068".into(),
        expected_outcome_digest:"e".repeat(64),producer_principal:principal.into(),repo_full_name:"chidionyema/idp".into(),accepted_at:now()-1,
        criteria:["release_on_main","telegram_delivery","authorized_action_ack"].iter().enumerate().map(|(i,n)|Criterion{
            criterion_id:(*n).into(),predicate_sha256:hash(n.as_bytes()),
            verifier_principal:format!("quad:independent:{i}"),verifier_public_key:pubkey(&verifiers[i])
        }).collect()};
    let accept_body=serde_json::to_string(&acceptance).unwrap();
    assert_eq!(app.clone().oneshot(signed("/api/truth/acceptance",accept_body.clone(),&issuer)).await.unwrap().status(),StatusCode::UNAUTHORIZED);
    let accepted=app.clone().oneshot(signed("/api/truth/acceptance",accept_body,&authority)).await.unwrap();
    assert_eq!(accepted.status(),StatusCode::OK);
    let contract=body_json(accepted).await["contract_sha256"].as_str().unwrap().to_owned();
    let call=|nonce:u64,path:&str,body:Value|{
        Request::builder().method("POST").uri(path).header("authorization",format!("Bearer {token}"))
            .header("x-estate-ticket",ticket).header("x-genesis-fence","10").header("x-estate-nonce",format!("{nonce:032x}"))
            .header("content-type","application/json").body(Body::from(body.to_string())).unwrap()
    };
    let artifact=FlowArtifact{contract_sha256:contract.clone(),release_sha:"a".repeat(40),
        artifact_sha256:"f".repeat(64),flow_event_id:"flow:artifact:8068".into()};
    let response=app.clone().oneshot(call(1,"/api/truth/flow",serde_json::to_value(&artifact).unwrap())).await.unwrap();
    assert_eq!(response.status(),StatusCode::ACCEPTED);
    let id=body_json(response).await["accepted_artifact_id"].as_str().unwrap().to_owned();
    let status=||serde_json::json!({"artifact_id":id});
    let initial=app.clone().oneshot(call(2,"/api/truth/yield/status",status())).await.unwrap();
    assert_eq!(body_json(initial).await["verified_yield"],0);
    assert_eq!(app.clone().oneshot(call(3,"/api/truth/yield",serde_json::json!({"artifact_id":id,"yield_receipt_id":"0".repeat(64)}))).await.unwrap().status(),StatusCode::UNPROCESSABLE_ENTITY);
    let observe=|i:usize,seq:i64,verdict:&str|Observation{
        instruction_id:ticket.into(),accepted_event_id:acceptance.accepted_event_id.clone(),
        contract_sha256:contract.clone(),expected_outcome_digest:acceptance.expected_outcome_digest.clone(),
        producer_principal:principal.into(),artifact_id:id.clone(),release_sha:artifact.release_sha.clone(),
        criterion_id:acceptance.criteria[i].criterion_id.clone(),predicate_sha256:acceptance.criteria[i].predicate_sha256.clone(),
        verifier_principal:acceptance.criteria[i].verifier_principal.clone(),evidence_sha256:hash(format!("fixture:{i}:{seq}").as_bytes()),
        source_receipt_id:format!("test:{i}:{seq}"),sequence:seq,observed_at:now(),valid_until:now()+120,verdict:verdict.into()
    };
    let mut wrong=observe(0,1,"PASS");wrong.release_sha="b".repeat(40);
    assert_eq!(app.clone().oneshot(signed("/api/truth/observation",serde_json::to_string(&wrong).unwrap(),&verifiers[0])).await.unwrap().status(),StatusCode::FORBIDDEN);
    assert_eq!(app.clone().oneshot(signed("/api/truth/observation",serde_json::to_string(&observe(0,1,"PASS")).unwrap(),&issuer)).await.unwrap().status(),StatusCode::UNAUTHORIZED);
    for i in 0..3 {
        let observation=serde_json::to_string(&observe(i,1,"PASS")).unwrap();
        assert_eq!(app.clone().oneshot(signed("/api/truth/observation",observation.clone(),&verifiers[i])).await.unwrap().status(),StatusCode::OK);
        assert_eq!(app.clone().oneshot(signed("/api/truth/observation",observation,&verifiers[i])).await.unwrap().status(),StatusCode::CONFLICT);
        let projection=app.clone().oneshot(call(10+i as u64,"/api/truth/yield/status",status())).await.unwrap();
        assert_eq!(body_json(projection).await["verified_yield"],if i==2{1}else{0});
    }
    let p=body_json(app.clone().oneshot(call(20,"/api/truth/yield/status",status())).await.unwrap()).await;
    let receipt=p["yield_receipt_id"].as_str().unwrap().to_owned();
    assert_eq!(receipt.len(),64);
    let report=||serde_json::json!({"artifact_id":id,"yield_receipt_id":receipt});
    assert_eq!(app.clone().oneshot(call(21,"/api/truth/yield",report())).await.unwrap().status(),StatusCode::OK);
    let mut fake=report();fake["verified_yield"]=serde_json::json!(1);
    assert_eq!(app.clone().oneshot(call(22,"/api/truth/yield",fake)).await.unwrap().status(),StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(app.clone().oneshot(signed("/api/truth/observation",serde_json::to_string(&observe(1,2,"FAIL")).unwrap(),&verifiers[1])).await.unwrap().status(),StatusCode::OK);
    assert_eq!(app.clone().oneshot(call(23,"/api/truth/yield",report())).await.unwrap().status(),StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(app.clone().oneshot(signed("/api/truth/observation",serde_json::to_string(&observe(1,1,"PASS")).unwrap(),&verifiers[1])).await.unwrap().status(),StatusCode::CONFLICT);
    let (a,b)=tokio::join!(app.clone().oneshot(call(24,"/api/truth/yield/status",status())),app.clone().oneshot(call(24,"/api/truth/yield/status",status())));
    let mut codes=vec![a.unwrap().status().as_u16(),b.unwrap().status().as_u16()];codes.sort();
    assert_eq!(codes,vec![200,409]);
    let revoked=serde_json::json!({"session_id":grant.session_id}).to_string();
    assert_eq!(app.clone().oneshot(signed("/api/truth/session/revoke",revoked,&issuer)).await.unwrap().status(),StatusCode::OK);
    assert_eq!(app.oneshot(call(25,"/api/truth/yield/status",status())).await.unwrap().status(),StatusCode::FORBIDDEN);
    std::env::remove_var("GENESIS_SESSION_ISSUER_PUBLIC_KEY");
    std::env::remove_var("GENESIS_ACCEPTANCE_AUTHORITY_PUBLIC_KEY");
}
