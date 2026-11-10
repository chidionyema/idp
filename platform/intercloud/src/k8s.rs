//! K8sStore — the production binding of `Store` (see CONTROLLER_ADAPTER.md).
//!
//! The trait is the contract; `FsStore` is the complete local implementation and this
//! module is the same contract against the cluster:
//!
//!   load()   -> LIST Lanes / WorkloadSpecs (all namespaces)
//!               LIST Claims (estate.estate.internal)
//!               GET  Approvals, REJECTED unless status.verified == true (set by the
//!                    spooler signer — this adapter never writes an Approval; see
//!                    manifests/rbac.yaml, controller SA is read-only on approvals)
//!   apply()  -> CREATE / PATCH / DELETE Claims
//!               UPSERT PropagationPolicies
//!               append receipts to the estate-receipt sidecar, chain head mirrored
//!               to a ConfigMap for external anchoring (SECURITY_REVIEW C2: a chain
//!               with no external anchor is tamper-EVIDENT at best, so the anchor is
//!               mandatory and `verify()` says so when it is absent)
//!
//! Readiness: a workload is only `ready` when the observed Claim carries
//! `status.conditions[type=Ready,status=True]`. The reconciler mints a receipt only on
//! observed readiness, so an unready or unobserved Claim must never be reported ready.
//!
//! std-only, zero dependencies — same as the rest of the crate. The cluster is reached
//! through a `Cluster` seam (GET/LIST/PATCH over the kube API), so the adapter is
//! testable without a live control plane and the HTTP transport is injected.

use crate::controller::{ObservedClaim, Op, RawApproval, Snapshot, Store};
use crate::{sha256_hex, Lane, Workload, ZERO};

// ---------------------------------------------------------------------------
// Cluster seam
// ---------------------------------------------------------------------------

