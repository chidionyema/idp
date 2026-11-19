use anyhow::{anyhow, Result};
use genesis_ground_truth::{PrerequisiteGateRequest, PrerequisiteGateVerdict};
use serde_json::Value;
use std::time::{SystemTime,UNIX_EPOCH};
fn nonce()->String {
    use std::sync::atomic::{AtomicU64,Ordering};
    static COUNT:AtomicU64=AtomicU64::new(0);
    let n=COUNT.fetch_add(1,Ordering::SeqCst);
    let t=SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_nanos();
    genesis_ground_truth::web::hash(format!("{}:{t}:{n}",std::process::id()).as_bytes())
}

/// Universal zero-friction prerequisite CLI for ANY agent surface (Claude Code, OpenCode, Codex, agent-sandbox.yml).
/// Usage:
///   genesis-truth-boot <base_url> <agent_surface> <role_id> <repo_full_name> [--read-only | path1 path2 ...]
/// Prints the live 6-block Markdown ground truth + lease JSON, and exits non-zero if NOT admitted.
#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 5 {
        return Err(anyhow!(
            "Usage: {} <base_url> <agent_surface> <role_id> <repo_full_name> [--read-only | path1 ...]",
            args[0]
        ));
    }

    let base_url = args[1].trim_end_matches('/');
    let agent_surface = args[2].clone();
    let role_id = args[3].clone();
    let repo_full_name = args[4].clone();
    let rest = &args[5..];
    let read_only = rest.iter().any(|a| a == "--read-only");
    let is_atomic_ic = rest.iter().any(|a| a == "--atomic-ic");
    let planned_paths: Vec<String> = rest
        .iter()
        .filter(|a| *a != "--read-only" && *a != "--atomic-ic")
        .cloned()
        .collect();

    let ticket=std::env::var("GENESIS_INSTRUCTION_ID").map_err(|_|anyhow!("NO_BOUND_INSTRUCTION"))?;
    let token=std::env::var("GENESIS_SESSION_TOKEN").map_err(|_|anyhow!("NO_AUTHENTICATED_SESSION"))?;
    if ticket.trim().is_empty()||token.len()!=64{return Err(anyhow!("INVALID_SESSION_BINDING"));}
    let base=reqwest::Url::parse(base_url)?;
    if base.scheme()!="https" && !(base.scheme()=="http" && matches!(base.host_str(),Some("127.0.0.1"|"localhost"|"::1"))){
        return Err(anyhow!("SESSION_REQUIRES_TLS"));
    }
    let client = reqwest::Client::builder().redirect(reqwest::redirect::Policy::none())
        .timeout(std::time::Duration::from_secs(20)).build()?;

    // Step 1: Fetch live ground-truth fence
    let live: Value = client
        .get(format!("{base_url}/api/truth/live"))
        .bearer_auth(&token).header("x-estate-ticket",&ticket).header("x-estate-nonce",nonce())
        .send()
        .await?
        .error_for_status()?
        .json()
        .await?;
    let fence = live
        .pointer("/projection/fencing_token")
        .and_then(|v| v.as_u64())
        .ok_or_else(|| anyhow!("Missing fencing_token in /api/truth/live response"))?;

    // Step 2: Request mandatory admission lease bound to live fence
    let req = PrerequisiteGateRequest {
        agent_surface,
        role_id,
        repo_full_name,
        seen_fencing_token: fence,
        planned_paths,
        is_atomic_ic_bundle: is_atomic_ic,
        read_only_recon: read_only,
        ttl_seconds: Some(300),
    };

    let resp = client
        .post(format!("{base_url}/api/truth/admit"))
        .bearer_auth(&token).header("x-estate-ticket",&ticket).header("x-estate-nonce",nonce())
        .header("x-genesis-fence",fence.to_string()).json(&req)
        .send()
        .await?;
    let status = resp.status();
    let verdict: PrerequisiteGateVerdict = resp.json().await?;

    println!("{}", verdict.live_markdown_brief);
    eprintln!(
        "ADMISSION_RECEIPT={}",
        serde_json::to_string(&serde_json::json!({
            "admitted": verdict.admitted,
            "httpStatus": status.as_u16(),
            "reason": verdict.reason,
            "leaseId": verdict.lease_id,
            "boundFencingToken": verdict.bound_fencing_token,
            "scopeSha256": verdict.scope_sha256,
            "providerPool": verdict.selected_provider_pool
        }))?
    );

    if !verdict.admitted {
        std::process::exit(2);
    }
    Ok(())
}
