//! intercloud controller — file-system mode (complete adapter).
//! Runs the reconcile loop over a state directory. The K8s adapter (same Store
//! trait) ships in the estate deployment; see manifests/.
use intercloud::controller::{Store, Reconciler, FsStore};
use std::env;

fn main() {
    let dir = env::args().nth(1).unwrap_or_else(|| "./state".into());
    let key = env::var("SPOOLER_HMAC_KEY").unwrap_or_else(|_| "dev-key".into());
    let mut store = FsStore::open(&dir);
    let snap = store.load().expect("load snapshot");
    let ops = Reconciler::new(key.as_bytes(), 100).reconcile(&snap);
    store.apply(ops).expect("apply ops");
    println!("reconcile pass complete");
}
