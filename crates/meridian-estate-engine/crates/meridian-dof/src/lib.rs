//! DOF-GOVERNANCE-v1: Degrees-of-Freedom Capability Lease Engine (`meridian-dof`).
//!
//! Moves the full `L0 -> L1 -> L2 -> L3` lease engine out of TypeScript mocks into
//! compiled Rust with Zone B components (zero retired OKE paths):
//!   - GEN-DOF-001 (Rule Zero): Capabilities are leased, never possessed.
//!   - GEN-DOF-002 (Epoch Fencing): Probe drop bumps `lease_epoch`, invalidating in-flight L0 mutations.
//!   - GEN-DOF-003 (Dual-Probe Agreement): Single-method disagreement holds at L1; dual agreement drops to L2.
//!   - GEN-DOF-004 (1-down / 3-up Hysteresis): Restores L0 ONLY after repair completion + 3 consecutive passes.
//!   - Cross-surface bypass during outage escalates immediately to L3 Frozen + Red Card.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum DofLevel {
    L0FullLease = 0,
    L1ReadDiagnoseOnly = 1,
    L2ComponentRepairOnly = 2,
    L3FrozenEscalated = 3,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProbeStatus {
    Pass,
    Fail,
    CannotRun,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DualProbeReading {
    pub component_id: String,
    pub method_a: ProbeStatus,
    pub method_b: ProbeStatus,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActionCategory {
    DiagnosticRead,
    SafeLowEffectDocOrTest,
    RepairStep,
    TaskMutation,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActionRequest {
    pub tool_name: String,
    pub category: ActionCategory,
    pub target_paths: Vec<String>,
    pub surface: String,
    pub claimed_lease_epoch: u64,
    pub resolving_component: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RefusalEnvelope {
    pub status: String,
    pub lease_epoch: u64,
    pub active_level: DofLevel,
    pub failing_component: Option<String>,
    pub cross_surface_bypass: bool,
    pub red_card_issued: bool,
    pub directive: String,
}

#[derive(Clone, Debug)]
pub struct ComponentSpec {
    pub id: String,
    pub repair_prefixes: Vec<String>,
    pub required_repair_steps: usize,
}

#[derive(Clone, Debug)]
pub struct DofLeaseEngine {
    pub lease_epoch: u64,
    pub active_level: DofLevel,
    pub failing_component: Option<String>,
    pub completed_repair_steps: usize,
    pub consecutive_passes: u8,
    pub red_card_issued: bool,
    components: BTreeMap<String, ComponentSpec>,
    immutable_while_red: BTreeSet<String>,
}

impl DofLeaseEngine {
    /// Default Zone B component registry (OKE paths purged).
    pub fn zone_b_default() -> Self {
        let mut components = BTreeMap::new();
        for (id, prefixes, steps) in [
            (
                "ROUTER-EDGE-01",
                vec!["platform/router-edge/", "crates/meridian-ledger/"],
                3,
            ),
            (
                "BATTALION-FIT-01",
                vec![
                    "crates/meridian-battalion/",
                    ".github/workflows/agent-sandbox.yml",
                ],
                2,
            ),
            (
                "MEMORY-ZONEB-01",
                vec!["platform/unified-memory-server/", "crates/meridian-karma/"],
                3,
            ),
            (
                "GREENLANE-01",
                vec!["greenlane/", "crates/meridian-greenlane/"],
                2,
            ),
        ] {
            components.insert(
                id.to_string(),
                ComponentSpec {
                    id: id.to_string(),
                    repair_prefixes: prefixes.into_iter().map(String::from).collect(),
                    required_repair_steps: steps,
                },
            );
        }
        let immutable_while_red = [
            "bin/dof-gate",
            "catalog/dof-registry.json",
            "crates/meridian-dof/src/lib.rs",
            ".github/workflows/ci.yml",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        Self {
            lease_epoch: 1,
            active_level: DofLevel::L0FullLease,
            failing_component: None,
            completed_repair_steps: 0,
            consecutive_passes: 0,
            red_card_issued: false,
            components,
            immutable_while_red,
        }
    }

    /// Evaluates orthogonal dual-probe reading with `1-down / 3-up` hysteresis.
    pub fn evaluate_probe(&mut self, reading: &DualProbeReading) -> DofLevel {
        if self.active_level == DofLevel::L3FrozenEscalated {
            return self.active_level;
        }
        match (reading.method_a, reading.method_b) {
            (ProbeStatus::Fail, ProbeStatus::Fail) => {
                if self.active_level != DofLevel::L2ComponentRepairOnly
                    || self.failing_component.as_deref() != Some(reading.component_id.as_str())
                {
                    self.lease_epoch = self.lease_epoch.saturating_add(1);
                    self.completed_repair_steps = 0;
                }
                self.active_level = DofLevel::L2ComponentRepairOnly;
                self.failing_component = Some(reading.component_id.clone());
                self.consecutive_passes = 0;
            }
            (ProbeStatus::Fail, _)
            | (_, ProbeStatus::Fail)
            | (ProbeStatus::CannotRun, _)
            | (_, ProbeStatus::CannotRun) => {
                if self.active_level == DofLevel::L0FullLease {
                    self.lease_epoch = self.lease_epoch.saturating_add(1);
                    self.active_level = DofLevel::L1ReadDiagnoseOnly;
                    self.failing_component = Some(reading.component_id.clone());
                }
                self.consecutive_passes = 0;
            }
            (ProbeStatus::Pass, ProbeStatus::Pass) => {
                if self.active_level == DofLevel::L0FullLease {
                    return self.active_level;
                }
                if self.active_level == DofLevel::L2ComponentRepairOnly {
                    let req_steps = self
                        .failing_component
                        .as_ref()
                        .and_then(|c| self.components.get(c))
                        .map(|s| s.required_repair_steps)
                        .unwrap_or(1);
                    if self.completed_repair_steps < req_steps {
                        // Cannot restore via transient pass before repair steps are receipted
                        self.consecutive_passes = 0;
                        return self.active_level;
                    }
                }
                self.consecutive_passes = self.consecutive_passes.saturating_add(1);
                if self.consecutive_passes >= 3 {
                    self.active_level = DofLevel::L0FullLease;
                    self.failing_component = None;
                    self.completed_repair_steps = 0;
                    self.lease_epoch = self.lease_epoch.saturating_add(1);
                }
            }
        }
        self.active_level
    }

    pub fn authorize(&mut self, req: &ActionRequest) -> Result<(), RefusalEnvelope> {
        if req.claimed_lease_epoch != self.lease_epoch {
            return Err(self.refusal(false, "STALE_LEASE_EPOCH_FENCED"));
        }
        if req.category == ActionCategory::DiagnosticRead {
            return Ok(());
        }
        if self.active_level == DofLevel::L0FullLease {
            return Ok(());
        }
        // Immutable control paths can NEVER be unlocked while red
        for p in &req.target_paths {
            if self.immutable_while_red.contains(p) {
                return Err(self.refusal(false, "IMMUTABLE_CONTROL_WHILE_RED"));
            }
        }
        if self.active_level == DofLevel::L3FrozenEscalated {
            return Err(self.refusal(false, "L3_FROZEN_ESCALATED"));
        }
        // Cross-surface bypass (e.g. trying to mutate via web-chat while CLI is in L1/L2) -> immediate L3 Red Card
        if req.surface == "web-chat" && req.category == ActionCategory::TaskMutation {
            self.active_level = DofLevel::L3FrozenEscalated;
            self.red_card_issued = true;
            self.lease_epoch = self.lease_epoch.saturating_add(1);
            return Err(self.refusal(true, "CROSS_SURFACE_BYPASS_ESCALATED_TO_L3"));
        }
        // Scope-aware deadlock breaker (idp#7787): pure safe docs/tests allowed if outside failing substrate
        if req.category == ActionCategory::SafeLowEffectDocOrTest
            && req
                .target_paths
                .iter()
                .all(|p| p.starts_with("docs/specs/") || p.starts_with("tests/"))
        {
            return Ok(());
        }
        // L2 allows ONLY scoped repair steps for the exact failing component
        if self.active_level == DofLevel::L2ComponentRepairOnly
            && req.category == ActionCategory::RepairStep
        {
            if let (Some(fail_id), Some(claim_id)) =
                (&self.failing_component, &req.resolving_component)
            {
                if fail_id == claim_id {
                    if let Some(spec) = self.components.get(fail_id) {
                        let in_scope = !req.target_paths.is_empty()
                            && req.target_paths.iter().all(|p| {
                                spec.repair_prefixes.iter().any(|pref| p.starts_with(pref))
                            });
                        if in_scope {
                            self.completed_repair_steps =
                                self.completed_repair_steps.saturating_add(1);
                            return Ok(());
                        }
                    }
                }
            }
        }
        Err(self.refusal(false, "CAPABILITY_LEASE_INSUFFICIENT_REPAIR_FIRST"))
    }

    fn refusal(&self, bypass: bool, directive: &str) -> RefusalEnvelope {
        RefusalEnvelope {
            status: "REFUSED_CAPABILITY_LEASE_INSUFFICIENT".to_string(),
            lease_epoch: self.lease_epoch,
            active_level: self.active_level,
            failing_component: self.failing_component.clone(),
            cross_surface_bypass: bypass,
            red_card_issued: self.red_card_issued,
            directive: directive.to_string(),
        }
    }
}
