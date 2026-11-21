use crate::schema::{InstructionEnvelopeV1, StepReceiptV1, ToolCall};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use walkdir::WalkDir;

// The exec door is a named-verb allowlist read from the repository's own immutable manifest.
// When the manifest is absent or unreadable the door refuses: a missing contract is not a licence.
const ALLOWLIST_REL_PATH: &str = ".genesis/allowlist.json";
const PROTECTED_PATH_PREFIXES: &[&str] = &[
    ".github/workflows/",
    "cage/",
    "certifier/",
    "features/",
    "tests/acceptance/",
];

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

pub fn resolve_safe_path(root: &Path, rel: &str) -> Result<PathBuf, String> {
    let rel_path = Path::new(rel);
    if rel_path.is_absolute() {
        return Err("absolute paths are forbidden".to_string());
    }
    for comp in rel_path.components() {
        if matches!(comp, Component::ParentDir | Component::RootDir | Component::Prefix(_)) {
            return Err("path traversal is forbidden".to_string());
        }
    }
    Ok(root.join(rel_path))
}

/// verb -> argv, read from `.genesis/allowlist.json`:
/// `{"check": ["bin/pre-push-wall.py", "--fast"], "unit_test": ["cargo", "test"]}`.
/// Anything that is not a declared verb is refused, and so is a manifest we cannot read.
fn load_allowlist(root: &Path) -> Result<std::collections::BTreeMap<String, Vec<String>>, String> {
    let path = root.join(ALLOWLIST_REL_PATH);
    let raw = fs::read_to_string(&path)
        .map_err(|e| format!("allowlist unreadable at {ALLOWLIST_REL_PATH}: {e}"))?;
    let manifest: std::collections::BTreeMap<String, Vec<String>> =
        serde_json::from_str(&raw).map_err(|e| format!("allowlist is not verb -> argv: {e}"))?;
    if manifest.is_empty() {
        return Err("allowlist declares no verbs".to_string());
    }
    Ok(manifest)
}

fn is_protected_path(rel: &str) -> bool {
    PROTECTED_PATH_PREFIXES.iter().any(|p| rel.starts_with(p))
}

