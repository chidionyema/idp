//! Engines 1 & 2: Google-Grade Greenlane Presubmit, 3/3 Blackbox Canary & Auto-Recovery.
//!
//! Eliminates the 0% settlement rate by:
//!   1. Failing closed BEFORE MERGE on proxy URLs (`github.com`, `api.github.com`, `raw.githubusercontent.com`),
//!      zero-delta contracts (`baseline == target`), `Optimus=UNKNOWN`, and broken `bin/*` permissions.
//!   2. Requiring 3/3 independent blackbox probes confirming HTTP 200, Zone B header, exact `COMMIT_SHA`,
//!      and Golden Signal p99 latency SLO before declaring `OPERATIONAL`.
//!   3. Closing the `recovery_required` dead-end: Tier-0 failures automatically trip `dof-gate` freeze,
//!      bump `revocation_epoch` / `fencing_token`, and issue one bounded recovery lease.

use meridian_ledger::BudgetLedger;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ShipContract {
    pub accept_url: String,
    pub optimus_metric: String,
    pub baseline: String,
    pub target: String,
    pub failure_classes: Vec<String>,
    pub debug_pack: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "code", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PresubmitError {
    ProxyGreenSubstitution { url: String },
    ZeroDeltaContract { metric: String, value: String },
    InvalidShipContract { reason: String },
    OptimusMeasureUnknown { metric: String, raw: String },
    OptimusTargetNotMet { metric: String, observed: i64, target: i64 },
    NonExecutableBinScript { path: String, mode: u32 },
}

pub fn is_proxy_green_url(url: &str) -> bool {
    let low = url.trim().to_ascii_lowercase();
    let Some(rest) = low.strip_prefix("https://") else {
        return true;
    };
    let authority = rest.split(['/', '?', '#']).next().unwrap_or("");
    // The real host is after the last '@': `https://good.example@api.github.com/` talks to github.
    let hostport = authority.rsplit('@').next().unwrap_or("");
    let host = match hostport.strip_prefix('[') {
        Some(v6) => v6.split(']').next().unwrap_or(""),
        None => hostport.split(':').next().unwrap_or(""),
    };
    let host = host.trim_end_matches('.');
    if host.is_empty() || host == "localhost" || host.ends_with(".localhost") {
        return true;
    }
    if let Ok(ip) = host.parse::<std::net::IpAddr>() {
        let mapped_loopback = match ip {
            std::net::IpAddr::V6(v6) => v6.to_ipv4_mapped().is_some_and(|v4| v4.is_loopback()),
            std::net::IpAddr::V4(_) => false,
        };
        return ip.is_loopback() || ip.is_unspecified() || mapped_loopback;
    }
    [("github.com"), ("githubusercontent.com")]
        .iter()
        .any(|d| host == *d || host.ends_with(&format!(".{d}")))
}

pub fn parse_and_validate_contract_presubmit(raw: &str) -> Result<ShipContract, PresubmitError> {
    let mut has_header = false;
    let mut accept_url: Option<String> = None;
    let mut metric: Option<String> = None;
    let mut baseline: Option<String> = None;
    let mut target: Option<String> = None;
    let mut failure_classes: Vec<String> = Vec::new();
    let mut debug_pack: Option<String> = None;

    for line in raw.lines() {
        let t = line.trim();
        if t == "SHIP-CONTRACT" {
            has_header = true;
        } else if let Some(rest) = t.strip_prefix("accept:") {
            let parts: Vec<&str> = rest.split_whitespace().collect();
            if parts.len() == 6
                && parts[0] == "GET"
                && parts[2] == "expect"
                && parts[3] == "200"
                && parts[4] == "within"
                && parts[5].ends_with('m')
            {
                let u = parts[1].to_string();
                if is_proxy_green_url(&u) {
                    return Err(PresubmitError::ProxyGreenSubstitution { url: u });
                }
                accept_url = Some(u);
            } else {
                return Err(PresubmitError::InvalidShipContract {
                    reason: "malformed accept: line".to_string(),
                });
            }
        } else if let Some(rest) = t.strip_prefix("optimus:") {
            let parts: Vec<&str> = rest.split_whitespace().collect();
            if parts.len() == 3 {
                if let (Some(b), Some(tg)) = (
                    parts[1].strip_prefix("baseline="),
                    parts[2].strip_prefix("target="),
                ) {
                    if b == tg {
                        return Err(PresubmitError::ZeroDeltaContract {
                            metric: parts[0].to_string(),
                            value: b.to_string(),
                        });
                    }
                    metric = Some(parts[0].to_string());
                    baseline = Some(b.to_string());
                    target = Some(tg.to_string());
                } else {
                    return Err(PresubmitError::InvalidShipContract {
                        reason: "optimus missing baseline=/target=".to_string(),
                    });
                }
            } else {
                return Err(PresubmitError::InvalidShipContract {
                    reason: "malformed optimus: line".to_string(),
                });
            }
        } else if let Some(rest) = t.strip_prefix("failure-classes:") {
            failure_classes = rest
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();
        } else if let Some(rest) = t.strip_prefix("debug-pack:") {
            let dp = rest.trim();
            if dp.starts_with("DBG-") && dp.len() >= 5 {
                debug_pack = Some(dp.to_string());
            }
        }
    }

    if !has_header {
        return Err(PresubmitError::InvalidShipContract {
            reason: "missing SHIP-CONTRACT".to_string(),
        });
    }
    let accept_url = accept_url.ok_or_else(|| PresubmitError::InvalidShipContract {
        reason: "missing accept:".to_string(),
    })?;
    let optimus_metric = metric.ok_or_else(|| PresubmitError::InvalidShipContract {
        reason: "missing optimus:".to_string(),
    })?;
    let baseline = baseline.ok_or_else(|| PresubmitError::InvalidShipContract {
        reason: "missing baseline".to_string(),
    })?;
    let target = target.ok_or_else(|| PresubmitError::InvalidShipContract {
        reason: "missing target".to_string(),
    })?;
    if failure_classes.is_empty() {
        return Err(PresubmitError::InvalidShipContract {
            reason: "missing failure-classes:".to_string(),
        });
    }
    let debug_pack = debug_pack.ok_or_else(|| PresubmitError::InvalidShipContract {
        reason: "missing debug-pack:".to_string(),
    })?;

    Ok(ShipContract {
        accept_url,
        optimus_metric,
        baseline,
        target,
        failure_classes,
        debug_pack,
    })
}

/// Presubmit verification of candidate Optimus output + `bin/*` executable modes (Zero Broken Windows).
pub fn verify_presubmit_parity(
    contract: &ShipContract,
    optimus_stdout: &str,
    higher_is_better: bool,
    bin_modes: &[(&str, u32)],
) -> Result<i64, PresubmitError> {
    for (path, mode) in bin_modes {
        if *mode & 0o111 == 0 {
            return Err(PresubmitError::NonExecutableBinScript {
                path: (*path).to_string(),
                mode: *mode,
            });
        }
    }

    let prefix = format!("optimus.{}=", contract.optimus_metric);
    let raw_val = optimus_stdout
        .lines()
        .find_map(|l| l.trim().strip_prefix(&prefix))
        .ok_or_else(|| PresubmitError::OptimusMeasureUnknown {
            metric: contract.optimus_metric.clone(),
            raw: optimus_stdout.trim().to_string(),
        })?;

    if raw_val.eq_ignore_ascii_case("UNKNOWN") {
        return Err(PresubmitError::OptimusMeasureUnknown {
            metric: contract.optimus_metric.clone(),
            raw: raw_val.to_string(),
        });
    }
    let observed = raw_val
        .parse::<i64>()
        .map_err(|_| PresubmitError::OptimusMeasureUnknown {
            metric: contract.optimus_metric.clone(),
            raw: raw_val.to_string(),
        })?;
    let target = contract
        .target
        .parse::<i64>()
        .map_err(|_| PresubmitError::InvalidShipContract {
            reason: "non-integer target".to_string(),
        })?;

    let ok = if higher_is_better {
        observed >= target
    } else {
        observed <= target
    };
    if !ok {
        return Err(PresubmitError::OptimusTargetNotMet {
            metric: contract.optimus_metric.clone(),
            observed,
            target,
        });
    }
    Ok(observed)
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BlackboxProbeRound {
    pub http_status: u16,
    pub zone_header: String,
    pub deployed_sha: String,
    pub latency_ms: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryLease {
    pub issue: String,
    pub reason: String,
    pub dof_freeze_active: bool,
    pub new_revocation_epoch: u64,
    pub rollback_sha: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReleaseVerdict {
    Operational {
        commit_sha: String,
        rounds_passed: usize,
        p99_ms: u32,
    },
    AutoRecoveryTriggered(RecoveryLease),
}

/// Evaluates 3/3 blackbox probes against exact `expected_sha` and Golden Signal latency SLO.
/// On any failure, automatically trips `dof-gate` freeze, fences stale epochs, and emits a RecoveryLease.
pub fn settle_or_auto_recover(
    issue: &str,
    expected_sha: &str,
    last_known_good_sha: &str,
    max_latency_ms: u32,
    rounds: &[BlackboxProbeRound],
    ledger: &mut BudgetLedger,
) -> ReleaseVerdict {
    let mut fail_reason: Option<String> = None;

    if rounds.len() < 3 {
        fail_reason = Some(format!("INSUFFICIENT_BLACKBOX_ROUNDS:{}", rounds.len()));
    } else {
        for (i, r) in rounds.iter().enumerate() {
            if r.http_status != 200 {
                fail_reason = Some(format!("ROUND_{}_HTTP_{}", i + 1, r.http_status));
                break;
            }
            if r.zone_header != "zone-b-cloudflare-edge" {
                fail_reason = Some(format!("ROUND_{}_WRONG_ZONE:{}", i + 1, r.zone_header));
                break;
            }
            if r.deployed_sha != expected_sha {
                fail_reason = Some(format!("ROUND_{}_SHA_MISMATCH:{}", i + 1, r.deployed_sha));
                break;
            }
            if r.latency_ms > max_latency_ms {
                fail_reason = Some(format!("ROUND_{}_SLO_BREACH:{}ms", i + 1, r.latency_ms));
                break;
            }
        }
    }

    match fail_reason {
        None => {
            let max_lat = rounds.iter().map(|r| r.latency_ms).max().unwrap_or(0);
            ReleaseVerdict::Operational {
                commit_sha: expected_sha.to_string(),
                rounds_passed: rounds.len(),
                p99_ms: max_lat,
            }
        }
        Some(reason) => {
            let new_epoch = ledger.bump_revocation_epoch();
            ReleaseVerdict::AutoRecoveryTriggered(RecoveryLease {
                issue: issue.to_string(),
                reason,
                dof_freeze_active: true,
                new_revocation_epoch: new_epoch,
                rollback_sha: last_known_good_sha.to_string(),
            })
        }
    }
}
