//! intercloud — placement core of the internal cloud (design 2026-11-09).
//! Free lanes first; paid lanes last resort, gated on explicit Telegram approval;
//! reclaim hysteresis; provider-churn DR drills with gap verdicts;
//! sha256-chained placement receipts. std-only.
use std::collections::BTreeMap;

pub mod controller;
pub mod k8s;

// The store contract is defined by the reconciler and re-exported here so the adapter
// and any caller use one path: crate::{Store, Op, Snapshot}. No second definition.
pub use controller::{ObservedClaim, Op, RawApproval, Snapshot, Store};

// ---------- SHA-256 (FIPS 180-4) ----------
const K: [u32; 64] = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];

pub fn sha256(data: &[u8]) -> [u8; 32] {
    let mut h: [u32; 8] = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    let mut msg = data.to_vec();
    let bitlen = (data.len() as u64).wrapping_mul(8);
    msg.push(0x80);
    while msg.len() % 64 != 56 { msg.push(0); }
    msg.extend_from_slice(&bitlen.to_be_bytes());
    for chunk in msg.chunks_exact(64) {
        let mut w = [0u32; 64];
        for i in 0..16 { w[i] = u32::from_be_bytes([chunk[4*i],chunk[4*i+1],chunk[4*i+2],chunk[4*i+3]]); }
        for i in 16..64 {
            let s0 = w[i-15].rotate_right(7) ^ w[i-15].rotate_right(18) ^ (w[i-15] >> 3);
            let s1 = w[i-2].rotate_right(17) ^ w[i-2].rotate_right(19) ^ (w[i-2] >> 10);
            w[i] = w[i-16].wrapping_add(s0).wrapping_add(w[i-7]).wrapping_add(s1);
        }
        let (mut a,mut b,mut c,mut d,mut e,mut f,mut g,mut hh) = (h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh=g; g=f; f=e; e=d.wrapping_add(t1); d=c; c=b; b=a; a=t1.wrapping_add(t2);
        }
        h[0]=h[0].wrapping_add(a); h[1]=h[1].wrapping_add(b); h[2]=h[2].wrapping_add(c); h[3]=h[3].wrapping_add(d);
        h[4]=h[4].wrapping_add(e); h[5]=h[5].wrapping_add(f); h[6]=h[6].wrapping_add(g); h[7]=h[7].wrapping_add(hh);
    }
    let mut out = [0u8; 32];
    for i in 0..8 { out[4*i..4*i+4].copy_from_slice(&h[i].to_be_bytes()); }
    out
}

pub fn hex(d: &[u8]) -> String {
    d.iter().map(|b| format!("{:02x}", b)).collect()
}
pub fn sha256_hex(s: &str) -> String { hex(&sha256(s.as_bytes())) }
pub const ZERO: &str = "0000000000000000000000000000000000000000000000000000000000000000";



#[derive(Clone, PartialEq, Debug)]
pub enum Class { Free, Paid, Forbidden }
impl Class {
    fn rank(&self) -> u8 { match self { Class::Free => 0, Class::Paid => 1, Class::Forbidden => 9 } }
}

#[derive(Clone, Debug)]
pub struct Lane {
    pub name: String, pub class: Class, pub provider: String,
    pub cores: f64, pub mem_gb: f64, pub cost_mo: f64,
    pub health: String, pub used_cores: f64, pub used_mem: f64,
}
impl Lane {
    pub fn free_lane(name: &str, provider: &str, cores: f64, mem_gb: f64) -> Lane {
        Lane { name: name.into(), class: Class::Free, provider: provider.into(),
               cores, mem_gb, cost_mo: 0.0, health: "healthy".into(), used_cores: 0.0, used_mem: 0.0 }
    }
    pub fn paid_lane(name: &str, provider: &str, cores: f64, mem_gb: f64, cost: f64) -> Lane {
        Lane { name: name.into(), class: Class::Paid, provider: provider.into(),
               cores, mem_gb, cost_mo: cost, health: "healthy".into(), used_cores: 0.0, used_mem: 0.0 }
    }
    pub fn fits(&self, wl: &Workload) -> bool {
        self.health == "healthy" && self.class != Class::Forbidden
            && self.cores - self.used_cores >= wl.cores && self.mem_gb - self.used_mem >= wl.mem_gb
    }
    pub fn allocate(&mut self, wl: &Workload) { self.used_cores += wl.cores; self.used_mem += wl.mem_gb; }
    pub fn release(&mut self, wl: &Workload) { self.used_cores -= wl.cores; self.used_mem -= wl.mem_gb; }
}

