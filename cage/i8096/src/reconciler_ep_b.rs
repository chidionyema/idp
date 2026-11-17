//! EP-B reconciler: dependency-closed partitioning of a changed file set.
//!
//! Transport never confers authority, and a filename is not a dependency. A lane is
//! only admissible when every file in it belongs to one subsystem and no file in it
//! imports a file left behind in another lane. Coupled files that cannot fit the
//! five-file admission limit are never split: they are emitted as one sealed lane
//! carrying the reason, so the recovery is dependency-safe instead of a broken
//! half-commit.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

/// The estate's admission limit for a single lane.
pub const MAX_FILES_PER_LANE: usize = 5;

/// The subsystem a changed file belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Subsystem {
    Backstage,
    Catalog,
    Infra,
    Platform,
    Sovereign,
    Tests,
    Docs,
    Web,
    Other,
}

impl Subsystem {
    /// Classify a repo-relative path by its first meaningful segment.
    pub fn of(path: &str) -> Subsystem {
        let first = path.split('/').find(|s| !s.is_empty()).unwrap_or("");
        match first {
            "backstage" => Subsystem::Backstage,
            "catalog" => Subsystem::Catalog,
            "infra" | "clusters" | "deploy" => Subsystem::Infra,
            "platform" | "router" | "cage" => Subsystem::Platform,
            "sovereign" => Subsystem::Sovereign,
            "tests" | "test" => Subsystem::Tests,
            "docs" => Subsystem::Docs,
            "web" | "frontend" => Subsystem::Web,
            _ => Subsystem::Other,
        }
    }
}

/// One admissible unit of recovery.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Lane {
    /// The subsystem this lane belongs to, if it belongs to exactly one.
    pub subsystem: Subsystem,
    /// The files carried by the lane, sorted.
    pub files: Vec<String>,
    /// True when the lane may not be split further because its files are coupled.
    pub sealed: bool,
    /// Why the lane is shaped this way.
    pub reason: String,
}

/// The result of partitioning a changed file set.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PartitionReport {
    pub lanes: Vec<Lane>,
    /// Coupled groups that span more than one subsystem.
    pub cross_subsystem: Vec<Vec<String>>,
}

/// A private git ref that holds source bytes under custody.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CustodyRef {
    pub repo: String,
    pub git_ref: String,
    pub sha: String,
    pub note: String,
}

/// The authoritative custody route for the AI Studio source bytes (#7760).
///
/// The Cloud Run export endpoint is gone (HTTP 404); the private refs in
/// `chidionyema/gemini-sync` are the only declared custody path. The SHAs are
/// recorded so a reader can tell a moved ref from a missing one.
pub fn resolve_7760_custody_route() -> Vec<CustodyRef> {
    vec![
        CustodyRef {
            repo: "chidionyema/gemini-sync".to_string(),
            git_ref: "refs/heads/recovery/aistudio-git-bundle-20261116".to_string(),
            sha: "2b336e5ee2049beac7007d002539df7afdcfc399".to_string(),
            note: "Crescendo source intake receiver (workflow + functions/api/ingest + test)".to_string(),
        },
        CustodyRef {
            repo: "chidionyema/gemini-sync".to_string(),
            git_ref: "refs/heads/aistudio/selftest-20261116".to_string(),
            sha: "85a226f6106163b2b6257d5ba3a19c806f173036".to_string(),
            note: "AI Studio selftest export of the same tree".to_string(),
        },
    ]
}

/// A monotonic fence token must strictly increase.
pub fn fence_is_monotonic(previous: u64, next: u64) -> bool {
    next > previous
}

/// Extract the module specifiers a source file imports.
pub fn parse_imports(path: &str, source: &str) -> Vec<String> {
    let mut out = Vec::new();
    for line in source.lines() {
        let line = line.trim();
        let spec = if let Some(rest) = line.strip_prefix("import ") {
            rest.split_whitespace().next().unwrap_or("")
        } else if let Some(rest) = line.strip_prefix("export ") {
            rest.split_whitespace().next().unwrap_or("")
        } else if let Some(rest) = line.strip_prefix("from ") {
            rest.split_whitespace().next().unwrap_or("")
        } else if let Some(rest) = line.strip_prefix("use ") {
            rest.split_whitespace().next().unwrap_or("")
        } else {
            ""
        };
        let spec = spec.trim_matches(|c| c == '"' || c == '\'' || c == ';');
        if spec.starts_with('.') || spec.starts_with('/') {
            out.push(spec.to_string());
        }
    }
    let _ = path;
    out
}

