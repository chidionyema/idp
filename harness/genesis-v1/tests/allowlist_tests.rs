use std::fs;
use std::io::Write;
use std::process::{Command, Stdio};
use tempfile::tempdir;

fn receipt_for(root: &std::path::Path, tool_call: serde_json::Value) -> serde_json::Value {
    let envelope = serde_json::json!({
        "schema_version": "InstructionEnvelope.v1",
        "instruction_id": "INS-ALLOW-01",
        "parent_instruction_id": null,
        "role": "coder",
        "target_repo": "idp",
        "worktree_root": root.to_str().unwrap(),
        "ttl_secs": 300,
        "max_output_bytes": 4096,
        "tool_call": tool_call,
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
    serde_json::from_slice(&output.stdout).unwrap()
}

fn exec_call(verb: &str) -> serde_json::Value {
    serde_json::json!({
        "tool": "exec_scoped",
        "args": { "program": verb, "args": [] }
    })
}

#[test]
fn refuses_when_no_manifest_is_declared() {
    let dir = tempdir().unwrap();
    let receipt = receipt_for(dir.path(), exec_call("check"));
    assert_eq!(receipt["ok"], false);
    assert_eq!(receipt["exit_code"], 403);
}

#[test]
fn refuses_a_verb_the_manifest_does_not_declare() {
    let dir = tempdir().unwrap();
    fs::create_dir_all(dir.path().join(".genesis")).unwrap();
    fs::write(
        dir.path().join(".genesis/allowlist.json"),
        r#"{"check": ["true"]}"#,
    )
    .unwrap();
    let receipt = receipt_for(dir.path(), exec_call("rm"));
    assert_eq!(receipt["ok"], false);
    assert_eq!(receipt["exit_code"], 403);
}

#[test]
fn refuses_arguments_smuggled_onto_a_declared_verb() {
    let dir = tempdir().unwrap();
    fs::create_dir_all(dir.path().join(".genesis")).unwrap();
    fs::write(
        dir.path().join(".genesis/allowlist.json"),
        r#"{"check": ["true"]}"#,
    )
    .unwrap();
    let receipt = receipt_for(
        dir.path(),
        serde_json::json!({
            "tool": "exec_scoped",
            "args": { "program": "check", "args": ["--force"] }
        }),
    );
    assert_eq!(receipt["ok"], false);
    assert_eq!(receipt["exit_code"], 403);
}

#[test]
fn runs_a_declared_verb_from_the_manifest() {
    let dir = tempdir().unwrap();
    fs::create_dir_all(dir.path().join(".genesis")).unwrap();
    fs::write(
        dir.path().join(".genesis/allowlist.json"),
        r#"{"check": ["true"]}"#,
    )
    .unwrap();
    let receipt = receipt_for(dir.path(), exec_call("check"));
    assert_eq!(receipt["ok"], true);
    assert_eq!(receipt["exit_code"], 0);
}

#[test]
fn acceptance_paths_are_write_blocked() {
    let dir = tempdir().unwrap();
    let acceptance = dir.path().join("tests/acceptance");
    fs::create_dir_all(&acceptance).unwrap();
    fs::write(acceptance.join("voice.feature"), "Feature: x\n").unwrap();
    let receipt = receipt_for(
        dir.path(),
        serde_json::json!({
            "tool": "patch_apply_anchored",
            "args": {
                "rel_path": "tests/acceptance/voice.feature",
                "expected_sha256": "deadbeef",
                "search_block": "Feature: x",
                "replace_block": "Feature: pwned",
                "fuzzy_whitespace": false
            }
        }),
    );
    assert_eq!(receipt["ok"], false);
    assert_eq!(receipt["exit_code"], 403);
}