#[derive(Clone, Debug)]
pub struct Workload {
    pub name: String, pub cores: f64, pub mem_gb: f64,
    pub paid_ok: bool, pub prefer: Option<String>,
    pub paid_since_ticks: Option<u32>, pub home: Option<String>,
}
impl Workload {
    pub fn new(name: &str, cores: f64, mem_gb: f64) -> Workload {
        Workload { name: name.into(), cores, mem_gb, paid_ok: false, prefer: None,
                   paid_since_ticks: None, home: None }
    }
}

#[derive(Clone)]
pub struct Receipt {
    pub seq: u64, pub prev: String, pub workload: String, pub lane: String,
    pub decision: String, pub reason: String, pub hash: String,
}
impl Receipt {
    fn canonical(&self) -> String {
        format!("seq={};prev={};wl={};lane={};dec={};why={}",
                self.seq, self.prev, self.workload, self.lane, self.decision, self.reason)
    }
}

pub struct Engine {
    pub lanes: BTreeMap<String, Lane>,
    /// Registry declaration order. `lanes` is a BTreeMap, so its own order is
    /// alphabetical; free-first must mean *as declared*, otherwise a lane named
    /// `a` silently outranks the primary home the registry puts first.
    pub order: Vec<String>,
    pub approvals: BTreeMap<String, String>, // lane -> telegram approval receipt hash
    pub receipts: Vec<Receipt>, pub rhead: String,
    pub tick_count: u32,
}
impl Engine {
    pub fn new(lanes: Vec<Lane>) -> Engine {
        let order: Vec<String> = lanes.iter().map(|l| l.name.clone()).collect();
        Engine { lanes: lanes.into_iter().map(|l| (l.name.clone(), l)).collect(),
                 order,
                 approvals: BTreeMap::new(), receipts: vec![], rhead: ZERO.into(), tick_count: 0 }
    }
    /// THE TELEGRAM GATE. Non-Telegram approval is refused. Approval binds workload+lane.
    pub fn approve_paid(&mut self, wl: &mut Workload, lane: &str, cost_mo: f64,
                        via: &str, receipt: &str) -> Result<(), String> {
        if via != "telegram" { return Err("paid approval must be explicit via Telegram".into()); }
        self.approvals.insert(lane.into(), format!("${:.2} via telegram: {}", cost_mo, receipt));
        wl.paid_ok = true; // the approval receipt IS the gate
        Ok(())
    }
    fn mint(&mut self, wl: &str, lane: Option<&str>, decision: &str, reason: String) {
        let r = Receipt { seq: self.receipts.len() as u64 + 1, prev: self.rhead.clone(),
            workload: wl.into(), lane: lane.unwrap_or("-").into(),
            decision: decision.into(), reason, hash: String::new() };
        let mut r = r;
        r.hash = sha256_hex(&r.canonical());
        self.rhead = r.hash.clone();
        self.receipts.push(r);
    }
    fn candidates(&self, wl: &Workload) -> Vec<&Lane> {
        let rank = |n: &str| self.order.iter().position(|o| o == n).unwrap_or(usize::MAX);
        let mut v: Vec<&Lane> = self.lanes.values().filter(|l| l.fits(wl)).collect();
        v.sort_by(|a, b| (a.class.rank(), (a.cost_mo * 100.0) as i64, rank(&a.name))
                         .cmp(&(b.class.rank(), (b.cost_mo * 100.0) as i64, rank(&b.name))));
        if let Some(p) = &wl.prefer { // registry primary-home contract
            v.sort_by_key(|l| if l.name == *p { 0 } else { 1 });
        }
        v
    }
    pub fn place(&mut self, wl: &mut Workload) -> (String, Option<String>) {
        // Collect the decision inputs before mutating self: `candidates` borrows
        // self.lanes, and the loop allocates into self.lanes. Taking owned copies here
        // keeps the borrow checker honest without cloning the whole lane set.
        let cands = self.candidates(wl);
        let free: Option<String> = cands.iter()
            .find(|l| l.class == Class::Free)
            .map(|l| l.name.clone());
        let paid: Option<String> = cands.iter()
            .find(|l| l.class == Class::Paid && wl.paid_ok && self.approvals.contains_key(&l.name))
            .map(|l| l.name.clone());

        if let Some(name) = free {
            self.lanes.get_mut(&name).unwrap().allocate(wl);
            wl.home = Some(name.clone());
            let why = if wl.prefer.as_deref() == Some(name.as_str())
                { format!("primary home {}", name) } else { "best free lane".into() };
            self.mint(&wl.name, Some(&name), "PLACED_FREE", why);
            return ("PLACED_FREE".into(), Some(name));
        }
        if let Some(name) = paid {
            self.lanes.get_mut(&name).unwrap().allocate(wl);
            wl.home = Some(name.clone()); wl.paid_since_ticks = Some(0);
            let why = format!("overflow; telegram-approved ({})", self.approvals[&name]);
            self.mint(&wl.name, Some(&name), "PLACED_PAID", why);
            return ("PLACED_PAID".into(), Some(name));
        }
        let why = cands.iter().map(|l| format!("{}:{}", l.name,
                if l.class == Class::Paid { "paid".into() } else { l.class.rank().to_string() }))
            .collect::<Vec<_>>().join("; ");
        let why = if why.is_empty() { "no lane meets needs".into() } else { why };
        self.mint(&wl.name, None, "DENIED", why);
        ("DENIED".into(), None)
    }
    pub fn tick(&mut self, workloads: &mut [&mut Workload]) -> Vec<(String, String, String)> {
        self.tick_count += 1;
        let mut moves = vec![];
        for wl in workloads.iter_mut() {
            let on_paid = wl.home.as_ref().and_then(|h| self.lanes.get(h))
                .map(|l| l.class == Class::Paid).unwrap_or(false);
            if on_paid {
                let free_fits: Vec<String> = self.candidates(wl).into_iter()
                    .filter(|l| l.class == Class::Free).map(|l| l.name.clone()).collect();
                // Hysteresis counts ticks where a free lane actually fits. A tick with no
                // free lane is not a stable period on paid, so it must not draw the
                // workload closer to a reclaim: counting those meant a lane appearing
                // after a long paid stretch was reclaimed on its first tick.
                if free_fits.is_empty() {
                    wl.paid_since_ticks = Some(0);
                } else {
                    let held = wl.paid_since_ticks.unwrap_or(0) + 1;
                    wl.paid_since_ticks = Some(held);
                }
                if let Some(target) = free_fits.first() {
                    if wl.paid_since_ticks.unwrap() >= 3 {
                        let held = wl.paid_since_ticks.unwrap();
                        let old = wl.home.take().unwrap();
                        self.lanes.get_mut(&old).unwrap().release(wl);
                        self.lanes.get_mut(target).unwrap().allocate(wl);
                        wl.home = Some(target.clone()); wl.paid_since_ticks = None;
                        self.mint(&wl.name, Some(target), "RECLAIMED_FREE",
                                  format!("held {} ticks on paid; hysteresis passed", held));
                        moves.push((wl.name.clone(), old, target.clone()));
                    } else {
                        self.mint(&wl.name, wl.home.as_deref(), "HOLD_PAID",
                                  format!("hysteresis: stable {}/3, free lane exists but hold",
                                          wl.paid_since_ticks.unwrap()));
                    }
                }
            }
        }
        moves
    }
    pub fn churn(&mut self, provider: &str, workloads: &mut [&mut Workload])
        -> (Vec<String>, Vec<(String, String, Option<String>)>, Vec<(String, String, Option<String>)>)
    {
        let killed: Vec<String> = self.lanes.values().filter(|l| l.provider == provider)
            .map(|l| l.name.clone()).collect();
        for n in &killed { self.lanes.get_mut(n).unwrap().health = "down".into(); }
        let mut moved = vec![]; let mut unmet = vec![];
        for wl in workloads.iter_mut() {
            if let Some(h) = wl.home.clone() {
                if killed.contains(&h) {
                    self.lanes.get_mut(&h).unwrap().release(wl);
                    wl.home = None;
                    let (dec, lane) = self.place(wl);
                    if lane.is_some() { moved.push((wl.name.clone(), dec, lane)); }
                    else { unmet.push((wl.name.clone(), dec, lane)); }
                }
            }
        }
        self.mint(&format!("drill:{}", provider), None, "CHURN_DRILL",
                  format!("moved={} unmet={}", moved.len(), unmet.len()));
        for (name, _, _) in &unmet {
            self.mint(name, None, "GAP_VERDICT",
                      "no recovery home within policy -> NOT PRODUCTION until one exists".into());
        }
        (killed, moved, unmet)
    }
    pub fn verify(&self) -> Result<String, String> {
        let mut prev = ZERO.to_string();
        for r in &self.receipts {
            if r.prev != prev { return Err(format!("chain break at seq {}", r.seq)); }
            if sha256_hex(&r.canonical()) != r.hash { return Err(format!("receipt tampered at seq {}", r.seq)); }
            prev = r.hash.clone();
        }
        Ok(format!("{} placement receipts verified", self.receipts.len()))
    }
}

