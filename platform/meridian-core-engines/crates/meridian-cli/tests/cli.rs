use std::io::Write;
use std::process::{Command, Stdio};

fn meridian() -> Command {
    Command::new(env!("CARGO_BIN_EXE_meridian"))
}

fn run_with_stdin(args: &[&str], stdin: &str) -> (i32, String, String) {
    let mut child = meridian()
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn meridian");
    child
        .stdin
        .take()
        .expect("stdin")
        .write_all(stdin.as_bytes())
        .expect("write stdin");
    let out = child.wait_with_output().expect("wait");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).to_string(),
        String::from_utf8_lossy(&out.stderr).to_string(),
    )
}

#[test]
fn optimus_canary_runs_all_four_engines_and_prints_one() {
    let out = meridian().arg("--optimus").output().expect("run");
    assert_eq!(out.status.code(), Some(0));
    assert_eq!(
        String::from_utf8_lossy(&out.stdout).trim(),
        "optimus.estate.four_engines_interconnected=1"
    );
}

#[test]
fn presubmit_accepts_a_real_contract_and_echoes_it_as_json() {
    let good = "SHIP-CONTRACT\naccept: GET https://llm.meridianlabs.cloud/health expect 200 within 30m\noptimus: m baseline=0 target=1\nfailure-classes: a,b\ndebug-pack: DBG-001\n";
    let (code, stdout, _) = run_with_stdin(&["presubmit"], good);
    assert_eq!(code, 0);
    assert!(stdout.contains("\"accept_url\":\"https://llm.meridianlabs.cloud/health\""), "{stdout}");
}

#[test]
fn presubmit_exits_two_on_proxy_zero_delta_and_garbage() {
    let proxy = "SHIP-CONTRACT\naccept: GET https://api.github.com/repos/chidionyema/idp/commits/main expect 200 within 30m\noptimus: m baseline=0 target=1\nfailure-classes: a\ndebug-pack: DBG-001\n";
    let (code, _, stderr) = run_with_stdin(&["presubmit"], proxy);
    assert_eq!(code, 2);
    assert!(stderr.contains("PROXY_GREEN_SUBSTITUTION"), "{stderr}");

    let zero = "SHIP-CONTRACT\naccept: GET https://llm.meridianlabs.cloud/health expect 200 within 30m\noptimus: m baseline=1 target=1\nfailure-classes: a\ndebug-pack: DBG-001\n";
    let (code, _, stderr) = run_with_stdin(&["presubmit"], zero);
    assert_eq!(code, 2);
    assert!(stderr.contains("ZERO_DELTA_CONTRACT"), "{stderr}");

    let (code, _, _) = run_with_stdin(&["presubmit"], "garbage");
    assert_eq!(code, 2);
}

#[test]
fn unknown_subcommand_is_a_usage_error() {
    let out = meridian().arg("bogus").output().expect("run");
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("usage:"));
}
