use anyhow::{anyhow, Result};
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

type HmacSha256 = Hmac<Sha256>;

#[derive(thiserror::Error, Debug, PartialEq, Eq)]
pub enum AuthError {
    #[error("WEBHOOK_SECRET_NOT_CONFIGURED")]
    WebhookSecretMissing,
    #[error("INVALID_GITHUB_WEBHOOK_SIGNATURE")]
    InvalidWebhookSignature,
    #[error("FOUNDER_PUBKEY_NOT_CONFIGURED")]
    FounderPubkeyMissing,
    #[error("MISSING_ED25519_HEADERS")]
    MissingEd25519Headers,
    #[error("SIGNATURE_TIMESTAMP_EXPIRED")]
    TimestampExpired,
    #[error("ED25519_SIGNATURE_INVALID")]
    InvalidEd25519Signature,
}

/// Constant-time GitHub X-Hub-Signature-256 verification. Fails closed on missing secret.
pub fn verify_github_webhook_hmac(
    secret: Option<&str>,
    signature_header: Option<&str>,
    raw_body: &[u8],
) -> Result<(), AuthError> {
    let secret = secret
        .filter(|s| !s.is_empty())
        .ok_or(AuthError::WebhookSecretMissing)?;
    let sig_header = signature_header
        .and_then(|s| s.strip_prefix("sha256="))
        .ok_or(AuthError::InvalidWebhookSignature)?;
    let expected_bytes = hex::decode(sig_header).map_err(|_| AuthError::InvalidWebhookSignature)?;

    let mut mac =
        HmacSha256::new_from_slice(secret.as_bytes()).map_err(|_| AuthError::WebhookSecretMissing)?;
    mac.update(raw_body);
    mac.verify_slice(&expected_bytes)
        .map_err(|_| AuthError::InvalidWebhookSignature)
}

/// Helper for tests and internal clients to compute GitHub-compatible sha256=<hex>.
pub fn compute_github_webhook_hmac(secret: &str, raw_body: &[u8]) -> Result<String> {
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| anyhow!("invalid hmac key: {e}"))?;
    mac.update(raw_body);
    Ok(format!("sha256={}", hex::encode(mac.finalize().into_bytes())))
}

/// Deterministic chained SHA-256 Merkle root matching genesis-kernel v0.8.0+.
pub fn compute_chained_merkle_root(
    prev_root: &str,
    ts_ns: u64,
    fencing_token: u64,
    topic: &str,
    payload_str: &str,
) -> String {
    let mut hasher = Sha256::new();
    hasher.update([0x01]);
    hasher.update(prev_root.as_bytes());
    hasher.update(ts_ns.to_be_bytes());
    hasher.update(fencing_token.to_be_bytes());
    hasher.update(topic.as_bytes());
    hasher.update(payload_str.as_bytes());
    hex::encode(hasher.finalize())
}

/// Deterministic SHA-256 scope digest binding repo, fencing token, and sorted admitted paths.
pub fn compute_scope_sha256(
    repo_full_name: &str,
    fencing_token: u64,
    paths: &[String],
) -> String {
    let mut sorted = paths.to_vec();
    sorted.sort();
    sorted.dedup();
    let canonical = serde_json::json!({
        "repo": repo_full_name,
        "fencing_token": fencing_token,
        "paths": sorted,
    });
    let mut hasher = Sha256::new();
    hasher.update(canonical.to_string().as_bytes());
    hex::encode(hasher.finalize())
}

#[derive(Clone)]
pub struct FounderVerifier {
    pub verifying_key: VerifyingKey,
}

impl FounderVerifier {
    pub fn from_hex(hex_key: &str) -> Result<Self> {
        let trimmed = hex_key.trim();
        if trimmed.len() != 64 || trimmed.chars().all(|c| c == '0') {
            return Err(anyhow!("Invalid 32-byte hex Ed25519 public key"));
        }
        let bytes = hex::decode(trimmed)?;
        let arr: [u8; 32] = bytes
            .try_into()
            .map_err(|_| anyhow!("Ed25519 public key must be 32 bytes"))?;
        let verifying_key = VerifyingKey::from_bytes(&arr)
            .map_err(|e| anyhow!("Invalid Ed25519 public key: {e}"))?;
        Ok(Self { verifying_key })
    }

    pub fn from_env() -> Option<Self> {
        let hex_key = std::env::var("FOUNDER_ED25519_PUBLIC_KEY").ok()?;
        Self::from_hex(&hex_key).ok()
    }

    /// Fail-closed Ed25519 verification with 60s anti-replay window.
    pub fn verify_signed_request(
        &self,
        method: &str,
        path: &str,
        timestamp_str: Option<&str>,
        signature_hex: Option<&str>,
        raw_body: &str,
    ) -> Result<(), AuthError> {
        let ts_str = timestamp_str
            .filter(|s| !s.is_empty())
            .ok_or(AuthError::MissingEd25519Headers)?;
        let sig_hex = signature_hex
            .filter(|s| !s.is_empty())
            .ok_or(AuthError::MissingEd25519Headers)?;

        let ts: i64 = ts_str.parse().map_err(|_| AuthError::TimestampExpired)?;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs() as i64;
        if (now - ts).abs() > 60 {
            return Err(AuthError::TimestampExpired);
        }

        let sig_bytes = hex::decode(sig_hex).map_err(|_| AuthError::InvalidEd25519Signature)?;
        let sig_arr: [u8; 64] = sig_bytes
            .try_into()
            .map_err(|_| AuthError::InvalidEd25519Signature)?;
        let signature = Signature::from_bytes(&sig_arr);

        let canonical = format!("{method}:{path}:{ts_str}:{raw_body}");
        let mut hasher = Sha256::new();
        hasher.update(canonical.as_bytes());
        let digest = hasher.finalize();

        self.verifying_key
            .verify_strict(&digest, &signature)
            .map_err(|_| AuthError::InvalidEd25519Signature)
    }
}

/// Test/Client helper for signing canonical requests with an Ed25519 seed.
pub fn sign_canonical_request(
    seed: &[u8; 32],
    method: &str,
    path: &str,
    timestamp_sec: i64,
    raw_body: &str,
) -> (String, String) {
    let key = SigningKey::from_bytes(seed);
    let ts_str = timestamp_sec.to_string();
    let canonical = format!("{method}:{path}:{ts_str}:{raw_body}");
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    let digest = hasher.finalize();
    let sig = key.sign(&digest);
    (ts_str, hex::encode(sig.to_bytes()))
}
