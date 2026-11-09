"""Render the existing estate onboarding packet from one versioned data source.

NO remote fetches, private memory, agent-supplied policy, new scheduler, or new
authority. This file ships with the existing platform/estate release. A packet
proves which source was seen; it does not prove the agent comprehended it or
that any stated target is operating.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL = HERE / "operating_model.json"
REQUIRED = ("systems", "authority", "lifecycle", "placement",
            "infrastructure", "session_contract", "sources")
REQUIRED_SOURCES = (
    "docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md",
    "docs/decisions/0048-the-estate-runs-on-one-node-with-an-admission-list.md",
    "https://github.com/chidionyema/argon/blob/main/AGENTS.md",
)
MAX_BYTES = 32_768


class OnboardingUnavailable(ValueError):
    """No valid model; the session must not claim admission based on this pack."""


def load(path: Path = MODEL) -> tuple[dict, str]:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_BYTES:
            raise OnboardingUnavailable("onboarding pack exceeds size bound")
        model = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise OnboardingUnavailable(f"onboarding model unreadable: {type(exc).__name__}") from exc
    if not isinstance(model, dict) or model.get("schema_version") != "estate.onboarding.v1":
        raise OnboardingUnavailable("onboarding model schema not recognised")
    if any(key not in model for key in REQUIRED):
        raise OnboardingUnavailable("onboarding model missing required fields")
    if not all(isinstance(model.get(name), dict) for name in ("systems", "authority", "infrastructure")):
        raise OnboardingUnavailable("onboarding model has invalid structural fields")
    if set(model["systems"]) != {"idp", "genesis"}:
        raise OnboardingUnavailable("onboarding model must distinguish IDP and Genesis")
    if not isinstance(model.get("sources"), list) or not all(
        src in model["sources"] for src in REQUIRED_SOURCES
    ):
        raise OnboardingUnavailable("onboarding model missing authoritative source pointers")
    # The context describes the CURRENT canonical ADRs. Pin their exact Git
    # blob identities and ship those source copies through the existing
    # installer, so a changed or missing ADR yields UNKNOWN, never stale
    # architectural certainty. Runtime *health* still needs independent probes.
    blobs = model.get("canonical_source_blobs")
    if not isinstance(blobs, dict) or not all(
        isinstance(blobs.get(src), str) and len(blobs[src]) == 40
        for src in REQUIRED_SOURCES[:2]
    ):
        raise OnboardingUnavailable("pinned canonical ADR blobs missing")
    root = path.resolve().parents[3]
    for source, expected in blobs.items():
        if not isinstance(source, str) or not source.startswith("docs/decisions/"):
            raise OnboardingUnavailable("invalid pinned ADR source")
        source_path = root / source
        try:
            data = source_path.read_bytes()
        except OSError as exc:
            raise OnboardingUnavailable("pinned ADR source unavailable") from exc
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()
        if actual != expected:
            raise OnboardingUnavailable("pinned ADR changed without refreshing onboarding pack")
    if model["infrastructure"].get("live_verdict") != "UNKNOWN until fresh independent caller/runtime probe":
        raise OnboardingUnavailable("onboarding model must not assert live health from source")
    if "SOURCE_CANDIDATE_NOT_DEPLOYED" != model.get("fleet_policy", {}).get("state"):
        raise OnboardingUnavailable("onboarding model's fleet policy state needs a governed revision")
    return model, hashlib.sha256(raw).hexdigest()


def render(path: Path = MODEL) -> str:
    try:
        model, digest = load(path)
    except OnboardingUnavailable as exc:
        return ("<estate-operating-model status=\"UNKNOWN\" privileged-admission=\"UNVERIFIED\">\n"
                f"Onboarding model not available: {exc}. Use verified read-only diagnosis; "
                "do not infer founder authority or infrastructure health.\n"
                "</estate-operating-model>")
    infra = model["infrastructure"]
    sys = model["systems"]
    return "\n".join([
        f'<estate-operating-model schema="estate.onboarding.v1" sha256="{digest}" status="SOURCE_ONLY">',
        "IDP: " + sys["idp"]["purpose"],
        "GENESIS: " + sys["genesis"]["purpose"],
        "SOVEREIGN AUTHORITY: " + model["authority"]["founder"],
        "PROOF: " + model["authority"]["precedence"],
        "FLOW: " + model["lifecycle"],
        "PLACEMENT: " + "; ".join(f'{row[0]} (rung {row[2]})' for row in model["placement"]),
        "INFRA TARGET, NOT LIVE: " + infra["target"],
        "INFRA RECONCILE: " + infra["old_oke"] + " " + infra["recovery_candidate"],
        "LIVE HEALTH: UNKNOWN. Probe: " + "; ".join(infra["live_probes"])
        + "; declared-only: " + infra["desired_state_probe"] + ".",
        "SOURCE OF CURRENT RECOVERY: " + infra["recovery_incident"],
        "FLEET POLICY: " + model["fleet_policy"]["state"] + "; " + model["fleet_policy"]["activation"],
        "REQUIRED: " + model["session_contract"]["first_turn"],
        "FULL PACK: docs/onboarding/estate-idp-genesis-and-infrastructure.md (shipped from pinned repository).",
        "MISSING OR CONFLICTING: " + model["session_contract"]["missing_or_conflicting"],
        "This is trusted *source context* only; policy effect doors must independently enforce action authority.",
        "</estate-operating-model>",
    ])
