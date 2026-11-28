//! `meridian-outbox-ingest`: the single verifier for the Gemini -> Drive -> idp submit lane.
//!
//! `bin/gemini-outbox-pull` does the I/O (Drive, git). Every accept/reject decision about a
//! packet lives here and nowhere else, so there is no second copy to drift.
//!
//! Usage: `meridian-outbox-ingest <outbox_dir> <packet_json> <staging_root> <receipts_dir> [expected_repo]`
//! Prints one JSON receipt on stdout. Exit 0 = accepted, 1 = REJECTED, 2 = bad usage.
//!
//! A packet is accepted only if every rule holds; anything this code cannot judge is refused:
//!   1. schema is `meridian.gemini-packet.v1` and the branch prefix is `submit/gemini-`.
//!   2. `packet_id` is `[a-z0-9-]`, 1..=64 chars (it becomes a git branch and a Drive filename).
//!   3. `target_repo` equals `expected_repo` when the caller supplies one.
//!   4. `claim_issue` has the shape `owner/repo#N`.
//!   5. `ship_contract_accept_url` is https and not a proxy host (github, localhost, ...).
//!   6. every artifact is a plain filename (no separator), unique, at most `MAX_ARTIFACTS`.
//!   7. every `target_subdir` is under `intake/` with no traversal, so a packet can never write
//!      `.github/`, `bin/`, `platform/` ... (a Gemini packet is untrusted input; the Greenlane
//!      merges what lands on the submit branch).
//!   8. forbidden agent-note paths are refused.
//!   9. the LANDED bytes (re-read from the destination) match the declared sha256 and length
//!      (closes the short-copy defect of PR #8164).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::ExitCode;

