use anyhow::{anyhow, Result};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::Path;

pub const CRITICAL_REPOS: [&str; 4] = [
    "chidionyema/idp",
    "chidionyema/argon",
    "chidionyema/argon-sync",
    "chidionyema/crew",
];

pub struct CifKernel {
    pub conn: Connection,
}

impl CifKernel {
    pub fn open(db_path: impl AsRef<Path>) -> Result<Self> {
        let path_str = db_path.as_ref().to_string_lossy();
        if path_str.contains("/.estate/") || path_str.ends_with("/estate.db") {
            return Err(anyhow!(
                "HISTORY_QUARANTINE_VIOLATION: Genesis kernel cannot mount legacy History ledger {}",
                path_str
            ));
        }
        let conn = Connection::open(db_path)?;
        let kernel = Self { conn };
        kernel.init_v080_sovereign_tables()?;
        Ok(kernel)
    }
}

#[derive(thiserror::Error, Debug, PartialEq)]
pub enum CertificationError {
    #[error("ASYMMETRIC_SIGNATURE_INVALID: Ed25519 verification failed for payload {0}")]
    InvalidEd25519Signature(String),
    #[error("NON_FINITE_TELEMETRY_VALUE: NaN or Inf detected in window {window_id}")]
    NonFiniteTelemetry { window_id: String },
    #[error("UNMEASURED_PROVENANCE_DIGEST: expected measured tree digest {expected}, got {actual}")]
    ProvenanceDigestMismatch { expected: String, actual: String },
    #[error("INSUFFICIENT_EMPIRICAL_TRIALS: required >= {required} post-registration trials (min 2 for Welch df), found {found}")]
    InsufficientEmpiricalTrials { required: usize, found: usize },
    #[error("INVALID_COHORT_LABEL: expected BASELINE or CANDIDATE, got {0}")]
    InvalidCohortLabel(String),
    #[error("BACKDATED_TRIAL_VIOLATION: trial timestamp {trial_ts} <= preregistration timestamp {prereg_ts}")]
    BackdatedTrialDetected { trial_ts: u64, prereg_ts: u64 },
    #[error("STATISTICAL_SIGNIFICANCE_FAILED: Welch t={t_stat:.3} did not meet threshold {min_t:.3}")]
    InsignificantImprovement { t_stat: f64, min_t: f64 },
    #[error("CVAR_BUDGET_EXCEEDED: empirical CVaR_99 £{cvar_gbp:.4} > cap £{cap_gbp:.4}")]
    CvarBudgetExceeded { cvar_gbp: f64, cap_gbp: f64 },
}

pub fn reduce_rfc6962_merkle_root(mut layer: Vec<[u8; 32]>) -> [u8; 32] {
    if layer.is_empty() {
        return Sha256::digest([]).into();
    }
    while layer.len() > 1 {
        let mut next_layer = Vec::with_capacity((layer.len() + 1) / 2);
        for pair in layer.chunks(2) {
            if pair.len() == 2 {
                let mut node_hasher = Sha256::new();
                node_hasher.update([0x01]);
                node_hasher.update(pair[0]);
                node_hasher.update(pair[1]);
                next_layer.push(node_hasher.finalize().into());
            } else {
                next_layer.push(pair[0]);
            }
        }
        layer = next_layer;
    }
    layer[0]
}

pub fn compute_measured_tree_sha256(root_dir: impl AsRef<Path>, rel_paths: &[&str]) -> Result<String> {
    let mut sorted_leaves: BTreeMap<&str, [u8; 32]> = BTreeMap::new();
    for rel in rel_paths {
        let full_path = root_dir.as_ref().join(rel);
        let bytes = std::fs::read(&full_path)
            .map_err(|e| anyhow!("Failed to read tracked artifact {}: {e}", full_path.display()))?;
        let mut leaf_hasher = Sha256::new();
        leaf_hasher.update([0x00]);
        leaf_hasher.update((rel.len() as u64).to_be_bytes());
        leaf_hasher.update(rel.as_bytes());
        leaf_hasher.update((bytes.len() as u64).to_be_bytes());
        leaf_hasher.update(&bytes);
        sorted_leaves.insert(*rel, leaf_hasher.finalize().into());
    }
    let leaves: Vec<[u8; 32]> = sorted_leaves.into_values().collect();
    Ok(hex::encode(reduce_rfc6962_merkle_root(leaves)))
}

pub struct CertifierPrivateEnclave {
    signing_key: SigningKey,
}

impl CertifierPrivateEnclave {
    pub fn from_secret_seed(seed_bytes: &[u8; 32]) -> Self {
        Self {
            signing_key: SigningKey::from_bytes(seed_bytes),
        }
    }

    pub fn public_verifying_key(&self) -> VerifyingKey {
        self.signing_key.verifying_key()
    }