pub fn dispatch(env: &InstructionEnvelopeV1) -> StepReceiptV1 {
    let root = Path::new(&env.worktree_root);
    let max_bytes = env.max_output_bytes.clamp(512, 32_768);

    match &env.tool_call {
        ToolCall::RepoSearch { query, max_results } => {
            let cap = (*max_results).clamp(1, 50);
            let mut hits = Vec::new();
            for entry in WalkDir::new(root)
                .into_iter()
                .filter_map(Result::ok)
                .filter(|e| e.file_type().is_file())
            {
                let path = entry.path();
                if path.components().any(|c| c.as_os_str() == ".git" || c.as_os_str() == "target") {
                    continue;
                }
                if let Ok(content) = fs::read_to_string(path) {
                    for (idx, line) in content.lines().enumerate() {
                        if line.contains(query) {
                            let rel = path
                                .strip_prefix(root)
                                .unwrap_or(path)
                                .to_string_lossy()
                                .to_string();
                            hits.push(json!({
                                "file": rel,
                                "line": idx + 1,
                                "snippet": line.chars().take(160).collect::<String>()
                            }));
                            if hits.len() >= cap {
                                break;
                            }
                        }
                    }
                }
                if hits.len() >= cap {
                    break;
                }
            }
            let payload = json!({ "hits": hits });
            build_receipt(&env.instruction_id, "repo_search", true, 0, false, payload, None)
        }

        ToolCall::FileReadBounded {
            rel_path,
            start_line,
            end_line,
        } => {
            let target = match resolve_safe_path(root, rel_path) {
                Ok(p) => p,
                Err(e) => {
                    return build_receipt(
                        &env.instruction_id,
                        "file_read_bounded",
                        false,
                        1,
                        false,
                        json!({}),
                        Some(e),
                    )
                }
            };
            match fs::read(&target) {
                Ok(bytes) => {
                    let file_hash = sha256_hex(&bytes);
                    let text = String::from_utf8_lossy(&bytes);
                    let start = start_line.saturating_sub(1);
                    let end = (*end_line).max(*start_line).min(start + 250);
                    let slice: Vec<String> = text
                        .lines()
                        .skip(start)
                        .take(end.saturating_sub(start))
                        .enumerate()
                        .map(|(i, l)| format!("{}: {}", start + i + 1, l))
                        .collect();
                    let joined = slice.join("
");
                    let truncated = joined.len() > max_bytes;
                    let clipped: String = joined.chars().take(max_bytes).collect();
                    let payload = json!({
                        "rel_path": rel_path,
                        "sha256": file_hash,
                        "content": clipped
                    });
                    build_receipt(
                        &env.instruction_id,
                        "file_read_bounded",
                        true,
                        0,
                        truncated,
                        payload,
                        None,
                    )
                }
                Err(e) => build_receipt(
                    &env.instruction_id,
                    "file_read_bounded",
                    false,
                    1,
                    false,
                    json!({}),
                    Some(e.to_string()),
                ),
            }
        }

        ToolCall::PatchApplyAnchored {
            rel_path,
            expected_sha256,
            search_block,
            replace_block,
            fuzzy_whitespace,
        } => {
            if is_protected_path(rel_path) {
                return build_receipt(
                    &env.instruction_id,
                    "patch_apply_anchored",
                    false,
                    403,
                    false,
                    json!({}),
                    Some("split-authority violation: protected test/workflow path is immutable to coder".to_string()),
                );
            }
            let target = match resolve_safe_path(root, rel_path) {
                Ok(p) => p,
                Err(e) => {
                    return build_receipt(
                        &env.instruction_id,
                        "patch_apply_anchored",
                        false,
                        1,
                        false,
                        json!({}),
                        Some(e),
                    )
                }
            };
            let bytes = match fs::read(&target) {
                Ok(b) => b,
                Err(e) => {
                    return build_receipt(
                        &env.instruction_id,
                        "patch_apply_anchored",
                        false,
                        1,
                        false,
                        json!({}),
                        Some(e.to_string()),
                    )
                }
            };
            let actual_hash = sha256_hex(&bytes);
            if actual_hash != *expected_sha256 {
                return build_receipt(
                    &env.instruction_id,
                    "patch_apply_anchored",
                    false,
                    409,
                    false,
                    json!({ "actual_sha256": actual_hash }),
                    Some("pre-edit sha256 mismatch; re-read file before patching".to_string()),
                );
            }
            let text = String::from_utf8_lossy(&bytes).to_string();
            let updated = if text.contains(search_block) {
                text.replacen(search_block, replace_block, 1)
            } else if *fuzzy_whitespace {
                match fuzzy_replace_once(&text, search_block, replace_block) {
                    Some(s) => s,
                    None => {
                        return build_receipt(
                            &env.instruction_id,
                            "patch_apply_anchored",
                            false,
                            422,
                            false,
                            json!({}),
                            Some("search_block not found even with fuzzy whitespace matching".to_string()),
                        )
                    }
                }
            } else {
                return build_receipt(
                    &env.instruction_id,
                    "patch_apply_anchored",
                    false,
                    422,
                    false,
                    json!({}),
                    Some("exact search_block not found".to_string()),
                );
            };

            if let Err(e) = fs::write(&target, updated.as_bytes()) {
                return build_receipt(
                    &env.instruction_id,
                    "patch_apply_anchored",
                    false,
                    1,
                    false,
                    json!({}),
                    Some(e.to_string()),
                );
            }
            let new_hash = sha256_hex(updated.as_bytes());
            build_receipt(
                &env.instruction_id,
                "patch_apply_anchored",
                true,
                0,
                false,
                json!({ "rel_path": rel_path, "new_sha256": new_hash }),
                None,
            )
        }

        ToolCall::ExecScoped { program, args } => {
            let manifest = match load_allowlist(root) {
                Ok(m) => m,
                Err(e) => {
                    return build_receipt(
                        &env.instruction_id,
                        "exec_scoped",
                        false,
                        403,
                        false,
                        json!({}),
                        Some(e),
                    );
                }
            };
            let argv = match manifest.get(program) {
                Some(a) => a.clone(),
                None => {
                    return build_receipt(
                        &env.instruction_id,
                        "exec_scoped",
                        false,
                        403,
                        false,
                        json!({ "verbs": manifest.keys().cloned().collect::<Vec<String>>() }),
                        Some(format!("'{program}' is not a declared verb")),
                    );
                }
            };
            if !args.is_empty() {
                return build_receipt(
                    &env.instruction_id,
                    "exec_scoped",
                    false,
                    403,
                    false,
                    json!({}),
                    Some("exec_scoped runs a declared verb; it takes no arguments".to_string()),
                );
            }
            let (bin, rest) = match argv.split_first() {
                Some(pair) => pair,
                None => {
                    return build_receipt(
                        &env.instruction_id,
                        "exec_scoped",
                        false,
                        403,
                        false,
                        json!({}),
                        Some(format!("verb '{program}' declares an empty argv")),
                    );
                }
            };
            let output = Command::new(bin)
                .args(rest)
                .current_dir(root)
                .env_clear()
                .env("PATH", "/usr/local/bin:/usr/bin:/bin")
                .output();

            match output {
                Ok(out) => {
                    let code = out.status.code().unwrap_or(-1);
                    let mut combined = String::from_utf8_lossy(&out.stdout).to_string();
                    let stderr = String::from_utf8_lossy(&out.stderr);
                    if !stderr.is_empty() {
                        combined.push_str("
--- STDERR ---
");
                        combined.push_str(&stderr);
                    }
                    let truncated = combined.len() > max_bytes;
                    let clipped: String = combined.chars().take(max_bytes).collect();
                    build_receipt(
                        &env.instruction_id,
                        "exec_scoped",
                        out.status.success(),
                        code,
                        truncated,
                        json!({ "output": clipped }),
                        None,
                    )
                }
                Err(e) => build_receipt(
                    &env.instruction_id,
                    "exec_scoped",
                    false,
                    1,
                    false,
                    json!({}),
                    Some(e.to_string()),
                ),
            }
        }

        ToolCall::DiffExportCandidate { base_ref } => {
            let output = Command::new("git")
                .args(["diff", "--unified=3", base_ref])
                .current_dir(root)
                .env_clear()
                .env("PATH", "/usr/local/bin:/usr/bin:/bin")
                .output();
            match output {
                Ok(out) => {
                    let diff = String::from_utf8_lossy(&out.stdout).to_string();
                    let truncated = diff.len() > max_bytes;
                    let clipped: String = diff.chars().take(max_bytes).collect();
                    build_receipt(
                        &env.instruction_id,
                        "diff_export_candidate",
                        out.status.success(),
                        out.status.code().unwrap_or(-1),
                        truncated,
                        json!({ "diff": clipped }),
                        None,
                    )
                }
                Err(e) => build_receipt(
                    &env.instruction_id,
                    "diff_export_candidate",
                    false,
                    1,
                    false,
                    json!({}),
                    Some(e.to_string()),
                ),
            }
        }
    }
}

fn fuzzy_replace_once(haystack: &str, needle: &str, replacement: &str) -> Option<String> {
    let h_lines: Vec<&str> = haystack.lines().collect();
    let n_lines: Vec<&str> = needle.lines().map(|l| l.trim()).filter(|l| !l.is_empty()).collect();
    if n_lines.is_empty() || n_lines.len() > h_lines.len() {
        return None;
    }
    for start in 0..=(h_lines.len() - n_lines.len()) {
        let mut matched = true;
        for (offset, n_line) in n_lines.iter().enumerate() {
            if h_lines[start + offset].trim() != *n_line {
                matched = false;
                break;
            }
        }
        if matched {
            let mut out = Vec::with_capacity(h_lines.len());
            out.extend_from_slice(&h_lines[..start]);
            out.push(replacement);
            out.extend_from_slice(&h_lines[start + n_lines.len()..]);
            return Some(out.join("
"));
        }
    }
    None
}

fn build_receipt(
    instruction_id: &str,
    tool: &str,
    ok: bool,
    exit_code: i32,
    truncated: bool,
    payload: serde_json::Value,
    error: Option<String>,
) -> StepReceiptV1 {
    let serialized = serde_json::to_vec(&payload).unwrap_or_default();
    StepReceiptV1 {
        schema_version: "StepReceipt.v1".to_string(),
        instruction_id: instruction_id.to_string(),
        tool: tool.to_string(),
        ok,
        exit_code,
        truncated,
        output_sha256: sha256_hex(&serialized),
        payload,
        error,
    }
}
