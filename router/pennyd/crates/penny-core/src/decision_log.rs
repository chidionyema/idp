//! Hash-chained decision log — the same construction as the Tempo estate
//! log: any edit, deletion, reorder, or insertion is detectable on verify().
//! Every allow/refuse/route/cache-hit decision lands here, so founder
//! visibility and legal replay come free.

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

pub fn record_hash(seq: u64, ts: u64, prev_hash: &str, decision: &Value) -> String {
    let canon = serde_json::json!({ "seq": seq, "ts": ts, "prev_hash": prev_hash, "decision": decision });
    let mut h = Sha256::new();
    h.update(canon.to_string().as_bytes());
    hex::encode(h.finalize())
}

/// Validate one line against the running chain head. Returns (seq, hash) when valid.
fn parsed_ok(line: &str, head: &str, expect_seq: u64) -> Option<(u64, String)> {
    let rec: Value = serde_json::from_str(line).ok()?;
    let rseq = rec["seq"].as_u64()?;
    let ts = rec["ts"].as_u64()?;
    let prev = rec["prev_hash"].as_str()?;
    let h = rec["hash"].as_str()?;
    if record_hash(rseq, ts, prev, &rec["decision"]) == h && prev == head && rseq == expect_seq {
        Some((rseq, h.to_string()))
    } else {
        None
    }
}

pub struct DecisionLog {
    path: PathBuf,
    file: File,
    pub seq: u64,
    pub head: String,
    /// P1-5: first tampered/corrupt row observed at open. NEVER truncated
    /// away — the chain keeps the invalid region visible forever, and the
    /// break is reported by /health instead of being silently erased.
    pub tampered_at: Option<u64>,
}

impl DecisionLog {
    pub fn open(path: impl AsRef<Path>) -> io::Result<Self> {
        let path = path.as_ref().to_path_buf();
        let mut seq = 0u64;
        let mut head = "0".repeat(64);
        let mut tampered_at: Option<u64> = None;
        if let Ok(f) = File::open(&path) {
            let mut expect_seq = 1u64;
            for line in BufReader::new(f).lines() {
                let line = line?;
                if line.trim().is_empty() {
                    continue;
                }
                let valid = parsed_ok(&line, &head, expect_seq);
                if let Some((rseq, h)) = valid {
                    seq = rseq;
                    head = h;
                    expect_seq = seq + 1;
                } else if tampered_at.is_none() {
                    // P1-5: keep the file byte-for-byte intact; mark the break.
                    // head/seq stay at the last VERIFIED prefix; verify() and
                    // /health report the break forever — never erased.
                    tampered_at = Some(expect_seq);
                }
            }
        }
        let file = OpenOptions::new().create(true).append(true).open(&path)?;
        Ok(Self { path, file, seq, head, tampered_at })
    }

    fn write_line(&mut self, line: &str) -> io::Result<()> {
        writeln!(self.file, "{line}")?;
        self.file.sync_all()
    }

    pub fn append(&mut self, ts: u64, decision: &Value) -> io::Result<()> {
        let seq = self.seq + 1;
        let hash = record_hash(seq, ts, &self.head, decision);
        let line = json!({
            "seq": seq, "ts": ts, "decision": decision,
            "prev_hash": self.head, "hash": hash,
        })
        .to_string();
        if let Err(e) = self.write_line(&line) {
            // log rotated or deleted under us: reopen once and retry (F-LOG-4)
            self.file = OpenOptions::new().create(true).append(true).open(&self.path)?;
            self.write_line(&line).map_err(|e2| {
                io::Error::new(e2.kind(), format!("append failed ({e}); reopen failed: {e2}"))
            })?;
        }
        self.seq = seq;
        self.head = hash;
        Ok(())
    }

