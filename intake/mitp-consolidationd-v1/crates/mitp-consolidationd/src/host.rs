//! E7: host-survival guard, velocity-aware (control-barrier style, mirroring
//! crates/mitp-thinking-packs control.rs): a cycle never starts while the host
//! is in or approaching S4. Consolidation is discretionary work; the host is not.

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HostEnvelope {
    pub disk_free_mb: i64,
    /// Negative means shrinking (e.g. -120 MB/min burn).
    pub disk_rate_mb_per_min: i64,
    pub swap_used_mb: u64,
    pub load_1m: f64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CycleGate {
    Run,
    Skip(String),
}

pub const DISK_FLOOR_MB: i64 = 1500;
pub const SWAP_CEIL_MB: u64 = 1500;
pub const LOAD_CEIL: f64 = 8.0;
/// Forward-invariance horizon: refuse to start a cycle that could not finish
/// before the disk crosses the floor at the current burn rate.
pub const CYCLE_HORIZON_MIN: i64 = 15;

impl HostEnvelope {
    /// h(x) + gamma * h_dot >= 0 over the cycle horizon, plus static tripwires.
    pub fn gate(&self) -> CycleGate {
        if self.swap_used_mb > SWAP_CEIL_MB {
            return CycleGate::Skip(format!("swap {} MB > {} MB", self.swap_used_mb, SWAP_CEIL_MB));
        }
        if self.load_1m > LOAD_CEIL {
            return CycleGate::Skip(format!("load {:.2} > {}", self.load_1m, LOAD_CEIL));
        }
        if self.disk_free_mb < DISK_FLOOR_MB {
            return CycleGate::Skip(format!("disk {} MB < floor {} MB", self.disk_free_mb, DISK_FLOOR_MB));
        }
        // Velocity-aware: projected free at end of a worst-case cycle.
        let projected = self.disk_free_mb + self.disk_rate_mb_per_min.min(0) * CYCLE_HORIZON_MIN;
        if projected < DISK_FLOOR_MB {
            return CycleGate::Skip(format!(
                "projected disk {} MB at +{} min < floor (burn {} MB/min)",
                projected, CYCLE_HORIZON_MIN, self.disk_rate_mb_per_min
            ));
        }
        CycleGate::Run
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn healthy() -> HostEnvelope {
        HostEnvelope { disk_free_mb: 20_000, disk_rate_mb_per_min: 0, swap_used_mb: 0, load_1m: 1.0 }
    }

    #[test]
    fn healthy_host_runs() {
        assert_eq!(healthy().gate(), CycleGate::Run);
    }

    #[test]
    fn static_floor_skips() {
        let h = HostEnvelope { disk_free_mb: 1400, ..healthy() };
        assert!(matches!(h.gate(), CycleGate::Skip(_)));
    }

    #[test]
    fn swap_and_load_skip() {
        assert!(matches!(
            HostEnvelope { swap_used_mb: 1600, ..healthy() }.gate(),
            CycleGate::Skip(_)
        ));
        assert!(matches!(
            HostEnvelope { load_1m: 9.0, ..healthy() }.gate(),
            CycleGate::Skip(_)
        ));
    }

    #[test]
    fn momentum_triggers_before_cliff() {
        // 1600 MB free is ABOVE the static floor, but -120 MB/min over a 15-min
        // horizon projects -200 MB: the CBF margin is negative -> skip.
        let h = HostEnvelope { disk_free_mb: 1600, disk_rate_mb_per_min: -120, ..healthy() };
        match h.gate() {
            CycleGate::Skip(why) => assert!(why.contains("projected")),
            CycleGate::Run => panic!("momentum breach must skip before the cliff"),
        }
    }

    #[test]
    fn gentle_burn_above_floor_runs() {
        // 5000 MB free, -10 MB/min -> projected 4850 > floor.
        let h = HostEnvelope { disk_free_mb: 5000, disk_rate_mb_per_min: -10, ..healthy() };
        assert_eq!(h.gate(), CycleGate::Run);
    }
}
