//! Empirical parity lock: the Rust `harper::grammar_findings` wrapper reproduces the Python
//! `copy_lint.grammar_findings` oracle over the same live texts and the installed
//! `harper-cli`. Expected `{'AnA': 2}` was measured by running the Python oracle (see the
//! git/commit note) — not asserted from a guess.
//!
//! The test self-skips when harper-cli is not on PATH or in the Homebrew fallbacks, so the
//! crate stays green on a machine with no checker (mirroring the Python fail-open contract).
//! When it DOES run and the oracle disagrees, parity is broken and this fails loudly.

use std::collections::BTreeMap;
use voice_gate::harper;

fn oracle_needles() -> BTreeMap<String, String> {
    let mut m = BTreeMap::new();
    m.insert(
        "a.md".to_string(),
        "An historical agreement was signed by the parties in a European country and moved \
         near an university, which was a large and confusing institution for everybody \
         involved in the move."
            .to_string(),
    );
    m.insert(
        "c.md".to_string(),
        "The agreement is filed, it is current, it is signed, and it needs a review soonest \
         before the accounts are finalised by the audit committee tomorrow."
            .to_string(),
    );
    m
}

#[test]
fn grammar_findings_matches_python_oracle() {
    if harper::harper_path().is_none() {
        eprintln!("SKIP: harper-cli not installed; fail-open, nothing graded");
        return;
    }
    let got = harper::grammar_findings(&oracle_needles(), 60);
    // Python `copy_lint.grammar_findings` over these exact texts returned {'AnA': 2}.
    match got {
        Some(counts) => {
            assert_eq!(
                counts.get("AnA"),
                Some(&2),
                "expected {{'AnA':2}} like Python, got {counts:?}"
            );
            // parity: Python returned ONLY AnA on this corpus.
            assert_eq!(counts.len(), 1, "non-allowlisted or spurious counts leak in {counts:?}");
        }
        None => panic!("harper is installed but was reported unavailable (parity broken)"),
    }
}
