//! Edge Runtime: loads one artifact directory (model.gguf, model-card.yaml, tokenizer.json,
//! pulled by an `oras` init container) and answers `/v1/infer` on loopback (R20).
//! Config by environment only (LAW 46): EDGE_ARTIFACT_DIR, EDGE_BIND, OTEL_EXPORTER_OTLP_ENDPOINT.
use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use opentelemetry::global;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::runtime;

mod engine;
mod server;

fn init_otel() -> Option<opentelemetry_sdk::trace::Tracer> {
    let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").ok()?;
    opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(
            opentelemetry_otlp::new_exporter()
                .http()
                .with_endpoint(endpoint),
        )
        .with_trace_config(
            opentelemetry_sdk::trace::Config::default()
                .with_resource(opentelemetry_sdk::Resource::new(vec![
                    opentelemetry::KeyValue::new("service.name", "edge-runtime"),
                ])),
        )
        .install_batch(runtime::Tokio)
        .ok()
}

/// `--health`: is the server on this box answering? Exit 0 if it is, 1 if it is not.
///
/// WHY THIS EXISTS AS A FLAG AND NOT A PROBE COMMAND. The image is DISTROLESS -- no shell, no curl,
/// no wget -- so a Kubernetes exec probe has nothing to run. And an httpGet probe cannot work at
/// all: the server binds 127.0.0.1 on purpose (R20, enforced below), and the KUBELET issues its
/// probes from outside the pod's network namespace, so it dials the pod IP and gets "connection
/// refused" forever while the container is healthy.
///
/// So the binary checks itself: same process image, same loopback, one exit code. The kubelet runs
/// it INSIDE the container, where 127.0.0.1 is the server's own address.
fn health_check(bind: &str) -> std::process::ExitCode {
    use std::net::TcpStream;
    use std::time::Duration;
    let addr = bind.trim_start_matches("http://");
    match TcpStream::connect_timeout(
        &addr.parse().expect("EDGE_BIND must be host:port"),
        Duration::from_secs(2),
    ) {
        Ok(_) => std::process::ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("health: {addr} refused: {e}");
            std::process::ExitCode::FAILURE
        }
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _tracer = init_otel();
    let subscriber = tracing_subscriber::fmt()
        .json()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .finish();
    if _tracer.is_some() {
        use tracing_subscriber::layer::SubscriberExt;
        tracing::subscriber::set_global_default(
            subscriber.with(tracing_opentelemetry::layer()),
        )?;
    } else {
        tracing::subscriber::set_global_default(subscriber)?;
    }
    let dir = PathBuf::from(std::env::var("EDGE_ARTIFACT_DIR").unwrap_or_else(|_| "artifact".into()));
    let bind = std::env::var("EDGE_BIND").unwrap_or_else(|_| "127.0.0.1:8421".into());
    if !bind.starts_with("127.0.0.1:") {
        anyhow::bail!("EDGE_BIND must be loopback (R20), got {bind}");
    }
    // THE PROBE RUNS BEFORE THE MODEL LOADS. A health check that waits for a 1.1 GB model answers
    // "is the model up", which the readiness gate already asks; this answers "will the listener
    // reach me", which is the question a probe is for and the one that failed for 77 seconds.
    if std::env::args().any(|a| a == "--health") {
        std::process::exit(match health_check(&bind) {
            std::process::ExitCode::SUCCESS => 0,
            _ => 1,
        });
    }
    let engine = engine::Engine::load(&dir)?;
    tracing::info!(task = engine.card.task, dir = %dir.display(), "artifact loaded");
    let state = Arc::new(server::AppState {
        engine: Mutex::new(engine),
        latencies: Mutex::new(VecDeque::with_capacity(1000)),
        calls: Mutex::new((0, 0)),
    });
    let listener = tokio::net::TcpListener::bind(&bind).await?;
    tracing::info!(%bind, "listening");
    axum::serve(listener, server::app(state)).await?;
    global::shutdown_tracer_provider();
    Ok(())
}
