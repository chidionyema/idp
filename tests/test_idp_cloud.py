"""bin/idp-cloud: the one primitive layer between the estate's operator scripts and the cloud.

The compartment is what every OCI verb is scoped to, and it is resolved in four roads, in one
order, everywhere (bin/idp-cloud's oci_compartment): the environment, the tfvars the
provisioner rendered, the committed estate config (clusters/oke/estate-config.yaml), and the
sops envelope on a laptop.

The defect (2026-10-25): the secret verbs resolved the compartment from the sops envelope
ONLY. On a laptop that has a live OCI session but no sops envelope and no rendered tfvars,
every secret verb failed -- "cannot operate on non-existent file .../OCI_COMPARTMENT_OCID.yaml"
-- while the vault it should have been reading was perfectly reachable. The vault write the
cluster's signing key needed could not even be attempted.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD = ROOT / "bin/idp-cloud"

ENV_CONFIG = "ocid1.configfilecompartment"
ENV_TFVARS = "ocid1.renderedtfvars"
ENV_ENVELOPE = "ocid1.sopsenvelope"


def _function() -> str:
    src = CLOUD.read_text()
    start = src.index("oci_compartment() {")
    end = src.index("\n}\n", start) + 3
    return src[start:end]


def _resolve(tree: Path, env: dict) -> str:
    e = dict(os.environ)
    e.pop("OCI_COMPARTMENT_OCID", None)
    e.update(env)
    e["IDP"] = str(tree)
    e["OCI_CLI_PROFILE"] = "test"  # no profile discovery, no founder action
    r = subprocess.run(
        ["bash", "-c", f"{_function()}\noci_compartment"],
        capture_output=True,
        text=True,
        env=e,
        timeout=60,
    )
    return r.stdout.strip()


def _tree(tmp_path: Path, with_config: bool = True, with_tfvars: bool = False) -> Path:
    tree = tmp_path / "idp"
    (tree / "clusters" / "oke").mkdir(parents=True)
    if with_config:
        (tree / "clusters" / "oke" / "estate-config.yaml").write_text(
            f'ESTATE_OCI_COMPARTMENT_OCID: "{ENV_CONFIG}"\n'
        )
    if with_tfvars:
        (tree / "platform" / "oci").mkdir(parents=True)
        (tree / "platform" / "oci" / "terraform.tfvars").write_text(
            f'compartment_ocid = "{ENV_TFVARS}"\n'
        )
    return tree


def test_the_committed_estate_config_is_a_road(tmp_path):
    """The road that made the laptop work: no sops envelope, no tfvars, a live session."""
    tree = _tree(tmp_path)
    assert _resolve(tree, {}) == ENV_CONFIG


def test_the_environment_wins(tmp_path):
    tree = _tree(tmp_path)
    assert _resolve(tree, {"OCI_COMPARTMENT_OCID": "ocid1.fromenv"}) == "ocid1.fromenv"


def test_the_rendered_tfvars_win_over_the_committed_config(tmp_path):
    tree = _tree(tmp_path, with_tfvars=True)
    assert _resolve(tree, {}) == ENV_TFVARS


def test_no_secret_verb_resolves_the_compartment_from_the_sops_envelope_alone(tmp_path):
    """The old shape is gone: the sops envelope is one road inside the one function, and no
    verb resolves the compartment on its own."""
    src = CLOUD.read_text()
    assert src.count("""sops -d --extract '["OCI_COMPARTMENT_OCID"]'""") == 1
    assert "C=$(oci_compartment)" in src
    assert src.count("C=$(oci_compartment)") >= 5
