use crate::types::CounterexampleUpsertRequest;
use std::path::Path;

/// Deterministically classifies a failing CI workflow/step into the 6 canonical failure classes.
pub fn classify_ci_failure(
    workflow_name: &str,
    failing_step: &str,
    conclusion: &str,
) -> &'static str {
    if conclusion == "success" || conclusion == "skipped" || conclusion == "neutral" {
        return "NONE";
    }
    let wf = workflow_name.to_ascii_lowercase();
    let step = failing_step.to_ascii_lowercase();

    if wf.contains("recover ai studio")
        || wf.contains("recover canonical io")
        || step.contains("producer git custody")
    {
        return "NO-PRODUCER-CUSTODY";
    }
    if wf.contains("drive bridge")
        || wf.contains("outbox delivery")
        || wf.contains("model lane")
        || wf.contains("inbound bridge")
        || step.contains("credential")
        || step.contains("token")
    {
        return "MISSING-CREDENTIAL";
    }
    if wf.contains("dof gate") || step.contains("degree of freedom") || step.contains("probe critical") {
        return "CRITICAL-DEP-DOWN";
    }
    if wf.contains("provenance guardian") || wf.contains("main-guardian") || step.contains("history rewrite") {
        return "MAIN-INTEGRITY";
    }
    if wf.contains("production acceptance")
        || wf.contains("merian-lab-verified")
        || wf.contains("helm-founder-evidence-ui")
        || step.contains("viewport")
        || step.contains("playwright")
        || step.contains("chromium")
    {
        return "RUNNER-ENV";
    }
    if wf.contains("provenance gate")
        || wf == "ci"
        || wf.contains("portal-app")
        || wf.contains("turn-gate")
        || step.contains("fast gate")
        || step.contains("fast-gate")
        || step.contains("offline-gate")
    {
        return "GATE-ALWAYS-RED";
    }
    "UNCLASSIFIED-FAILURE"
}

