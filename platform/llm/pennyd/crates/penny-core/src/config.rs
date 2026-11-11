//! Daemon config. Provider/model definitions live in `providers_dir`
//! (see providers.rs) — this file is only daemon behaviour: cache, budgets,
//! shaping, breakers, keys.

use crate::error::PennyError;
pub use crate::providers::LaneClass; // re-export: the type lives with the registry
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub bind: String,
    pub log_path: String,
    pub providers_dir: String,
    /// Optional secret-mounted file with extra [[keys]] entries. Edge API
    /// keys belong in a Secret, not in a ConfigMap (deployment finding).
    #[serde(default)]
    pub keys_file: Option<String>,
    #[serde(default = "default_reload_s")]
    pub reload_interval_s: u64,
    pub cache: CacheCfg,
    pub budgets: BudgetsCfg,
    pub shaping: ShapingCfg,
    pub router: RouterCfg,
    #[serde(default)]
    pub keys: Vec<KeyCfg>,
    /// Enterprise default: false — unknown keys are refused (401). Only
    /// loopback toy setups should set true.
    #[serde(default)]
    pub allow_unknown_keys: bool,
    /// Request body cap (F-IN-5): oversized payloads are refused with 413
    /// before any upstream dollar is at risk.
    #[serde(default = "default_max_body_bytes")]
    pub max_body_bytes: usize,
    /// Per-lane bulkhead (F-RO-7): caps concurrent in-flight calls per lane.
    #[serde(default = "default_max_inflight")]
    pub max_inflight_per_lane: usize,
}

fn default_max_body_bytes() -> usize {
    2 * 1024 * 1024
}

fn default_max_inflight() -> usize {
    1024
}

fn default_reload_s() -> u64 {
    5
}

#[derive(Debug, Clone, Deserialize)]
pub struct CacheCfg {
    pub capacity: u64,
    pub ttl_min_s: u64,
    pub ttl_max_s: u64,
    pub hit_rate_floor: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BudgetsCfg {
    pub default_daily_usd: f64,
    /// Optional persistence file for per-key spend (P0-5: survive restart).
    #[serde(default)]
    pub budgets_path: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ShapingCfg {
    pub cache_control: bool,
    pub max_tokens_cap: u64,
    pub tool_result_max_chars: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RouterCfg {
    pub breaker_threshold: u32,
    pub breaker_cooldown_s: u64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct KeyCfg {
    pub key: String,
    pub daily_budget_usd: f64,
    /// Model ACL: aliases or canonical ids this key may use. Empty = all.
    /// Closes the escape hatch budgets alone can't (F-IN-6).
    #[serde(default)]
    pub allowed_models: Vec<String>,
}

impl Config {
    pub fn load(path: &str) -> Result<Self, PennyError> {
        let text = std::fs::read_to_string(path).map_err(|e| PennyError::Config(e.to_string()))?;
        let mut cfg: Self = toml::from_str(&text).map_err(|e| PennyError::Config(e.to_string()))?;
        if let Some(kf) = &cfg.keys_file {
            let extra = std::fs::read_to_string(kf)
                .map_err(|e| PennyError::Config(format!("keys_file {kf}: {e}")))?;
            #[derive(serde::Deserialize)]
            struct KeysFile {
                keys: Vec<KeyCfg>,
            }
            let parsed: KeysFile = toml::from_str(&extra)
                .map_err(|e| PennyError::Config(format!("keys_file {kf}: {e}")))?;
            cfg.keys.extend(parsed.keys);
        }
        cfg.validate()?;
        Ok(cfg)
    }

    pub fn validate(&self) -> Result<(), PennyError> {
        if self.providers_dir.is_empty() {
            return Err(PennyError::Config("providers_dir must be set".into()));
        }
        if self.cache.ttl_max_s < self.cache.ttl_min_s {
            return Err(PennyError::Config("cache.ttl_max_s < ttl_min_s".into()));
        }
        if self.max_body_bytes == 0 {
            return Err(PennyError::Config("max_body_bytes must be > 0".into()));
        }
        if self.keys.is_empty() {
            return Err(PennyError::Config(
                "at least one [[keys]] entry required".into(),
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const TOML: &str = r#"
bind = "127.0.0.1:4000"
log_path = "/var/lib/pennyd/decisions.jsonl"
providers_dir = "providers"

[cache]
capacity = 10000
ttl_min_s = 300
ttl_max_s = 3600
hit_rate_floor = 0.5

[budgets]
default_daily_usd = 1.0

[shaping]
cache_control = true
max_tokens_cap = 1024
tool_result_max_chars = 2000

[router]
breaker_threshold = 3
breaker_cooldown_s = 60

[[keys]]
key = "sk-watch-1"
daily_budget_usd = 0.10
"#;

    #[test]
    fn parses_and_validates() {
        let cfg: Config = toml::from_str(TOML).unwrap();
        cfg.validate().unwrap();
        assert_eq!(cfg.providers_dir, "providers");
    }

    #[test]
    fn rejects_empty_keys() {
        let mut cfg: Config = toml::from_str(TOML).unwrap();
        cfg.keys.clear();
        assert!(cfg.validate().is_err());
    }

    #[test]
    fn keys_file_supplies_the_required_edge_keys() {
        let p = std::env::temp_dir().join(format!("pennyd-keys-{}", std::process::id()));
        std::fs::write(
            &p,
            "[[keys]]\nkey = \"edge-secret\"\ndaily_budget_usd = 1.0\n",
        )
        .unwrap();
        let body = format!(
            r#"
bind = "127.0.0.1:4000"
log_path = "/tmp/pennyd.jsonl"
providers_dir = "providers"
keys_file = "{}"

[cache]
capacity = 1
ttl_min_s = 1
ttl_max_s = 2
hit_rate_floor = 0.5

[budgets]
default_daily_usd = 1.0

[shaping]
cache_control = true
max_tokens_cap = 1024
tool_result_max_chars = 2000

[router]
breaker_threshold = 3
breaker_cooldown_s = 60
"#,
            p.display()
        );
        let load_path = std::env::temp_dir().join(format!("pennyd-config-{}", std::process::id()));
        std::fs::write(&load_path, body).unwrap();
        let cfg = Config::load(load_path.to_str().unwrap()).unwrap();
        assert_eq!(cfg.keys.len(), 1);
        assert_eq!(cfg.keys[0].key, "edge-secret");
        let _ = std::fs::remove_file(p);
        let _ = std::fs::remove_file(load_path);
    }
}
