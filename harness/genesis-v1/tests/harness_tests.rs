use std::fs;
use std::process::{Command, Stdio};
use std::io::Write;
use tempfile::tempdir;

#[test]
fn rejects_protected_workflow_patch() {
    let dir = tempdir().unwrap();
    let wf_dir = dir.path().join(".github/workflows");
    fs::create_dir_all(&wf_dir).unwrap();
    let wf_file = wf_dir.join("ci.yml");
    fs::write(&wf_file, "name: ci
").unwrap();

    let envelope = serde_json::json!({
        "schema_version": "InstructionEnvelope.v1",
        "instruction_id": "INS-TEST-01",
        "parent_instruction_id": null,
        "role": "coder",
        "target_repo": "argon-sync",
        "worktree_root": dir.path().to_str().unwrap(),
        "ttl_secs": 300,
        "max_output_bytes": 4096,
        "tool_call": {
            "tool": "patch_apply_anchored",
            "args": {
                "rel_path": ".github/workflows/ci.yml",
                "expected_sha256": "deadbeef",
                "search_block": "name: ci",
                "replace_block": "name: pwned",
                "fuzzy_whitespace": false
            }
        }
    });

    let mut child = Command::new(env!("CARGO_BIN_EXE_genesis-harness-v1"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();

    child
        .stdin
        .as_mut()
        .unwrap()
        .write_all(envelope.to_string().as_bytes())
        .unwrap();

    let output = child.wait_with_output().unwrap();
    let receipt: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(receipt["ok"], false);
    assert_eq!(receipt["exit_code"], 403);
}
