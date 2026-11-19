use crate::store::GroundTruthEngine;
use crate::types::TRACKED_REPOS;
use anyhow::Result;
use serde_json::Value;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

/// Gap-only cold-boot / missed-delivery reconciler against the GitHub REST API.
/// NEVER runs on a polling timer; invoked strictly at daemon startup or after a delivery-gap alert.
pub async fn cold_boot_reconcile(engine: Arc<GroundTruthEngine>, github_token: &str) -> Result<usize> {
    if github_token.trim().is_empty() {
        return Ok(0);
    }

    let client = reqwest::Client::builder()
        .user_agent("genesis-ground-truth/0.9.1")
        .build()?;
    let mut ingested = 0usize;
    let boot_tag = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    for repo in TRACKED_REPOS {
        // 1. Default branch HEAD SHA
        let repo_url = format!("https://api.github.com/repos/{repo}");
        if let Ok(resp) = client
            .get(&repo_url)
            .bearer_auth(github_token)
            .send()
            .await
        {
            if let Ok(meta) = resp.json::<Value>().await {
                let default_branch = meta
                    .get("default_branch")
                    .and_then(|v| v.as_str())
                    .unwrap_or("main");
                let ref_url = format!("https://api.github.com/repos/{repo}/git/ref/heads/{default_branch}");
                if let Ok(ref_resp) = client.get(&ref_url).bearer_auth(github_token).send().await {
                    if let Ok(ref_json) = ref_resp.json::<Value>().await {
                        if let Some(sha) = ref_json.pointer("/object/sha").and_then(|v| v.as_str()) {
                            let synthetic = serde_json::json!({
                                "ref": format!("refs/heads/{default_branch}"),
                                "after": sha,
                                "repository": {
                                    "full_name": repo,
                                    "default_branch": default_branch
                                }
                            });
                            let delivery = format!("coldboot-push-{repo}-{sha}-{boot_tag}");
                            if engine.ingest_github_webhook(&delivery, "push", &synthetic)?.is_some() {
                                ingested += 1;
                            }
                        }
                    }
                }
            }
        }

        // 2. Recent workflow runs (up to 100 newest)
        let runs_url = format!("https://api.github.com/repos/{repo}/actions/runs?per_page=100");
        if let Ok(resp) = client.get(&runs_url).bearer_auth(github_token).send().await {
            if let Ok(body) = resp.json::<Value>().await {
                if let Some(runs) = body.get("workflow_runs").and_then(|v| v.as_array()) {
                    for run in runs {
                        let run_id = run.get("id").and_then(|v| v.as_i64()).unwrap_or(0);
                        let synthetic = serde_json::json!({
                            "repository": { "full_name": repo },
                            "workflow_run": run
                        });
                        let delivery = format!("coldboot-run-{repo}-{run_id}-{boot_tag}");
                        if engine
                            .ingest_github_webhook(&delivery, "workflow_run", &synthetic)?
                            .is_some()
                        {
                            ingested += 1;
                        }
                    }
                }
            }
        }

        // 3. Open PRs
        let prs_url = format!("https://api.github.com/repos/{repo}/pulls?state=open&per_page=100");
        if let Ok(resp) = client.get(&prs_url).bearer_auth(github_token).send().await {
            if let Ok(prs) = resp.json::<Vec<Value>>().await {
                for pr in prs {
                    let num = pr.get("number").and_then(|v| v.as_i64()).unwrap_or(0);
                    let synthetic = serde_json::json!({
                        "action": "opened",
                        "repository": { "full_name": repo },
                        "pull_request": pr
                    });
                    let delivery = format!("coldboot-pr-{repo}-{num}-{boot_tag}");
                    if engine
                        .ingest_github_webhook(&delivery, "pull_request", &synthetic)?
                        .is_some()
                    {
                        ingested += 1;
                    }
                }
            }
        }
    }

    Ok(ingested)
}
