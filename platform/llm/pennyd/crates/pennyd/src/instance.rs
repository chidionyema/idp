//! One daemon per host.
//!
//! Two pennyd writers interleave the hash-chained decision log and the budget
//! counters, and the verifier cannot tell which process wrote a row. The Rust
//! kernel already takes an exclusive flock for the same reason. This is that
//! contract for pennyd: take the lock or exit `EX_TEMPFAIL` (75), so a second
//! start is a visible refusal, not a silent second writer.

use std::fs::{File, OpenOptions};
use std::path::Path;

/// `sysexits.h` EX_TEMPFAIL: "temporary failure, the user is invited to retry".
pub const EXIT_ALREADY_RUNNING: i32 = 75;

#[derive(Debug)]
pub struct InstanceLock {
    _file: File,
}

pub fn acquire(path: impl AsRef<Path>) -> Result<InstanceLock, String> {
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("lock dir {}: {e}", parent.display()))?;
        }
    }
    let file = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(path)
        .map_err(|e| format!("open lock {}: {e}", path.display()))?;
    match file.try_lock() {
        Ok(()) => Ok(InstanceLock { _file: file }),
        Err(std::fs::TryLockError::WouldBlock) => Err(format!(
            "another pennyd holds {}; refusing a second writer",
            path.display()
        )),
        Err(std::fs::TryLockError::Error(e)) => Err(format!("lock {}: {e}", path.display())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lock_path(tag: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!("pennyd-instance-{}-{tag}.lock", std::process::id()))
    }

    #[test]
    fn a_second_writer_is_refused_until_the_first_exits() {
        let path = lock_path("refuse");
        let _ = std::fs::remove_file(&path);
        let first = acquire(&path).expect("first writer takes the lock");
        let second = acquire(&path);
        assert!(second.is_err(), "a second writer must be refused");
        assert!(second.unwrap_err().contains("second writer"));
        drop(first);
        acquire(&path).expect("the lock is released when the first writer exits");
    }

    #[test]
    fn the_lock_directory_is_created() {
        let dir = std::env::temp_dir().join(format!("pennyd-instance-dir-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        let path = dir.join("run").join("pennyd.lock");
        let _guard = acquire(&path).expect("nested lock path");
        assert!(path.exists());
    }
}