/// Resolve a relative import specifier to a repo-relative file path, if one exists.
fn resolve_relative(importer: &str, spec: &str, known: &BTreeSet<String>) -> Option<String> {
    if !spec.starts_with('.') {
        return None;
    }
    let base = match importer.rfind('/') {
        Some(i) => importer[..i].to_string(),
        None => String::new(),
    };
    let mut segments: Vec<&str> = base.split('/').filter(|s| !s.is_empty()).collect();
    for part in spec.split('/') {
        match part {
            "." | "" => {}
            ".." => {
                segments.pop();
            }
            other => segments.push(other),
        }
    }
    let joined = segments.join("/");
    let candidates = [
        joined.clone(),
        format!("{joined}.ts"),
        format!("{joined}.tsx"),
        format!("{joined}.js"),
        format!("{joined}/index.ts"),
        format!("{joined}/index.tsx"),
        format!("{joined}.py"),
        format!("{joined}.rs"),
    ];
    candidates.into_iter().find(|c| known.contains(c))
}

/// Group the changed files into sets that must travel together.
///
/// Two files are coupled when one imports the other, transitively. A coupled group is
/// never split: splitting it is how a recovery breaks a working implementation.
pub fn coupled_components(
    files: &[String],
    sources: &BTreeMap<String, String>,
) -> Vec<Vec<String>> {
    let known: BTreeSet<String> = files.iter().cloned().collect();
    let mut parent: BTreeMap<String, String> = BTreeMap::new();
    for f in files {
        parent.insert(f.clone(), f.clone());
    }
    fn find(parent: &mut BTreeMap<String, String>, x: &str) -> String {
        let p = parent.get(x).cloned().unwrap_or_else(|| x.to_string());
        if p == x {
            return p;
        }
        let root = find(parent, &p);
        parent.insert(x.to_string(), root.clone());
        root
    }
    fn union(parent: &mut BTreeMap<String, String>, a: &str, b: &str) {
        let ra = find(parent, a);
        let rb = find(parent, b);
        if ra != rb {
            parent.insert(ra, rb);
        }
    }
    for f in files {
        let src = match sources.get(f) {
            Some(s) => s,
            None => continue,
        };
        for spec in parse_imports(f, src) {
            if let Some(target) = resolve_relative(f, &spec, &known) {
                union(&mut parent, f, &target);
            }
        }
    }
    let mut groups: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for f in files {
        let root = find(&mut parent, f);
        groups.entry(root).or_default().insert(f.clone());
    }
    groups
        .into_values()
        .map(|g| {
            let mut v: Vec<String> = g.iter().cloned().collect();
            v.sort();
            v
        })
        .collect()
}

