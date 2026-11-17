//! `i8096-partition` ? compute admissible recovery lanes for a changed file set.
//!
//! Usage:
//!   i8096-partition --repo <root> [--max-files N] [--json] [path ...]
//!   git diff --name-only origin/main...HEAD | i8096-partition --repo . --json
//!
//! The partition is dependency-closed: files that import one another travel in the
//! same lane, a lane never mixes subsystems, and a coupled group larger than the
//! admission limit is emitted as one sealed lane rather than a broken half-commit.

use i8096_certifier::reconciler_ep_b::{partition_into_lanes, MAX_FILES_PER_LANE};
use std::collections::BTreeMap;
use std::io::Read;

fn main() {
    let mut repo: Option<String> = None;
    let mut max_files: usize = MAX_FILES_PER_LANE;
    let mut as_json = false;
    let mut paths: Vec<String> = Vec::new();

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--repo" => repo = args.next(),
            "--max-files" => {
                max_files = args
                    .next()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(MAX_FILES_PER_LANE);
            }
            "--json" => as_json = true,
            "--help" | "-h" => {
                println!("usage: i8096-partition --repo <root> [--max-files N] [--json] [path ...]");
                return;
            }
            other => paths.push(other.to_string()),
        }
    }

    if paths.is_empty() {
        let mut buffer = String::new();
        if std::io::stdin().read_to_string(&mut buffer).is_err() {
            eprintln!("i8096-partition: cannot read paths from stdin");
            std::process::exit(2);
        }
        paths = buffer
            .lines()
            .map(|l| l.trim())
            .filter(|l| !l.is_empty())
            .map(|l| l.to_string())
            .collect();
    }

    paths.sort();
    paths.dedup();

    let mut sources: BTreeMap<String, String> = BTreeMap::new();
    if let Some(root) = &repo {
        for path in &paths {
            let full = std::path::Path::new(root).join(path);
            if let Ok(content) = std::fs::read_to_string(&full) {
                sources.insert(path.clone(), content);
            }
        }
    }

    let report = partition_into_lanes(&paths, &sources, max_files);

    if as_json {
        println!("{}", serde_json::to_string_pretty(&report).unwrap_or_default());
    } else {
        println!("lanes: {}", report.lanes.len());
        for lane in &report.lanes {
            let mark = if lane.sealed { "SEALED" } else { "lane" };
            println!("{mark} [{}] {}", lane.subsystem.label(), lane.reason);
            for file in &lane.files {
                println!("    {file}");
            }
        }
        if !report.cross_subsystem.is_empty() {
            println!("cross-subsystem coupled groups: {}", report.cross_subsystem.len());
            for group in &report.cross_subsystem {
                println!("    {}", group.join(" "));
            }
        }
    }
}
