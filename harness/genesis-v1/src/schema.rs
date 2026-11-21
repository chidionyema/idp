use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum LogicalRole {
    Concierge,
    Architect,
    Coder,
    Verifier,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeytermContextV1 {
    pub schema_version: String,
    pub active_repo: String,
    pub keyterms: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstructionEnvelopeV1 {
    pub schema_version: String,
    pub instruction_id: String,
    pub parent_instruction_id: Option<String>,
    pub role: LogicalRole,
    pub target_repo: String,
    pub worktree_root: String,
    pub ttl_secs: u64,
    pub max_output_bytes: usize,
    pub tool_call: ToolCall,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "tool", content = "args", rename_all = "snake_case")]
pub enum ToolCall {
    RepoSearch {
        query: String,
        max_results: usize,
    },
    FileReadBounded {
        rel_path: String,
        start_line: usize,
        end_line: usize,
    },
    PatchApplyAnchored {
        rel_path: String,
        expected_sha256: String,
        search_block: String,
        replace_block: String,
        fuzzy_whitespace: bool,
    },
    ExecScoped {
        program: String,
        args: Vec<String>,
    },
    DiffExportCandidate {
        base_ref: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepReceiptV1 {
    pub schema_version: String,
    pub instruction_id: String,
    pub tool: String,
    pub ok: bool,
    pub exit_code: i32,
    pub truncated: bool,
    pub output_sha256: String,
    pub payload: serde_json::Value,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationReceiptV1 {
    pub schema_version: String,
    pub instruction_id: String,
    pub commit_sha: String,
    pub fail_before_verified: bool,
    pub pass_after_verified: bool,
    pub protected_tests_untouched: bool,
    pub certifier_kid: String,
    pub signature_es256_b64: String,
}
