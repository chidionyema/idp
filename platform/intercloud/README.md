# intercloud
Placement core of the internal cloud (design 2026-11-09). Free lanes first; paid lanes
are last resort and require explicit Telegram approval (the approval receipt IS the gate);
reclaim hysteresis stops flapping; provider-churn drills emit GAP_VERDICT receipts when a
workload lacks a recovery home within policy. std-only, zero dependencies.
Run: cargo test
Reference proof (green, same logic): ../intercloud-ref/intercloud_ref.py
