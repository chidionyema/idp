//! controller: the reconcile loop (Piece 1). Split out of lib.rs so the module
//! declaration `pub mod controller;` resolves; the bundle shipped the code inline.  
// ===================== controller: reconcile loop (Piece 1) =====================
use crate::{hex, load_registry, sha256, sha256_hex, Class, Engine, Lane, Workload, ZERO};
// Decides from desired state, emits ops, mints receipts ONLY on observed readiness.
// std-only. FsStore is a complete adapter (runs today); the K8s adapter implements
// the same Store trait against Lane/Approval CRs + Crossplane Claims (see controller/README.md).

#[derive(Clone, Debug)]
pub struct Snapshot {
    pub lanes: Vec<Lane>, // health may be "healthy"|"down"
    pub workloads: Vec<Workload>,
    pub approvals: Vec<RawApproval>,
    pub claims: Vec<ObservedClaim>, // last observed Crossplane state
}
#[derive(Clone, Debug)]
pub struct RawApproval {
    pub lane: String,
    pub cost_mo: f64,
    pub via: String,
    pub sig: String,
}
#[derive(Clone, Debug)]
pub struct ObservedClaim {
    pub workload: String,
    pub lane: String,
    pub ready: bool,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Op {
    CreateClaim {
        workload: String,
        lane: String,
    },
    DeleteClaim {
        workload: String,
        lane: String,
    },
    WritePolicy {
        ordering: Vec<String>,
    },
    MintReceipt {
        workload: String,
        lane: Option<String>,
        decision: String,
        reason: String,
    },
}

pub trait Store {
    fn load(&self) -> Result<Snapshot, String>;
    fn apply(&mut self, ops: Vec<Op>) -> Result<(), String>;
}

/// HMAC-SHA256 approval signature (std-only; spooler key distributed via estate-secrets).
pub fn hmac_sha256(key: &[u8], msg: &[u8]) -> String {
    let mut k = [0u8; 64];
    for (i, b) in key.iter().take(64).enumerate() {
        k[i] = *b;
    }
    let (mut ipad, mut opad) = ([0x36u8; 64], [0x5cu8; 64]);
    for i in 0..64 {
        ipad[i] ^= k[i];
        opad[i] ^= k[i];
    }
    let mut inner = ipad.to_vec();
    inner.extend_from_slice(msg);
    let ih = sha256(&inner);
    let mut outer = opad.to_vec();
    outer.extend_from_slice(&ih);
    hex(&sha256(&outer))
}
pub fn approval_canonical(lane: &str, cost: f64, via: &str) -> String {
    format!("lane={};cost={:.2};via={}", lane, cost, via)
}

pub struct Reconciler {
    pub spooler_key: Vec<u8>,
    pub receipt_cap: usize,
}
impl Reconciler {
    pub fn new(key: &[u8], receipt_cap: usize) -> Reconciler {
        Reconciler {
            spooler_key: key.to_vec(),
            receipt_cap,
        }
    }
    fn approval_valid(&self, a: &RawApproval) -> bool {
        if a.via != "telegram" {
            return false;
        }
        let expect = hmac_sha256(
            &self.spooler_key,
            approval_canonical(&a.lane, a.cost_mo, &a.via).as_bytes(),
        );
        expect == a.sig
    }
    pub fn reconcile(&self, snap: &Snapshot) -> Vec<Op> {
        let mut ops = vec![];
        let mut engine = Engine::new(snap.lanes.clone());
        let mut budget = self.receipt_cap;
        let spend = |ops: &mut Vec<Op>,
                     budget: &mut usize,
                     wl: &str,
                     lane: Option<&str>,
                     dec: &str,
                     why: String| {
            if *budget > 0 {
                *budget -= 1;
                ops.push(Op::MintReceipt {
                    workload: wl.into(),
                    lane: lane.map(|s| s.into()),
                    decision: dec.into(),
                    reason: why,
                });
            } else {
                ops.push(Op::MintReceipt {
                    workload: wl.into(),
                    lane: None,
                    decision: "RECEIPT_SPILL".into(),
                    reason: "budget exceeded; overflow logged to spill".into(),
                });
            }
        };
        for a in &snap.approvals {
            if self.approval_valid(a) {
                engine.approvals.insert(
                    a.lane.clone(),
                    format!("${:.2} via telegram: {}", a.cost_mo, &a.sig[..12]),
                );
            }
        }
        let mut wls: Vec<Workload> = snap
            .workloads
            .iter()
            .map(|w| Workload {
                name: w.name.clone(),
                cores: w.cores,
                mem_gb: w.mem_gb,
                // A valid Telegram approval IS the gate; Engine::approve_paid sets this same
                // flag. Building workloads with paid_ok:false and never lifting it meant a
                // correctly-approved overflow was silently DENIED forever. paid_ok is
                // per-workload, but an approval is per-lane, so it is lifted for a workload
                // when any approved lane could hold it -- place() still re-checks
                // approvals.contains_key(lane) before spending.
                paid_ok: !engine.approvals.is_empty(),
                prefer: w.prefer.clone(),
                paid_since_ticks: None,
                home: None,
            })
            .collect();
        for wl in wls.iter_mut() {
            // seed home from observed claims (reality, not wish)
            if let Some(c) = snap.claims.iter().find(|c| c.workload == wl.name) {
                wl.home = Some(c.lane.clone());
            }
            let (decision, lane) = engine.place(wl);
            match (decision.as_str(), lane) {
                ("PLACED_FREE" | "PLACED_PAID", Some(l)) => {
                    let observed = snap
                        .claims
                        .iter()
                        .find(|c| c.workload == wl.name && c.lane == l);
                    match observed {
                        Some(c) if c.ready => spend(
                            &mut ops,
                            &mut budget,
                            &wl.name,
                            Some(&l),
                            &decision,
                            "observed Ready=true on managed resource; receipt anchored".into(),
                        ),
                        Some(_) => {} // provisioned, awaiting readiness; no new ops
                        None => {
                            ops.push(Op::CreateClaim {
                                workload: wl.name.clone(),
                                lane: l.clone(),
                            });
                            let ordering: Vec<String> = engine
                                .candidates(wl)
                                .into_iter()
                                .filter(|x| x.class == Class::Free)
                                .map(|x| x.name.clone())
                                .collect();
                            if !ordering.is_empty() {
                                ops.push(Op::WritePolicy { ordering });
                            }
                        }
                    }
                }
                ("DENIED", _) => spend(
                    &mut ops,
                    &mut budget,
                    &wl.name,
                    None,
                    "DENIED",
                    "no free lane fits; paid requires valid Telegram approval (HMAC)".into(),
                ),
                _ => {}
            }
        }
        // churn: observed claims whose lane is now down -> delete + re-place on next pass
        for c in &snap.claims {
            let lane_down = snap
                .lanes
                .iter()
                .any(|l| l.name == c.lane && l.health != "healthy");
            if lane_down {
                ops.push(Op::DeleteClaim {
                    workload: c.workload.clone(),
                    lane: c.lane.clone(),
                });
            }
        }
        ops
    }
}

// ---- FsStore: complete file-system adapter (the seam's working implementation) ----
use std::fs;
use std::path::PathBuf;

pub struct FsStore {
    pub dir: PathBuf,
    pub head: String,
}
impl FsStore {
    pub fn open(dir: &str) -> FsStore {
        let p = PathBuf::from(dir);
        fs::create_dir_all(p.join("claims")).ok();
        let head = fs::read_to_string(p.join("receipts.log"))
            .ok()
            .and_then(|s| {
                s.lines()
                    .filter(|l| !l.trim().is_empty())
                    .next_back()
                    .map(|l| l.split(' ').next().unwrap_or(ZERO).to_string())
            })
            .unwrap_or_else(|| ZERO.to_string());
        FsStore { dir: p, head }
    }
    fn write_receipt(&mut self, wl: &str, lane: Option<&str>, dec: &str, why: &str, spill: bool) {
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
        let file = if spill { "spill.log" } else { "receipts.log" };
        use std::io::Write;
        let mut f = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(self.dir.join(file))
            .unwrap();
        writeln!(f, "{}", line).unwrap();
        if !spill {
            self.head = h;
        }
    }
    pub fn verify_log(&self) -> Result<String, String> {
        let text = fs::read_to_string(self.dir.join("receipts.log")).map_err(|e| e.to_string())?;
        let mut prev = ZERO.to_string();
        let mut n = 0;
        for l in text.lines().filter(|l| !l.trim().is_empty()) {
            let mut parts = l.splitn(2, ' ');
            let h = parts.next().unwrap();
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
        Ok(format!("{} receipts verified", n))
    }
}
impl Store for FsStore {
    fn load(&self) -> Result<Snapshot, String> {
        let lanes_txt = fs::read_to_string(self.dir.join("lanes.reg"))
            .map_err(|_| "lanes.reg missing".to_string())?;
        let mut lanes = load_registry(&lanes_txt)?;
        // optional health overrides: line "lane <name> ... " 8th field handled in loader? apply overrides file
        if let Ok(h) = fs::read_to_string(self.dir.join("health.reg")) {
            for line in h.lines() {
                let p: Vec<&str> = line.split_whitespace().collect();
                if p.len() == 2 {
                    if let Some(l) = lanes.iter_mut().find(|l| l.name == p[0]) {
                        l.health = p[1].into();
                    }
                }
            }
        }
        let mut workloads = vec![];
        if let Ok(w) = fs::read_to_string(self.dir.join("workloads.reg")) {
            for (i, line) in w.lines().enumerate() {
                let t = line.trim();
                if t.is_empty() || t.starts_with('#') {
                    continue;
                }
                let p: Vec<&str> = t.split_whitespace().collect();
                if p.len() < 4 || p[0] != "wl" {
                    return Err(format!("workloads.reg line {}: bad format", i + 1));
                }
                workloads.push(Workload {
                    name: p[1].into(),
                    cores: p[2].parse().map_err(|_| "bad cores")?,
                    mem_gb: p[3].parse().map_err(|_| "bad mem")?,
                    paid_ok: false,
                    prefer: p.get(4).map(|s| s.to_string()),
                    paid_since_ticks: None,
                    home: None,
                });
            }
        }
        let mut approvals = vec![];
        if let Ok(a) = fs::read_to_string(self.dir.join("approvals.reg")) {
            for line in a.lines() {
                let p: Vec<&str> = line.split_whitespace().collect();
                if p.len() == 5 && p[0] == "approval" {
                    approvals.push(RawApproval {
                        lane: p[1].into(),
                        cost_mo: p[2].parse().unwrap_or(0.0),
                        via: p[3].into(),
                        sig: p[4].into(),
                    });
                }
            }
        }
        let mut claims = vec![];
        let cd = self.dir.join("claims");
        if let Ok(rd) = fs::read_dir(&cd) {
            for e in rd.flatten() {
                let content = fs::read_to_string(e.path()).unwrap_or_default();
                let p: Vec<&str> = content.split_whitespace().collect();
                if p.len() == 2 {
                    claims.push(ObservedClaim {
                        workload: e.file_name().to_string_lossy().into(),
                        lane: p[0].into(),
                        ready: p[1] == "true",
                    });
                }
            }
        }
        Ok(Snapshot {
            lanes,
            workloads,
            approvals,
            claims,
        })
    }
    fn apply(&mut self, ops: Vec<Op>) -> Result<(), String> {
        for op in ops {
            match op {
                Op::CreateClaim { workload, lane } => {
                    fs::write(
                        self.dir.join("claims").join(&workload),
                        format!("{} false", lane),
                    )
                    .map_err(|e| e.to_string())?;
                }
                Op::DeleteClaim { workload, lane: _ } => {
                    fs::remove_file(self.dir.join("claims").join(&workload)).ok();
                }
                Op::WritePolicy { ordering } => {
                    fs::write(self.dir.join("policy.out"), ordering.join("\n"))
                        .map_err(|e| e.to_string())?;
                }
                Op::MintReceipt {
                    workload,
                    lane,
                    decision,
                    reason,
                } => {
                    self.write_receipt(
                        &workload,
                        lane.as_deref(),
                        &decision,
                        &reason,
                        decision == "RECEIPT_SPILL",
                    );
                }
            }
        }
        Ok(())
    }
}
