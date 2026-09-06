//! Tier 1: deterministic grading over compiled DFA automata (spec §2/§15).
//! One automaton per rule (attribution is the product: a finding names its rule id).
//! O(n) per rule, zero variance, no backtracking — ReDoS is impossible by construction.

use regex_automata::meta::Regex;
use serde::Serialize;

use crate::policy::{Lane, VoicePolicy};
use crate::prose::ProseStripper;

#[derive(Debug, Clone, Serialize)]
pub struct Span {
    pub start: usize,
    pub end: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct Finding {
    pub rule_id: String,
    pub lane: String,
    pub field: String,
    pub span: Span,
    pub detail: String,
    pub tier: &'static str,
}

#[derive(Debug, thiserror::Error)]
pub enum Tier1Error {
    #[error("rule `{id}` pattern failed DFA compile: {detail}")]
    Compile { id: String, detail: String },
}

struct CompiledRule {
    id: String,
    message: String,
    re: Regex,
}

pub struct Tier1 {
    stripper: ProseStripper,
    // rules per lane name, inheritance already resolved by policy
    rules: std::collections::HashMap<String, Vec<CompiledRule>>,
}

impl Tier1 {
    pub fn new(policy: &VoicePolicy) -> Result<Self, Tier1Error> {
        let mut rules = std::collections::HashMap::new();
        for (name, lane) in &policy.lanes {
            let mut compiled = Vec::with_capacity(lane.deny_patterns.len());
            for p in &lane.deny_patterns {
                let flags = p.flags.clone().unwrap_or_else(|| "i".to_string());
                let re = Regex::new(&format!("(?{}m){}", flags, p.pattern)).map_err(|e| {
                    Tier1Error::Compile { id: p.id.clone(), detail: e.to_string() }
                })?;
                compiled.push(CompiledRule { id: p.id.clone(), message: p.message.clone(), re });
            }
            rules.insert(name.clone(), compiled);
        }
        Ok(Self { stripper: ProseStripper::new(), rules })
    }

    pub fn knows_lane(&self, lane: &str) -> bool {
        self.rules.contains_key(lane)
    }

    pub fn lane_excludes(&self, lane: &Lane, field: &str) -> bool {
        lane.exclude_fields.contains(&field.to_lowercase())
    }

    /// Grade one field's text against a lane. Non-prose spans are blanked first;
    /// findings carry spans into the ORIGINAL text.
    pub fn grade(&self, lane_name: &str, lane: &Lane, field: &str, text: &str) -> Vec<Finding> {
        if self.lane_excludes(lane, field) {
            return Vec::new();
        }
        let prose = self.stripper.prose_only(text);
        let mut findings = Vec::new();
        if let Some(rules) = self.rules.get(lane_name) {
            for rule in rules {
                for m in rule.re.find_iter(&prose) {
                    findings.push(Finding {
                        rule_id: rule.id.clone(),
                        lane: lane_name.to_string(),
                        field: field.to_string(),
                        span: Span { start: m.start(), end: m.end() },
                        detail: rule.message.clone(),
                        tier: "tier1",
                    });
                }
            }
        }
        findings
    }
}
