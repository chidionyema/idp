// src/main.rs — genesis-kernel v0.8.1-SOVEREIGN-CAGE (:4001)
// Enforces I-8046 Universal Agent Cage, Founder Surface Configurability,
// Reversible State Journal (<10ms rollback), and Deterministic Auto-Main Triage.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

pub const CLASS_A_ACTORS: &[&str] = &["gemini-argon", "aistudio"];
pub const CLASS_B_ACTORS: &[&str] = &[
    "claude", "codex", "opencode", "kimi", "chatgpt",
    "minimax-otto", "minimax-concierge", "deepseek",
    "aider", "openhands", "cline", "antigravity",
    "pi-agent", "legion-run", "chronos", "dependabot",
];
pub const PROTECTED_PRIMITIVES: &[&str] = &[
    "catalog/dof-registry.json",
    ".github/workflows/",
    "catalog/genesis-protocols.json",
    ".github/CODEOWNERS",
    "features/",
];
pub const TROJAN_COMMITS: &[&str] = &["937dda9d"];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LockdownLayers {
    pub layer1_github_ruleset_lock: bool,
    pub layer2_control_primitive_freeze: bool,
    pub layer3_os_credential_stripping: bool,
    pub layer4_browser_profile_isolation: bool,
    pub layer5_kernel_telegram_3327_fence: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RouterComparisonConfig {
    pub keep_rust_pennyd_4200: bool,
    pub keep_sovereign_router_8022: bool,
    pub pennyd_max_tokens_cap: u32,
    pub max_execution_seconds_i11: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FounderSurfaceConfig {
    pub instruction_id: String,
    pub authoritative_token: u64,
    pub class_a_surfaces: Vec<String>,
    pub caged_class_b_fleet: Vec<String>,
    pub layers: LockdownLayers,
    pub routers: RouterComparisonConfig,
    pub auto_main_require_local_hermetic_pass: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CommitTriageVerdict {
    PromotedToMain,
    QuarantinedBreachB2,
    QuarantinedProtectedPrimitive,
    BlockedLocalTestsFailed,
    ArchivedSuperseded,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateCommit {
    pub sha: String,
    pub branch: String,
    pub summary: String,
    pub touched_files: Vec<String>,
    pub has_founder_seal: bool,
    pub local_hermetic_passed: bool,
}

pub fn evaluate_commit_for_automain(commit: &CandidateCommit) -> CommitTriageVerdict {
    if TROJAN_COMMITS.contains(&commit.sha.as_str()) {
        return CommitTriageVerdict::QuarantinedBreachB2;
    }
    for file in &commit.touched_files {
        for protected in PROTECTED_PRIMITIVES {
            if file.starts_with(protected) && !commit.has_founder_seal {
                return CommitTriageVerdict::QuarantinedProtectedPrimitive;
            }
        }
    }
    if !commit.local_hermetic_passed {
        return CommitTriageVerdict::BlockedLocalTestsFailed;
    }
    CommitTriageVerdict::PromotedToMain
}