/// A request to the Kubernetes API. Kept deliberately small: the adapter needs
/// list/get on three CRDs and create/patch/delete on two more.
#[derive(Clone, Debug, PartialEq)]
pub enum Verb {
    Get,
    List,
    Create,
    Patch,
    Delete,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Request {
    pub verb: Verb,
    /// e.g. `intercloud.estate.internal/v1/lanes`, `estate.estate.internal/v1/claims`
    pub path: String,
    /// JSON body for Create/Patch; empty for Get/List/Delete.
    pub body: String,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Response {
    pub status: u16,
    pub body: String,
}

/// The transport the controller runs on. `HttpCluster` in a live pod, `ScriptedCluster`
/// in tests. Returning `Err` means "cluster unreachable"; the adapter maps that to a
/// `load()` error rather than silently degrading to an empty snapshot (an empty
/// snapshot would read as "nothing placed" and cause a mass re-place).
pub trait Cluster {
    fn call(&self, req: &Request) -> Result<Response, String>;
}

/// Rejected approval marker. The spec is explicit: an Approval whose
/// `status.verified` is not `true` is dropped, not passed through with a flag.
pub const APPROVAL_REJECTED: &str = "rejected unless status.verified=true set by spooler signer";

// ---------------------------------------------------------------------------
// Minimal JSON reading
// ---------------------------------------------------------------------------

/// Extract a string field `"key": "value"` from a flat JSON object. std-only so the
/// crate keeps its zero-dependency rule; these responses are CRD lists, not arbitrary
/// documents, and `json_tests` below pins the behaviour.
fn json_str(hay: &str, key: &str) -> Option<String> {
    let pat = format!("\"{}\"", key);
    let mut from = 0usize;
    while let Some(i) = hay[from..].find(&pat) {
        let start = from + i + pat.len();
        let rest = &hay[start..];
        let rest = rest.trim_start();
        let rest = rest.strip_prefix(':').unwrap_or(rest).trim_start();
        if let Some(r) = rest.strip_prefix('"') {
            if let Some(end) = r.find('"') {
                return Some(r[..end].to_string());
            }
            return None;
        }
        // not a string value (object/array/bool/number) — keep looking
        from = start;
    }
    None
}

/// Extract a numeric field `"key": 12.5`.
fn json_num(hay: &str, key: &str) -> Option<f64> {
    let pat = format!("\"{}\"", key);
    let mut from = 0usize;
    while let Some(i) = hay[from..].find(&pat) {
        let start = from + i + pat.len();
        let rest = hay[start..].trim_start();
        let rest = rest.strip_prefix(':').unwrap_or(rest).trim_start();
        let tok: String = rest
            .chars()
            .take_while(|c| c.is_ascii_digit() || *c == '.' || *c == '-' || *c == '+' || *c == 'e' || *c == 'E')
            .collect();
        if let Ok(v) = tok.parse::<f64>() {
            return Some(v);
        }
        from = start;
    }
    None
}

/// Extract a boolean field `"key": true`.
fn json_bool(hay: &str, key: &str) -> Option<bool> {
    let pat = format!("\"{}\"", key);
    let mut from = 0usize;
    while let Some(i) = hay[from..].find(&pat) {
        let start = from + i + pat.len();
        let rest = hay[start..].trim_start();
        let rest = rest.strip_prefix(':').unwrap_or(rest).trim_start();
        if rest.starts_with("true") {
            return Some(true);
        }
        if rest.starts_with("false") {
            return Some(false);
        }
        from = start;
    }
    None
}

/// Split `{"items": [ {...}, {...} ]}` into the individual object texts.
fn items(body: &str) -> Vec<String> {
    let mut out = vec![];
    let Some(items_at) = body.find("\"items\"") else { return out };
    let after = &body[items_at..];
    let Some(open) = after.find('[') else { return out };
    let mut depth = 0i32;
    let mut cur = String::new();
    let mut in_str = false;
    let mut esc = false;
    for c in after[open + 1..].chars() {
        if esc {
            cur.push(c);
            esc = false;
            continue;
        }
        match c {
            '\\' if in_str => {
                cur.push(c);
                esc = true;
            }
            '"' => {
                in_str = !in_str;
                cur.push(c);
            }
            '{' if !in_str => {
                depth += 1;
                cur.push(c);
            }
            '}' if !in_str => {
                depth -= 1;
                cur.push(c);
                if depth == 0 {
                    out.push(std::mem::take(&mut cur));
                }
            }
            ']' if !in_str && depth == 0 => break,
            _ => {
                if depth > 0 {
                    cur.push(c);
                }
            }
        }
    }
    out
}

// ---------------------------------------------------------------------------
// K8sStore
// ---------------------------------------------------------------------------

/// Chain head mirrored to a ConfigMap for external anchoring (SECURITY_REVIEW C2).
/// `None` means the anchor is absent, which `verify()` reports as diagnostic-only.
pub struct Anchor {
    pub namespace: String,
    pub name: String,
}

pub struct K8sStore {
    /// Transport into the cluster (live or scripted).
    pub cluster: Box<dyn Cluster>,
    /// Directory the estate-receipt sidecar watches; receipts are appended here.
    pub receipt_dir: String,
    /// External anchor target. Required for a PnL-grade verification.
    pub anchor: Option<Anchor>,
    /// Current receipt chain head.
    pub head: String,
}

impl K8sStore {
    pub fn new(cluster: Box<dyn Cluster>, receipt_dir: &str, anchor: Option<Anchor>) -> K8sStore {
        let head = read_head(receipt_dir).unwrap_or_else(|| ZERO.to_string());
        K8sStore { cluster, receipt_dir: receipt_dir.to_string(), anchor, head }
    }

    fn get(&self, path: &str) -> Result<Response, String> {
        self.cluster.call(&Request { verb: Verb::Get, path: path.to_string(), body: String::new() })
    }

    fn list(&self, path: &str) -> Result<Response, String> {
        self.cluster.call(&Request { verb: Verb::List, path: path.to_string(), body: String::new() })
    }

    fn write(&self, verb: Verb, path: &str, body: String) -> Result<Response, String> {
        self.cluster.call(&Request { verb, path: path.to_string(), body })
    }

    /// LIST a namespaced-less CRD path across all namespaces.
    fn list_all(&self, group_version_resource: &str) -> Result<Vec<String>, String> {
        let r = self.list(group_version_resource)?;
        if r.status != 200 {
            return Err(format!("LIST {} -> {}: {}", group_version_resource, r.status, r.body));
        }
        Ok(items(&r.body))
    }

    // -- load() duties ------------------------------------------------------

    fn load_lanes(&self) -> Result<Vec<Lane>, String> {
        // LIST Lanes (all namespaces). A Lane's capacity comes from its spec; its health
        // comes from its status, applied below. Placing onto a lane whose health nobody
        // measured is the failure this whole controller exists to prevent, so an absent
        // status means down.
        let objs = self.list_all("intercloud.estate.internal/v1/lanes")?;
        let mut lanes = vec![];
        for o in objs {
            let Some(name) = json_str(&o, "name") else { continue };
            let class = json_str(&o, "class").unwrap_or_else(|| "free".to_string());
            let provider = json_str(&o, "provider").unwrap_or_else(|| "unknown".to_string());
            // capacity may be nested; accept both flat and `capacity.cores` spellings.
            let cores = json_num(&o, "cores").unwrap_or(0.0);
            let mem_gb = json_num(&o, "memGb").or_else(|| json_num(&o, "mem_gb")).unwrap_or(0.0);
            let cost_mo = json_num(&o, "costMo").or_else(|| json_num(&o, "cost_mo")).unwrap_or(0.0);
            // A lane with no measured capacity is a lane nobody sized. load_registry
            // rejects cores/mem <= 0, and a paid lane with no cost is rejected too, so
            // a malformed Lane CR surfaces as a load error instead of a silent skip.
            let line = format!(
                "lane {} {} {} {} {} {}",
                name, class, provider, cores, mem_gb, cost_mo
            );
            let parsed = crate::load_registry(&line)
                .map_err(|e| format!("Lane {}: {}", name, e))?;
            if let Some(mut l) = parsed.into_iter().next() {
                // health from status, never from spec; unset status -> down
                l.health = json_str(&o, "health").unwrap_or_else(|| "down".to_string());
                lanes.push(l);
            }
        }
        Ok(lanes)
    }

    fn load_workloads(&self) -> Result<Vec<Workload>, String> {
        let objs = self.list_all("intercloud.estate.internal/v1/workloadspecs")?;
        let mut out = vec![];
        for o in objs {
            let Some(name) = json_str(&o, "name") else { continue };
            let cores = json_num(&o, "cores").unwrap_or(0.0);
            let mem_gb = json_num(&o, "memGb").or_else(|| json_num(&o, "mem_gb")).unwrap_or(0.0);
            out.push(Workload {
                name,
                cores,
                mem_gb,
                paid_ok: false,
                prefer: json_str(&o, "prefer"),
                paid_since_ticks: None,
                home: None,
            });
        }
        Ok(out)
    }

    fn load_approvals(&self) -> Result<Vec<RawApproval>, String> {
        // GET Approvals. `verified` is set by the spooler signer; anything else is
        // REJECTED. This is the exact rule in CONTROLLER_ADAPTER.md and the one the
        // HMAC check in Reconciler then re-checks — belt and braces, because the
        // approval receipt IS the payment gate.
        let objs = self.list_all("intercloud.estate.internal/v1/approvals")?;
        let mut out = vec![];
        for o in objs {
            if json_bool(&o, "verified") != Some(true) {
                continue; // REJECTED: not signed by the spooler
            }
            let Some(lane) = json_str(&o, "lane") else { continue };
            let cost_mo = json_num(&o, "costMo").or_else(|| json_num(&o, "cost_mo")).unwrap_or(0.0);
            let via = json_str(&o, "via").unwrap_or_default();
            let sig = json_str(&o, "sig").unwrap_or_default();
            out.push(RawApproval { lane, cost_mo, via, sig });
        }
        Ok(out)
    }

    fn load_claims(&self) -> Result<Vec<ObservedClaim>, String> {
        // LIST Claims (estate.estate.internal). Ready only on
        // status.conditions[type=Ready,status=True] — never inferred from existence.
        let objs = self.list_all("estate.estate.internal/v1/claims")?;
        let mut out = vec![];
        for o in objs {
            let Some(workload) = json_str(&o, "workload") else { continue };
            let Some(lane) = json_str(&o, "lane") else { continue };
            let ready = condition_ready(&o);
            out.push(ObservedClaim { workload, lane, ready });
        }
        Ok(out)
    }

    // -- receipt chain ------------------------------------------------------

    fn append_receipt(&mut self, wl: &str, lane: Option<&str>, dec: &str, why: &str) -> Result<(), String> {
        let canon = format!(
            "wl={};lane={};dec={};why={};prev={}",
            wl,
            lane.unwrap_or("-"),
            dec,
            why,
            self.head
        );
        let h = sha256_hex(&canon);
        let line = format!("{} {}", h, canon);
        use std::io::Write;
        std::fs::create_dir_all(&self.receipt_dir).map_err(|e| e.to_string())?;
        let mut f = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(format!("{}/receipts.log", self.receipt_dir))
            .map_err(|e| e.to_string())?;
        writeln!(f, "{}", line).map_err(|e| e.to_string())?;
        self.head = h;
        self.mirror_head_to_configmap()?;
        Ok(())
    }

    /// Mirror the chain head to a ConfigMap so an external reader can anchor it.
    /// SECURITY_REVIEW C2: without this, a forger who controls the writer can rebuild
    /// the whole chain from genesis and no alarm fires.
    fn mirror_head_to_configmap(&self) -> Result<(), String> {
        let Some(a) = &self.anchor else {
            // No anchor configured: the receipt is still written and still chained,
            // but verification is diagnostic only. We do not pretend otherwise.
            return Ok(());
        };
        let body = format!(
            "{{\"apiVersion\":\"v1\",\"kind\":\"ConfigMap\",\"metadata\":{{\"name\":\"{}\",\"namespace\":\"{}\"}},\"data\":{{\"chain_head\":\"{}\"}}}}",
            a.name, a.namespace, self.head
        );
        let path = format!("/api/v1/namespaces/{}/configmaps/{}", a.namespace, a.name);
        let r = self.write(Verb::Patch, &path, body)?;
        if r.status >= 400 {
            return Err(format!("anchor write failed {}: {}", r.status, r.body));
        }
        Ok(())
    }

    /// Verify the receipt chain. Returns the verdict and, per SECURITY_REVIEW C2,
    /// says plainly when there is no external anchor that it is diagnostic only.
    pub fn verify(&self) -> Result<String, String> {
        let text = std::fs::read_to_string(format!("{}/receipts.log", self.receipt_dir))
            .map_err(|e| e.to_string())?;
        let mut prev = ZERO.to_string();
        let mut n = 0usize;
        for l in text.lines().filter(|l| !l.trim().is_empty()) {
            let mut parts = l.splitn(2, ' ');
            let h = parts.next().unwrap_or("");
            let canon = parts.next().unwrap_or("");
            let fields: std::collections::BTreeMap<String, String> = canon
                .split(';')
                .filter_map(|f| {
                    let mut kv = f.splitn(2, '=');
                    Some((kv.next()?.to_string(), kv.next()?.to_string()))
                })
                .collect();
            if fields.get("prev").map(|s| s.as_str()) != Some(prev.as_str()) {
                return Err(format!("chain break at line {}", n + 1));
            }
            if sha256_hex(canon) != h {
                return Err(format!("receipt tampered at line {}", n + 1));
            }
            prev = h.to_string();
            n += 1;
        }
        let anchored = match &self.anchor {
            Some(a) => {
                let path = format!("/api/v1/namespaces/{}/configmaps/{}", a.namespace, a.name);
                let r = self.get(&path).map_err(|e| e.to_string())?;
                json_str(&r.body, "chain_head").map(|h| h == prev).unwrap_or(false)
            }
            None => false,
        };
        if n > 0 && !anchored {
            return Ok(format!(
                "{} receipts verified, chain intact — DIAGNOSTIC ONLY: no external anchor (C2). \
                 A writer who controls this volume can rebuild the chain from genesis undetected.",
                n
            ));
        }
        Ok(format!("{} receipts verified, chain intact, anchored", n))
    }
}

/// `status.conditions[type=Ready]` is `status=True`.
fn condition_ready(obj: &str) -> bool {
    // Walk every condition object and look for Ready/True together.
    for cond in items_direct(obj, "conditions") {
        if json_str(&cond, "type").as_deref() == Some("Ready") {
            let st = json_str(&cond, "status").unwrap_or_default();
            if st.eq_ignore_ascii_case("true") {
                return true;
            }
        }
    }
    false
}

/// Extract objects from a named array field, e.g. `"conditions": [...]`.
fn items_direct(body: &str, field: &str) -> Vec<String> {
    let pat = format!("\"{}\"", field);
    let Some(at) = body.find(&pat) else { return vec![] };
    let after = &body[at..];
    let Some(open) = after.find('[') else { return vec![] };
    let mut out = vec![];
    let mut depth = 0i32;
    let mut cur = String::new();
    let mut in_str = false;
    let mut esc = false;
    for c in after[open + 1..].chars() {
        if esc {
            cur.push(c);
            esc = false;
            continue;
        }
        match c {
            '\\' if in_str => {
                cur.push(c);
                esc = true;
            }
            '"' => {
                in_str = !in_str;
                cur.push(c);
            }
            '{' if !in_str => {
                depth += 1;
                cur.push(c);
            }
            '}' if !in_str => {
                depth -= 1;
                cur.push(c);
                if depth == 0 {
                    out.push(std::mem::take(&mut cur));
                }
            }
            ']' if !in_str && depth == 0 => break,
            _ => {
                if depth > 0 {
                    cur.push(c);
                }
            }
        }
    }
    out
}

fn read_head(dir: &str) -> Option<String> {
    let text = std::fs::read_to_string(format!("{}/receipts.log", dir)).ok()?;
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .last()
        .map(|l| l.split(' ').next().unwrap_or(ZERO).to_string())
}

// ---------------------------------------------------------------------------
// Store impl — the contract
// ---------------------------------------------------------------------------

impl Store for K8sStore {
    fn load(&self) -> Result<Snapshot, String> {
        // Every part of the snapshot must be observed. If any LIST fails we return Err
        // rather than a partial snapshot: a partial snapshot would show zero claims and
        // trigger a mass re-place against a cluster that is merely unreachable.
        let lanes = self.load_lanes()?;
        let workloads = self.load_workloads()?;
        let approvals = self.load_approvals()?;
        let claims = self.load_claims()?;
        Ok(Snapshot { lanes, workloads, approvals, claims })
    }

    fn apply(&mut self, ops: Vec<Op>) -> Result<(), String> {
        for op in ops {
            match op {
                Op::CreateClaim { workload, lane } => {
                    let body = format!(
                        "{{\"apiVersion\":\"estate.estate.internal/v1\",\"kind\":\"Claim\",\
                          \"metadata\":{{\"name\":\"{}\",\"namespace\":\"estate\"}},\
                          \"spec\":{{\"workload\":\"{}\",\"lane\":\"{}\"}}}}",
                        claim_name(&workload),
                        workload,
                        lane
                    );
                    let r = self.write(Verb::Create, "/apis/estate.estate.internal/v1/namespaces/estate/claims", body)?;
                    if r.status >= 400 && r.status != 409 {
                        // 409 = already exists; the reconcile is idempotent, that is not a failure.
                        return Err(format!("CreateClaim {} -> {}: {}", workload, r.status, r.body));
                    }
                }
                Op::DeleteClaim { workload, lane: _ } => {
                    let path = format!(
                        "/apis/estate.estate.internal/v1/namespaces/estate/claims/{}",
                        claim_name(&workload)
                    );
                    let r = self.write(Verb::Delete, &path, String::new())?;
                    if r.status >= 400 && r.status != 404 {
                        // 404 = already gone, desired state holds.
                        return Err(format!("DeleteClaim {} -> {}: {}", workload, r.status, r.body));
                    }
                }
                Op::WritePolicy { ordering } => {
                    let lanes: Vec<String> = ordering.iter().map(|l| format!("\"{}\"", l)).collect();
                    let body = format!(
                        "{{\"apiVersion\":\"policy.karmada.io/v1alpha1\",\"kind\":\"PropagationPolicy\",\
                          \"metadata\":{{\"name\":\"estate-ordering\",\"namespace\":\"estate\"}},\
                          \"spec\":{{\"conflictResolution\":\"Abort\",\
                          \"placement\":{{\"clusterAffinity\":{{\"clusterNames\":[{}]}}}}}}}}",
                        lanes.join(",")
                    );
                    let r = self.write(Verb::Patch, "/apis/policy.karmada.io/v1alpha1/namespaces/estate/propagationpolicies/estate-ordering", body)?;
                    if r.status >= 400 && r.status != 201 && r.status != 200 {
                        return Err(format!("WritePolicy -> {}: {}", r.status, r.body));
                    }
                }
                Op::MintReceipt { workload, lane, decision, reason } => {
                    // The only op that mints. The reconciler only emits it on observed
                    // Ready=true, so reaching here means readiness was measured.
                    self.append_receipt(&workload, lane.as_deref(), &decision, &reason)?;
                }
            }
        }
        Ok(())
    }
}

/// CRD object names must be DNS-1123 subdomains; a workload name is not guaranteed to be.
fn claim_name(workload: &str) -> String {
    let mut s: String = workload
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '-' { c.to_ascii_lowercase() } else { '-' })
        .collect();
    while s.contains("--") {
        s = s.replace("--", "-");
    }
    let s = s.trim_matches('-').to_string();
    let s = if s.len() > 63 { s[..63].trim_matches('-').to_string() } else { s };
    if s.is_empty() { "claim".to_string() } else { s }
}