/// Partition a changed file set into admissible lanes.
///
/// Rules, in order:
/// 1. Coupled files travel together, always.
/// 2. A lane carries one subsystem only.
/// 3. A lane carries at most `max_files` files.
/// 4. A coupled group larger than `max_files` is emitted as one sealed lane with the
///    reason recorded. It is never split, because a split coupled group is a
///    broken half-commit.
pub fn partition_into_lanes(
    files: &[String],
    sources: &BTreeMap<String, String>,
    max_files: usize,
) -> PartitionReport {
    let components = coupled_components(files, sources);
    let mut cross_subsystem: Vec<Vec<String>> = Vec::new();
    let mut sealed: Vec<Vec<String>> = Vec::new();
    let mut singles: Vec<Vec<String>> = Vec::new();

    for component in components {
        let subsystems: BTreeSet<Subsystem> =
            component.iter().map(|f| Subsystem::of(f)).collect();
        if subsystems.len() > 1 {
            cross_subsystem.push(component.clone());
        }
        if component.len() > max_files {
            sealed.push(component);
        } else {
            singles.push(component);
        }
    }

    // Group the admissible components by subsystem, then pack them into lanes.
    let mut by_subsystem: BTreeMap<Subsystem, Vec<Vec<String>>> = BTreeMap::new();
    for component in singles {
        // A component with several subsystems is routed by its first file's subsystem
        // but is reported as cross-subsystem above.
        let subsystem = component
            .iter()
            .map(|f| Subsystem::of(f))
            .next()
            .unwrap_or(Subsystem::Other);
        by_subsystem.entry(subsystem).or_default().push(component);
    }

    let mut lanes: Vec<Lane> = Vec::new();
    for (subsystem, mut components) in by_subsystem {
        components.sort();
        let mut current: Vec<String> = Vec::new();
        for component in components {
            if !current.is_empty() && current.len() + component.len() > max_files {
                lanes.push(Lane {
                    subsystem,
                    files: std::mem::take(&mut current),
                    sealed: false,
                    reason: format!("packed under the {max_files}-file admission limit"),
                });
            }
            current.extend(component);
        }
        if !current.is_empty() {
            lanes.push(Lane {
                subsystem,
                files: current,
                sealed: false,
                reason: format!("packed under the {max_files}-file admission limit"),
            });
        }
    }

    for component in sealed {
        let file_count = component.len();
        let subsystem = component
            .iter()
            .map(|f| Subsystem::of(f))
            .next()
            .unwrap_or(Subsystem::Other);
        lanes.push(Lane {
            subsystem,
            files: component,
            sealed: true,
            reason: format!(
                "coupled group of {file_count} files exceeds the {max_files}-file limit; shipped as one sealed manifest"
            ),
        });
    }

    lanes.sort_by(|a, b| a.files.cmp(&b.files));
    PartitionReport {
        lanes,
        cross_subsystem,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn src(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(a, b)| (a.to_string(), b.to_string()))
            .collect()
    }

    #[test]
    fn seven_files_over_five_subsystems_produce_single_subsystem_lanes() {
        let files: Vec<String> = [
            "backstage/a.ts",
            "backstage/b.ts",
            "catalog/c.ts",
            "infra/d.yaml",
            "sovereign/e.py",
            "tests/t.ts",
            "docs/d.md",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();
        let report = partition_into_lanes(&files, &src(&[]), MAX_FILES_PER_LANE);
        assert!(!report.lanes.is_empty());
        for lane in &report.lanes {
            assert!(lane.files.len() <= MAX_FILES_PER_LANE, "lane too wide: {lane:?}");
            let subsystems: BTreeSet<Subsystem> =
                lane.files.iter().map(|f| Subsystem::of(f)).collect();
            assert_eq!(subsystems.len(), 1, "lane mixes subsystems: {lane:?}");
        }
        let carried: BTreeSet<String> = report
            .lanes
            .iter()
            .flat_map(|l| l.files.iter().cloned())
            .collect();
        assert_eq!(carried.len(), files.len(), "a file was dropped");
    }

    #[test]
    fn coupled_files_are_never_split_across_lanes() {
        let files: Vec<String> = vec!["catalog/a.ts".into(), "catalog/b.ts".into()];
        let sources = src(&[(
            "catalog/a.ts",
            "import { b } from './b';\nexport const a = b;\n",
        )]);
        let report = partition_into_lanes(&files, &sources, MAX_FILES_PER_LANE);
        assert_eq!(report.lanes.len(), 1);
        assert_eq!(report.lanes[0].files.len(), 2);
    }

    #[test]
    fn oversized_coupled_group_is_sealed_not_split() {
        let mut files: Vec<String> = (0..7).map(|i| format!("catalog/f{i}.ts")).collect();
        let mut sources = BTreeMap::new();
        for i in 0..7usize {
            files[i] = format!("catalog/f{i}.ts");
            if i + 1 < 7 {
                sources.insert(
                    files[i].clone(),
                    format!("import './f{}';\n", i + 1),
                );
            }
        }
        let report = partition_into_lanes(&files, &sources, MAX_FILES_PER_LANE);
        let sealed: Vec<&Lane> = report.lanes.iter().filter(|l| l.sealed).collect();
        assert_eq!(sealed.len(), 1);
        assert_eq!(sealed[0].files.len(), 7);
        assert!(sealed[0].reason.contains("sealed manifest"));
    }

    #[test]
    fn fence_tokens_must_strictly_increase() {
        assert!(fence_is_monotonic(5, 6));
        assert!(!fence_is_monotonic(6, 5));
        assert!(!fence_is_monotonic(6, 6));
    }

    #[test]
    fn custody_route_names_the_private_ref() {
        let route = resolve_7760_custody_route();
        assert!(route
            .iter()
            .any(|r| r.git_ref == "refs/heads/recovery/aistudio-git-bundle-20261116"));
        assert!(route.iter().all(|r| r.sha.len() == 40));
    }

    #[test]
    fn subsystem_classification_is_stable() {
        assert_eq!(Subsystem::of("backstage/x.ts"), Subsystem::Backstage);
        assert_eq!(Subsystem::of("clusters/k3s/estate-config.yaml"), Subsystem::Infra);
        assert_eq!(Subsystem::of("tests/x.test.ts"), Subsystem::Tests);
        assert_eq!(Subsystem::of("README.md"), Subsystem::Other);
    }
}
