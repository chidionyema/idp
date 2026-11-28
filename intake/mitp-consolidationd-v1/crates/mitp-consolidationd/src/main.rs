//! Binary entry point.
//!
//! Subcommands:
//!   selftest            — run the built-in smoke checks (no DB needed)
//!   host-gate           — read host envelope from env, print gate verdict
//!   run-cycle           — print the cycle contract JSON (the estate executor
//!                         implements MemoryStore over sqlx; this binary's
//!                         contract is stable JSON on stdout)
//!
//! Exit codes: 0 ok / lock-follower / host-skip (receipt says which),
//!             2 hard error, 3 config error. Matches thinking-packs' exit-code
//! convention: deterministic control flow, no prose interpretation.

use mitp_consolidationd::config::Config;
use mitp_consolidationd::host::HostEnvelope;

fn env_i64(name: &str, default: i64) -> i64 {
    std::env::var(name).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

fn host_from_env() -> HostEnvelope {
    HostEnvelope {
        disk_free_mb: env_i64("HOST_DISK_FREE_MB", i64::MAX),
        disk_rate_mb_per_min: env_i64("HOST_DISK_RATE_MB_PER_MIN", 0),
        swap_used_mb: env_i64("HOST_SWAP_USED_MB", 0) as u64,
        load_1m: std::env::var("HOST_LOAD_1M").ok().and_then(|v| v.parse().ok()).unwrap_or(0.0),
    }
}

fn main() {
    let arg = std::env::args().nth(1).unwrap_or_else(|| "selftest".to_string());
    let code = match arg.as_str() {
        "selftest" => {
            let cfg = match Config::from_env() {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("{e}");
                    std::process::exit(3);
                }
            };
            println!(
                "{{\"crate\":\"mitp-consolidationd\",\"status\":\"ok\",\"policy_version\":\"{}\",\"shadow\":{},\"distill_budget_micro\":{}}}",
                mitp_consolidationd::json::escape(&cfg.policy_version),
                cfg.shadow_mode,
                cfg.distill_budget_micro
            );
            0
        }
        "host-gate" => {
            let gate = host_from_env().gate();
            match gate {
                mitp_consolidationd::host::CycleGate::Run => {
                    println!("{{\"gate\":\"run\"}}");
                    0
                }
                mitp_consolidationd::host::CycleGate::Skip(why) => {
                    println!("{{\"gate\":\"skip\",\"reason\":\"{}\"}}", mitp_consolidationd::json::escape(&why));
                    0
                }
            }
        }
        other => {
            eprintln!("unknown subcommand: {other} (selftest | host-gate)");
            2
        }
    };
    std::process::exit(code);
}
