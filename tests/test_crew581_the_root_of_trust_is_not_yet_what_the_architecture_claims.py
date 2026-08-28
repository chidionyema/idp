"""crew#581: the three claims the trust architecture makes that main does not yet meet.

The founder handed the crew a 3-tier "Identity-Backed Ephemeral Trust" doc written in the present
tense. Three of its load-bearing sentences are false on main today, measured 2026-08-28. This file
is the instrument, not the fix: each target below is asserted as the architecture states it, and
marked xfail(strict=True) because it does not hold yet.

strict=True is the whole point and is why this file is worth merging red. While the defect stands
the suite is green and the gap is on the record with its measurement. The moment the fix lands the
test XPASSes, strict turns that into a FAILURE, and whoever landed the fix must delete the marker in
the same PR. A guard that removes itself cannot rot into a comment nobody reads (LAW 28), and it
cannot be walked past (LAW 45).

Every xfail test is paired with a plain test that proves the parser actually sees content, so a
typo in a path can never make a target look met or make an xfail look like a real defect.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VAULT_TF = ROOT / "platform" / "oci" / "vault.tf"
BIN = ROOT / "bin"

# The doc: "Hardware Cryptography (KMS) ... physically baked into a silicon chip in the data
# centre ... cannot be downloaded or viewed by anyone, not even you."
# OCI spells that protection_mode = "HSM", and an HSM partition the estate alone occupies is
# vault_type = "VIRTUAL_PRIVATE". main declares SOFTWARE in a DEFAULT vault (vault.tf:11,18).
HSM_TARGET = {"protection_mode": "HSM", "vault_type": "VIRTUAL_PRIVATE"}

# The doc: "No internal API keys exist" and no human holds the root. main's actual root of trust is
# a static age private key in a file on one named laptop, defaulted into twelve bin/ scripts as
#   SOPS_AGE_KEY_FILE=${SOPS_AGE_KEY_FILE:-$HOME/.config/prospector/age-key.txt}
# and made fail-closed by bin/idp-flux-bootstrap:16. It is also LAW 46's own failure case: a literal
# path under $HOME on one machine.
HOME_KEY_DEFAULT = re.compile(r"\$\{[A-Z0-9_]*KEY[A-Z0-9_]*:-\$HOME/")

# The doc, tier 1: every service holds a SPIFFE SVID and talks mTLS. On main the only mounts of the
# SPIFFE CSI driver are SPIRE's own proof and the collector that reads it, so the mesh carries no
# real traffic and no API key can yet be deleted.
SPIFFE_CSI = "csi.spiffe.io"
PROOF_HARNESS = {
    "platform/spire/proof.yaml",
    "platform/spire/proof-cronjob.yaml",
    "platform/state/cluster-state.yaml",
    "platform/edge/provider-independence.yaml",
}


def _vault_tf():
    return VAULT_TF.read_text()


def _hcl_scalars(text):
    """Every `name = "value"` in the file, last assignment wins."""
    return dict(re.findall(r'^\s*([a-z_]+)\s*=\s*"([^"]+)"', text, re.M))


def _shell_scripts():
    return sorted(p for p in BIN.iterdir() if p.is_file() and not p.name.endswith((".py", ".md")))


def _manifests():
    return sorted(
        p
        for d in ("platform", "clusters")
        for p in (ROOT / d).rglob("*.yaml")
    )


# --- anti-vacuous: prove the instrument is reading real content ------------------------------


def test_the_vault_terraform_is_read_and_declares_a_key():
    text = _vault_tf()
    assert "oci_kms_key" in text, f"{VAULT_TF} declares no KMS key; this test is grading nothing"
    scalars = _hcl_scalars(text)
    for key in HSM_TARGET:
        assert key in scalars, f"{key} is not declared in {VAULT_TF}; the parser would pass blindly"


def test_the_bin_directory_is_read_and_the_home_key_pattern_matches_what_it_describes():
    scripts = _shell_scripts()
    assert len(scripts) > 50, f"only {len(scripts)} scripts found under {BIN}; wrong path"
    # The pattern is graded against a literal, not against the defect still being present: once the
    # fix lands the offender list goes empty and only the xfail below may flip. An anti-vacuous test
    # that asserts the bug still exists would fail alongside the fix and hide which one moved.
    assert HOME_KEY_DEFAULT.search(
        "SOPS_AGE_KEY_FILE=${SOPS_AGE_KEY_FILE:-$HOME/.config/prospector/age-key.txt}"
    ), "the pattern no longer matches the line it was written for"
    assert not HOME_KEY_DEFAULT.search(
        "SOPS_AGE_KEY_FILE=${SOPS_AGE_KEY_FILE:-/run/secrets/age-key.txt}"
    ), "the pattern matches a key sourced outside $HOME; it would never go green"


def test_the_manifest_sweep_finds_the_spiffe_proof_harness():
    mounting = {
        str(p.relative_to(ROOT))
        for p in _manifests()
        if SPIFFE_CSI in p.read_text()
    }
    assert mounting, f"no manifest mounts {SPIFFE_CSI}; the sweep is reading the wrong tree"
    assert mounting & PROOF_HARNESS, (
        f"the SPIRE proof harness is gone from {sorted(mounting)}; tier 1 has changed shape and "
        "this instrument needs rewriting before it can be trusted"
    )


# --- the three targets the architecture claims are already true -------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "crew#581 CP1: vault.tf:11,18 declare vault_type=DEFAULT and protection_mode=SOFTWARE. "
        "The architecture claims a key baked into silicon. Delete this marker with the fix."
    ),
)
def test_the_kms_key_is_protected_by_hardware():
    scalars = _hcl_scalars(_vault_tf())
    assert {k: scalars[k] for k in HSM_TARGET} == HSM_TARGET


@pytest.mark.xfail(
    strict=True,
    reason=(
        "crew#581 CP2: twelve bin/ scripts default a decryption key to a path under $HOME, so the "
        "estate's root of trust is a file one person carries. Delete this marker with the fix."
    ),
)
def test_no_script_roots_the_estate_in_a_key_file_under_a_home_directory():
    offenders = [p.name for p in _shell_scripts() if HOME_KEY_DEFAULT.search(p.read_text())]
    assert offenders == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "crew#581 CP3: the only mounts of the SPIFFE CSI driver are SPIRE's own proof and the "
        "collector, so no product workload holds an SVID. Delete this marker with the fix."
    ),
)
def test_a_workload_outside_the_proof_harness_holds_an_svid():
    mounting = {
        str(p.relative_to(ROOT))
        for p in _manifests()
        if SPIFFE_CSI in p.read_text()
    }
    assert mounting - PROOF_HARNESS