    pub fn sign_canonical_digest(&self, canonical_payload: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(canonical_payload.as_bytes());
        let digest = hasher.finalize();
        let signature: Signature = self.signing_key.sign(&digest);
        hex::encode(signature.to_bytes())
    }
}

#[derive(Clone)]
pub struct CertifierPublicVerifier {
    pub verifying_key: VerifyingKey,
}

impl CertifierPublicVerifier {
    pub fn from_public_bytes(pub_bytes: &[u8; 32]) -> Result<Self> {
        let verifying_key = VerifyingKey::from_bytes(pub_bytes)
            .map_err(|e| anyhow!("Invalid Ed25519 public key bytes: {e}"))?;
        Ok(Self { verifying_key })
    }

    pub fn from_env_or_default() -> Option<Self> {
        let hex_key = std::env::var("FOUNDER_ED25519_PUBLIC_KEY").ok()?;
        if hex_key.len() != 64 || hex_key.chars().all(|c| c == '0') {
            return None;
        }
        let bytes = hex::decode(hex_key).ok()?;
        let arr: [u8; 32] = bytes.try_into().ok()?;
        Self::from_public_bytes(&arr).ok()
    }

    pub fn verify_canonical_digest(
        &self,
        canonical_payload: &str,
        signature_hex: &str,
    ) -> Result<(), CertificationError> {
        let sig_bytes = hex::decode(signature_hex)
            .map_err(|_| CertificationError::InvalidEd25519Signature(canonical_payload.to_string()))?;
        let sig_array: [u8; 64] = sig_bytes
            .try_into()
            .map_err(|_| CertificationError::InvalidEd25519Signature(canonical_payload.to_string()))?;
        let signature = Signature::from_bytes(&sig_array);

        let mut hasher = Sha256::new();
        hasher.update(canonical_payload.as_bytes());
        let digest = hasher.finalize();

        self.verifying_key
            .verify_strict(&digest, &signature)
            .map_err(|_| CertificationError::InvalidEd25519Signature(canonical_payload.to_string()))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmpiricalScienceVerdict {
    pub experiment_id: String,
    pub preregistration_sha256: String,
    pub preregistered_at: u64,
    pub baseline_n: usize,
    pub candidate_n: usize,
    pub baseline_mean_ms: f64,
    pub candidate_mean_ms: f64,
    pub welch_t_stat: f64,
    pub ed25519_signature: String,
}

impl CifKernel {
    pub fn init_v080_sovereign_tables(&self) -> Result<()> {
        self.conn.execute_batch(
            "
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA busy_timeout = 5000;

            -- Canonical Unified Otto Instructions Schema (Shared across Rust & Python)
            CREATE TABLE IF NOT EXISTS otto_instructions (
                id TEXT PRIMARY KEY,
                intent TEXT NOT NULL,
                proposed_action TEXT NOT NULL,
                tool_kind TEXT NOT NULL DEFAULT 'direct_answer',
                status TEXT NOT NULL,
                verified_outcome TEXT NOT NULL,
                source_surface TEXT NOT NULL,
                model_used TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS otto_conversation_memory (
                turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                surface TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS people_graph (
                name TEXT PRIMARY KEY COLLATE NOCASE,
                relationship TEXT NOT NULL,
                preferred_channel TEXT DEFAULT 'telegram',
                notes_and_invariants TEXT NOT NULL,
                trust_tier TEXT DEFAULT 'restricted',
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS personas (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                system_rules TEXT NOT NULL,
                active INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS otto_skills (
                skill_name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                endpoint_or_script TEXT NOT NULL,
                verified_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hardware_heartbeats (
                device_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                battery_pct INTEGER,
                last_ip TEXT,
                last_seen_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experiment_preregistrations (
                experiment_id TEXT PRIMARY KEY,
                github_issue INTEGER NOT NULL,
                hypothesis TEXT NOT NULL,
                min_sample_size INTEGER NOT NULL CHECK(min_sample_size >= 2),
                min_welch_t REAL NOT NULL,
                preregistration_sha256 TEXT NOT NULL,
                preregistered_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experiment_trial_runs (
                trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                cohort TEXT NOT NULL CHECK(cohort IN ('BASELINE', 'CANDIDATE')),
                duration_ms REAL NOT NULL,
                tla_and_bdd_passed INTEGER NOT NULL CHECK(tla_and_bdd_passed IN (0, 1)),
                recorded_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cost_telemetry_ledger (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                window_id TEXT NOT NULL,
                cost_gbp REAL NOT NULL,
                verified_merges INTEGER NOT NULL,
                recorded_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS catechism_antibodies (
                antibody_id TEXT PRIMARY KEY,
                failure_class_signature TEXT NOT NULL UNIQUE,
                remediation_cmd TEXT NOT NULL,
                ed25519_signature TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promotion_audit_log (
                candidate_commit_sha TEXT NOT NULL,
                repo_full_name TEXT NOT NULL,
                ed25519_signature TEXT NOT NULL,
                verified_by_pubkey TEXT NOT NULL,
                promoted_at INTEGER NOT NULL,
                PRIMARY KEY (repo_full_name, candidate_commit_sha)
            );
            ",
        )?;
        Ok(())
    }

    pub fn evaluate_empirical_experiment(
        &self,
        experiment_id: &str,
        enclave: &CertifierPrivateEnclave,
    ) -> Result<EmpiricalScienceVerdict> {
        let (min_n, min_t, prereg_sha, prereg_at): (usize, f64, String, u64) = self
            .conn
            .query_row(
                "SELECT min_sample_size, min_welch_t, preregistration_sha256, preregistered_at
                 FROM experiment_preregistrations WHERE experiment_id = ?1",
                params![experiment_id],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
            )?;

        let effective_min_n = min_n.max(2);

        let mut stmt = self.conn.prepare(
            "SELECT cohort, duration_ms, tla_and_bdd_passed, recorded_at
             FROM experiment_trial_runs WHERE experiment_id = ?1",
        )?;
        let rows = stmt.query_map(params![experiment_id], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, f64>(1)?,
                r.get::<_, i64>(2)?,
                r.get::<_, u64>(3)?,
            ))
        })?;

        let mut baseline = Vec::new();
        let mut candidate = Vec::new();

        for row in rows {
            let (cohort, ms, passed, ts) = row?;
            if !ms.is_finite() || ms < 0.0 {
                return Err(CertificationError::NonFiniteTelemetry {
                    window_id: experiment_id.to_string(),
                }
                .into());
            }
            if ts <= prereg_at {
                return Err(CertificationError::BackdatedTrialDetected {
                    trial_ts: ts,
                    prereg_ts: prereg_at,
                }
                .into());
            }
            if passed != 1 {
                return Err(anyhow!("Trial failed TLA+/BDD safety gate during experiment {experiment_id}"));
            }
            match cohort.as_str() {
                "BASELINE" => baseline.push(ms),
                "CANDIDATE" => candidate.push(ms),
                other => return Err(CertificationError::InvalidCohortLabel(other.to_string()).into()),
            }
        }

        if baseline.len() < effective_min_n || candidate.len() < effective_min_n {
            return Err(CertificationError::InsufficientEmpiricalTrials {
                required: effective_min_n,
                found: baseline.len().min(candidate.len()),
            }
            .into());
        }

        let nb = baseline.len() as f64;
        let nc = candidate.len() as f64;
        let mean_b = baseline.iter().sum::<f64>() / nb;
        let mean_c = candidate.iter().sum::<f64>() / nc;
        let var_b = baseline.iter().map(|x| (x - mean_b).powi(2)).sum::<f64>() / (nb - 1.0);
        let var_c = candidate.iter().map(|x| (x - mean_c).powi(2)).sum::<f64>() / (nc - 1.0);
        let se = ((var_b / nb) + (var_c / nc)).sqrt().max(1e-9);
        let t_stat = (mean_b - mean_c) / se;

        if !t_stat.is_finite() || t_stat < min_t {
            return Err(CertificationError::InsignificantImprovement { t_stat, min_t }.into());
        }

        let canonical = format!("EXP:{experiment_id}:{prereg_sha}:{mean_b:.4}:{mean_c:.4}:{t_stat:.4}");
        let sig = enclave.sign_canonical_digest(&canonical);

        Ok(EmpiricalScienceVerdict {
            experiment_id: experiment_id.to_string(),
            preregistration_sha256: prereg_sha,
            preregistered_at: prereg_at,
            baseline_n: baseline.len(),
            candidate_n: candidate.len(),
            baseline_mean_ms: mean_b,
            candidate_mean_ms: mean_c,
            welch_t_stat: t_stat,
            ed25519_signature: sig,
        })
    }

    pub fn compute_ledger_merkle_root(&self) -> Result<String> {
        let mut stmt = self.conn.prepare(
            "SELECT seq_id, topic, merkle_root FROM realtime_event_ring ORDER BY seq_id ASC",
        )?;
        let rows = stmt.query_map([], |r| {
            Ok((
                r.get::<_, i64>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, String>(2)?,
            ))
        })?;

        let mut leaves: Vec<[u8; 32]> = Vec::new();
        for row in rows {
            let (seq_id, topic, root) = row?;
            let mut leaf = Sha256::new();
            leaf.update([0x00]);
            leaf.update(seq_id.to_be_bytes());
            leaf.update(topic.as_bytes());
            leaf.update(root.as_bytes());
            leaves.push(leaf.finalize().into());
        }
        Ok(hex::encode(reduce_rfc6962_merkle_root(leaves)))
    }
}