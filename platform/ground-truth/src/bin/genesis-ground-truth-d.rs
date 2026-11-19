use genesis_ground_truth::crypto::FounderVerifier;
use genesis_ground_truth::reconciler::cold_boot_reconcile;
use genesis_ground_truth::{ground_truth_router, GroundTruthEngine};
use std::net::SocketAddr;
use std::path::PathBuf;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let db_path = PathBuf::from(
        std::env::var("GENESIS_DB_PATH").unwrap_or_else(|_| "/var/lib/genesis/genesis.db".into()),
    );
    let initial_fence: u64 = std::env::var("GENESIS_INITIAL_FENCE")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(1);
    let webhook_secret = std::env::var("GITHUB_WEBHOOK_SECRET").ok();
    let founder_verifier = FounderVerifier::from_env();

    let engine = GroundTruthEngine::open(&db_path, initial_fence, webhook_secret, founder_verifier)?;

    // Gap-only cold boot reconciliation (runs once at boot if token is present; zero polling)
    if let Ok(token) = std::env::var("GITHUB_READ_TOKEN") {
        let eng_clone = engine.clone();
        tokio::spawn(async move {
            match cold_boot_reconcile(eng_clone, &token).await {
                Ok(n) => eprintln!("[genesis-ground-truth-d] cold-boot reconciled {n} records"),
                Err(e) => eprintln!("[genesis-ground-truth-d] cold-boot reconcile error: {e}"),
            }
        });
    }

    // One private, pre-provisioned mirror; credentials live behind the deployed
    // workload identity, never in the consumer browser or in the source tree.
    if let (Ok(id),Ok(token_file))=(std::env::var("GENESIS_DRIVE_MIRROR_FILE_ID"),std::env::var("GENESIS_DRIVE_TOKEN_FILE")){
        tokio::spawn(genesis_ground_truth::web::drive_mirror(engine.clone(),id,PathBuf::from(token_file)));
    }
    let app = ground_truth_router(engine);
    let addr: SocketAddr = std::env::var("GENESIS_BIND_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:4001".into())
        .parse()?;
    eprintln!("[genesis-ground-truth-d] listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}
