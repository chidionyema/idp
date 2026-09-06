//! Item 5/6 house-measure parity — Oracle lock.
//!
//! The reference numbers in `tests/fixtures/prose_measure_oracle.json` were produced by
//! running the REAL Python oracle (`prospector/prose_measure.document_measures` and
//! `prose_target.grade`) over the byte-clean prose fixtures `tests/fixtures/*.txt` (plain
//! single-flowing text, no escapes) using the committed `prose_target.json`. Rust must
//! reproduce them or the arithmetic has drifted from the reference it claims to mirror.
//! These tests are the "done" command for items 5 (bands) and 6 (split) per
//! SPEC-house-measures.md.

use serde_json::Value;
use voice_gate::house_measure::{document_measures, grade};

const ORACLE: &str = include_str!("fixtures/prose_measure_oracle.json");

const PROBES: &[&str] = &[
    "harvest_bill",
    "semicolon_heavy",
    "stacked_compounds",
    "flat_assert",
    "long_formal",
    "mattr",
];

fn txt(name: &str) -> &'static str {
    match name {
        "harvest_bill" => include_str!("fixtures/harvest_bill.txt"),
        "semicolon_heavy" => include_str!("fixtures/semicolon_heavy.txt"),
        "stacked_compounds" => include_str!("fixtures/stacked_compounds.txt"),
        "flat_assert" => include_str!("fixtures/flat_assert.txt"),
        "long_formal" => include_str!("fixtures/long_formal.txt"),
        "mattr" => include_str!("fixtures/mattr.txt"),
        _ => panic!("unknown probe {name}"),
    }
}

/// Tolerance for raw measured values (parts per ~1e-6); Python round-to-6 was applied at
/// authoring, so a faithful Rust implementation must agree to well under 1e-4.
const VTOL: f64 = 1e-4;

#[test]
fn each_probe_is_locked_in_the_oracle() {
    let oracle: Value = serde_json::from_str(ORACLE).expect("lock json parses");
    assert_eq!(
        PROBES.len(),
        oracle.as_object().map(|o| o.len()).unwrap_or(0),
        "oracle must cover every probe"
    );
}

#[test]
fn document_measures_matches_python_every_probe() {
    let oracle: Value = serde_json::from_str(ORACLE).unwrap();
    let kv = oracle.as_object().unwrap();
    for name in PROBES {
        let text = txt(name);
        let measures = document_measures(text);
        let expected = kv[*name]["measures"].as_object().unwrap();
        for (k, want) in expected {
            let want = want.as_f64();
            match want {
                None => assert!(
                    measures.get(k).is_none(),
                    "[{name}]: key {k} expected ABSENT (mattr undefined / NaN dropped) \
                     but Rust emitted a value"
                ),
                Some(w) => {
                    let got = measures
                        .get(k)
                        .unwrap_or_else(|| panic!("[{name}]: missing key {k}"));
                    assert!(
                        (got - w).abs() < VTOL,
                        "[{name}]: {k} expected {w}, got {got}"
                    );
                }
            }
        }
    }
}

#[test]
fn grade_matches_python_every_probe() {
    let oracle: Value = serde_json::from_str(ORACLE).unwrap();
    let kv = oracle.as_object().unwrap();
    for name in PROBES {
        let text = txt(name);
        let got = grade(&document_measures(text));
        let want = kv[*name]["grade"]
            .as_array()
            .unwrap()
            .iter()
            .map(|e| {
                (
                    e["measure"].as_str().unwrap().to_string(),
                    e["value"].as_f64().unwrap(),
                    e["side"].as_str().unwrap().to_string(),
                    e["z"].as_f64(),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            got.len(),
            want.len(),
            "[{name}]: grade length {} != python {}",
            got.len(),
            want.len()
        );
        for exp in &want {
            let hit = got
                .iter()
                .find(|b| b.measure == exp.0)
                .unwrap_or_else(|| panic!("[{name}]: no band for {}", exp.0));
            assert_eq!(hit.side.as_deref(), Some(exp.2.as_str()), "[{name}] {} side", exp.0);
            assert!(
                (hit.value - exp.1).abs() < 5e-3,
                "[{name}] {} value got {} want {}",
                exp.0,
                hit.value,
                exp.1
            );
            match (hit.z, exp.3) {
                (Some(gz), Some(wz)) => {
                    assert!((gz - wz).abs() < 1e-2, "[{name}] {} z got {gz} want {wz}", exp.0)
                }
                (None, None) => {}
                (Some(gz), None) => panic!("[{name}] {} got a z {gz} but python had none", exp.0),
                (None, Some(wz)) => panic!("[{name}] {} missing z, python had {wz}", exp.0),
            }
        }
    }
}
