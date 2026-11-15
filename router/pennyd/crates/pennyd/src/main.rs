use penny_core::{
    budget::Budgets, cache::ExactCache, config::Config, decision_log::DecisionLog,
    ledger::Ledger, providers::Registry, router::Router as LaneRouter,
};
use pennyd::{gateway::{build_router, App}, lanes::lanes_from_registry};
use std::path::Path;
use std::sync::{Arc, RwLock};
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();
    let cfg_path = std::env::args().nth(1).unwrap_or_else(|| "config.toml".into());
    let cfg = Config::load(&cfg_path)?;

    let registry = Arc::new(Registry::load_dir(Path::new(&cfg.providers_dir))?);
    let lanes = lanes_from_registry(&registry, cfg.shaping.cache_control)?;
    let lane_router = Arc::new(LaneRouter::new(
        lanes,
        cfg.router.breaker_threshold,
        cfg.router.breaker_cooldown_s,
        cfg.max_inflight_per_lane,
    ));

    let log = DecisionLog::open(&cfg.log_path)?;
    let budgets = match &cfg.budgets_path {
        Some(p) => Budgets::with_persistence(p),
        None => Budgets::new(),
    };
    let app = Arc::new(App {
        cache: ExactCache::new(cfg.cache.capacity, cfg.cache.ttl_min_s, cfg.cache.ttl_max_s),
        budgets,
        ledger: Ledger::default(),
        registry: RwLock::new(registry),
        router: RwLock::new(lane_router),
        cfg: cfg.clone(),
        log: tokio::sync::Mutex::new(log),
        dropped_decisions: std::sync::atomic::AtomicU64::new(0),
    });

    // hot reload: editing providers/*.toml swaps in a new registry + router
    // within reload_interval_s. A broken file keeps the last good state.
    let app2 = app.clone();
    let dir = cfg.providers_dir.clone();
    let (threshold, cooldown, inflight) = (
        cfg.router.breaker_threshold,
        cfg.router.breaker_cooldown_s,
        cfg.max_inflight_per_lane,
    );
    let interval = cfg.reload_interval_s.max(1);
    tokio::spawn(async move {
        let mut last = Registry::fingerprint(Path::new(&dir));
        let mut tick = tokio::time::interval(Duration::from_secs(interval));
        loop {
            tick.tick().await;
            let fp = Registry::fingerprint(Path::new(&dir));
            if fp == last {
                continue;
            }
            match Registry::load_dir(Path::new(&dir)) {
                Ok(reg) => match lanes_from_registry(&reg, app2.cfg.shaping.cache_control) {
                    Ok(lanes) => {
                        *app2.registry.write().unwrap() = Arc::new(reg);
                        *app2.router.write().unwrap() =
                            Arc::new(LaneRouter::new(lanes, threshold, cooldown, inflight));
                        last = fp;
                        tracing::info!("providers reloaded");
                    }
                    Err(e) => tracing::error!("lane build failed; keeping previous: {e}"),
                },
                Err(e) => tracing::error!("registry reload failed; keeping previous: {e}"),
            }
        }
    });

    let n_models = app.registry.read().unwrap().models.len();
    let router = build_router(app);
    let listener = tokio::net::TcpListener::bind(&cfg.bind).await?;
    tracing::info!("pennyd listening on {} ({n_models} models)", cfg.bind);
    axum::serve(listener, router).await?;
    Ok(())
}