    pub fn verify(&self) -> io::Result<Option<u64>> {
        let f = File::open(&self.path)?;
        let mut prev = "0".repeat(64);
        let mut expect_seq = 1u64;
        for line in BufReader::new(f).lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            let rec: Value = match serde_json::from_str(&line) {
                Ok(v) => v,
                Err(_) => return Ok(Some(expect_seq)),
            };
            let (Some(seq), Some(ts), Some(p), Some(h)) = (
                rec["seq"].as_u64(),
                rec["ts"].as_u64(),
                rec["prev_hash"].as_str(),
                rec["hash"].as_str(),
            ) else { return Ok(Some(expect_seq)) };
            if p != prev || record_hash(seq, ts, p, &rec["decision"]) != h || seq != expect_seq {
                return Ok(Some(expect_seq));
            }
            prev = h.to_string();
            expect_seq += 1;
        }
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn tmp() -> PathBuf {
        let p = std::env::temp_dir().join(format!("penny-log-test-{}", std::process::id()));
        let _ = std::fs::remove_file(&p);
        p
    }

    #[test]
    fn append_and_verify() {
        let p = tmp();
        let mut log = DecisionLog::open(&p).unwrap();
        log.append(1, &json!({"decision": "route"})).unwrap();
        log.append(2, &json!({"decision": "cache_hit"})).unwrap();
        assert!(log.verify().unwrap().is_none());
        let _ = std::fs::remove_file(&p);
    }

    #[test]
    fn tamper_detected_with_seq() {
        let p = tmp();
        let mut log = DecisionLog::open(&p).unwrap();
        for i in 1..=3 {
            log.append(i, &json!({"i": i})).unwrap();
        }
        let mut lines: Vec<String> = std::fs::read_to_string(&p).unwrap().lines().map(String::from).collect();
        lines[1] = lines[1].replace(""i":2", ""i":99");
        std::fs::write(&p, lines.join("\n") + "\n").unwrap();
        assert_eq!(log.verify().unwrap(), Some(2));
        let _ = std::fs::remove_file(&p);
    }

    #[test]
    fn tampering_is_visible_after_restart() {
        // P1-5: restart must NOT erase tampering
        let p = tmp();
        let mut log = DecisionLog::open(&p).unwrap();
        for i in 1..=3 {
            log.append(i, &json!({"i": i})).unwrap();
        }
        drop(log);
        let mut lines: Vec<String> = std::fs::read_to_string(&p).unwrap().lines().map(String::from).collect();
        lines[1] = lines[1].replace("\"i\":2", "\"i\":99");
        std::fs::write(&p, lines.join("\n") + "\n").unwrap();
        let log2 = DecisionLog::open(&p).unwrap();
        assert_eq!(log2.tampered_at, Some(2));
        assert_eq!(log2.seq, 1); // head stays at last verified
        // and the break is still detectable by verify()
        assert!(log2.verify().unwrap().is_some());
        let _ = std::fs::remove_file(&p);
    }

    #[test]
    fn reopens_after_log_deleted() {
        // external rotation deletes the file; append must recreate, chain intact
        let p = tmp();
        let mut log = DecisionLog::open(&p).unwrap();
        log.append(1, &json!({"a": 1})).unwrap();
        std::fs::remove_file(&p).unwrap();
        log.append(2, &json!({"a": 2})).unwrap();
        drop(log);
        assert!(DecisionLog::open(&p).unwrap().verify().unwrap().is_none());
        let _ = std::fs::remove_file(&p);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn append_surfaces_io_error_on_full_disk() {
        // /dev/full: writes fail ENOSPC — the error must propagate, not vanish
        let mut log = DecisionLog::open("/dev/full").unwrap();
        assert!(log.append(1, &json!({"a": 1})).is_err());
    }

    #[test]
    fn torn_tail_recovered_on_open() {
        let p = tmp();
        let mut log = DecisionLog::open(&p).unwrap();
        log.append(1, &json!({"a": 1})).unwrap();
        drop(log);
        use std::io::Write as _;
        let mut f = OpenOptions::new().append(true).open(&p).unwrap();
        f.write_all(b"{\"seq\":2,\"ts\":2,\"torn").unwrap();
        drop(f);
        let log2 = DecisionLog::open(&p).unwrap();
        assert_eq!(log2.seq, 1);
        assert!(log2.verify().unwrap().is_none());
        let _ = std::fs::remove_file(&p);
    }
}
