use mitp_thinking_packs::bayes::{CandidateProbe, HypothesisSpace, select_best_probe};
use mitp_thinking_packs::belief::AtmsBeliefBase;
use mitp_thinking_packs::bounds::ExecutionConsumption;
use mitp_thinking_packs::control::{CbfConfig, HostBarrierState, evaluate_cbf};
use mitp_thinking_packs::decision::find_dependency_cycles;
use mitp_thinking_packs::gateway::{PreToolUseGateway, StepAction, ToolStepProposal};
use mitp_thinking_packs::rca::minimal_hitting_sets;
use mitp_thinking_packs::scenario::{ReasoningContract, ScenarioInput};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::process::ExitCode;

#[derive(Deserialize)]
struct AdmitStepInput {
    contract: ReasoningContract,
    consumption: ExecutionConsumption,
    host: HostBarrierState,
    #[serde(default)]
    cbf_cfg: CbfConfig,
    #[serde(default)]
    atms: AtmsBeliefBase,
    #[serde(default)]
    seen_probe_keys: BTreeSet<String>,
    proposal: ToolStepProposal,
}

#[derive(Deserialize)]
struct BayesInput {
    priors: BTreeMap<String, f64>,
    unknown_floor: f64,
    probes: Vec<CandidateProbe>,
    utilities: BTreeMap<String, BTreeMap<String, f64>>,
    cost_weight_lambda: f64,
    min_net_voi: f64,
}

fn read_json_arg<T: for<'de> Deserialize<'de>>(path: &str) -> Result<T, String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("Failed reading '{path}': {e}"))?;
    serde_json::from_str(&raw).map_err(|e| format!("Invalid JSON in '{path}': {e}"))
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!(
            "Usage:\n  \
             mitp-thinking-packs classify <scenario_input.json>\n  \
             mitp-thinking-packs admit-step <admit_step_input.json>\n  \
             mitp-thinking-packs diagnose-hs <conflict_sets.json>\n  \
             mitp-thinking-packs bayes-next <bayes_input.json>\n  \
             mitp-thinking-packs cbf-check <host_barrier_state.json>\n  \
             mitp-thinking-packs tarjan-scc <dependency_graph.json>"
        );
        return ExitCode::from(1);
    }

    let cmd = args[1].as_str();
    let path = args[2].as_str();

    let result: Result<ExitCode, String> = match cmd {
        "classify" => (|| {
            let input: ScenarioInput = read_json_arg(path)?;
            let contract = PreToolUseGateway::classify(&input);
            println!("{}", serde_json::to_string_pretty(&contract).map_err(|e| e.to_string())?);
            Ok(ExitCode::SUCCESS)
        })(),
        "admit-step" => (|| {
            let inp: AdmitStepInput = read_json_arg(path)?;
            let decision = PreToolUseGateway::evaluate_step(
                &inp.contract,
                &inp.consumption,
                &inp.host,
                &inp.cbf_cfg,
                &inp.atms,
                &inp.seen_probe_keys,
                &inp.proposal,
            );
            println!("{}", serde_json::to_string_pretty(&decision).map_err(|e| e.to_string())?);
            match decision.action {
                StepAction::AllowExecute | StepAction::AllowZeroDiskReflex => Ok(ExitCode::SUCCESS),
                StepAction::OffloadToCloudCi => Ok(ExitCode::from(4)),
                StepAction::TransitionToActionStopProbing => Ok(ExitCode::from(3)),
                StepAction::RefuseRetryOrReroute => Ok(ExitCode::from(2)),
            }
        })(),
        "diagnose-hs" => (|| {
            let conflicts: Vec<BTreeSet<String>> = read_json_arg(path)?;
            let hs = minimal_hitting_sets(&conflicts, 4);
            println!("{}", serde_json::to_string_pretty(&hs).map_err(|e| e.to_string())?);
            Ok(ExitCode::SUCCESS)
        })(),
        "bayes-next" => (|| {
            let inp: BayesInput = read_json_arg(path)?;
            let space = HypothesisSpace::new(inp.priors, inp.unknown_floor)?;
            let best = select_best_probe(
                &space,
                &inp.probes,
                &inp.utilities,
                inp.cost_weight_lambda,
                inp.min_net_voi,
            );
            println!("{}", serde_json::to_string_pretty(&best).map_err(|e| e.to_string())?);
            Ok(ExitCode::SUCCESS)
        })(),
        "cbf-check" => (|| {
            let state: HostBarrierState = read_json_arg(path)?;
            let verdict = evaluate_cbf(&state, &CbfConfig::default());
            println!("{}", serde_json::to_string_pretty(&verdict).map_err(|e| e.to_string())?);
            Ok(if verdict.safe_for_local_heavy_work {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(2)
            })
        })(),
        "tarjan-scc" => (|| {
            let graph: BTreeMap<String, Vec<String>> = read_json_arg(path)?;
            let cycles = find_dependency_cycles(&graph);
            println!("{}", serde_json::to_string_pretty(&cycles).map_err(|e| e.to_string())?);
            Ok(if cycles.is_empty() {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(2)
            })
        })(),
        other => Err(format!("Unknown subcommand '{other}'")),
    };

    match result {
        Ok(code) => code,
        Err(err) => {
            eprintln!("{}", serde_json::json!({"status": "ERROR", "detail": err}));
            ExitCode::from(1)
        }
    }
}
