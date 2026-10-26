"""EFDA -- the estate's universal coverage layer.

Five layers, one property: when a component fails, the next actor reads the
evidence before it acts, or the gap is visible.

    L1 checkpoint   a wrapper writes progress every 30s and on SIGTERM, so a
                    stall-kill loses <=30s of work instead of the whole run
    L2 evidence     every failure leaves a schema-valid DiagnosticArtifact at a
                    deterministic address
    L3 synthesis    the pack factory turns observed failures into candidate
                    SkillPacks, and refuses to promote one that cannot be proven
    L4 reasoning    Reason(artifact, pack) -> DiagnosticReport, ranked and cited
    L5 remediation  a separate executor, an empty allowlist on day one, and a
                    safety_proof before anything may act

The interfaces are the spec's; the language is Python because that is the
language this repository's gate speaks (pytest, ruff, pytest-bdd).
"""

__all__ = ["SCHEMA_VERSION", "INTERFACE_VERSION"]

# The artifact envelope version. A major bump needs a dual-write window.
SCHEMA_VERSION = "v3"

# The pack/artifact interface version both sides negotiate.
INTERFACE_VERSION = "v1"
