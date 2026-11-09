//! DX — stack-agnostic agent diagnostics (Rust-first, greenfield).
//!
//! Two commands:
//!   dx sweep --targets host:port,... --max-probes N
//!       Run the VoI controller over typed probes against live targets. Emits
//!       a machine-readable JSON report of verdicts + evidence.
//!   dx mock --port P
//!       Run a disposable mock target for the sweep to prove against.

mod controller;
mod mock;
mod probe;
mod probe_http;

use controller::{BeliefState, VoIController};
use probe::Probe;
use probe_http::{HttpProbe, HTTP_CLASSES};

fn sweep(targets: &[String], max_probes: usize) -> serde_json::Value {
    let mut results: Vec<serde_json::Value> = Vec::new();
    let controller = VoIController;

    for target in targets {
        let mut belief = BeliefState::new(HTTP_CLASSES);
        let probe = HttpProbe;
        let mut probes_run = 0usize;
        let mut verdict: Option<String> = None;
        let mut evidence_log: Vec<serde_json::Value> = Vec::new();

        while probes_run < max_probes && belief.terminated().is_none() {
            let probe_sigs: Vec<(&str, Vec<String>)> = vec![(
                probe.id(),
                probe.discriminates(),
            )];
            let _next = controller.next_probe(&belief, &probe_sigs);

            match probe.run(target) {
                Ok(ev) => {
                    // Deterministic likelihood mapping: the class matching
                    // the observed mode is far more likely than any other.
                    let mode = match &ev.observation {
                        probe::Observation::Http { mode, .. } => mode.clone(),
                        _ => "unreachable".to_string(),
                    };
                    let mut likelihoods: Vec<(String, f64)> = Vec::new();
                    for c in HTTP_CLASSES {
                        let l = if c == &mode {
                            0.90
                        } else if mode == "ok" && *c == "healthy" {
                            0.90
                        } else if mode == "unreachable" && *c == "healthy" {
                            0.02
                        } else {
                            0.03
                        };
                        likelihoods.push((c.to_string(), l));
                    }
                    belief.update(&probe.discriminates(), &likelihoods);
                    evidence_log.push(serde_json::to_value(&ev).unwrap());
                }
                Err(e) => {
                    let mut likelihoods: Vec<(String, f64)> = Vec::new();
                    for c in HTTP_CLASSES {
                        likelihoods.push((
                            c.to_string(),
                            if *c == "healthy" { 0.02 } else { 0.30 },
                        ));
                    }
                    belief.update(&probe.discriminates(), &likelihoods);
                    evidence_log.push(serde_json::json!({
                        "id": probe.id(),
                        "target": target,
                        "error": e,
                    }));
                }
            }
            probes_run += 1;
        }

        if let Some(name) = belief.terminated() {
            verdict = Some(name.to_string());
        } else {
            verdict = Some("unresolved".to_string());
        }

        results.push(serde_json::json!({
            "target": target,
            "verdict": verdict,
            "probes_run": probes_run,
            "posteriors": belief.hypotheses.iter().map(|h| {
                serde_json::json!({ "class": h.name, "posterior": h.posterior })
            }).collect::<Vec<_>>(),
            "evidence": evidence_log,
        }));
    }

    serde_json::json!({
        "dx_version": env!("CARGO_PKG_VERSION"),
        "controller": "voi",
        "termination": "posterior>=0.95 AND evidence-backed AND healthy->faults<EPS(0.002)",
        "results": results,
    })
}

fn parse_ports(s: &str) -> Vec<String> {
    s.split(',')
        .map(|t| t.trim().to_string())
        .filter(|t| !t.is_empty())
        .collect()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0usize;
    let mut cmd: Option<String> = None;
    let mut targets: Vec<String> = Vec::new();
    let mut max_probes = 40usize;
    let mut port: u16 = 0;

    while i < args.len() {
        match args[i].as_str() {
            "sweep" => cmd = Some("sweep".to_string()),
            "mock" => cmd = Some("mock".to_string()),
            "--targets" => {
                i += 1;
                targets = parse_ports(&args[i]);
            }
            "--max-probes" => {
                i += 1;
                max_probes = args[i].parse().unwrap_or(40);
            }
            "--port" => {
                i += 1;
                port = args[i].parse().unwrap_or(0);
            }
            other => {
                eprintln!("dx: unknown argument {other:?}");
                std::process::exit(2);
            }
        }
        i += 1;
    }

    match cmd.as_deref() {
        Some("sweep") => {
            if targets.is_empty() {
                eprintln!("dx sweep: --targets host:port,... is required");
                std::process::exit(2);
            }
            let report = sweep(&targets, max_probes);
            println!("{}", serde_json::to_string_pretty(&report).unwrap());
        }
        Some("mock") => {
            if port == 0 {
                eprintln!("dx mock: --port P is required");
                std::process::exit(2);
            }
            eprintln!("dx mock serving 127.0.0.1:{port} (Ctrl-C to stop)");
            if let Err(e) = mock::serve(port) {
                eprintln!("dx mock: {e}");
                std::process::exit(1);
            }
        }
        _ => {
            eprintln!("usage: dx sweep --targets h:p,... [--max-probes N]");
            eprintln!("       dx mock --port P");
            std::process::exit(2);
        }
    }
}
