//! Policy loading: `voice-policy.yaml` validated against the embedded JSONSchema (spec §2/§15).
//! Lane inheritance is resolved here; `exclude_fields` defaults to the enum/category fields a
//! deny pattern must never fire on (the 2026-09-06 phase-0 boundary decision).

use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use std::path::Path;

const SCHEMA: &str = include_str!("policy.schema.json");

/// Fields a deny pattern never fires on unless the lane says otherwise: structured
/// category data, not prose (e.g. `gate: "SUPPORTED"`).
pub const DEFAULT_EXCLUDE_FIELDS: [&str; 3] = ["gate", "gateLabel", "verdict"];

#[derive(Debug, Deserialize)]
pub struct RawPolicy {
    pub version: u32,
    pub lanes: HashMap<String, RawLane>,
    #[serde(default)]
    pub rules: serde_yaml::Value,
    #[serde(default)]
    pub tier2: Option<serde_yaml::Value>,
    #[serde(default)]
    pub tier3: Option<serde_yaml::Value>,
}

#[derive(Debug, Deserialize)]
pub struct RawLane {
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub deny_patterns: Vec<DenyPattern>,
    #[serde(default)]
    pub inherit: Vec<String>,
    #[serde(default)]
    pub exclude_fields: Option<Vec<String>>,
    #[serde(default)]
    #[allow(dead_code)]
    pub rules: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DenyPattern {
    pub id: String,
    pub pattern: String,
    pub message: String,
}

/// One lane with inheritance fully resolved.
#[derive(Debug, Clone)]
pub struct Lane {
    pub name: String,
    pub deny_patterns: Vec<DenyPattern>,
    pub exclude_fields: HashSet<String>,
}

#[derive(Debug)]
pub struct VoicePolicy {
    pub version: u32,
    pub lanes: HashMap<String, Lane>,
}

#[derive(Debug, thiserror::Error)]
pub enum PolicyError {
    #[error("policy YAML parse failed: {0}")]
    Parse(String),
    #[error("policy failed JSONSchema validation: {0}")]
    Schema(String),
    #[error("lane `{lane}` inherits from unknown lane `{parent}`")]
    BadInherit { lane: String, parent: String },
    #[error("inheritance cycle involving lane `{0}`")]
    InheritCycle(String),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
}

impl VoicePolicy {
    pub fn load(path: &Path) -> Result<Self, PolicyError> {
        let text = std::fs::read_to_string(path)?;
        Self::from_str(&text)
    }

    pub fn from_str(text: &str) -> Result<Self, PolicyError> {
        let yaml: serde_yaml::Value =
            serde_yaml::from_str(text).map_err(|e| PolicyError::Parse(e.to_string()))?;
        let json: serde_json::Value =
            serde_json::to_value(&yaml).map_err(|e| PolicyError::Parse(e.to_string()))?;
        let schema: serde_json::Value =
            serde_json::from_str(SCHEMA).expect("embedded schema is valid JSON");
        let validator = jsonschema::JSONSchema::compile(&schema)
            .map_err(|e| PolicyError::Schema(e.to_string()))?;
        if let Err(errors) = validator.validate(&json) {
            let detail = errors.map(|e| e.to_string()).collect::<Vec<_>>().join("; ");
            return Err(PolicyError::Schema(detail));
        }
        let raw: RawPolicy =
            serde_yaml::from_value(yaml).map_err(|e| PolicyError::Parse(e.to_string()))?;
        let lanes = resolve_lanes(&raw)?;
        Ok(VoicePolicy { version: raw.version, lanes })
    }

    pub fn lane(&self, name: &str) -> Option<&Lane> {
        self.lanes.get(name)
    }
}

fn resolve_lanes(raw: &RawPolicy) -> Result<HashMap<String, Lane>, PolicyError> {
    fn resolve(
        name: &str,
        raw: &RawPolicy,
        done: &mut HashMap<String, Lane>,
        stack: &mut Vec<String>,
    ) -> Result<Lane, PolicyError> {
        if let Some(l) = done.get(name) {
            return Ok(l.clone());
        }
        if stack.iter().any(|s| s == name) {
            return Err(PolicyError::InheritCycle(name.to_string()));
        }
        let raw_lane = raw
            .lanes
            .get(name)
            .ok_or_else(|| PolicyError::BadInherit { lane: stack.last().cloned().unwrap_or_default(), parent: name.to_string() })?;
        stack.push(name.to_string());
        let mut patterns: Vec<DenyPattern> = Vec::new();
        for parent in &raw_lane.inherit {
            let p = resolve(parent, raw, done, stack)?;
            patterns.extend(p.deny_patterns);
        }
        patterns.extend(raw_lane.deny_patterns.clone());
        let exclude_fields: HashSet<String> = raw_lane
            .exclude_fields
            .clone()
            .map(|v| v.into_iter().map(|s| s.to_lowercase()).collect())
            .unwrap_or_else(|| DEFAULT_EXCLUDE_FIELDS.iter().map(|s| s.to_lowercase()).collect());
        stack.pop();
        let lane = Lane { name: name.to_string(), deny_patterns: patterns, exclude_fields };
        done.insert(name.to_string(), lane.clone());
        Ok(lane)
    }

    let mut done = HashMap::new();
    for name in raw.lanes.keys() {
        resolve(name, raw, &mut done, &mut Vec::new())?;
    }
    Ok(done)
}