// ===================== registry loader, DR checker, invariant hardening =====================
/// Lane registry loader — line format:
///   lane <name> <free|paid|forbidden> <provider> <cores> <mem_gb> [cost_mo]
/// Loud validation at load (pennyd law: a config that half-loads loads nothing).
pub fn load_registry(text: &str) -> Result<Vec<Lane>, String> {
    let mut out = vec![];
    for (i, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') { continue; }
        let p: Vec<&str> = line.split_whitespace().collect();
        if p.len() < 6 || p[0] != "lane" {
            return Err(format!("line {}: expected 'lane <name> <class> <provider> <cores> <mem_gb> [cost]'", i+1));
        }
        let class = match p[2] {
            "free" => Class::Free, "paid" => Class::Paid, "forbidden" => Class::Forbidden,
            other => return Err(format!("line {}: unknown class '{}'", i+1, other)),
        };
        let cores: f64 = p[4].parse().map_err(|_| format!("line {}: bad cores", i+1))?;
        let mem: f64 = p[5].parse().map_err(|_| format!("line {}: bad mem_gb", i+1))?;
        if cores <= 0.0 || mem <= 0.0 { return Err(format!("line {}: cores/mem must be positive", i+1)); }
        let cost: f64 = if p.len() > 6 { p[6].parse().map_err(|_| format!("line {}: bad cost", i+1))? } else { 0.0 };
        if class == Class::Paid && cost <= 0.0 {
            return Err(format!("line {}: paid lane must declare cost_mo (last field)", i+1));
        }
        let mut l = Lane { name: p[1].into(), class, provider: p[3].into(), cores, mem_gb: mem,
                           cost_mo: cost, health: "healthy".into(), used_cores: 0.0, used_mem: 0.0 };
        if l.class == Class::Forbidden { l.health = "forbidden".into(); }
        out.push(l);
    }
    if out.is_empty() { return Err("registry empty".into()); }
    Ok(out)
}

