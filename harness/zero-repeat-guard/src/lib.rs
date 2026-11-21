//! Deterministic Zero-Repeat & Headless Continuation Guard
//!
//! Enforces five non-advisory invariants with zero external crate dependencies:
//! 1. 1-Strike Failure-Class Circuit Breaker & Bot Auto-Merge Loop Cap
//! 2. Headless Worker Auto-Continuation (bans push-announce-wait-for-Founder)
//! 3. Superseded-Head Watcher Abort (stops infinite pending polls on force-pushed lanes)
//! 4. Durable Consumer-Ack Founder Inbox & Passkey Sink (bans 24h nonce-only TTL & Mac PID pollers)
//! 5. Pre-Emit Workflow 0-Job & Legion Admission Precondition Preflight

use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct FailureClassId {
    pub gate: String,
    pub rule: String,
    pub target: String,
}

impl FailureClassId {
    pub fn new(gate: &str, rule: &str, target: &str) -> Self {
        Self {
            gate: gate.trim().to_string(),
            rule: rule.trim().to_string(),
            target: target.trim().to_string(),
        }
    }

    pub fn canonical(&self) -> String {
        format!("{}::{}::{}", self.gate, self.rule, self.target)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ClassStatus {
    Clear,
    ImmunizationRequired {
        first_sha: String,
        strike_count: u32,
    },
    ClassQuarantine {
        first_sha: String,
        repeat_sha: String,
        strike_count: u32,
    },
    Immunized {
        wall_check_path: String,
        regression_test_path: String,
        commit_sha: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ImmunizationProof {
    pub commit_sha: String,
    pub wall_check_path: String,
    pub regression_test_path: String,
    pub failed_before_fix: bool,
    pub passed_after_fix: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GuardError {
    UnimmunizedRetry { class_id: String, strike_count: u32 },
    ClassQuarantined { class_id: String, strike_count: u32 },
    InvalidImmunizationProof(String),
    BotSyncLoopQuarantined { pr_id: String, red_sync_count: u32 },
    FounderEventLoopForbidden { worker_id: String, lane: String },
    UnconsumedFounderTap { key: String },
    LocalPollerOrTerminalTrapForbidden(String),
    ZeroJobWorkflow(String),
    AdmissionPreconditionFailed(Vec<String>),
}

#[derive(Debug, Default)]
pub struct CircuitBreakerLedger {
    classes: BTreeMap<String, ClassStatus>,
    red_bot_syncs: BTreeMap<String, u32>,
}

impl CircuitBreakerLedger {
    pub fn new() -> Self {
        Self::default()
    }

    /// Record a CI/gate failure. Strike 1 demands immunization; Strike 2 triggers hard CLASS_QUARANTINE.
    pub fn record_failure(&mut self, class_id: &FailureClassId, head_sha: &str) -> ClassStatus {
        let key = class_id.canonical();
        let next = match self.classes.get(&key) {
            None | Some(ClassStatus::Clear) | Some(ClassStatus::Immunized { .. }) => {
                ClassStatus::ImmunizationRequired {
                    first_sha: head_sha.to_string(),
                    strike_count: 1,
                }
            }
            Some(ClassStatus::ImmunizationRequired {
                first_sha,
                strike_count,
            }) => ClassStatus::ClassQuarantine {
                first_sha: first_sha.clone(),
                repeat_sha: head_sha.to_string(),
                strike_count: strike_count + 1,
            },
            Some(ClassStatus::ClassQuarantine {
                first_sha,
                strike_count,
                ..
            }) => ClassStatus::ClassQuarantine {
                first_sha: first_sha.clone(),
                repeat_sha: head_sha.to_string(),
                strike_count: strike_count + 1,
            },
        };
        self.classes.insert(key, next.clone());
        next
    }

    /// Authorize whether a retry/dispatch touching this failure class may proceed.
    pub fn allow_dispatch(&self, class_id: &FailureClassId) -> Result<(), GuardError> {
        let key = class_id.canonical();
        match self.classes.get(&key) {
            None | Some(ClassStatus::Clear) | Some(ClassStatus::Immunized { .. }) => Ok(()),
            Some(ClassStatus::ImmunizationRequired { strike_count, .. }) => {
                Err(GuardError::UnimmunizedRetry {
                    class_id: key,
                    strike_count: *strike_count,
                })
            }
            Some(ClassStatus::ClassQuarantine { strike_count, .. }) => {
                Err(GuardError::ClassQuarantined {
                    class_id: key,
                    strike_count: *strike_count,
                })
            }
        }
    }

    /// Immunize a failure class only with verified pre-emit wall check + failing-then-passing regression test.
    pub fn record_immunization(
        &mut self,
        class_id: &FailureClassId,
        proof: &ImmunizationProof,
    ) -> Result<ClassStatus, GuardError> {
        if !is_valid_git_sha(&proof.commit_sha) {
            return Err(GuardError::InvalidImmunizationProof(
                "commit_sha must be 7..=40 lowercase hex chars".into(),
            ));
        }
        if proof.wall_check_path.trim().is_empty() || proof.regression_test_path.trim().is_empty() {
            return Err(GuardError::InvalidImmunizationProof(
                "both wall_check_path and regression_test_path are mandatory".into(),
            ));
        }
        if !(proof.failed_before_fix && proof.passed_after_fix) {
            return Err(GuardError::InvalidImmunizationProof(
                "regression test must prove failed_before_fix=true and passed_after_fix=true".into(),
            ));
        }
        let status = ClassStatus::Immunized {
            wall_check_path: proof.wall_check_path.clone(),
            regression_test_path: proof.regression_test_path.clone(),
            commit_sha: proof.commit_sha.clone(),
        };
        self.classes.insert(class_id.canonical(), status.clone());
        Ok(status)
    }

    /// Cap bot main-into-PR auto-merges on red branches to 1; any second merge without a fix commit is quarantined.
    pub fn record_bot_sync(
        &mut self,
        pr_id: &str,
        ci_is_green: bool,
        has_new_fix_commit: bool,
    ) -> Result<u32, GuardError> {
        if ci_is_green || has_new_fix_commit {
            self.red_bot_syncs.insert(pr_id.to_string(), 0);
            return Ok(0);
        }
        let count = self.red_bot_syncs.entry(pr_id.to_string()).or_insert(0);
        *count += 1;
        if *count > 1 {
            return Err(GuardError::BotSyncLoopQuarantined {
                pr_id: pr_id.to_string(),
                red_sync_count: *count,
            });
        }
        Ok(*count)
    }
}

/// Headless Worker Continuation Engine (Invariant 2)
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkerNextAction {
    PullNextTicket { mission_id: String },
    HandleGreenlaneVerdict { lane: String, head_sha: String },
    IdleWaitForQueueEvent,
    IdleWaitForFounder,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LaneHandoffReceipt {
    pub worker_id: String,
    pub lane: String,
    pub head_sha: String,
    pub issue_id: String,
    pub next_action: WorkerNextAction,
}

pub fn enforce_headless_handoff(
    worker_id: &str,
    lane: &str,
    head_sha: &str,
    issue_id: &str,
    pending_verdict: Option<(String, String)>,
    next_unblocked_ticket: Option<String>,
    requested_action: WorkerNextAction,
) -> Result<LaneHandoffReceipt, GuardError> {
    if requested_action == WorkerNextAction::IdleWaitForFounder {
        return Err(GuardError::FounderEventLoopForbidden {
            worker_id: worker_id.to_string(),
            lane: lane.to_string(),
        });
    }
    let next_action = if let Some((v_lane, v_sha)) = pending_verdict {
        WorkerNextAction::HandleGreenlaneVerdict {
            lane: v_lane,
            head_sha: v_sha,
        }
    } else if let Some(ticket) = next_unblocked_ticket {
        WorkerNextAction::PullNextTicket { mission_id: ticket }
    } else {
        WorkerNextAction::IdleWaitForQueueEvent
    };

    Ok(LaneHandoffReceipt {
        worker_id: worker_id.to_string(),
        lane: lane.to_string(),
        head_sha: head_sha.to_string(),
        issue_id: issue_id.to_string(),
        next_action,
    })
}

/// Superseded-Head Watcher Verdict (Invariant 3)
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WatchVerdict {
    ContinueWatching,
    TerminalVerdict(String),
    SupersededHead {
        watched_sha: String,
        current_lane_head: String,
    },
    LaneRetired,
}

pub fn evaluate_lane_watcher(
    watched_sha: &str,
    commit_status: &str,
    greenlane_state_lane_head: Option<&str>,
) -> WatchVerdict {
    match greenlane_state_lane_head {
        None => WatchVerdict::LaneRetired,
        Some(current_head) if current_head != watched_sha => WatchVerdict::SupersededHead {
            watched_sha: watched_sha.to_string(),
            current_lane_head: current_head.to_string(),
        },
        Some(_) => match commit_status {
            "success" | "failure" | "error" => WatchVerdict::TerminalVerdict(commit_status.to_string()),
            _ => WatchVerdict::ContinueWatching,
        },
    }
}

/// Durable Consumer-Ack Founder Inbox & Passkey Sink (Invariant 4)
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EscalationChannel {
    DurableFounderInbox,
    LocalTerminalStdout,
    LocalMacPollerPid(u32),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DurablePasskeyRegistration {
    pub stable_key: String,
    pub credential_id: String,
    pub public_key_spki_b64: String,
    pub committed_sha: Option<String>,
    pub ttl_seconds: u64,
}

#[derive(Debug, Default)]
pub struct FounderInboxStore {
    registrations: BTreeMap<String, DurablePasskeyRegistration>,
}

impl FounderInboxStore {
    pub const STABLE_KEY: &'static str = "reg:founder";
    pub const MIN_DURABLE_TTL_SECS: u64 = 30 * 86_400;

    pub fn validate_escalation_channel(channel: &EscalationChannel) -> Result<(), GuardError> {
        match channel {
            EscalationChannel::DurableFounderInbox => Ok(()),
            EscalationChannel::LocalTerminalStdout => Err(
                GuardError::LocalPollerOrTerminalTrapForbidden(
                    "ESCALATE/1 terminal dumps are forbidden; route to DurableFounderInbox".into(),
                ),
            ),
            EscalationChannel::LocalMacPollerPid(pid) => Err(
                GuardError::LocalPollerOrTerminalTrapForbidden(format!(
                    "local Mac poller pid {pid} violates DARWIN_THIN_CLIENT; use cloud consumer"
                )),
            ),
        }
    }

    pub fn put_passkey_registration(
        &mut self,
        credential_id: &str,
        public_key_spki_b64: &str,
        ttl_seconds: u64,
    ) -> Result<DurablePasskeyRegistration, GuardError> {
        if credential_id.trim().is_empty() || public_key_spki_b64.trim().is_empty() {
            return Err(GuardError::InvalidImmunizationProof(
                "credential_id and public_key_spki_b64 are required".into(),
            ));
        }
        let enforced_ttl = ttl_seconds.max(Self::MIN_DURABLE_TTL_SECS);
        let rec = DurablePasskeyRegistration {
            stable_key: Self::STABLE_KEY.to_string(),
            credential_id: credential_id.to_string(),
            public_key_spki_b64: public_key_spki_b64.to_string(),
            committed_sha: None,
            ttl_seconds: enforced_ttl,
        };
        self.registrations.insert(Self::STABLE_KEY.to_string(), rec.clone());
        Ok(rec)
    }

    /// Always readable regardless of nonce rotation.
    pub fn read_by_any_nonce(&self, _nonce: &str) -> Option<&DurablePasskeyRegistration> {
        self.registrations.get(Self::STABLE_KEY)
    }

    /// Record git commit SHA receipt proving the public key landed in source control.
    pub fn ack_committed(&mut self, committed_sha: &str) -> Result<(), GuardError> {
        if committed_sha.len() != 40 || !is_valid_git_sha(committed_sha) {
            return Err(GuardError::InvalidImmunizationProof(
                "committed_sha must be a full 40-char lowercase hex commit SHA".into(),
            ));
        }
        let rec = self
            .registrations
            .get_mut(Self::STABLE_KEY)
            .ok_or_else(|| GuardError::UnconsumedFounderTap {
                key: Self::STABLE_KEY.to_string(),
            })?;
        rec.committed_sha = Some(committed_sha.to_string());
        Ok(())
    }

    /// Refuse purge/expiry if no committed_sha receipt exists.
    pub fn purge_if_consumed(&mut self) -> Result<(), GuardError> {
        match self.registrations.get(Self::STABLE_KEY) {
            Some(rec) if rec.committed_sha.is_some() => {
                self.registrations.remove(Self::STABLE_KEY);
                Ok(())
            }
            _ => Err(GuardError::UnconsumedFounderTap {
                key: Self::STABLE_KEY.to_string(),
            }),
        }
    }
}

/// Pre-Emit Workflow & Legion Admission Preflight (Invariant 5)
pub fn validate_workflow_has_runnable_jobs(workflow_name: &str, job_names: &[&str]) -> Result<(), GuardError> {
    let valid_jobs: Vec<&&str> = job_names.iter().filter(|j| !j.trim().is_empty()).collect();
    if valid_jobs.is_empty() {
        return Err(GuardError::ZeroJobWorkflow(workflow_name.to_string()));
    }
    Ok(())
}

#[derive(Debug, Clone)]
pub struct LegionAdmissionRequest {
    pub issue_id: String,
    pub requested_paths: Vec<String>,
    pub active_claims: BTreeMap<String, Vec<String>>, // agent_id -> claimed paths
    pub has_acceptance_contract: bool,
    pub required_tools_available: BTreeSet<String>,
    pub required_tools_needed: BTreeSet<String>,
    pub target_merges_cleanly_on_main: bool,
}

pub fn preflight_legion_admission(req: &LegionAdmissionRequest) -> Result<(), GuardError> {
    let mut errors = Vec::new();
    if !req.has_acceptance_contract {
        errors.push(format!("issue {} missing executable acceptance contract", req.issue_id));
    }
    if !req.target_merges_cleanly_on_main {
        errors.push(format!("issue {} base/branch does not merge cleanly onto origin/main", req.issue_id));
    }
    for tool in &req.required_tools_needed {
        if !req.required_tools_available.contains(tool) {
            errors.push(format!("missing required sandbox tool: {tool}"));
        }
    }
    for (owner, claimed) in &req.active_claims {
        for path in &req.requested_paths {
            if claimed.iter().any(|c| c == path) {
                errors.push(format!("claim conflict on {path} held by {owner}"));
            }
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(GuardError::AdmissionPreconditionFailed(errors))
    }
}

pub fn is_valid_git_sha(sha: &str) -> bool {
    (7..=40).contains(&sha.len())
        && sha
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strike_1_blocks_blind_retry_and_strike_2_quarantines_class() {
        let mut ledger = CircuitBreakerLedger::new();
        let fc = FailureClassId::new("bdd-suites", "acceptance-render", "platform/llm");

        let s1 = ledger.record_failure(&fc, "e4ce3c3");
        assert_eq!(
            s1,
            ClassStatus::ImmunizationRequired {
                first_sha: "e4ce3c3".into(),
                strike_count: 1
            }
        );
        assert!(matches!(
            ledger.allow_dispatch(&fc),
            Err(GuardError::UnimmunizedRetry { strike_count: 1, .. })
        ));

        let s2 = ledger.record_failure(&fc, "708fa0a");
        assert_eq!(
            s2,
            ClassStatus::ClassQuarantine {
                first_sha: "e4ce3c3".into(),
                repeat_sha: "708fa0a".into(),
                strike_count: 2
            }
        );
        assert!(matches!(
            ledger.allow_dispatch(&fc),
            Err(GuardError::ClassQuarantined { strike_count: 2, .. })
        ));

        let proof = ImmunizationProof {
            commit_sha: "cb274aa87aca6c2982b60c400463ff35974fc864".into(),
            wall_check_path: "bin/pre-push-wall.py".into(),
            regression_test_path: "tests/test_zero_repeat_headless_control.py".into(),
            failed_before_fix: true,
            passed_after_fix: true,
        };
        ledger.record_immunization(&fc, &proof).unwrap();
        assert!(ledger.allow_dispatch(&fc).is_ok());
    }

    #[test]
    fn bot_auto_merge_loop_stops_after_one_red_sync() {
        let mut ledger = CircuitBreakerLedger::new();
        assert_eq!(ledger.record_bot_sync("idp#8207", false, false).unwrap(), 1);
        assert!(matches!(
            ledger.record_bot_sync("idp#8207", false, false),
            Err(GuardError::BotSyncLoopQuarantined { red_sync_count: 2, .. })
        ));
    }

    #[test]
    fn headless_worker_cannot_stop_to_wait_for_founder() {
        let refused = enforce_headless_handoff(
            "glm-5.3-pennyd",
            "lane/harness-rust-ci",
            "cb47fac",
            "#8395",
            None,
            Some("#8390".into()),
            WorkerNextAction::IdleWaitForFounder,
        );
        assert!(matches!(refused, Err(GuardError::FounderEventLoopForbidden { .. })));

        let ok = enforce_headless_handoff(
            "glm-5.3-pennyd",
            "lane/harness-rust-ci",
            "cb47fac",
            "#8395",
            None,
            Some("#8390".into()),
            WorkerNextAction::IdleWaitForQueueEvent,
        )
        .unwrap();
        assert_eq!(
            ok.next_action,
            WorkerNextAction::PullNextTicket {
                mission_id: "#8390".into()
            }
        );
    }

    #[test]
    fn watcher_aborts_on_superseded_head_even_when_status_is_pending() {
        let verdict = evaluate_lane_watcher("7d8741cc1", "pending", Some("7d575dacc"));
        assert_eq!(
            verdict,
            WatchVerdict::SupersededHead {
                watched_sha: "7d8741cc1".into(),
                current_lane_head: "7d575dacc".into()
            }
        );
        assert_eq!(
            evaluate_lane_watcher("7d575dacc", "pending", None),
            WatchVerdict::LaneRetired
        );
    }

    #[test]
    fn durable_founder_passkey_survives_nonce_change_and_refuses_unconsumed_purge() {
        assert!(FounderInboxStore::validate_escalation_channel(&EscalationChannel::LocalTerminalStdout).is_err());
        assert!(FounderInboxStore::validate_escalation_channel(&EscalationChannel::LocalMacPollerPid(85399)).is_err());
        assert!(FounderInboxStore::validate_escalation_channel(&EscalationChannel::DurableFounderInbox).is_ok());

        let mut store = FounderInboxStore::new();
        let rec = store.put_passkey_registration("cred-123", "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...", 86_400).unwrap();
        assert!(rec.ttl_seconds >= FounderInboxStore::MIN_DURABLE_TTL_SECS);
        assert_eq!(store.read_by_any_nonce("different-nonce").unwrap().credential_id, "cred-123");
        assert!(matches!(store.purge_if_consumed(), Err(GuardError::UnconsumedFounderTap { .. })));

        store.ack_committed("49c76e3190000000000000000000000000000000").unwrap();
        assert!(store.purge_if_consumed().is_ok());
    }

    #[test]
    fn preflight_blocks_zero_job_workflow_and_conflicting_legion_admission() {
        assert!(matches!(
            validate_workflow_has_runnable_jobs(".github/workflows/incident-loop.yml", &[]),
            Err(GuardError::ZeroJobWorkflow(_))
        ));
        let mut active_claims = BTreeMap::new();
        active_claims.insert(
            "dsh-web-bind-20261119".to_string(),
            vec!["platform/estate/web/door.py".to_string()],
        );
        let req = LegionAdmissionRequest {
            issue_id: "#8302".into(),
            requested_paths: vec!["platform/estate/web/door.py".into()],
            active_claims,
            has_acceptance_contract: true,
            required_tools_available: BTreeSet::from(["git".into()]),
            required_tools_needed: BTreeSet::from(["git".into(), "ruff".into()]),
            target_merges_cleanly_on_main: false,
        };
        let err = preflight_legion_admission(&req).unwrap_err();
        match err {
            GuardError::AdmissionPreconditionFailed(reasons) => assert_eq!(reasons.len(), 3),
            other => panic!("unexpected error: {other:?}"),
        }
    }
}
