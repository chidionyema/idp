//! Harper grammar wrapper (HANDOFF item 5b / copy_lint.check_grammar parity).
//!
//! Mirrors `prospector/copy_lint.py` faithfully: same binary resolution (PATH, then the two
//! Homebrew absolute fallbacks), same fail-open contract (missing binary, a child that will
//! not spawn, or an unreadable profile returns `None` == "grammar unavailable" — never a
//! false clean and never a false defect), same pre-flight `_strip_code` (fences / inline
//! code / URLs blanked so a build spec is not graded as writing), same invocation
//! (`empty...lint --no-color <files...>`, per-file budget scaled to a 600 s hard ceiling),
//! and the same aggregation: only `<Rule: count>` tuples whose rule is on
//! `HARPER_GRAMMAR_RULES` are summed. Grammar is advisory today (no lane grades its output);
//! this module exists so the diff can close the day a grammar lane is wired, and its equality
//! to the Python `grammar_findings` oracle is what the item-5b spec locks, never asserted.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::Command;

/// HARPER_GRAMMAR_RULES from copy_lint.py:339, verbatim — the only rules counted. 14.
const HARPER_GRAMMAR_RULES: [&str; 14] = [
    "Agreement",
    "MissingTo",
    "AnA",
    "MissingPreposition",
    "InflectedVerbAfterTo",
    "CommaFixes",
    "UnclosedQuotes",
    "Repetition",
    "NounVerbConfusion",
    "MassNouns",
    "SplitWords",
    "PhrasalVerbAsCompoundNoun",
    "CompoundNouns",
    "OrthographicConsistency",
];

/// Absolute fallbacks searched only when PATH lookup fails (launchd keeps a minimal PATH).
const HARPER_FALLBACK_PATHS: [&str; 2] =
    ["/usr/local/bin/harper-cli", "/opt/homebrew/bin/harper-cli"];

/// Hard ceiling on one harper invocation (copy_lint._HARPER_TIMEOUT_CEILING_S).
const HARPER_TIMEOUT_CEILING_S: u64 = 600;

fn is_executable(path: &Path) -> bool {
    std::fs::metadata(path)
        .map(|md| {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                md.permissions().mode() & 0o111 != 0
            }
            #[cfg(not(unix))]
            {
                let _ = md;
                true
            }
        })
        .unwrap_or(false)
}

fn path_lookup(exe: &str) -> Option<PathBuf> {
    let path = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path) {
        let cand = dir.join(exe);
        if cand.is_file() && is_executable(&cand) {
            return Some(cand);
        }
    }
    None
}

/// Resolve `harper-cli` exactly as copy_lint.harper_path: PATH first, then the fallbacks.
/// The only two ways a harper run is ever characterised as something other than a reading.
#[derive(Debug)]
pub enum HarperError {
    /// Binary absent from PATH and both Homebrew fallbacks.
    Missing,
    /// Child could not spawn, was killed on budget, or produced no readable stream.
    Exec(String),
}

pub fn harper_path() -> Option<PathBuf> {
    if let Some(p) = path_lookup("harper-cli") {
        return Some(p);
    }
    HARPER_FALLBACK_PATHS
        .iter()
        .map(PathBuf::from)
        .find(|p| p.is_file() && is_executable(p))
}

/// Sanitize a text name into a filesystem-safe stem (copy_lint strips to `[A-Za-z0-9_.-]`).
fn sanitize_name(name: &str) -> String {
    name.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-') {
                c
            } else {
                '_'
            }
        })
        .collect()
}

/// Blank fenced blocks, inline code and URLs within `text` (copy_lint._strip_code). Only
/// shapes what harper reads; it does not need to preserve byte offsets for findings.
/// Newlines are kept so line numbers stay roughly meaningful.
pub fn strip_code(text: &str) -> String {
    let chars: Vec<char> = text.chars().collect();
    let n = chars.len();
    let mut blank = vec![false; n];
    let mut i = 0usize;
    while i < n {
        if i + 3 <= n && chars[i] == '`' && chars[i + 1] == '`' && chars[i + 2] == '`' {
            // fenced ``` ... ``` (dotall), or to the end when unclosed
            let closer = {
                let mut j = i + 3;
                let mut found = None;
                while j + 2 < n {
                    if chars[j] == '`' && chars[j + 1] == '`' && chars[j + 2] == '`' {
                        found = Some(j + 3);
                        break;
                    }
                    j += 1;
                }
                found.unwrap_or(n)
            };
            for k in i..closer {
                if chars[k] != '\n' {
                    blank[k] = true;
                }
            }
            i = closer;
        } else if chars[i] == '`' {
            // inline `....` never spanning a newline
            let mut j = i + 1;
            while j < n && chars[j] != '`' && chars[j] != '\n' {
                j += 1;
            }
            if j < n && chars[j] == '`' {
                for k in i..=j {
                    blank[k] = true;
                }
                i = j + 1;
            } else {
                i += 1;
            }
        } else if is_http_or_www(&chars, i, n) {
            let start = i;
            while i < n && !chars[i].is_whitespace() {
                i += 1;
            }
            for k in start..i {
                blank[k] = true;
            }
        } else {
            i += 1;
        }
    }
    let mut out = String::with_capacity(n);
    for k in 0..n {
        if blank[k] && chars[k] != '\n' {
            out.push(' ');
        } else {
            out.push(chars[k]);
        }
    }
    out
}

