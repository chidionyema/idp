use crate::classifier::{classify_ci_failure, is_guarded_path, is_zone_a_forbidden_path};
use crate::crypto::{compute_chained_merkle_root, compute_scope_sha256, FounderVerifier};
use crate::types::{
    CounterexampleEntry, CounterexampleUpsertRequest, CustodyEntry, CustodyUpsertRequest,
    FailureClassSummary, FleetKpis, GroundTruthProjection, OpenPrSummary, PrerequisiteGateRequest,
    PrerequisiteGateVerdict, ProviderEventRequest, ProviderHealth, ReadinessVerdict,
    RealtimeEnvelope, RepoHeadSummary, RoleAllocation, RoleAllocationUpdateRequest,
    StrandedBranchSummary, VerifyFenceRequest, VerifyFenceVerdict, WorkerReadiness,
    MAX_FILES_PER_CHANGE,
};
use anyhow::{anyhow, Result};
use rusqlite::{params, Connection, OptionalExtension};
use serde_json::Value;
use std::collections::{BTreeMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::broadcast;

const MIGRATION_SQL: &str = include_str!("../migrations/001_ground_truth.sql");

fn now_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}

fn now_sec() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

pub struct GroundTruthEngine {
    pub db_path: PathBuf,
    pub write_conn: Mutex<Connection>,
    pub tx: broadcast::Sender<RealtimeEnvelope>,
    pub fencing_token: AtomicU64,
    pub webhook_secret: Option<String>,
    pub founder_verifier: Option<FounderVerifier>,
}