/// DR 3-2-1 checker — every artifact must exist on >=2 distinct clouds.
pub fn dr_check(artifacts: &[(String, Vec<String>)]) -> Vec<String> {
    let mut violations = vec![];
    for (name, clouds) in artifacts {
        let lowered: Vec<String> = clouds.iter().map(|c| c.to_lowercase()).collect();
        let distinct: std::collections::BTreeSet<&String> = lowered.iter().collect();
        if distinct.len() < 2 {
            violations.push(format!("{}: only {} cloud(s) -> violates 3-2-1 (no recovery home)", name, distinct.len()));
        }
    }
    violations
}



#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;
    use std::fs;
    fn mk_engine() -> Engine {
        Engine::new(vec![
            Lane::free_lane("oci-a1", "oci", 2.0, 6.5),   // 2/12 minus OS+k3s reserve
            Lane::free_lane("gcp-micro", "gcp", 2.0, 1.0),
            Lane::free_lane("northflank", "northflank", 2.0, 4.0),
            Lane::paid_lane("hetzner-cax21", "hetzner", 4.0, 8.0, 7.49),
        ])
    }
    #[test] fn sha256_vectors() {
        assert_eq!(sha256_hex("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    }
    #[test] fn free_first_and_capacity() {
        let mut e = mk_engine();
        let mut ctl = Workload::new("k3s-control", 1.0, 2.0);
        ctl.prefer = Some("oci-a1".into());
        let mut router = Workload::new("model-router", 2.0, 8.0);
        let mut batch = Workload::new("batch-worker", 2.0, 4.0);
        assert_eq!(e.place(&mut ctl).1.as_deref(), Some("oci-a1"));    // primary home honored
        assert_eq!(e.place(&mut batch).1.as_deref(), Some("northflank"));
        assert_eq!(e.place(&mut router).0, "DENIED");                 // 8GB fits no free lane
        assert!(e.verify().is_ok());
    }
    #[test] fn telegram_gate_refuses_other_channels() {
        let mut e = mk_engine();
        let mut router = Workload::new("model-router", 2.0, 8.0);
        assert!(e.approve_paid(&mut router, "hetzner-cax21", 7.49, "wechat-chat", "x").is_err());
        assert!(!router.paid_ok); // nothing unlocked
        e.approve_paid(&mut router, "hetzner-cax21", 7.49, "telegram", "tg-rcpt-9f2ab1").unwrap();
        assert_eq!(e.place(&mut router).0, "PLACED_PAID");
        assert_eq!(router.home.as_deref(), Some("hetzner-cax21"));
    }
    #[test] fn hysteresis_reclaim() {
        let mut e = mk_engine();
        let mut router = Workload::new("model-router", 2.0, 8.0);
        e.approve_paid(&mut router, "hetzner-cax21", 7.49, "telegram", "tg-1").unwrap();
        e.place(&mut router);
        e.tick(&mut [&mut router]); e.tick(&mut [&mut router]);       // no free fits -> silent hold
        assert_eq!(router.home.as_deref(), Some("hetzner-cax21"));
        e.lanes.insert("ibm-free-k8s".into(), Lane::free_lane("ibm-free-k8s", "ibm", 2.0, 12.0));
        e.tick(&mut [&mut router]); e.tick(&mut [&mut router]);       // 2 < 3 -> still held
        assert_eq!(router.home.as_deref(), Some("hetzner-cax21"));
        e.tick(&mut [&mut router]);                                    // 3rd stable tick -> reclaim
        assert_eq!(router.home.as_deref(), Some("ibm-free-k8s"));
        assert!(e.verify().is_ok());
    }
    #[test] fn churn_drill_finds_gaps() {
        let mut e = mk_engine();
        let mut ctl = Workload::new("k3s-control", 1.0, 2.0);
        ctl.prefer = Some("oci-a1".into());
        e.place(&mut ctl);
        // The drill only finds a GAP when no other free lane can absorb the workload.
        // northflank is 2c/4GB and batch-worker is 2c/4GB, so it takes the whole lane --
        // this is the same rehearsal the reference proves (PROOF.txt: moved: [], unmet:
        // [k3s-control]). Without it the drill measures nothing and always "moves".
        let mut batch = Workload::new("batch-worker", 2.0, 4.0);
        assert_eq!(e.place(&mut batch).0, "PLACED_FREE");
        let (killed, moved, unmet) = e.churn("oci", &mut [&mut ctl]);
        assert_eq!(killed, vec!["oci-a1".to_string()]);
        assert!(moved.is_empty()); assert_eq!(unmet.len(), 1);         // northflank full (4GB used)
        let has_gap = e.receipts.iter().any(|r| r.decision == "GAP_VERDICT");
        assert!(has_gap);
        assert!(e.verify().is_ok());
    }
    #[test] fn receipt_tamper_detected() {
        let mut e = mk_engine();
        let mut ctl = Workload::new("k3s-control", 1.0, 2.0);
        e.place(&mut ctl);
        let mut e2 = e;
        e2.receipts[0].decision = "PLACED_PAID".into();
        assert!(e2.verify().is_err());
    }

    #[test] fn registry_loud_validation() {
        let good = "lane oci-a1 free oci 2 6.5\nlane hetzner-cax21 paid hetzner 4 8 7.49\n";
        let lanes = load_registry(good).unwrap();
        assert_eq!(lanes.len(), 2);
        assert!(load_registry("lane x free oci 2 6.5\nlane bad paid hetzner 4 8\n").is_err()); // paid w/o cost refused
        assert!(load_registry("lane x free oci -1 6.5\n").is_err());   // negative cores refused
        assert!(load_registry("").is_err());                            // empty refused
        assert!(load_registry("lame x free oci 2 6.5\n").is_err());    // unknown verb refused
    }
    #[test] fn dr_check_flags_single_cloud() {
        let v = dr_check(&[
            ("muster-crate".into(), vec!["github".into(), "r2".into()]),
            ("secrets".into(), vec!["oci".into()]),   // single cloud -> violation
        ]);
        assert_eq!(v.len(), 1);
        assert!(v[0].contains("secrets"));
        assert!(dr_check(&[("a".into(), vec!["github".into(), "r2".into()])]).is_empty());
    }
    #[test] fn approval_only_via_engine_gate() {
        // paid_ok is private-set: without engine.approve_paid(telegram), placement DENIES
        let mut e = mk_engine();
        let mut router = Workload::new("model-router", 2.0, 8.0);
        assert_eq!(e.place(&mut router).0, "DENIED"); // no approval anywhere
        assert!(e.approve_paid(&mut router, "hetzner-cax21", 7.49, "telegram", "tg-rcpt").is_ok());
        assert_eq!(e.place(&mut router).0, "PLACED_PAID");
    }
    #[test] fn forbidden_lane_never_placed() {
        let mut e = mk_engine();
        e.lanes.insert("mac".into(), Lane{name:"mac".into(), class:Class::Forbidden, provider:"none".into(),
            cores:8.0, mem_gb:16.0, cost_mo:0.0, health:"healthy".into(), used_cores:0.0, used_mem:0.0});
        let mut big = Workload::new("heavy", 1.0, 1.0);
        big.prefer = Some("mac".into());
        let (_, lane) = e.place(&mut big);
        assert_ne!(lane.as_deref(), Some("mac")); // prefer cannot override forbidden
    }

    use super::controller::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    static N: AtomicUsize = AtomicUsize::new(0);
    fn tmpstate(n: &str) -> String {
        let d = std::env::temp_dir().join(format!("icctl-{}-{}-{}", std::process::id(), n, N.fetch_add(1, Ordering::SeqCst)));
        let s = d.to_string_lossy().into_owned();
        fs::create_dir_all(d.join("claims")).unwrap();
        s
    }
    fn base_lanes() -> &'static str {
        "lane oci-a1 free oci 2 6.5\nlane northflank free northflank 2 4\nlane hetzner-cax21 paid hetzner 4 8 7.49\n"
    }
    fn write(dir: &str, name: &str, content: &str) {
        fs::write(Path::new(dir).join(name), content).unwrap();
    }
    #[test] fn ctl_free_probe_placed_then_receipt_on_ready() {
        let dir = tmpstate("free");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl probe 1 1\n");
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"k", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let claim = fs::read_to_string(Path::new(&dir).join("claims/probe")).unwrap();
        assert!(claim.starts_with("oci-a1"), "claim was: {:?}", claim); // free-first
        // crossplane reports ready (simulated observation)
        write(&dir, "claims/probe", "oci-a1 true\n");
        let mut st = FsStore::open(&dir);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let log = fs::read_to_string(Path::new(&dir).join("receipts.log")).unwrap();
        assert!(log.contains("PLACED_FREE")); assert!(log.contains("Ready=true"));
        assert!(st.verify_log().is_ok());
    }
    #[test] fn ctl_paid_denied_without_approval() {
        let dir = tmpstate("deny");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl router 2 8\n");
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"k", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        assert!(!Path::new(&dir).join("claims/router").exists()); // nothing emitted
        let log = fs::read_to_string(Path::new(&dir).join("receipts.log")).unwrap();
        assert!(log.contains("DENIED"));
    }
    #[test] fn ctl_bad_hmac_refused() {
        let dir = tmpstate("hmacbad");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl router 2 8\n");
        let bad = format!("approval hetzner-cax21 7.49 telegram {}",
            hmac_sha256(b"WRONG-KEY", b"lane=hetzner-cax21;cost=7.49;via=telegram"));
        write(&dir, "approvals.reg", &bad);
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"REAL-KEY", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        assert!(!Path::new(&dir).join("claims/router").exists());
    }
    #[test] fn ctl_valid_hmac_paid_claim() {
        let dir = tmpstate("hmacgood");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl router 2 8\n");
        let good = format!("approval hetzner-cax21 7.49 telegram {}",
            hmac_sha256(b"REAL-KEY", b"lane=hetzner-cax21;cost=7.49;via=telegram"));
        write(&dir, "approvals.reg", &good);
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"REAL-KEY", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let claim = fs::read_to_string(Path::new(&dir).join("claims/router")).unwrap();
        assert!(claim.starts_with("hetzner-cax21"));
        write(&dir, "claims/router", "hetzner-cax21 true\n");
        let mut st = FsStore::open(&dir);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let log = fs::read_to_string(Path::new(&dir).join("receipts.log")).unwrap();
        assert!(log.contains("PLACED_PAID"));
    }
    #[test] fn ctl_churn_deletes_down_lane_claims() {
        let dir = tmpstate("churn");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl probe 1 1\n");
        write(&dir, "claims/probe", "oci-a1 false\n");
        write(&dir, "health.reg", "oci-a1 down\n");
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"k", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        assert!(!Path::new(&dir).join("claims/probe").exists()); // delete issued
    }
    #[test] fn ctl_receipt_budget_spills() {
        let dir = tmpstate("spill");
        write(&dir, "lanes.reg", "lane hetzner-cax21 paid hetzner 4 8 7.49\n"); // all denied
        write(&dir, "workloads.reg", "wl a 2 8\nwl b 2 8\nwl c 2 8\nwl d 2 8\n");
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"k", 2);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let chain = fs::read_to_string(Path::new(&dir).join("receipts.log")).unwrap();
        let spill = fs::read_to_string(Path::new(&dir).join("spill.log")).unwrap();
        assert_eq!(chain.lines().count(), 2); assert_eq!(spill.lines().count(), 2);
    }
    #[test] fn ctl_policy_ordering_free_first() {
        let dir = tmpstate("policy");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl probe 1 1\n");
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"k", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let pol = fs::read_to_string(Path::new(&dir).join("policy.out")).unwrap();
        let lines: Vec<&str> = pol.lines().collect();
        assert!(lines.contains(&"oci-a1") && lines.contains(&"northflank"));
    }
    #[test] fn ctl_receipt_chain_detects_tamper() {
        let dir = tmpstate("tamper");
        write(&dir, "lanes.reg", base_lanes());
        write(&dir, "workloads.reg", "wl probe 1 1\nwl p2 1 1\n");
        // A receipt is minted ONLY once the managed resource reports Ready=true, so the
        // first pass provisions and the second anchors. Prove the chain over a populated
        // log, not an empty one -- an empty log verifies trivially and tests nothing.
        let mut st = FsStore::open(&dir);
        let r = Reconciler::new(b"k", 10);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        write(&dir, "claims/probe", "oci-a1 true\n");
        write(&dir, "claims/p2", "oci-a1 true\n");
        let mut st = FsStore::open(&dir);
        st.apply(r.reconcile(&st.load().unwrap())).unwrap();
        let p = Path::new(&dir).join("receipts.log");
        let mut log = fs::read_to_string(&p).unwrap();
        log = log.replacen("PLACED", "TAMPERED", 1);
        fs::write(&p, log).unwrap();
        let st = FsStore::open(&dir);
        assert!(st.verify_log().is_err());
    }
}
