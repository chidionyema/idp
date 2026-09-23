import hashlib
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# =====================================================================
# 1. OWASP ASI06 Write-Time Security Pipeline
# =====================================================================


class MemoryWritePayload(BaseModel):
    namespace: str = Field(..., max_length=128)
    key: str = Field(..., max_length=256)
    content: str
    expected_version: Optional[int] = None
    trust_tier: str = Field(default="raw_source")
    provenance: Dict[str, Any] = Field(default_factory=dict)


class SecurityViolationException(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class OWASPWriteGuard:
    MAX_PAYLOAD_SIZE = 64 * 1024  # 64 KB limit
    IMMUTABLE_KEYS = {"system.manifest", "root.identity", "security.policy"}

    # Production-hardened patterns: includes extended character counts to patch the fixed-length leak
    PATTERNS = {
        "prompt_injection": re.compile(
            r"(ignore\s+(previous|all)\s+instructions|system\s+override|developer\s+mode\s+enabled|"
            r"human_confirmed\s*:\s*true|role:\s*system|<\|im_start\|>)",
            re.IGNORECASE,
        ),
        "secret_github_pat": re.compile(
            r"gh[pousr]_[A-Za-z0-9_]{36,42}"
        ),  # Expanded from fixed 36
        "secret_google_key": re.compile(
            r"AIza[0-9A-Za-z\-_]{35,42}"
        ),  # Expanded from fixed 35
        "secret_generic_bearer": re.compile(
            r"Bearer\s+[A-Za-z0-9\-\._~\+\/]{32,}", re.IGNORECASE
        ),
        "secret_rsa_private": re.compile(r"-----BEGIN (RSA )?PRIVATE KEY-----"),
    }

    @classmethod
    def inspect(
        cls, payload: MemoryWritePayload, baseline_hash: Optional[str] = None
    ) -> str:
        raw_bytes = payload.content.encode("utf-8")

        # 1. Size Anomaly Check
        if len(raw_bytes) > cls.MAX_PAYLOAD_SIZE:
            raise SecurityViolationException(
                "SIZE_ANOMALY", f"Content length {len(raw_bytes)} exceeds 64KB ceiling"
            )

        # 2. Protected Key Modification Check
        if (
            payload.key in cls.IMMUTABLE_KEYS
            and payload.trust_tier != "human_confirmed"
        ):
            raise SecurityViolationException(
                "PROTECTED_KEY", f"Key '{payload.key}' is immutable to automated agents"
            )

        # 3. SHA-256 Baseline Integrity Check
        computed_hash = hashlib.sha256(raw_bytes).hexdigest()
        if baseline_hash and computed_hash != baseline_hash:
            raise SecurityViolationException(
                "INTEGRITY_FAIL", "Content hash does not match computed baseline"
            )

        # 4. Prompt Injection Scanner
        if cls.PATTERNS["prompt_injection"].search(payload.content):
            raise SecurityViolationException(
                "PROMPT_INJECTION", "Hostile instruction sequence detected"
            )

        # 5. Secret / PII Leakage Scanner
        for category, pattern in cls.PATTERNS.items():
            if category.startswith("secret_") and pattern.search(payload.content):
                raise SecurityViolationException(
                    "SECRET_LEAK", f"Identified confidential material: {category}"
                )

        return computed_hash


# =====================================================================
# 2. MAPLE-Guard Lifecycle Gates
# =====================================================================


class MAPLEGuard:
    """
    Five Gates: Write, Retrieval, Promotion, Cross-Agent Reuse, Outcome Update
    Formula:
      value = sim(q,m) + β·ρ + γ·τ - λ·h - η·taint(m) - κ·scope(m) - μ·r(m, c_t)
    """

    BETA = 0.3  # Weight for relevance (ρ)
    GAMMA = 0.4  # Weight for truthfulness (τ)
    LAMBDA_ = 0.8  # Weight for harm penalization (h)
    ETA = 0.5  # Weight for taint
    KAPPA = 0.3  # Weight for scope violation
    MU = 0.6  # Weight for query-conditional risk

    THETA_RHO = 0.75
    THETA_TAU = 0.85
    THETA_H = 0.10

    @classmethod
    def calculate_retrieval_score(
        cls,
        cosine_sim: float,
        rho: float,
        tau: float,
        h: float,
        taint: float,
        scope: float,
        conditional_risk: float,
    ) -> float:
        return (
            cosine_sim
            + (cls.BETA * rho)
            + (cls.GAMMA * tau)
            - (cls.LAMBDA_ * h)
            - (cls.ETA * taint)
            - (cls.KAPPA * scope)
            - (cls.MU * conditional_risk)
        )

    @classmethod
    def evaluate_promotion_gate(cls, rho: float, tau: float, h: float) -> bool:
        """
        Gate 3: Private -> Shared promotion condition:
        ρ >= θ_ρ AND τ >= θ_τ AND h <= θ_h
        """
        return (rho >= cls.THETA_RHO) and (tau >= cls.THETA_TAU) and (h <= cls.THETA_H)

    @classmethod
    def verify_cross_agent_reuse(
        cls, trust_tier: str, is_shared: bool, is_quarantined: bool
    ) -> bool:
        """Gate 4: Shared Memory -> Peer Agent."""
        if is_quarantined:
            return False
        if not is_shared:
            return False
        return True