const PACKET_SCHEMA: &str = "meridian.gemini-packet.v1";
const RECEIPT_SCHEMA: &str = "meridian.gemini-receipt.v1";
const BRANCH_PREFIX: &str = "submit/gemini-";
const INTAKE_ROOT: &str = "intake/";
const MAX_ARTIFACTS: usize = 16;
const MAX_ARTIFACT_BYTES: u64 = 64 * 1024 * 1024;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ArtifactSpec {
    pub filename: String,
    pub sha256: String,
    pub bytes: u64,
    pub target_subdir: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GeminiPacket {
    pub schema: String,
    pub packet_id: String,
    pub created_utc: String,
    pub source_surface: String,
    pub target_repo: String,
    pub target_branch_prefix: String,
    pub claim_issue: String,
    pub ship_contract_accept_url: Option<String>,
    pub artifacts: Vec<ArtifactSpec>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct VerifiedArtifactReceipt {
    pub filename: String,
    pub landed_sha256: String,
    pub landed_bytes: u64,
    pub dest_path: String,
    pub target_subdir: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct IngestReceipt {
    pub schema: String,
    pub packet_id: String,
    pub claim_issue: String,
    pub verdict: String, // "INGESTED_READY_FOR_SUBMIT" | "ALREADY_INGESTED" | "REJECTED"
    pub reason: String,
    pub submit_branch: String,
    pub verified_artifacts: Vec<VerifiedArtifactReceipt>,
}

fn reject(packet_id: &str, claim: &str, branch: &str, reason: String) -> IngestReceipt {
    IngestReceipt {
        schema: RECEIPT_SCHEMA.to_string(),
        packet_id: packet_id.to_string(),
        claim_issue: claim.to_string(),
        verdict: "REJECTED".to_string(),
        reason,
        submit_branch: branch.to_string(),
        verified_artifacts: vec![],
    }
}

pub fn sha256_file(path: &Path) -> Result<(String, u64), String> {
    let bytes = fs::read(path).map_err(|e| format!("read {:?}: {e}", path))?;
    let mut h = Sha256::new();
    h.update(&bytes);
    Ok((hex::encode(h.finalize()), bytes.len() as u64))
}

pub fn is_valid_packet_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && !id.starts_with('-')
        && id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

pub fn is_valid_claim_issue(raw: &str) -> bool {
    let Some((repo, num)) = raw.split_once('#') else {
        return false;
    };
    let Some((owner, name)) = repo.split_once('/') else {
        return false;
    };
    let part_ok = |s: &str| {
        !s.is_empty()
            && s.bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_' || b == b'.')
    };
    part_ok(owner) && part_ok(name) && !num.is_empty() && num.bytes().all(|b| b.is_ascii_digit())
}

pub fn is_safe_relative_path(raw: &str) -> bool {
    let p = Path::new(raw);
    if raw.trim().is_empty() || raw.contains('\\') || raw.contains('\0') || p.is_absolute() {
        return false;
    }
    p.components()
        .all(|c| matches!(c, Component::Normal(_) | Component::CurDir))
}

pub fn is_plain_filename(raw: &str) -> bool {
    is_safe_relative_path(raw) && !raw.contains('/') && raw != "." && raw != ".."
}

pub fn is_under_intake(raw: &str) -> bool {
    is_safe_relative_path(raw)
        && raw.starts_with(INTAKE_ROOT)
        && raw.len() > INTAKE_ROOT.len()
        && !raw.split('/').any(|seg| seg == ".git" || seg.is_empty())
}

pub fn is_forbidden_note(raw: &str) -> bool {
    let low = raw.trim().trim_start_matches("./").to_ascii_lowercase();
    low.starts_with("docs/diagnoses/")
        || low.starts_with("docs/notes/")
        || low.starts_with(".growmos/")
        || low.contains("handoff")
        || low.contains("journal")
}

pub fn is_proxy_url(url: &str) -> bool {
    let low = url.trim().to_ascii_lowercase();
    let Some(rest) = low.strip_prefix("https://") else {
        return true;
    };
    let authority = rest.split('/').next().unwrap_or("");
    if authority.contains('@') {
        return true;
    }
    let host = authority.split(':').next().unwrap_or("");
    matches!(
        host,
        "" | "github.com"
            | "api.github.com"
            | "raw.githubusercontent.com"
            | "localhost"
            | "127.0.0.1"
            | "0.0.0.0"
            | "[::1]"
    ) || host.ends_with(".github.com")
        || host.ends_with(".githubusercontent.com")
        || host.ends_with(".localhost")
}

pub fn ingest_packet(
    outbox_dir: &Path,
    packet_file: &Path,
    staging_root: &Path,
    receipts_dir: &Path,
    expected_repo: Option<&str>,
) -> IngestReceipt {
    let raw = match fs::read_to_string(packet_file) {
        Ok(s) => s,
        Err(e) => return reject("UNKNOWN", "", "", format!("READ_PACKET_FAILED:{e}")),
    };
    let pkt: GeminiPacket = match serde_json::from_str(&raw) {
        Ok(p) => p,
        Err(e) => return reject("UNKNOWN", "", "", format!("INVALID_PACKET_JSON:{e}")),
    };

    if !is_valid_packet_id(&pkt.packet_id) {
        return reject("UNKNOWN", "", "", "INVALID_PACKET_ID".to_string());
    }
    let branch = format!("{BRANCH_PREFIX}{}", pkt.packet_id);
    let fail = |reason: String| reject(&pkt.packet_id, &pkt.claim_issue, &branch, reason);

    if pkt.schema != PACKET_SCHEMA || pkt.target_branch_prefix != BRANCH_PREFIX {
        return fail("INVALID_SCHEMA_OR_BRANCH_PREFIX".to_string());
    }
    if let Some(repo) = expected_repo {
        if pkt.target_repo != repo {
            return fail(format!("TARGET_REPO_MISMATCH:{}", pkt.target_repo));
        }
    }
    if !is_valid_claim_issue(&pkt.claim_issue) {
        return fail("INVALID_CLAIM_ISSUE".to_string());
    }

    let receipt_path = receipts_dir.join(format!("RECEIPT_{}.json", pkt.packet_id));
    if receipt_path.is_file() {
        return IngestReceipt {
            schema: RECEIPT_SCHEMA.to_string(),
            packet_id: pkt.packet_id.clone(),
            claim_issue: pkt.claim_issue.clone(),
            verdict: "ALREADY_INGESTED".to_string(),
            reason: "IDEMPOTENT_SKIP_RECEIPT_EXISTS".to_string(),
            submit_branch: branch.clone(),
            verified_artifacts: vec![],
        };
    }

    match &pkt.ship_contract_accept_url {
        Some(url) if is_proxy_url(url) => {
            return fail(format!("PROXY_GREEN_URL_REJECTED:{url}"));
        }
        None => return fail("ACCEPT_URL_REQUIRED".to_string()),
        Some(_) => {}
    }

    if pkt.artifacts.is_empty() || pkt.artifacts.len() > MAX_ARTIFACTS {
        return fail(format!("ARTIFACT_COUNT_OUT_OF_RANGE:{}", pkt.artifacts.len()));
    }

    let mut seen: HashSet<(String, String)> = HashSet::new();
    for art in &pkt.artifacts {
        if !is_plain_filename(&art.filename)
            || !is_under_intake(&art.target_subdir)
            || is_forbidden_note(&art.filename)
            || is_forbidden_note(&art.target_subdir)
        {
            return fail(format!(
                "UNSAFE_OR_FORBIDDEN_PATH:{}/{}",
                art.target_subdir, art.filename
            ));
        }
        if art.bytes > MAX_ARTIFACT_BYTES {
            return fail(format!("ARTIFACT_TOO_LARGE:{}", art.filename));
        }
        if !seen.insert((art.target_subdir.clone(), art.filename.clone())) {
            return fail(format!("DUPLICATE_ARTIFACT:{}", art.filename));
        }
    }

    let mut verified = Vec::new();
    for art in &pkt.artifacts {
        let src = outbox_dir.join(&art.filename);
        let dest_dir: PathBuf = staging_root.join(&art.target_subdir);
        if let Err(e) = fs::create_dir_all(&dest_dir) {
            return fail(format!("MKDIR_FAILED:{e}"));
        }
        let dest = dest_dir.join(&art.filename);
        if let Err(e) = fs::copy(&src, &dest) {
            return fail(format!("COPY_FAILED:{}:{e}", art.filename));
        }

        // PR #8164 law: re-hash the LANDED destination bytes, never trust the source hash.
        let (landed_sha, landed_len) = match sha256_file(&dest) {
            Ok(v) => v,
            Err(e) => {
                let _ = fs::remove_file(&dest);
                return fail(format!("REHASH_FAILED:{e}"));
            }
        };
        if landed_sha != art.sha256.to_ascii_lowercase() || landed_len != art.bytes {
            let _ = fs::remove_file(&dest);
            return fail(format!(
                "LANDED_DIGEST_MISMATCH:{}:expected={}:{} got={}:{}",
                art.filename, art.sha256, art.bytes, landed_sha, landed_len
            ));
        }

        verified.push(VerifiedArtifactReceipt {
            filename: art.filename.clone(),
            landed_sha256: landed_sha,
            landed_bytes: landed_len,
            dest_path: format!("{}/{}", art.target_subdir, art.filename),
            target_subdir: art.target_subdir.clone(),
        });
    }

    IngestReceipt {
        schema: RECEIPT_SCHEMA.to_string(),
        packet_id: pkt.packet_id.clone(),
        claim_issue: pkt.claim_issue.clone(),
        verdict: "INGESTED_READY_FOR_SUBMIT".to_string(),
        reason: "ALL_LANDED_BYTES_VERIFIED".to_string(),
        submit_branch: branch.clone(),
        verified_artifacts: verified,
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    if args.len() < 5 {
        eprintln!(
            "usage: meridian-outbox-ingest <outbox_dir> <packet_json> <staging_root> <receipts_dir> [expected_repo]"
        );
        return ExitCode::from(2);
    }
    let receipt = ingest_packet(
        Path::new(&args[1]),
        Path::new(&args[2]),
        Path::new(&args[3]),
        Path::new(&args[4]),
        args.get(5).map(String::as_str),
    );
    match serde_json::to_string_pretty(&receipt) {
        Ok(s) => println!("{s}"),
        Err(e) => {
            eprintln!("receipt serialisation failed: {e}");
            return ExitCode::from(1);
        }
    }
    if receipt.verdict == "REJECTED" {
        ExitCode::from(1)
    } else {
        ExitCode::SUCCESS
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    static N: AtomicU32 = AtomicU32::new(0);

    struct Dirs {
        root: PathBuf,
    }
    impl Dirs {
        fn new() -> Dirs {
            let root = env::temp_dir().join(format!(
                "outbox-ingest-test-{}-{}",
                std::process::id(),
                N.fetch_add(1, Ordering::SeqCst)
            ));
            let _ = fs::remove_dir_all(&root);
            fs::create_dir_all(root.join("outbox")).expect("mkdir outbox");
            Dirs { root }
        }
        fn outbox(&self) -> PathBuf {
            self.root.join("outbox")
        }
        fn stage(&self) -> PathBuf {
            self.root.join("stage")
        }
        fn receipts(&self) -> PathBuf {
            self.root.join("receipts")
        }
    }
    impl Drop for Dirs {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.root);
        }
    }

    fn sha(bytes: &[u8]) -> String {
        hex::encode(Sha256::digest(bytes))
    }

    /// A known-good packet over one real artifact; tests mutate it into known-bad ones.
    fn good(d: &Dirs) -> serde_json::Value {
        let body = b"pub fn ok() -> u8 { 1 }\n";
        fs::write(d.outbox().join("crate.zip"), body).expect("write artifact");
        serde_json::json!({
            "schema": PACKET_SCHEMA,
            "packet_id": "20261128-test-ok",
            "created_utc": "2026-11-28T01:56:00Z",
            "source_surface": "gemini-web",
            "target_repo": "chidionyema/idp",
            "target_branch_prefix": BRANCH_PREFIX,
            "claim_issue": "chidionyema/idp#8702",
            "ship_contract_accept_url": "https://llm.meridianlabs.cloud/health",
            "artifacts": [{
                "filename": "crate.zip",
                "sha256": sha(body),
                "bytes": body.len(),
                "target_subdir": "intake/demo"
            }]
        })
    }

    fn run(d: &Dirs, pkt: &serde_json::Value, repo: Option<&str>) -> IngestReceipt {
        let pf = d.outbox().join("PACKET_x.json");
        fs::write(&pf, pkt.to_string()).expect("write packet");
        ingest_packet(&d.outbox(), &pf, &d.stage(), &d.receipts(), repo)
    }

    #[test]
    fn accepts_known_good_and_lands_bytes() {
        let d = Dirs::new();
        let pkt = good(&d);
        let r = run(&d, &pkt, Some("chidionyema/idp"));
        assert_eq!(r.verdict, "INGESTED_READY_FOR_SUBMIT", "{}", r.reason);
        assert!(d.stage().join("intake/demo/crate.zip").is_file());
        assert_eq!(r.submit_branch, "submit/gemini-20261128-test-ok");
        assert_eq!(r.verified_artifacts.len(), 1);
    }

    #[test]
    fn rejects_tampered_bytes_and_removes_landed_file() {
        let d = Dirs::new();
        let mut pkt = good(&d);
        pkt["artifacts"][0]["sha256"] = serde_json::json!("0".repeat(64));
        let r = run(&d, &pkt, None);
        assert_eq!(r.verdict, "REJECTED");
        assert!(r.reason.starts_with("LANDED_DIGEST_MISMATCH"), "{}", r.reason);
        assert!(!d.stage().join("intake/demo/crate.zip").exists());
    }

    #[test]
    fn rejects_short_copy_length_mismatch() {
        let d = Dirs::new();
        let mut pkt = good(&d);
        pkt["artifacts"][0]["bytes"] = serde_json::json!(3);
        assert_eq!(run(&d, &pkt, None).verdict, "REJECTED");
    }

    #[test]
    fn rejects_proxy_accept_urls() {
        for url in [
            "https://api.github.com/repos/chidionyema/idp/commits/main",
            "https://github.com/chidionyema/idp",
            "http://llm.meridianlabs.cloud/health",
            "https://localhost/health",
            "https://127.0.0.1/health",
            "https://user@llm.meridianlabs.cloud/health",
            "https://evil.github.com/x",
        ] {
            let d = Dirs::new();
            let mut pkt = good(&d);
            pkt["ship_contract_accept_url"] = serde_json::json!(url);
            let r = run(&d, &pkt, None);
            assert_eq!(r.verdict, "REJECTED", "{url}");
            assert!(r.reason.starts_with("PROXY_GREEN_URL_REJECTED"), "{url}");
        }
    }

    #[test]
    fn rejects_missing_accept_url() {
        let d = Dirs::new();
        let mut pkt = good(&d);
        pkt["ship_contract_accept_url"] = serde_json::Value::Null;
        assert_eq!(run(&d, &pkt, None).reason, "ACCEPT_URL_REQUIRED");
    }

    #[test]
    fn rejects_target_subdir_outside_intake() {
        for sub in [
            ".github/workflows",
            "bin",
            "platform/estate",
            "intake",
            "intake/",
            "intake/../bin",
            "/etc",
            "intake//x",
            "intake/.git/hooks",
            "intake\\x",
        ] {
            let d = Dirs::new();
            let mut pkt = good(&d);
            pkt["artifacts"][0]["target_subdir"] = serde_json::json!(sub);
            let r = run(&d, &pkt, None);
            assert_eq!(r.verdict, "REJECTED", "{sub}");
            assert!(r.reason.starts_with("UNSAFE_OR_FORBIDDEN_PATH"), "{sub}");
            assert!(!d.stage().exists(), "nothing may be staged for {sub}");
        }
    }

    #[test]
    fn rejects_unsafe_filenames_and_notes() {
        for name in ["../crate.zip", "a/b.zip", "/abs.zip", "handoff.zip", "journal.zip", ".."] {
            let d = Dirs::new();
            let mut pkt = good(&d);
            pkt["artifacts"][0]["filename"] = serde_json::json!(name);
            assert_eq!(run(&d, &pkt, None).verdict, "REJECTED", "{name}");
        }
        let d = Dirs::new();
        let mut pkt = good(&d);
        pkt["artifacts"][0]["target_subdir"] = serde_json::json!("intake/docs/diagnoses/x");
        // Under intake/ a note-looking path is inert data, not an agent note: accepted.
        assert_eq!(run(&d, &pkt, None).verdict, "INGESTED_READY_FOR_SUBMIT");
    }

    #[test]
    fn rejects_bad_packet_ids() {
        for id in ["", "A", "x y", "a/b", "../x", "-lead", "x;rm", &"a".repeat(65)] {
            let d = Dirs::new();
            let mut pkt = good(&d);
            pkt["packet_id"] = serde_json::json!(id);
            let r = run(&d, &pkt, None);
            assert_eq!(r.verdict, "REJECTED", "{id}");
            assert_eq!(r.reason, "INVALID_PACKET_ID", "{id}");
        }
    }

    #[test]
    fn rejects_wrong_repo_schema_prefix_and_claim() {
        let d = Dirs::new();
        let pkt = good(&d);
        assert!(run(&d, &pkt, Some("someone/else")).reason.starts_with("TARGET_REPO_MISMATCH"));

        let mut p = pkt.clone();
        p["schema"] = serde_json::json!("meridian.gemini-packet.v0");
        assert_eq!(run(&d, &p, None).reason, "INVALID_SCHEMA_OR_BRANCH_PREFIX");

        let mut p = pkt.clone();
        p["target_branch_prefix"] = serde_json::json!("main");
        assert_eq!(run(&d, &p, None).reason, "INVALID_SCHEMA_OR_BRANCH_PREFIX");

        for claim in ["", "8702", "idp#8702", "a/b#", "a/b#x1", "a b/c#1"] {
            let mut p = pkt.clone();
            p["claim_issue"] = serde_json::json!(claim);
            assert_eq!(run(&d, &p, None).reason, "INVALID_CLAIM_ISSUE", "{claim}");
        }
    }

    #[test]
    fn rejects_duplicates_empty_and_missing_artifact() {
        let d = Dirs::new();
        let mut pkt = good(&d);
        let a = pkt["artifacts"][0].clone();
        pkt["artifacts"] = serde_json::json!([a.clone(), a]);
        assert!(run(&d, &pkt, None).reason.starts_with("DUPLICATE_ARTIFACT"));

        pkt["artifacts"] = serde_json::json!([]);
        assert!(run(&d, &pkt, None).reason.starts_with("ARTIFACT_COUNT_OUT_OF_RANGE"));

        let mut missing = good(&d);
        missing["artifacts"][0]["filename"] = serde_json::json!("absent.zip");
        assert!(run(&d, &missing, None).reason.starts_with("COPY_FAILED"));
    }

    #[test]
    fn replay_with_existing_receipt_is_idempotent_skip() {
        let d = Dirs::new();
        let pkt = good(&d);
        fs::create_dir_all(d.receipts()).expect("mkdir receipts");
        fs::write(d.receipts().join("RECEIPT_20261128-test-ok.json"), "{}").expect("write receipt");
        let r = run(&d, &pkt, None);
        assert_eq!(r.verdict, "ALREADY_INGESTED");
        assert!(!d.stage().exists());
    }

    #[test]
    fn rejects_unparseable_packet() {
        let d = Dirs::new();
        let pf = d.outbox().join("PACKET_x.json");
        fs::write(&pf, "{not json").expect("write");
        let r = ingest_packet(&d.outbox(), &pf, &d.stage(), &d.receipts(), None);
        assert_eq!(r.verdict, "REJECTED");
        assert!(r.reason.starts_with("INVALID_PACKET_JSON"));
    }
}
