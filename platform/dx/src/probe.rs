//! DX — typed probe model.
//!
//! Everything is a PROBE. A probe is a deterministic, read-only check that
//! discriminates among a declared set of hypothesis classes, carries a cost
//! model, and produces typed `Evidence` that the controller folds into a
//! belief state. New stacks = new probe libraries; the controller is unchanged.

use serde::Serialize;

/// Every check carries a stable id, a severity, a verdict, evidence, and a
/// remediation hint (spec §1.7).
#[derive(Debug, Clone, Serialize)]
pub struct Evidence {
    /// Stable probe id, e.g. "http.status".
    pub id: String,
    /// Target the probe examined, e.g. "http://127.0.0.1:9101".
    pub target: String,
    /// Discriminated fault classes this probe can tell apart, by name.
    pub discriminates: Vec<String>,
    /// Observed measurement that the controller reasons over.
    pub observation: Observation,
    /// Severity of the finding, if any.
    pub severity: Severity,
    /// Human/machine remediation hint.
    pub remediation: String,
}

/// A typed observation — one probe reads one signal.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Observation {
    /// HTTP probe result.
    Http {
        status: u16,
        /// "ok" | "http500" | "corrupt" | "degraded" | "unreachable"
        mode: String,
        /// Round-trip latency, milliseconds.
        latency_ms: f64,
        /// Body length read, in bytes; 0 for an empty/refused response.
        body_len: usize,
    },
    /// Process-liveness probe result.
    Process { alive: bool },
    /// Local port reachability probe result.
    Port { open: bool },
}

/// Verdict severity for a finding.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Ok,
    Info,
    Warning,
    Critical,
}

/// The single contract a probe library implements. `run()` is read-only and
/// deterministic for a fixed target state.
pub trait Probe {
    /// Stable probe id.
    fn id(&self) -> &str;
    /// Which fault-class names this probe's evidence discriminates.
    fn discriminates(&self) -> Vec<String>;
    /// Run the probe against the target, never mutating it.
    fn run(&self, target: &str) -> Result<Evidence, String>;
}
