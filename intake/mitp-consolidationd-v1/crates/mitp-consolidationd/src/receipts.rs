//! Cycle receipts: every cycle — including a zero-work heartbeat (E14) —
//! emits a JSON receipt per tenant. Silence is never operational proof.

use crate::json::{num_field, str_field};

#[derive(Debug, Clone, Default, PartialEq)]
pub struct TenantReceipt {
    pub tenant_id: String,
    pub staged: u64,
    pub promoted: u64,
    pub quarantined: u64,
    pub held: u64,
    pub distilled_proposals: u64,
    pub distilled_written: u64,
    pub poison_blocked: u64,
    pub revalidated: u64,
    pub demoted: u64,
    pub human_queued: u64,
    pub scratchpad_expired: u64,
    pub recurrence_aged: u64,
    pub spend_micro: u64,
    pub shadow: bool,
    pub error: Option<String>,
}

impl TenantReceipt {
    pub fn to_json(&self, cycle_id: &str, policy_version: &str) -> String {
        let mut fields = vec![
            str_field("cycle_id", cycle_id),
            str_field("tenant_id", &self.tenant_id),
            str_field("policy_version", policy_version),
            num_field("staged", self.staged),
            num_field("promoted", self.promoted),
            num_field("quarantined", self.quarantined),
            num_field("held", self.held),
            num_field("distilled_proposals", self.distilled_proposals),
            num_field("distilled_written", self.distilled_written),
            num_field("poison_blocked", self.poison_blocked),
            num_field("revalidated", self.revalidated),
            num_field("demoted", self.demoted),
            num_field("human_queued", self.human_queued),
            num_field("scratchpad_expired", self.scratchpad_expired),
            num_field("recurrence_aged", self.recurrence_aged),
            num_field("spend_micro", self.spend_micro),
            format!("\"shadow\":{}", self.shadow),
        ];
        match &self.error {
            Some(e) => fields.push(str_field("error", e)),
            None => fields.push("\"error\":null".to_string()),
        }
        format!("{{{}}}", fields.join(","))
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct CycleReceipt {
    pub cycle_id: String,
    pub started_ms: i64,
    pub finished_ms: i64,
    pub tenants_ok: u64,
    pub tenants_failed: u64,
    pub leader: bool,
    pub host_gate: String,
}

impl CycleReceipt {
    pub fn to_json(&self) -> String {
        format!(
            "{{{}}}",
            [
                str_field("cycle_id", &self.cycle_id),
                num_field("started_ms", self.started_ms),
                num_field("finished_ms", self.finished_ms),
                num_field("tenants_ok", self.tenants_ok),
                num_field("tenants_failed", self.tenants_failed),
                format!("\"leader\":{}", self.leader),
                str_field("host_gate", &self.host_gate),
            ]
            .join(",")
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tenant_receipt_is_valid_shaped_json() {
        let r = TenantReceipt { tenant_id: "t\"1\n".into(), promoted: 3, shadow: true, ..Default::default() };
        let j = r.to_json("cyc-1", "tp-memory.policy.v1");
        assert!(j.starts_with('{') && j.ends_with('}'));
        assert!(j.contains("\"tenant_id\":\"t\\\"1\\n\""), "escaping works: {j}");
        assert!(j.contains("\"promoted\":3"));
        assert!(j.contains("\"shadow\":true"));
        assert!(j.contains("\"error\":null"));
    }

    #[test]
    fn e14_heartbeat_receipt_with_zero_counts() {
        let r = TenantReceipt::default();
        let j = r.to_json("cyc-empty", "tp-memory.policy.v1");
        assert!(j.contains("\"staged\":0"));
        assert!(j.contains("\"promoted\":0"), "empty tenant still receipts");
    }
}