impl GroundTruthEngine {
    /// Opens the isolated Zone B SQLite WAL ledger and rejects any Zone A ~/.estate path.
    pub fn open(
        db_path: impl AsRef<Path>,
        initial_fencing_token: u64,
        webhook_secret: Option<String>,
        founder_verifier: Option<FounderVerifier>,
    ) -> Result<Arc<Self>> {
        let path_buf = db_path.as_ref().to_path_buf();
        let path_str = path_buf.to_string_lossy();
        if path_str.contains("/.estate/") || path_str.ends_with("/estate.db") {
            return Err(anyhow!(
                "HISTORY_QUARANTINE_VIOLATION: GroundTruthEngine cannot mount legacy Zone A path {}",
                path_str
            ));
        }

        if let Some(parent) = path_buf.parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent)?;
            }
        }

        let conn = Connection::open(&path_buf)?;
        conn.execute_batch(MIGRATION_SQL)?;
        conn.execute_batch(crate::web::SQL)?;
        conn.execute(
            "INSERT OR IGNORE INTO kernel_fence_state (singleton_id, authoritative_token, last_merkle_root)
             VALUES (1, ?1, ?2)",
            params![initial_fencing_token as i64, "0".repeat(64)],
        )?;

        let persisted_token: u64 = conn.query_row(
            "SELECT authoritative_token FROM kernel_fence_state WHERE singleton_id = 1",
            [],
            |r| Ok(r.get::<_, i64>(0)? as u64),
        )?;

        let (tx, _) = broadcast::channel(4096);
        Ok(Arc::new(Self {
            db_path: path_buf,
            write_conn: Mutex::new(conn),
            tx,
            fencing_token: AtomicU64::new(persisted_token),
            webhook_secret,
            founder_verifier,
        }))
    }

    pub fn current_fencing_token(&self) -> u64 {
        self.fencing_token.load(Ordering::SeqCst)
    }

    fn emit_ring_event_locked(
        &self,
        conn: &Connection,
        bump_fence: bool,
        topic: &str,
        source_node: &str,
        payload: Value,
    ) -> Result<RealtimeEnvelope> {
        let ts = now_ns();
        let token = if bump_fence {
            self.fencing_token.fetch_add(1, Ordering::SeqCst) + 1
        } else {
            self.fencing_token.load(Ordering::SeqCst)
        };

        let prev_root: String = conn
            .query_row(
                "SELECT last_merkle_root FROM kernel_fence_state WHERE singleton_id = 1",
                [],
                |r| r.get(0),
            )
            .unwrap_or_else(|_| "0".repeat(64));

        let payload_str = serde_json::to_string(&payload)?;
        let merkle_root = compute_chained_merkle_root(&prev_root, ts, token, topic, &payload_str);

        conn.execute(
            "INSERT INTO realtime_event_ring
             (ts_ns, fencing_token, topic, source_node, prev_merkle_root, merkle_root, payload_json)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                ts as i64,
                token as i64,
                topic,
                source_node,
                prev_root,
                merkle_root,
                payload_str
            ],
        )?;
        let seq_id = conn.last_insert_rowid();

        conn.execute(
            "UPDATE kernel_fence_state SET authoritative_token = ?1, last_merkle_root = ?2 WHERE singleton_id = 1",
            params![token as i64, merkle_root],
        )?;

        let env = RealtimeEnvelope {
            seq_id,
            ts_ns: ts,
            fencing_token: token,
            topic: topic.to_string(),
            source_node: source_node.to_string(),
            prev_merkle_root: prev_root,
            merkle_root,
            payload,
        };
        let _ = self.tx.send(env.clone());
        Ok(env)
    }

    /// Idempotently reduces a verified GitHub webhook into live ground-truth tables + broadcasts delta.
    pub fn ingest_github_webhook(
        &self,
        delivery_id: &str,
        event_type: &str,
        payload: &Value,
    ) -> Result<Option<RealtimeEnvelope>> {
        let repo_full_name = payload
            .pointer("/repository/full_name")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown/unknown")
            .to_string();
        let ts = now_ns();

        let conn = self
            .write_conn
            .lock()
            .map_err(|_| anyhow!("SQLite write mutex poisoned"))?;

        // Idempotency guard against duplicate GitHub webhook deliveries
        let already_seen: Option<String> = conn
            .query_row(
                "SELECT delivery_id FROM gt_webhook_deliveries WHERE delivery_id = ?1",
                params![delivery_id],
                |r| r.get(0),
            )
            .optional()?;
        if already_seen.is_some() {
            return Ok(None);
        }

        conn.execute_batch("BEGIN IMMEDIATE;")?;
        let res = (|| -> Result<RealtimeEnvelope> {
            conn.execute(
                "INSERT INTO gt_webhook_deliveries (delivery_id, event_type, repo_full_name, received_at_ns)
                 VALUES (?1, ?2, ?3, ?4)",
                params![delivery_id, event_type, repo_full_name, ts as i64],
            )?;

            let mut bump_fence = false;
            let mut summary = serde_json::json!({
                "deliveryId": delivery_id,
                "eventType": event_type,
                "repo": repo_full_name
            });

            match event_type {
                "push" => {
                    let git_ref = payload.get("ref").and_then(|v| v.as_str()).unwrap_or("");
                    let after_sha = payload.get("after").and_then(|v| v.as_str()).unwrap_or("");
                    let branch = git_ref.strip_prefix("refs/heads/").unwrap_or(git_ref);
                    let default_branch = payload
                        .pointer("/repository/default_branch")
                        .and_then(|v| v.as_str())
                        .unwrap_or("main");
                    let author = payload
                        .pointer("/head_commit/author/name")
                        .and_then(|v| v.as_str())
                        .or_else(|| payload.pointer("/pusher/name").and_then(|v| v.as_str()))
                        .unwrap_or("unknown");
                    let committed_at = payload
                        .pointer("/head_commit/timestamp")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");

                    if branch == default_branch && !after_sha.is_empty() && !after_sha.chars().all(|c| c == '0') {
                        bump_fence = true;
                        conn.execute(
                            "INSERT INTO gt_repos (repo_full_name, default_branch, head_sha, updated_at_ns)
                             VALUES (?1, ?2, ?3, ?4)
                             ON CONFLICT(repo_full_name) DO UPDATE SET
                                default_branch = excluded.default_branch,
                                head_sha = excluded.head_sha,
                                updated_at_ns = excluded.updated_at_ns",
                            params![repo_full_name, default_branch, after_sha, ts as i64],
                        )?;
                    } else if !branch.is_empty() {
                        if after_sha.chars().all(|c| c == '0') {
                            conn.execute(
                                "DELETE FROM gt_branches WHERE repo_full_name = ?1 AND branch_name = ?2",
                                params![repo_full_name, branch],
                            )?;
                        } else {
                            let added_count = payload
                                .pointer("/head_commit/added")
                                .and_then(|v| v.as_array())
                                .map(|a| a.len() as i64)
                                .unwrap_or(0);
                            let modified_count = payload
                                .pointer("/head_commit/modified")
                                .and_then(|v| v.as_array())
                                .map(|a| a.len() as i64)
                                .unwrap_or(0);
                            conn.execute(
                                "INSERT INTO gt_branches (repo_full_name, branch_name, head_sha, code_files_not_on_main, last_author, last_commit_at, updated_at_ns)
                                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
                                 ON CONFLICT(repo_full_name, branch_name) DO UPDATE SET
                                    head_sha = excluded.head_sha,
                                    code_files_not_on_main = MAX(gt_branches.code_files_not_on_main, excluded.code_files_not_on_main),
                                    last_author = excluded.last_author,
                                    last_commit_at = excluded.last_commit_at,
                                    updated_at_ns = excluded.updated_at_ns",
                                params![
                                    repo_full_name,
                                    branch,
                                    after_sha,
                                    added_count + modified_count,
                                    author,
                                    committed_at,
                                    ts as i64
                                ],
                            )?;
                        }
                        self.recompute_repo_branch_counts_locked(&conn, &repo_full_name, ts)?;
                    }
                    summary["branch"] = Value::String(branch.to_string());
                    summary["afterSha"] = Value::String(after_sha.to_string());
                    summary["fencedMainMove"] = Value::Bool(bump_fence);
                }
                "workflow_run" => {
                    let run = payload.get("workflow_run").unwrap_or(&Value::Null);
                    let run_id = run.get("id").and_then(|v| v.as_i64()).unwrap_or(0);
                    let wf_name = run.get("name").and_then(|v| v.as_str()).unwrap_or("unknown");
                    let head_branch = run.get("head_branch").and_then(|v| v.as_str()).unwrap_or("");
                    let head_sha = run.get("head_sha").and_then(|v| v.as_str()).unwrap_or("");
                    let event_name = run.get("event").and_then(|v| v.as_str()).unwrap_or("");
                    let status = run.get("status").and_then(|v| v.as_str()).unwrap_or("completed");
                    let conclusion = run
                        .get("conclusion")
                        .and_then(|v| v.as_str())
                        .unwrap_or("pending");
                    let failing_step = payload
                        .pointer("/workflow_run/failing_step")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let completed_at = run
                        .get("updated_at")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let is_main = if head_branch == "main" { 1 } else { 0 };
                    let failure_class = classify_ci_failure(wf_name, failing_step, conclusion);

                    if run_id > 0 {
                        conn.execute(
                            "INSERT INTO gt_workflow_runs
                             (run_id, repo_full_name, workflow_name, head_branch, head_sha, event_name, status, conclusion, failing_step, failure_class, is_main, completed_at, updated_at_ns)
                             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)
                             ON CONFLICT(run_id) DO UPDATE SET
                                status = excluded.status,
                                conclusion = excluded.conclusion,
                                failing_step = CASE WHEN excluded.failing_step != '' THEN excluded.failing_step ELSE gt_workflow_runs.failing_step END,
                                failure_class = excluded.failure_class,
                                completed_at = excluded.completed_at,
                                updated_at_ns = excluded.updated_at_ns",
                            params![
                                run_id,
                                repo_full_name,
                                wf_name,
                                head_branch,
                                head_sha,
                                event_name,
                                status,
                                conclusion,
                                failing_step,
                                failure_class,
                                is_main,
                                completed_at,
                                ts as i64
                            ],
                        )?;
                    }
                    if is_main == 1 && conclusion == "failure" {
                        bump_fence = true;
                    }
                    summary["workflow"] = Value::String(wf_name.to_string());
                    summary["conclusion"] = Value::String(conclusion.to_string());
                    summary["failureClass"] = Value::String(failure_class.to_string());
                }
                "pull_request" => {
                    let action = payload.get("action").and_then(|v| v.as_str()).unwrap_or("");
                    let pr = payload.get("pull_request").unwrap_or(&Value::Null);
                    let pr_number = pr.get("number").and_then(|v| v.as_i64()).unwrap_or(0);
                    let title = pr.get("title").and_then(|v| v.as_str()).unwrap_or("");
                    let head_branch = pr
                        .pointer("/head/ref")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let head_sha = pr
                        .pointer("/head/sha")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let merged = pr.get("merged").and_then(|v| v.as_bool()).unwrap_or(false);
                    let raw_state = pr.get("state").and_then(|v| v.as_str()).unwrap_or("open");
                    let state = if merged {
                        "MERGED"
                    } else if raw_state.eq_ignore_ascii_case("closed") {
                        "CLOSED"
                    } else {
                        "OPEN"
                    };
                    let opened_at = pr.get("created_at").and_then(|v| v.as_str()).unwrap_or("");

                    if pr_number > 0 {
                        conn.execute(
                            "INSERT INTO gt_pull_requests
                             (repo_full_name, pr_number, title, head_branch, head_sha, state, checks_verdict, failing_checks_json, opened_at, updated_at_ns)
                             VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'PENDING', '[]', ?7, ?8)
                             ON CONFLICT(repo_full_name, pr_number) DO UPDATE SET
                                title = excluded.title,
                                head_branch = excluded.head_branch,
                                head_sha = excluded.head_sha,
                                state = excluded.state,
                                updated_at_ns = excluded.updated_at_ns",
                            params![
                                repo_full_name,
                                pr_number,
                                title,
                                head_branch,
                                head_sha,
                                state,
                                opened_at,
                                ts as i64
                            ],
                        )?;
                    }
                    if merged {
                        bump_fence = true;
                    }
                    summary["prNumber"] = Value::Number(pr_number.into());
                    summary["action"] = Value::String(action.to_string());
                    summary["state"] = Value::String(state.to_string());
                }
                "check_run" => {
                    let cr = payload.get("check_run").unwrap_or(&Value::Null);
                    let check_name = cr.get("name").and_then(|v| v.as_str()).unwrap_or("check");
                    let head_sha = cr.get("head_sha").and_then(|v| v.as_str()).unwrap_or("");
                    let conclusion = cr.get("conclusion").and_then(|v| v.as_str()).unwrap_or("");

                    if !head_sha.is_empty() && !conclusion.is_empty() {
                        let mut stmt = conn.prepare(
                            "SELECT pr_number, failing_checks_json FROM gt_pull_requests
                             WHERE repo_full_name = ?1 AND head_sha = ?2 AND state = 'OPEN'",
                        )?;
                        let matching_prs: Vec<(i64, String)> = stmt
                            .query_map(params![repo_full_name, head_sha], |r| {
                                Ok((r.get(0)?, r.get(1)?))
                            })?
                            .collect::<std::result::Result<Vec<_>, _>>()?;
                        drop(stmt);

                        for (pr_num, failing_json) in matching_prs {
                            let mut failing: Vec<String> =
                                serde_json::from_str(&failing_json).unwrap_or_default();
                            if conclusion == "failure" || conclusion == "timed_out" || conclusion == "action_required" {
                                if !failing.iter().any(|c| c == check_name) {
                                    failing.push(check_name.to_string());
                                }
                            } else if conclusion == "success" || conclusion == "skipped" || conclusion == "neutral" {
                                failing.retain(|c| c != check_name);
                            }
                            let verdict = if failing.is_empty() { "GREEN" } else { "RED" };
                            conn.execute(
                                "UPDATE gt_pull_requests
                                 SET checks_verdict = ?1, failing_checks_json = ?2, updated_at_ns = ?3
                                 WHERE repo_full_name = ?4 AND pr_number = ?5",
                                params![
                                    verdict,
                                    serde_json::to_string(&failing)?,
                                    ts as i64,
                                    repo_full_name,
                                    pr_num
                                ],
                            )?;
                        }
                    }
                    summary["checkName"] = Value::String(check_name.to_string());
                    summary["conclusion"] = Value::String(conclusion.to_string());
                }
                "issues" => {
                    let issue = payload.get("issue").unwrap_or(&Value::Null);
                    let num = issue.get("number").and_then(|v| v.as_i64()).unwrap_or(0);
                    let title = issue.get("title").and_then(|v| v.as_str()).unwrap_or("");
                    let state = if issue
                        .get("state")
                        .and_then(|v| v.as_str())
                        .unwrap_or("open")
                        .eq_ignore_ascii_case("closed")
                    {
                        "CLOSED"
                    } else {
                        "OPEN"
                    };
                    let labels: Vec<String> = issue
                        .get("labels")
                        .and_then(|v| v.as_array())
                        .map(|arr| {
                            arr.iter()
                                .filter_map(|l| l.get("name").and_then(|n| n.as_str()).map(String::from))
                                .collect()
                        })
                        .unwrap_or_default();
                    if num > 0 {
                        conn.execute(
                            "INSERT INTO gt_obligations (repo_full_name, issue_number, title, state, labels_json, updated_at_ns)
                             VALUES (?1, ?2, ?3, ?4, ?5, ?6)
                             ON CONFLICT(repo_full_name, issue_number) DO UPDATE SET
                                title = excluded.title,
                                state = excluded.state,
                                labels_json = excluded.labels_json,
                                updated_at_ns = excluded.updated_at_ns",
                            params![
                                repo_full_name,
                                num,
                                title,
                                state,
                                serde_json::to_string(&labels)?,
                                ts as i64
                            ],
                        )?;
                    }
                    summary["issueNumber"] = Value::Number(num.into());
                    summary["state"] = Value::String(state.to_string());
                }
                _ => {}
            }

            self.emit_ring_event_locked(
                &conn,
                bump_fence,
                &format!("truth.github.{event_type}"),
                "github-webhook",
                summary,
            )
        })();

        match res {
            Ok(env) => {
                conn.execute_batch("COMMIT;")?;
                Ok(Some(env))
            }
            Err(e) => {
                let _ = conn.execute_batch("ROLLBACK;");
                Err(e)
            }
        }
    }

    fn recompute_repo_branch_counts_locked(
        &self,
        conn: &Connection,
        repo_full_name: &str,
        ts: u64,
    ) -> Result<()> {
        let (total, stranded, blobs): (i64, i64, i64) = conn.query_row(
            "SELECT COUNT(*),
                    COALESCE(SUM(CASE WHEN code_files_not_on_main > 0 THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(code_files_not_on_main), 0)
             FROM gt_branches WHERE repo_full_name = ?1",
            params![repo_full_name],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )?;
        conn.execute(
            "INSERT INTO gt_repos (repo_full_name, default_branch, head_sha, branch_count, stranded_branch_count, unique_blobs_off_main, updated_at_ns)
             VALUES (?1, 'main', 'UNKNOWN', ?2, ?3, ?4, ?5)
             ON CONFLICT(repo_full_name) DO UPDATE SET
                branch_count = excluded.branch_count,
                stranded_branch_count = excluded.stranded_branch_count,
                unique_blobs_off_main = excluded.unique_blobs_off_main,
                updated_at_ns = excluded.updated_at_ns",
            params![repo_full_name, total, stranded, blobs, ts as i64],
        )?;
        Ok(())
    }

    /// Real-time provider health signal from sovereign-router / pennyd (trips circuit breakers immediately).
    pub fn ingest_provider_signal(&self, req: &ProviderEventRequest) -> Result<RealtimeEnvelope> {
        let ts = now_ns();
        let (status, bump_fence, open_until_ns) = if req.http_status == 429 {
            let secs = req.circuit_open_seconds.unwrap_or(60);
            ("DEGRADED_429", true, ts + secs * 1_000_000_000)
        } else if req.http_status >= 500 || req.http_status == 0 {
            let secs = req.circuit_open_seconds.unwrap_or(90);
            ("DOWN_5XX", true, ts + secs * 1_000_000_000)
        } else {
            ("HEALTHY", false, 0)
        };

        let conn = self
            .write_conn
            .lock()
            .map_err(|_| anyhow!("SQLite write mutex poisoned"))?;
        conn.execute(
            "INSERT INTO gt_provider_health (provider_id, status, last_http_status, circuit_open_until_ns, detail, updated_at_ns)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)
             ON CONFLICT(provider_id) DO UPDATE SET
                status = excluded.status,
                last_http_status = excluded.last_http_status,
                circuit_open_until_ns = excluded.circuit_open_until_ns,
                detail = excluded.detail,
                updated_at_ns = excluded.updated_at_ns",
            params![
                req.provider_id,
                status,
                req.http_status,
                open_until_ns as i64,
                req.detail.as_deref().unwrap_or(""),
                ts as i64
            ],
        )?;

        self.emit_ring_event_locked(
            &conn,
            bump_fence,
            "truth.provider.health",
            "sovereign-router",
            serde_json::json!({
                "providerId": req.provider_id,
                "status": status,
                "httpStatus": req.http_status,
                "circuitOpenUntilNs": open_until_ns
            }),
        )
    }

    /// Updates a source custody ledger record (AIS-*, GEM-*, QUA-*).
    pub fn upsert_custody(&self, req: &CustodyUpsertRequest) -> Result<RealtimeEnvelope> {
        let ts = now_ns();
        let conn = self
            .write_conn
            .lock()
            .map_err(|_| anyhow!("SQLite write mutex poisoned"))?;
        conn.execute(
            "INSERT INTO gt_custody_ledger (artifact_id, surface, artifact_name, status, location, evidence, updated_at_ns)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
             ON CONFLICT(artifact_id) DO UPDATE SET
                surface = excluded.surface,
                artifact_name = excluded.artifact_name,
                status = excluded.status,
                location = excluded.location,
                evidence = excluded.evidence,
                updated_at_ns = excluded.updated_at_ns",
            params![
                req.artifact_id,
                req.surface,
                req.artifact_name,
                req.status,
                req.location,
                req.evidence,
                ts as i64
            ],
        )?;
        self.emit_ring_event_locked(
            &conn,
            false,
            "truth.custody.updated",
            "custody-reconciler",
            serde_json::to_value(req)?,
        )
    }

    /// Records a deterministic counterexample verdict (bumps fence if a defect flips to CONFIRMED_DEFECT).
    pub fn upsert_counterexamples(
        &self,
        items: &[CounterexampleUpsertRequest],
    ) -> Result<RealtimeEnvelope> {
        let ts = now_ns();
        let conn = self
            .write_conn
            .lock()
            .map_err(|_| anyhow!("SQLite write mutex poisoned"))?;
        let mut any_defect = false;
        for item in items {
            if item.verdict == "CONFIRMED_DEFECT" {
                any_defect = true;
            }
            conn.execute(
                "INSERT INTO gt_counterexamples (check_id, claim, verdict, repo_full_name, head_sha, evidence, checked_at_ns)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
                 ON CONFLICT(check_id) DO UPDATE SET
                    claim = excluded.claim,
                    verdict = excluded.verdict,
                    repo_full_name = excluded.repo_full_name,
                    head_sha = excluded.head_sha,
                    evidence = excluded.evidence,
                    checked_at_ns = excluded.checked_at_ns",
                params![
                    item.check_id,
                    item.claim,
                    item.verdict,
                    item.repo_full_name,
                    item.head_sha,
                    item.evidence,
                    ts as i64
                ],
            )?;
        }
        self.emit_ring_event_locked(
            &conn,
            any_defect,
            "truth.counterexamples.updated",
            "deterministic-ast-scanner",
            serde_json::json!({ "count": items.len(), "anyConfirmedDefect": any_defect }),
        )
    }

    /// Founder-signed real-time role-to-model allocation update (LAW_DYNAMIC_ROLE_MODEL_ALLOCATION).
    /// Enforces >= 2 independent vendors per role unless founder_override_single_vendor is explicitly true.
    pub fn upsert_role_allocation(
        &self,
        req: &RoleAllocationUpdateRequest,
        founder_sig: &str,
    ) -> Result<RealtimeEnvelope> {
        let unique_vendors: HashSet<&str> = req.ordered_pool.iter().map(|s| s.as_str()).collect();
        if unique_vendors.is_empty() {
            return Err(anyhow!("FC_EMPTY_ROLE_POOL: role {} must have >= 1 provider", req.role_id));
        }
        if unique_vendors.len() < 2 && !req.founder_override_single_vendor {
            return Err(anyhow!(
                "FC_MODEL_VENDOR_DEPENDENCY: role {} requires >= 2 independent vendors unless founder_override_single_vendor=true",
                req.role_id
            ));
        }

        let ts = now_ns();
        let conn = self
            .write_conn
            .lock()
            .map_err(|_| anyhow!("SQLite write mutex poisoned"))?;

        let prev_ver: i64 = conn
            .query_row(
                "SELECT config_version FROM gt_role_allocations WHERE role_id = ?1",
                params![req.role_id],
                |r| r.get(0),
            )
            .unwrap_or(0);
        let next_ver = prev_ver + 1;
        let policy = req
            .circuit_breaker_policy
            .as_deref()
            .unwrap_or("trip_on_429_5xx_60s");

        conn.execute(
            "INSERT INTO gt_role_allocations
             (role_id, ordered_pool_json, weights_json, budget_cap_usd, max_tokens_cap, circuit_breaker_policy, config_version, founder_sig, updated_at_ns)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
             ON CONFLICT(role_id) DO UPDATE SET
                ordered_pool_json = excluded.ordered_pool_json,
                weights_json = excluded.weights_json,
                budget_cap_usd = excluded.budget_cap_usd,
                max_tokens_cap = excluded.max_tokens_cap,
                circuit_breaker_policy = excluded.circuit_breaker_policy,
                config_version = excluded.config_version,
                founder_sig = excluded.founder_sig,
                updated_at_ns = excluded.updated_at_ns",
            params![
                req.role_id,
                serde_json::to_string(&req.ordered_pool)?,
                serde_json::to_string(&req.weights)?,
                req.budget_cap_usd,
                req.max_tokens_cap,
                policy,
                next_ver,
                founder_sig,
                ts as i64
            ],
        )?;

        self.emit_ring_event_locked(
            &conn,
            true,
            "role.allocation.updated",
            "founder-control-plane",
            serde_json::json!({
                "roleId": req.role_id,
                "orderedPool": req.ordered_pool,
                "configVersion": next_ver,
                "budgetCapUsd": req.budget_cap_usd,
                "maxTokensCap": req.max_tokens_cap
            }),
        )
    }

    /// Reads the complete real-time 6-block GroundTruthProjection directly from SQLite WAL.
    pub fn read_live_projection(&self) -> Result<GroundTruthProjection> {
        let mut reader = Connection::open(&self.db_path)?;
        let conn=reader.transaction_with_behavior(rusqlite::TransactionBehavior::Deferred)?;
        let ts = now_ns();

        let (fencing_token, merkle_root): (u64, String) = conn
            .query_row(
                "SELECT authoritative_token, last_merkle_root FROM kernel_fence_state WHERE singleton_id = 1",
                [],
                |r| Ok((r.get::<_, i64>(0)? as u64, r.get(1)?)),
            )?;

        let seq_id: i64 = conn
            .query_row(
                "SELECT COALESCE(MAX(seq_id), 0) FROM realtime_event_ring",
                [],
                |r| r.get(0),
            )
            .unwrap_or(0);

        // Block 1: Fleet KPIs
        let (argon_failed, argon_total): (i64, i64) = conn.query_row(
            "SELECT COALESCE(SUM(CASE WHEN conclusion = 'failure' THEN 1 ELSE 0 END), 0), COUNT(*)
             FROM (SELECT conclusion FROM gt_workflow_runs WHERE repo_full_name = 'chidionyema/argon' ORDER BY updated_at_ns DESC LIMIT 1000)",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )?;
        let (gs_failed, gs_total): (i64, i64) = conn.query_row(
            "SELECT COALESCE(SUM(CASE WHEN conclusion = 'failure' THEN 1 ELSE 0 END), 0), COUNT(*)
             FROM gt_workflow_runs WHERE repo_full_name = 'chidionyema/gemini-sync'",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )?;
        let (open_prs_red, open_prs_total): (i64, i64) = conn.query_row(
            "SELECT COALESCE(SUM(CASE WHEN checks_verdict = 'RED' THEN 1 ELSE 0 END), 0), COUNT(*)
             FROM gt_pull_requests WHERE state = 'OPEN'",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )?;

        let mut repo_stmt = conn.prepare(
            "SELECT repo_full_name, default_branch, head_sha, branch_count, stranded_branch_count, unique_blobs_off_main
             FROM gt_repos ORDER BY repo_full_name ASC",
        )?;
        let repos: Vec<RepoHeadSummary> = repo_stmt
            .query_map([], |r| {
                Ok(RepoHeadSummary {
                    repo_full_name: r.get(0)?,
                    default_branch: r.get(1)?,
                    head_sha: r.get(2)?,
                    branch_count: r.get(3)?,
                    stranded_branch_count: r.get(4)?,
                    unique_blobs_off_main: r.get(5)?,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        let argon_meta = repos.iter().find(|r| r.repo_full_name == "chidionyema/argon");
        let block1 = FleetKpis {
            argon_ci_fail_pct: if argon_total > 0 {
                ((argon_failed as f64 / argon_total as f64) * 1000.0).round() / 10.0
            } else {
                0.0
            },
            argon_runs_sampled: argon_total,
            gemini_sync_fail_pct: if gs_total > 0 {
                ((gs_failed as f64 / gs_total as f64) * 1000.0).round() / 10.0
            } else {
                0.0
            },
            gemini_sync_runs_sampled: gs_total,
            open_prs_red,
            open_prs_total,
            argon_stranded_branches: argon_meta.map(|r| r.stranded_branch_count).unwrap_or(0),
            argon_total_branches: argon_meta.map(|r| r.branch_count).unwrap_or(0),
            argon_unique_blobs_off_main: argon_meta.map(|r| r.unique_blobs_off_main).unwrap_or(0),
            repos,
        };

        // Block 6 Counterexamples (needed to compute Block 2 Readiness accurately)
        let mut ce_stmt = conn.prepare(
            "SELECT check_id, claim, verdict, repo_full_name, head_sha, evidence, checked_at_ns
             FROM gt_counterexamples ORDER BY check_id ASC",
        )?;
        let counterexamples: Vec<CounterexampleEntry> = ce_stmt
            .query_map([], |r| {
                Ok(CounterexampleEntry {
                    check_id: r.get(0)?,
                    claim: r.get(1)?,
                    verdict: r.get(2)?,
                    repo_full_name: r.get(3)?,
                    head_sha: r.get(4)?,
                    evidence: r.get(5)?,
                    checked_at_ns: r.get::<_, i64>(6)? as u64,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        // Block 2: Worker Battle-Readiness
        let seven_days_ago_ns = ts.saturating_sub(7 * 24 * 3600 * 1_000_000_000) as i64;
        let (sb_succ, sb_fail, sb_succ_7d): (i64, i64, i64) = conn.query_row(
            "SELECT
                COALESCE(SUM(CASE WHEN conclusion = 'success' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN conclusion = 'failure' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN conclusion = 'success' AND updated_at_ns >= ?1 THEN 1 ELSE 0 END), 0)
             FROM gt_workflow_runs
             WHERE repo_full_name = 'chidionyema/idp' AND lower(workflow_name) LIKE '%agent-sandbox%'",
            params![seven_days_ago_ns],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )?;

        let mut prov_stmt = conn.prepare(
            "SELECT provider_id, status, last_http_status, circuit_open_until_ns, detail, updated_at_ns
             FROM gt_provider_health ORDER BY provider_id ASC",
        )?;
        let providers: Vec<ProviderHealth> = prov_stmt
            .query_map([], |r| {
                Ok(ProviderHealth {
                    provider_id: r.get(0)?,
                    status: r.get(1)?,
                    last_http_status: r.get(2)?,
                    circuit_open_until_ns: r.get::<_, i64>(3)? as u64,
                    detail: r.get(4)?,
                    updated_at_ns: r.get::<_, i64>(5)? as u64,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        let healthy_providers = providers
            .iter()
            .filter(|p| p.status == "HEALTHY" || p.circuit_open_until_ns <= ts)
            .count();
        let provider_capacity_ok = providers.is_empty() || healthy_providers > 0;

        let scope_bound = !counterexamples
            .iter()
            .any(|c| c.check_id == "CE-03-SANDBOX-SCOPE-BINDING" && c.verdict == "CONFIRMED_DEFECT");
        let seal_clean = !counterexamples
            .iter()
            .any(|c| c.check_id == "CE-01-FOUNDER-SEAL-BOOLEAN" && c.verdict == "CONFIRMED_DEFECT");

        let mut blockers = Vec::new();
        if !provider_capacity_ok {
            blockers.push("ALL_PROVIDERS_DEGRADED_OR_CIRCUIT_OPEN".into());
        }
        if !scope_bound {
            blockers.push("CE-03: agent-sandbox.yml missing --scope-sha256".into());
        }
        if !seal_clean {
            blockers.push("CE-01: verify_three_proofs.py forgeable --founder-seal active".into());
        }
        if sb_fail > 0 && sb_succ_7d == 0 {
            blockers.push(format!(
                "AGENT_SANDBOX_ZERO_7D_SUCCESSES (failures={sb_fail})"
            ));
        }

        let block2 = WorkerReadiness {
            verdict: if blockers.is_empty() {
                ReadinessVerdict::Ready
            } else {
                ReadinessVerdict::NotReady
            },
            agent_sandbox_success_lifetime: sb_succ,
            agent_sandbox_failure_lifetime: sb_fail,
            agent_sandbox_success_last_7d: sb_succ_7d,
            provider_capacity_ok,
            scope_bound_before_inference: scope_bound,
            founder_seal_boolean_eliminated: seal_clean,
            blockers,
            providers,
        };

        // Block 3: Custody Ledger
        let mut cust_stmt = conn.prepare(
            "SELECT artifact_id, surface, artifact_name, status, location, evidence, updated_at_ns
             FROM gt_custody_ledger ORDER BY artifact_id ASC",
        )?;
        let block3: Vec<CustodyEntry> = cust_stmt
            .query_map([], |r| {
                Ok(CustodyEntry {
                    artifact_id: r.get(0)?,
                    surface: r.get(1)?,
                    artifact_name: r.get(2)?,
                    status: r.get(3)?,
                    location: r.get(4)?,
                    evidence: r.get(5)?,
                    updated_at_ns: r.get::<_, i64>(6)? as u64,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        // Block 4: Recurrent CI Failure Taxonomy
        let mut tax_stmt = conn.prepare(
            "SELECT failure_class, repo_full_name, workflow_name,
                    SUM(CASE WHEN conclusion = 'failure' THEN 1 ELSE 0 END) AS failed_runs,
                    COUNT(*) AS total_runs,
                    SUM(CASE WHEN conclusion = 'failure' AND is_main = 1 THEN 1 ELSE 0 END) AS failed_on_main,
                    MAX(failing_step) AS failing_step
             FROM gt_workflow_runs
             WHERE failure_class != 'NONE'
             GROUP BY failure_class, repo_full_name, workflow_name
             ORDER BY failed_runs DESC
             LIMIT 30",
        )?;
        let block4: Vec<FailureClassSummary> = tax_stmt
            .query_map([], |r| {
                Ok(FailureClassSummary {
                    failure_class: r.get(0)?,
                    repo_full_name: r.get(1)?,
                    workflow_name: r.get(2)?,
                    failed_runs: r.get(3)?,
                    total_runs: r.get(4)?,
                    failed_on_main: r.get(5)?,
                    failing_step: r.get::<_, Option<String>>(6)?.unwrap_or_default(),
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        // Block 5: Open PRs & Stranded Branches
        let mut pr_stmt = conn.prepare(
            "SELECT repo_full_name, pr_number, title, head_branch, head_sha, checks_verdict, failing_checks_json, opened_at
             FROM gt_pull_requests WHERE state = 'OPEN' ORDER BY repo_full_name ASC, pr_number DESC LIMIT 100",
        )?;
        let block5_prs: Vec<OpenPrSummary> = pr_stmt
            .query_map([], |r| {
                let raw: String = r.get(6)?;
                Ok(OpenPrSummary {
                    repo_full_name: r.get(0)?,
                    pr_number: r.get(1)?,
                    title: r.get(2)?,
                    head_branch: r.get(3)?,
                    head_sha: r.get(4)?,
                    checks_verdict: r.get(5)?,
                    failing_checks: serde_json::from_str(&raw).unwrap_or_default(),
                    opened_at: r.get(7)?,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        let mut br_stmt = conn.prepare(
            "SELECT repo_full_name, branch_name, head_sha, code_files_not_on_main, last_author, last_commit_at
             FROM gt_branches WHERE code_files_not_on_main > 0
             ORDER BY code_files_not_on_main DESC LIMIT 20",
        )?;
        let block5_branches: Vec<StrandedBranchSummary> = br_stmt
            .query_map([], |r| {
                Ok(StrandedBranchSummary {
                    repo_full_name: r.get(0)?,
                    branch_name: r.get(1)?,
                    head_sha: r.get(2)?,
                    code_files_not_on_main: r.get(3)?,
                    last_author: r.get(4)?,
                    last_commit_at: r.get(5)?,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        let open_obligations: i64 = conn.query_row(
            "SELECT COUNT(*) FROM gt_obligations WHERE state = 'OPEN'",
            [],
            |r| r.get(0),
        )?;

        let mut role_stmt = conn.prepare(
            "SELECT role_id, ordered_pool_json, weights_json, budget_cap_usd, max_tokens_cap, circuit_breaker_policy, config_version, founder_sig, updated_at_ns
             FROM gt_role_allocations ORDER BY role_id ASC",
        )?;
        let role_allocations: Vec<RoleAllocation> = role_stmt
            .query_map([], |r| {
                let pool_raw: String = r.get(1)?;
                let weights_raw: String = r.get(2)?;
                Ok(RoleAllocation {
                    role_id: r.get(0)?,
                    ordered_pool: serde_json::from_str(&pool_raw).unwrap_or_default(),
                    weights: serde_json::from_str::<BTreeMap<String, f64>>(&weights_raw)
                        .unwrap_or_default(),
                    budget_cap_usd: r.get(3)?,
                    max_tokens_cap: r.get(4)?,
                    circuit_breaker_policy: r.get(5)?,
                    config_version: r.get(6)?,
                    founder_sig: r.get(7)?,
                    updated_at_ns: r.get::<_, i64>(8)? as u64,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        Ok(GroundTruthProjection {
            schema_version: "meridian-ground-truth-v1".into(),
            seq_id,
            fencing_token,
            merkle_root,
            generated_at_ns: ts,
            block1_fleet_kpis: block1,
            block2_worker_readiness: block2,
            block3_custody_ledger: block3,
            block4_failure_taxonomy: block4,
            block5_open_prs: block5_prs,
            block5_top_stranded_branches: block5_branches,
            block6_counterexamples: counterexamples,
            block6_open_obligation_count: open_obligations,
            block6_role_allocations: role_allocations,
        })
    }

    /// Compact, deterministic 6-block Markdown view for zero-friction boot injection on ANY agent surface.
    pub fn render_compact_markdown(&self, proj: &GroundTruthProjection) -> String {
        let mut out = String::with_capacity(2048);
        out.push_str(&format!(
            "# MERIDIAN LIVE GROUND TRUTH (FENCE #{} · SEQ #{} · MERKLE {})\n\n",
            proj.fencing_token,
            proj.seq_id,
            &proj.merkle_root
        ));
        out.push_str(&format!(
            "## 1. Fleet KPIs\n- argon CI failing: {:.1}% ({} runs) | gemini-sync failing: {:.1}% ({} runs)\n- Open PRs red: {}/{} | argon stranded branches: {}/{} ({} unique blobs)\n",
            proj.block1_fleet_kpis.argon_ci_fail_pct,
            proj.block1_fleet_kpis.argon_runs_sampled,
            proj.block1_fleet_kpis.gemini_sync_fail_pct,
            proj.block1_fleet_kpis.gemini_sync_runs_sampled,
            proj.block1_fleet_kpis.open_prs_red,
            proj.block1_fleet_kpis.open_prs_total,
            proj.block1_fleet_kpis.argon_stranded_branches,
            proj.block1_fleet_kpis.argon_total_branches,
            proj.block1_fleet_kpis.argon_unique_blobs_off_main
        ));
        for r in &proj.block1_fleet_kpis.repos {
            out.push_str(&format!(
                "- `{}` @ `{}` (branches={}, stranded={})\n",
                r.repo_full_name,
                &r.head_sha[..9.min(r.head_sha.len())],
                r.branch_count,
                r.stranded_branch_count
            ));
        }

        out.push_str(&format!(
            "\n## 2. Worker Readiness: {:?}\n- agent-sandbox: {} ok / {} fail (last 7d ok={}) | provider_capacity_ok={} | scope_bound={} | seal_clean={}\n",
            proj.block2_worker_readiness.verdict,
            proj.block2_worker_readiness.agent_sandbox_success_lifetime,
            proj.block2_worker_readiness.agent_sandbox_failure_lifetime,
            proj.block2_worker_readiness.agent_sandbox_success_last_7d,
            proj.block2_worker_readiness.provider_capacity_ok,
            proj.block2_worker_readiness.scope_bound_before_inference,
            proj.block2_worker_readiness.founder_seal_boolean_eliminated
        ));
        for b in &proj.block2_worker_readiness.blockers {
            out.push_str(&format!("- BLOCKER: {b}\n"));
        }

        if !proj.block3_custody_ledger.is_empty() {
            out.push_str("\n## 3. Source Custody\n");
            for c in &proj.block3_custody_ledger {
                out.push_str(&format!(
                    "- {} [{}] {}: {} ({})\n",
                    c.artifact_id, c.status, c.surface, c.location, c.evidence
                ));
            }
        }

        if !proj.block4_failure_taxonomy.is_empty() {
            out.push_str("\n## 4. Recurrent CI Failure Taxonomy\n");
            for f in proj.block4_failure_taxonomy.iter().take(12) {
                out.push_str(&format!(
                    "- [{}] {} · {}: {}/{} failed (main={}) step={}\n",
                    f.failure_class,
                    f.repo_full_name,
                    f.workflow_name,
                    f.failed_runs,
                    f.total_runs,
                    f.failed_on_main,
                    f.failing_step
                ));
            }
        }

        if !proj.block6_counterexamples.is_empty() {
            out.push_str("\n## 6. Live Counterexamples & Role Allocations\n");
            for ce in &proj.block6_counterexamples {
                out.push_str(&format!(
                    "- {} [{}]: {} ({})\n",
                    ce.check_id, ce.verdict, ce.claim, ce.evidence
                ));
            }
        }
        for role in &proj.block6_role_allocations {
            out.push_str(&format!(
                "- role `{}` v{}: pool={:?} cap=${:.2} max_tokens={}\n",
                role.role_id,
                role.config_version,
                role.ordered_pool,
                role.budget_cap_usd,
                role.max_tokens_cap
            ));
        }

        out
    }

    /// Universal mandatory prerequisite gate called BEFORE any agent spends inference tokens.
    pub fn admit_agent_turn(&self, req: &PrerequisiteGateRequest) -> Result<PrerequisiteGateVerdict> {
        let proj = self.read_live_projection()?;
        let brief = self.render_compact_markdown(&proj);
        let ts = now_ns();

        // 1. Stale fence check (forces every agent to read current live ground truth first)
        if req.seen_fencing_token != proj.fencing_token {
            return Ok(PrerequisiteGateVerdict {
                admitted: false,
                reason: format!(
                    "STALE_FENCING_TOKEN: agent saw fence #{}, live ground truth is #{}; refresh before inference",
                    req.seen_fencing_token, proj.fencing_token
                ),
                lease_id: None,
                bound_seq_id: proj.seq_id,
                bound_fencing_token: proj.fencing_token,
                scope_sha256: None,
                selected_provider_pool: vec![],
                expires_at_sec: None,
                live_markdown_brief: brief,
            });
        }

        // 2. Hard Zone A / DARWIN_THIN_CLIENT rejection
        for p in &req.planned_paths {
            if is_zone_a_forbidden_path(p) {
                return Ok(PrerequisiteGateVerdict {
                    admitted: false,
                    reason: format!("FC_ZONE_A_DARWIN_REGRESSION: forbidden path '{}'", p),
                    lease_id: None,
                    bound_seq_id: proj.seq_id,
                    bound_fencing_token: proj.fencing_token,
                    scope_sha256: None,
                    selected_provider_pool: vec![],
                    expires_at_sec: None,
                    live_markdown_brief: brief,
                });
            }
        }

        // 3. Provider capacity preflight (stops 429 token burn BEFORE inference starts)
        let role_pool: Vec<String> = proj
            .block6_role_allocations
            .iter()
            .find(|r| r.role_id == req.role_id)
            .map(|r| r.ordered_pool.clone())
            .unwrap_or_default();

        let available_pool: Vec<String> = if role_pool.is_empty() {
            proj.block2_worker_readiness
                .providers
                .iter()
                .filter(|p| p.status == "HEALTHY" || p.circuit_open_until_ns <= ts)
                .map(|p| p.provider_id.clone())
                .collect()
        } else {
            role_pool
                .into_iter()
                .filter(|prov| {
                    proj.block2_worker_readiness
                        .providers
                        .iter()
                        .find(|p| &p.provider_id == prov)
                        .map(|p| p.status == "HEALTHY" || p.circuit_open_until_ns <= ts)
                        .unwrap_or(true)
                })
                .collect()
        };

        if !proj.block2_worker_readiness.providers.is_empty() && available_pool.is_empty() {
            return Ok(PrerequisiteGateVerdict {
                admitted: false,
                reason: "PROVIDER_CAPACITY_EXHAUSTED: all providers for role have open circuit breakers (429/5xx)".into(),
                lease_id: None,
                bound_seq_id: proj.seq_id,
                bound_fencing_token: proj.fencing_token,
                scope_sha256: None,
                selected_provider_pool: vec![],
                expires_at_sec: None,
                live_markdown_brief: brief,
            });
        }

        // 4. Write-scope checks (bypassed only for pure read-only recon)
        if !req.read_only_recon {
            if req.planned_paths.is_empty() {
                return Ok(PrerequisiteGateVerdict {
                    admitted: false,
                    reason: "EMPTY_WRITE_SCOPE: mutating turn must declare exact planned_paths before inference".into(),
                    lease_id: None,
                    bound_seq_id: proj.seq_id,
                    bound_fencing_token: proj.fencing_token,
                    scope_sha256: None,
                    selected_provider_pool: available_pool,
                    expires_at_sec: None,
                    live_markdown_brief: brief,
                });
            }

            if !req.is_atomic_ic_bundle && req.planned_paths.len() > MAX_FILES_PER_CHANGE {
                return Ok(PrerequisiteGateVerdict {
                    admitted: false,
                    reason: format!(
                        "MAX_FILES_PER_CHANGE_EXCEEDED: {} > {} (set is_atomic_ic_bundle=true only for atomic IC bundles)",
                        req.planned_paths.len(),
                        MAX_FILES_PER_CHANGE
                    ),
                    lease_id: None,
                    bound_seq_id: proj.seq_id,
                    bound_fencing_token: proj.fencing_token,
                    scope_sha256: None,
                    selected_provider_pool: available_pool,
                    expires_at_sec: None,
                    live_markdown_brief: brief,
                });
            }

            // Orphan CA5 ban: catalog/issue-classes.json cannot be edited alone
            if req.planned_paths.len() == 1 && req.planned_paths[0] == "catalog/issue-classes.json" {
                return Ok(PrerequisiteGateVerdict {
                    admitted: false,
                    reason: "FC_ORPHAN_CLASS_WITHOUT_LIVE_ENFORCER: catalog/issue-classes.json cannot be mutated without live caller + falsifier in the same atomic IC bundle".into(),
                    lease_id: None,
                    bound_seq_id: proj.seq_id,
                    bound_fencing_token: proj.fencing_token,
                    scope_sha256: None,
                    selected_provider_pool: available_pool,
                    expires_at_sec: None,
                    live_markdown_brief: brief,
                });
            }

            // Refuse guarded paths on unsealed autonomous surfaces
            if req.planned_paths.iter().any(|p| is_guarded_path(p))
                && !req.agent_surface.starts_with("founder")
            {
                return Ok(PrerequisiteGateVerdict {
                    admitted: false,
                    reason: "GUARDED_PATH_REQUIRES_OFFHOST_FOUNDER_SEAL: autonomous Class B worker cannot admit guarded control-plane paths".into(),
                    lease_id: None,
                    bound_seq_id: proj.seq_id,
                    bound_fencing_token: proj.fencing_token,
                    scope_sha256: None,
                    selected_provider_pool: available_pool,
                    expires_at_sec: None,
                    live_markdown_brief: brief,
                });
            }
        }

        let scope_sha256 =
            compute_scope_sha256(&req.repo_full_name, proj.fencing_token, &req.planned_paths);
        
        let ttl = req.ttl_seconds.unwrap_or(300).min(600) as i64;
        let exp = now_sec() + ttl;

        let mut conn = self
            .write_conn
            .lock()
            .map_err(|_| anyhow!("SQLite write mutex poisoned"))?;
        let conn=conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
        let persisted: i64 = conn.query_row(
            "SELECT authoritative_token FROM kernel_fence_state WHERE singleton_id=1",[],|r|r.get(0))?;
        if persisted < 0 || persisted as u64 != proj.fencing_token {
            return Ok(PrerequisiteGateVerdict {
                admitted:false,reason:"STALE_FENCING_TOKEN: changed during admission".into(),
                lease_id:None,bound_seq_id:proj.seq_id,bound_fencing_token:persisted.max(0) as u64,
                scope_sha256:None,selected_provider_pool:vec![],expires_at_sec:None,live_markdown_brief:brief,
            });
        }
        let lease_id: String = conn.query_row("SELECT 'LEASE-' || lower(hex(randomblob(16)))", [], |r|r.get(0))?;
        conn.execute(
            "INSERT INTO gt_agent_leases
             (lease_id, agent_surface, role_id, repo_full_name, bound_seq_id, bound_fencing_token, admitted_paths_json, scope_sha256, expires_at_sec, status, created_at_ns)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, 'ACTIVE', ?10)",
            params![
                lease_id,
                req.agent_surface,
                req.role_id,
                req.repo_full_name,
                proj.seq_id,
                proj.fencing_token as i64,
                serde_json::to_string(&req.planned_paths)?,
                scope_sha256,
                exp,
                ts as i64
            ],
        )?;

        conn.commit()?;
        Ok(PrerequisiteGateVerdict {
            admitted: true,
            reason: "ADMITTED_WITH_LIVE_FENCE".into(),
            lease_id: Some(lease_id),
            bound_seq_id: proj.seq_id,
            bound_fencing_token: proj.fencing_token,
            scope_sha256: Some(scope_sha256),
            selected_provider_pool: available_pool,
            expires_at_sec: Some(exp),
            live_markdown_brief: brief,
        })
    }

    /// Mandatory pre-submit fence & scope verifier called by submit-lane / pre-push / CI.
    pub fn verify_fence(&self, req: &VerifyFenceRequest) -> Result<VerifyFenceVerdict> {
        let conn = self.write_conn.lock().map_err(|_| anyhow!("SQLite write mutex poisoned"))?;
        let current_fence: u64 = conn.query_row(
            "SELECT authoritative_token FROM kernel_fence_state WHERE singleton_id=1",[],|r|Ok(r.get::<_,i64>(0)? as u64))?;

        let row: Option<(i64, String, String, i64, String)> = conn
            .query_row(
                "SELECT bound_fencing_token, admitted_paths_json, scope_sha256, expires_at_sec, status
                 FROM gt_agent_leases WHERE lease_id = ?1",
                params![req.lease_id],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
            )
            .optional()?;

        let Some((bound_token, admitted_json, expected_sha, expires_at, status)) = row else {
            return Ok(VerifyFenceVerdict {
                valid: false,
                code: "LEASE_NOT_FOUND".into(),
                current_fencing_token: current_fence,
                detail: format!("No active lease found for {}", req.lease_id),
            });
        };

        if status != "ACTIVE" || now_sec() > expires_at {
            return Ok(VerifyFenceVerdict {
                valid: false,
                code: "LEASE_EXPIRED_OR_REVOKED".into(),
                current_fencing_token: current_fence,
                detail: format!("Lease {} is {} (expires_at={})", req.lease_id, status, expires_at),
            });
        }

        if req.presented_fencing_token != current_fence || bound_token as u64 != current_fence {
            return Ok(VerifyFenceVerdict {
                valid: false,
                code: "STALE_FENCING_TOKEN".into(),
                current_fencing_token: current_fence,
                detail: format!(
                    "Mutation fenced: lease bound to #{}, presented #{}, live truth is #{}",
                    bound_token, req.presented_fencing_token, current_fence
                ),
            });
        }

        if req.presented_scope_sha256 != expected_sha {
            return Ok(VerifyFenceVerdict {
                valid: false,
                code: "SCOPE_SHA256_MISMATCH".into(),
                current_fencing_token: current_fence,
                detail: format!(
                    "Expected scope_sha256 {}, got {}",
                    expected_sha, req.presented_scope_sha256
                ),
            });
        }

        let admitted: HashSet<String> = serde_json::from_str::<Vec<String>>(&admitted_json)
            .unwrap_or_default()
            .into_iter()
            .collect();
        for p in &req.touched_paths {
            if !admitted.contains(p) {
                return Ok(VerifyFenceVerdict {
                    valid: false,
                    code: "UNADMITTED_PATH_TOUCHED".into(),
                    current_fencing_token: current_fence,
                    detail: format!("Path '{}' was not admitted in lease {}", p, req.lease_id),
                });
            }
        }

        Ok(VerifyFenceVerdict {
            valid: true,
            code: "FENCE_AND_SCOPE_VERIFIED".into(),
            current_fencing_token: current_fence,
            detail: "Live fence, lease TTL, scope SHA-256, and touched paths verified".into(),
        })
    }

    pub fn fetch_replay_since(&self, since_seq: i64, limit: usize) -> Result<Vec<RealtimeEnvelope>> {
        let conn = Connection::open(&self.db_path)?;
        let mut stmt = conn.prepare(
            "SELECT seq_id, ts_ns, fencing_token, topic, source_node, prev_merkle_root, merkle_root, payload_json
             FROM realtime_event_ring
             WHERE seq_id > ?1
             ORDER BY seq_id ASC
             LIMIT ?2",
        )?;
        let rows = stmt.query_map(params![since_seq, limit as i64], |r| {
            let raw: String = r.get(7)?;
            Ok(RealtimeEnvelope {
                seq_id: r.get(0)?,
                ts_ns: r.get::<_, i64>(1)? as u64,
                fencing_token: r.get::<_, i64>(2)? as u64,
                topic: r.get(3)?,
                source_node: r.get(4)?,
                prev_merkle_root: r.get(5)?,
                merkle_root: r.get(6)?,
                payload: serde_json::from_str(&raw).unwrap_or(Value::Null),
            })
        })?;
        let mut out = Vec::new();
        for r in rows {
            out.push(r?);
        }
        Ok(out)
    }
}