/// Deterministic AST/config counterexample assertions executed directly against a local repo checkout.
/// Zero LLM involvement; produces exact file/line evidence for Block 6 of the live projection.
pub fn scan_idp_counterexamples(
    repo_root: &Path,
    head_sha: &str,
) -> Vec<CounterexampleUpsertRequest> {
    let mut results = Vec::new();
    let repo = "chidionyema/idp".to_string();

    // CE-01: Forgeable --founder-seal boolean in bin/verify_three_proofs.py
    let v3p_path = repo_root.join("bin/verify_three_proofs.py");
    if let Ok(content) = std::fs::read_to_string(&v3p_path) {
        let has_flag = content.contains("\"--founder-seal\"") || content.contains("'--founder-seal'");
        let has_bool_bypass = content.contains("has_founder_seal: bool");
        let (verdict, evidence) = if has_flag || has_bool_bypass {
            (
                "CONFIRMED_DEFECT",
                "bin/verify_three_proofs.py still exposes forgeable --founder-seal / has_founder_seal: bool bypass".to_string(),
            )
        } else {
            (
                "CLEARED",
                "No bare --founder-seal boolean bypass detected in bin/verify_three_proofs.py".to_string(),
            )
        };
        results.push(CounterexampleUpsertRequest {
            check_id: "CE-01-FOUNDER-SEAL-BOOLEAN".into(),
            claim: "bin/verify_three_proofs.py must not accept a bare --founder-seal boolean".into(),
            verdict: verdict.into(),
            repo_full_name: repo.clone(),
            head_sha: head_sha.into(),
            evidence,
        });
    }

    // CE-02: Unwired stand_in_database() dead code in bin/idp-shadow
    let shadow_path = repo_root.join("bin/idp-shadow");
    if let Ok(content) = std::fs::read_to_string(&shadow_path) {
        let occurrences = content.matches("stand_in_database").count();
        let (verdict, evidence) = if occurrences == 1 {
            (
                "CONFIRMED_DEFECT",
                "bin/idp-shadow defines stand_in_database once (count=1) with zero live call-site".to_string(),
            )
        } else if occurrences >= 2 {
            (
                "CLEARED",
                format!("bin/idp-shadow references stand_in_database {} times (defined + invoked)", occurrences),
            )
        } else {
            (
                "UNKNOWN",
                "stand_in_database symbol absent from bin/idp-shadow".to_string(),
            )
        };
        results.push(CounterexampleUpsertRequest {
            check_id: "CE-02-SHADOW-STANDIN-WIRED".into(),
            claim: "bin/idp-shadow stand_in_database() must have at least one live call-site".into(),
            verdict: verdict.into(),
            repo_full_name: repo.clone(),
            head_sha: head_sha.into(),
            evidence,
        });
    }

    // CE-03 & CE-05: agent-sandbox.yml scope binding + direct OAuth bypass check
    let sandbox_path = repo_root.join(".github/workflows/agent-sandbox.yml");
    if let Ok(content) = std::fs::read_to_string(&sandbox_path) {
        let invokes_apply = content.contains("idp-agent-base-apply.py");
        let passes_scope = content.contains("--scope-sha256")
            && (content.contains("--scope-file") || content.contains("--admit-paths-json"));
        let (verdict_scope, ev_scope) = if invokes_apply && !passes_scope {
            (
                "CONFIRMED_DEFECT",
                ".github/workflows/agent-sandbox.yml invokes idp-agent-base-apply.py without --scope-sha256 and --scope-file/--admit-paths-json".to_string(),
            )
        } else if invokes_apply && passes_scope {
            (
                "CLEARED",
                ".github/workflows/agent-sandbox.yml binds scope digest before applying candidate patch".to_string(),
            )
        } else {
            ("UNKNOWN", "idp-agent-base-apply.py not referenced in agent-sandbox.yml".to_string())
        };
        results.push(CounterexampleUpsertRequest {
            check_id: "CE-03-SANDBOX-SCOPE-BINDING".into(),
            claim: "agent-sandbox.yml must pass --scope-sha256 and admitted paths to idp-agent-base-apply.py".into(),
            verdict: verdict_scope.into(),
            repo_full_name: repo.clone(),
            head_sha: head_sha.into(),
            evidence: ev_scope,
        });

        let has_direct_oauth = content.contains("CLAUDE_CODE_OAUTH_TOKEN");
        let (verdict_oauth, ev_oauth) = if has_direct_oauth {
            (
                "CONFIRMED_DEFECT",
                ".github/workflows/agent-sandbox.yml directly references CLAUDE_CODE_OAUTH_TOKEN outside PennyD accounting".to_string(),
            )
        } else {
            (
                "CLEARED",
                "Zero direct CLAUDE_CODE_OAUTH_TOKEN bypasses in .github/workflows/agent-sandbox.yml".to_string(),
            )
        };
        results.push(CounterexampleUpsertRequest {
            check_id: "CE-05-NO-DIRECT-OAUTH-BYPASS".into(),
            claim: "agent-sandbox.yml must not bypass PennyD with direct CLAUDE_CODE_OAUTH_TOKEN".into(),
            verdict: verdict_oauth.into(),
            repo_full_name: repo.clone(),
            head_sha: head_sha.into(),
            evidence: ev_oauth,
        });
    }

    // CE-04: estate-state.yml periodic producer disabled
    let estate_state_path = repo_root.join(".github/workflows/estate-state.yml");
    if let Ok(content) = std::fs::read_to_string(&estate_state_path) {
        let commented_cron = content.lines().any(|l| {
            let t = l.trim();
            t.starts_with('#') && t.contains("cron:")
        });
        let (verdict, evidence) = if commented_cron {
            (
                "CONFIRMED_DEFECT",
                ".github/workflows/estate-state.yml has commented-out schedule cron".to_string(),
            )
        } else {
            (
                "CLEARED",
                ".github/workflows/estate-state.yml schedule is active or event-driven".to_string(),
            )
        };
        results.push(CounterexampleUpsertRequest {
            check_id: "CE-04-ESTATE-STATE-ACTIVE".into(),
            claim: "estate-state.yml producer must not be left disabled via commented cron".into(),
            verdict: verdict.into(),
            repo_full_name: repo,
            head_sha: head_sha.into(),
            evidence,
        });
    }

    results
}

/// Checks if a path is protected under guarded control-plane paths.
pub fn is_guarded_path(path: &str) -> bool {
    path.starts_with(".github/workflows/")
        || path == "bin/verify_three_proofs.py"
        || path == "bin/pre-push-wall.py"
        || path == "bin/idp-ci"
        || path.starts_with(".githooks/")
        || path == "catalog/genesis-protocols.json"
}

/// Checks if a planned path set violates DARWIN_THIN_CLIENT / Zone A quarantine.
pub fn is_zone_a_forbidden_path(path: &str) -> bool {
    let lower = path.to_ascii_lowercase();
    lower.contains(".estate/")
        || lower.ends_with("estate.db")
        || lower.contains("launchagents")
        || lower.contains("launchdaemons")
}
