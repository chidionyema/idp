//! Provider registry — model-agnostic by construction.
//!
//! A provider is a TOML file in `providers_dir`. Adding or updating a
//! provider/model is a file edit + hot reload (5s watcher); adding an
//! OpenAI-compatible provider is pure data, zero code. A genuinely new
//! wire dialect is one `impl Dialect` in dialect.rs.
//!
//! Laws (loud failure, never silent):
//!   * provider `id` MUST equal its filename stem — the file is the name
//!   * model ids and aliases are globally unique
//!   * dialect names are validated at load
//!   * cascade order is computed: (class, price_in) — never hand-ordered

use crate::dialect;
use crate::error::PennyError;
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LaneClass {
    Local,
    Free,
    Paid,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum AuthKind {
    None,
    Bearer { key_env: String },
    Header { name: String, key_env: String },
    QueryParam { name: String, key_env: String },
}

#[derive(Debug, Clone, Deserialize)]
pub struct ProviderDef {
    pub id: String,
    pub dialect: String,
    pub base_url: String,
    pub auth: AuthKind,
    #[serde(default = "default_timeout_s")]
    pub timeout_s: u64,
}

fn default_timeout_s() -> u64 {
    60
}

#[derive(Debug, Clone, Deserialize)]
pub struct ModelDef {
    pub id: String,
    pub class: LaneClass,
    pub price_in_per_mtok: f64,
    pub price_out_per_mtok: f64,
    #[serde(default)]
    pub context_window: u64,
    #[serde(default)]
    pub aliases: Vec<String>,
    /// Explicit fallback chain (aliases or provider/model ids), tried ONLY if
    /// this model's lane fails. The old router's sin: a bare model name fell
    /// through every lane in priority order — GLM requests could silently
    /// become MiniMax. Never again: no implicit cross-model substitution.
    #[serde(default)]
    pub fallbacks: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ModelEntry {
    pub provider: ProviderDef,
    pub model: ModelDef,
}

impl ModelEntry {
    pub fn canonical_name(&self) -> String {
        format!("{}/{}", self.provider.id, self.model.id)
    }
}

/// On-disk shape: one file per provider, explicit fields (no flatten — the
/// TOML deserializer handles explicit fields deterministically).
#[derive(Debug, Deserialize)]
struct ProviderFile {
    id: String,
    dialect: String,
    base_url: String,
    auth: AuthKind,
    #[serde(default = "default_timeout_s")]
    timeout_s: u64,
    #[serde(default)]
    models: Vec<ModelDef>,
}

#[derive(Debug, Clone, Default)]
pub struct Registry {
    pub models: Vec<ModelEntry>, // sorted (LaneClass, price_in): the cascade
    aliases: HashMap<String, usize>,
}

impl Registry {
    pub fn load_dir(dir: &Path) -> Result<Self, PennyError> {
        let mut files: Vec<_> = fs::read_dir(dir)
            .map_err(|e| PennyError::Config(format!("providers_dir {dir:?}: {e}")))?
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.extension().map(|x| x == "toml").unwrap_or(false))
            .collect();
        files.sort(); // deterministic load order
        if files.is_empty() {
            return Err(PennyError::Config(format!("no provider .toml files in {dir:?}")));
        }

        let mut models: Vec<ModelEntry> = Vec::new();
        let mut seen_ids: HashMap<String, ()> = HashMap::new();
        let mut seen_aliases: HashMap<String, ()> = HashMap::new();

        for path in &files {
            let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("").to_string();
            let text = fs::read_to_string(path)
                .map_err(|e| PennyError::Config(format!("{stem}: read failed: {e}")))?;
            let pf: ProviderFile = toml::from_str(&text)
                .map_err(|e| PennyError::Config(format!("{stem}.toml: {e}")))?;
            if pf.id != stem {
                return Err(PennyError::Config(format!(
                    "{stem}.toml declares id={:?}; filename is law", pf.id
                )));
            }
            dialect::for_name(&pf.dialect)?; // validate dialect early, loud
            let provider = ProviderDef {
                id: pf.id,
                dialect: pf.dialect,
                base_url: pf.base_url,
                auth: pf.auth,
                timeout_s: pf.timeout_s,
            };
            for m in pf.models {
                if m.price_in_per_mtok < 0.0 || m.price_out_per_mtok < 0.0 {
                    return Err(PennyError::Config(format!(
                        "{}/{}: negative price (F-BU-4)", provider.id, m.id)));
                }
                let key = format!("{}/{}", provider.id, m.id);
                if seen_ids.insert(key.clone(), ()).is_some() {
                    return Err(PennyError::Config(format!("duplicate model id {key}")));
                }
                for a in &m.aliases {
                    if seen_aliases.insert(a.clone(), ()).is_some() {
                        return Err(PennyError::Config(format!("duplicate alias {a:?}")));
                    }
                }
                models.push(ModelEntry { provider: provider.clone(), model: m });
            }
        }

        models.sort_by(|a, b| {
            (a.model.class, a.model.price_in_per_mtok)
                .partial_cmp(&(b.model.class, b.model.price_in_per_mtok))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        let mut aliases = HashMap::new();
        for (i, e) in models.iter().enumerate() {
            for a in &e.model.aliases {
                aliases.insert(a.clone(), i);
            }
        }
        // validate fallback chains at load — loud, never a runtime surprise
        for e in &models {
            for f in &e.model.fallbacks {
                let known = aliases.contains_key(f)
                    || f.split_once('/').map(|(p, m)| {
                        models.iter().any(|e2| e2.provider.id == p && e2.model.id == m)
                    }).unwrap_or(false);
                if !known {
                    return Err(PennyError::Config(format!(
                        "{} declares unknown fallback {f:?}", e.canonical_name())));
                }
            }
        }
        Ok(Self { models, aliases })
    }

    /// Resolve an alias or a `provider/model` id to its entry.
    pub fn resolve(&self, name: &str) -> Option<&ModelEntry> {
        if let Some(&i) = self.aliases.get(name) {
            return self.models.get(i);
        }
        name.split_once('/').and_then(|(p, m)| {
            self.models
                .iter()
                .find(|e| e.provider.id == p && e.model.id == m)
        })
    }

    pub fn alias_list(&self) -> String {
        let mut v: Vec<&str> = self.aliases.keys().map(String::as_str).collect();
        v.sort();
        v.into_iter().take(25).collect::<Vec<_>>().join(", ")
    }

    /// OpenAI /v1/models payload — clients discover available models.
    pub fn list_models(&self) -> Value {
        json!({
            "object": "list",
            "data": self.models.iter().map(|e| json!({
                "id": e.canonical_name(),
                "object": "model",
                "owned_by": e.provider.id,
            })).collect::<Vec<_>>(),
        })
    }

    /// Hot-reload fingerprint: fold of (filename, mtime) over ALL provider
    /// files. P1-7: deletions change the name set and the count, so a
    /// removed non-newest file still flips the fingerprint.
    pub fn fingerprint(dir: &Path) -> Option<u64> {
        let mut files: Vec<(String, u64)> = fs::read_dir(dir).ok()?
            .filter_map(|e| e.ok())
            .filter_map(|e| {
                let p = e.path();
                if p.extension()? != "toml" {
                    return None;
                }
                let mt = e.metadata().ok()?.modified().ok()?
                    .duration_since(std::time::UNIX_EPOCH).ok()?.as_secs();
                Some((p.file_name()?.to_string_lossy().to_string(), mt))
            })
            .collect();
        files.sort();
        if files.is_empty() {
            return None;
        }
        let mut h = 0xcbf29ce484222325u64;
        for (name, mt) in files {
            for b in name.bytes().chain(mt.to_le_bytes()) {
                h ^= b as u64;
                h = h.wrapping_mul(0x100000001b3);
            }
        }
        Some(h)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(dir: &Path, name: &str, body: &str) {
        fs::create_dir_all(dir).unwrap();
        fs::write(dir.join(format!("{name}.toml")), body).unwrap();
    }

    const DEEPSEEK: &str = r#"
id = "deepseek"
dialect = "openai"
base_url = "https://api.deepseek.com"

[auth]
kind = "bearer"
key_env = "DEEPSEEK_API_KEY"

[[models]]
id = "deepseek-chat"
class = "paid"
price_in_per_mtok = 0.14
price_out_per_mtok = 0.28
context_window = 64000
aliases = ["cheap-chat"]
"#;

    const CLAUDE: &str = r#"
id = "anthropic"
dialect = "anthropic"
base_url = "https://api.anthropic.com"

[auth]
kind = "header"
name = "x-api-key"
key_env = "ANTHROPIC_API_KEY"

[[models]]
id = "claude-haiku"
class = "paid"
price_in_per_mtok = 0.80
price_out_per_mtok = 4.00
"#;

    fn reg() -> (tempfile_unused::TempPath, Registry) {
        // no tempfile dep: use a unique dir under std::env::temp_dir()
        let dir = std::env::temp_dir().join(format!("penny-reg-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "deepseek", DEEPSEEK);
        write(&dir, "anthropic", CLAUDE);
        let r = Registry::load_dir(&dir).unwrap();
        (tempfile_unused::TempPath(dir), r)
    }

    // tiny helper to keep the dir alive for the test scope
    mod tempfile_unused {
        pub struct TempPath(pub std::path::PathBuf);
        impl Drop for TempPath { fn drop(&mut self) { let _ = std::fs::remove_dir_all(&self.0); } }
    }

    #[test]
    fn loads_and_sorts_cheapest_first() {
        let (_d, r) = reg();
        assert_eq!(r.models.len(), 2);
        assert!(r.models[0].model.price_in_per_mtok < r.models[1].model.price_in_per_mtok);
    }

    #[test]
    fn resolves_alias_and_canonical() {
        let (_d, r) = reg();
        assert_eq!(r.resolve("cheap-chat").unwrap().canonical_name(), "deepseek/deepseek-chat");
        assert_eq!(r.resolve("anthropic/claude-haiku").unwrap().model.id, "claude-haiku");
        assert!(r.resolve("nope").is_none());
    }

    #[test]
    fn filename_is_law() {
        let dir = std::env::temp_dir().join(format!("penny-reg-bad-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "not-the-id", DEEPSEEK); // id says "deepseek"
        assert!(Registry::load_dir(&dir).is_err());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn duplicate_alias_rejected() {
        let dir = std::env::temp_dir().join(format!("penny-reg-dup-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "a", DEEPSEEK);
        write(&dir, "b", &CLAUDE.replace("claude-haiku", "cheap-chat"));
        assert!(Registry::load_dir(&dir).is_err());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn unknown_fallback_rejected_at_load() {
        let dir = std::env::temp_dir().join(format!("penny-reg-fb-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "a", DEEPSEEK);
        // TOML single-quoted strings: no escape-sequence pitfalls
        write(&dir, "b", &CLAUDE.replace(
            "aliases = []",
            "aliases = []\nfallbacks = ['no-such-model']"));
        assert!(Registry::load_dir(&dir).is_err());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn negative_prices_rejected() {
        let dir = std::env::temp_dir().join(format!("penny-reg-neg-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "a", &DEEPSEEK.replace("price_in_per_mtok = 0.14", "price_in_per_mtok = -0.14"));
        assert!(Registry::load_dir(&dir).is_err());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn reload_after_file_delete() {
        let dir = std::env::temp_dir().join(format!("penny-reg-del-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "deepseek", DEEPSEEK);
        write(&dir, "anthropic", CLAUDE);
        assert_eq!(Registry::load_dir(&dir).unwrap().models.len(), 2);
        std::fs::remove_file(dir.join("anthropic.toml")).unwrap();
        assert_eq!(Registry::load_dir(&dir).unwrap().models.len(), 1);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn deletion_changes_fingerprint() {
        // P1-7: removing a non-newest file must flip the fingerprint
        let dir = std::env::temp_dir().join(format!("penny-reg-fp-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        write(&dir, "aaa", DEEPSEEK);
        write(&dir, "zzz", CLAUDE);
        std::thread::sleep(std::time::Duration::from_millis(20));
        let fp1 = Registry::fingerprint(&dir);
        std::fs::remove_file(dir.join("aaa.toml")).unwrap(); // older file goes
        let fp2 = Registry::fingerprint(&dir);
        assert_ne!(fp1, fp2, "deletion must change fingerprint");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn list_models_payload() {
        let (_d, r) = reg();
        let v = r.list_models();
        assert_eq!(v["data"].as_array().unwrap().len(), 2);
        assert_eq!(v["data"][0]["owned_by"], "deepseek"); // cascade order: cheapest first
    }
}