fn is_http_or_www(chars: &[char], i: usize, n: usize) -> bool {
    if i + 7 <= n && chars[i..i + 7].iter().collect::<String>() == "http://" {
        return true;
    }
    if i + 8 <= n && chars[i..i + 8].iter().collect::<String>() == "https://" {
        return true;
    }
    i + 4 <= n && chars[i..i + 4].iter().collect::<String>() == "www."
}

/// Run harper over `texts`, returning `{allowlisted_rule: count}`, or `None` when the
/// checker is unavailable (fail-open). Mirrors copy_lint.grammar_findings.
pub fn grammar_findings(
    texts: &BTreeMap<String, String>,
    timeout_s: u64,
) -> Option<BTreeMap<String, u64>> {
    let exe = harper_path()?;
    let td = std::env::temp_dir().join(format!("harper-vg-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&td);

    let mut paths: Vec<PathBuf> = Vec::new();
    for (name, text) in texts.iter() {
        if text.trim().len() < 60 {
            continue;
        }
        let p = td.join(format!("{}_{}.md", sanitize_name(name), paths.len()));
        if std::fs::write(&p, strip_code(text)).is_err() {
            continue;
        }
        paths.push(p);
    }
    let outcome = if paths.is_empty() {
        Some(BTreeMap::new())
    } else {
        let eff = (timeout_s * paths.len() as u64).min(HARPER_TIMEOUT_CEILING_S);
        match run_lint(&exe, &paths, eff) {
            Ok(bytes) => {
                let combined = String::from_utf8_lossy(&bytes).to_string();
                Some(parse_rule_counts(&combined))
            }
            Err(_) => None, // fail-open: child missing / hung beyond budget / killed
        }
    };
    for p in &paths {
        let _ = std::fs::remove_file(p);
    }
    let _ = std::fs::remove_dir_all(&td);
    outcome
}

/// Run `harper-cli lint --no-color <files>` and collect stdout+cstderr, bounded to budget_s.
/// A child that outlives its budget is killed and the whole call fails open (returns Err).
fn run_lint(exe: &Path, paths: &[PathBuf], budget_s: u64) -> Result<Vec<u8>, HarperError> {
    use std::io::Read;
    use std::process::Stdio;
    let mut child = Command::new(exe)
        .arg("lint")
        .arg("--no-color")
        .args(paths)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| HarperError::Exec(format!("spawn: {e}")))?;
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(budget_s);
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) if std::time::Instant::now() >= deadline => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(HarperError::Exec("harper exceeded budget".to_string()));
            }
            Ok(None) => std::thread::sleep(std::time::Duration::from_millis(50)),
            Err(e) => return Err(HarperError::Exec(format!("wait: {e}"))),
        }
    }
    let mut out = Vec::new();
    if let Some(mut stdout) = child.stdout.take() {
        let _ = stdout.read_to_end(&mut out);
    }
    let mut err_bytes = Vec::new();
    if let Some(mut stderr) = child.stderr.take() {
        let _ = stderr.read_to_end(&mut err_bytes);
    }
    out.extend_from_slice(&err_bytes); // stdout then stderr, as Python concatenates both
    let _ = child.wait();
    Ok(out)
}

fn parse_rule_counts(combined: &str) -> BTreeMap<String, u64> {
    let mut counts: BTreeMap<String, u64> = BTreeMap::new();
    for elem in combined.split('<').skip(1) {
        let Some((rule_raw, tail)) = elem.split_once(':') else {
            continue;
        };
        let rule = rule_raw.trim();
        let Some(num_raw) = tail.split('>').next() else { continue };
        let Ok(num) = num_raw.trim().parse::<u64>() else { continue };
        if HARPER_GRAMMAR_RULES.contains(&rule) {
            *counts.entry(rule.to_string()).or_insert(0) += num;
        }
    }
    counts
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn parses_only_allowlisted_rules() {
        // copy_lint membership-filter semantics: only an echoed rule name that is in
        // HARPER_GRAMMAR_RULES counts. "AnA" and "CommaFixes" are allowlisted;
        // "RepeatedWords" (the leaf under Repetition) is not, exactly as Python drops it.
        let out = "<AnA: 3> <RepeatedWords: 2> <CommaFixes: 5> <CommaFixes: 1>\nwhatever";
        let got = parse_rule_counts(out);
        assert_eq!(got.get("AnA"), Some(&3));
        assert_eq!(got.get("CommaFixes"), Some(&6), "sums across occurrences");
        assert!(!got.contains_key("RepeatedWords"), "leaf not in allowlist is dropped");
    }

    #[test]
    fn strip_code_blanks_fence_inline_and_url_keeps_prose_newlines() {
        let s = strip_code("See the spec: ```\ncode x=1\n``` then ``y`` and https://example.com/a and prose stays.");
        assert!(s.contains("prose stays."));
        assert!(s.contains('\n'), "newline preserved");
        // the code tokens should be gone
        assert!(!s.contains("x=1"));
        assert!(!s.contains("https://example.com"));
        assert!(!s.contains('`'));
    }
}
