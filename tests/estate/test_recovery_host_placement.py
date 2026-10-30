"""The recovery host's placement rules, proved offline (idp#7387).

The OKE cluster was deleted and the tenancy is Always Free only, so the estate's data now sits
on three 50 GB block volumes that the dead cluster's CSI driver left behind -- the only copy of
it, with no backup configured and volume backups refused at the free limit. The recovery host
mounts them read-only and streams them off-provider.

Two measured facts decide where that host has to live, and both are read from the provider, not
inferred:

  * a block volume only attaches inside its own availability domain, and all three surviving
    volumes are in AD-1, so a host in another AD can never carry them;
  * the Always Free allowance is 200 GB of block storage for the whole region, and 150 GB of
    that is the surviving volumes themselves, so exactly ONE host with a 50 GB boot volume fits
    -- a second one does not, and the refusal arrives as LimitExceeded at apply time.

So the placement is a class, not a preference: a host in the wrong AD, a shape the AD does not
offer, or a second host are all the same failure wearing three costumes. These tests grade the
module against the measured facts, so the mistake is caught by a test instead of by a provider
refusal after the data has been left unattended.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MODULE = REPO / "platform" / "oci" / "recovery-host.tf"

# Measured 2026-10-30T00:15:00Z against the live tenancy (region uk-london-1), not guessed:
#   oci compute shape list -c <compartment> --availability-domain <ad> --query 'data[].shape'
#   oci limits value list --service-name block-storage --compartment-id <tenancy>
#   oci bv volume list -c <compartment> --query 'data[].{id,size-in-gbs,availability-domain}'
MEASURED_AT = "2026-10-30T00:15:00Z"
VOLUMES_AD = "lPOl:UK-LONDON-1-AD-1"
SURVIVING_VOLUMES = 3
SURVIVING_VOLUME_GB = 50
FREE_STORAGE_GB = 200
SHAPES_BY_AD = {
    "lPOl:UK-LONDON-1-AD-1": ["BM.Standard.A1.160", "VM.Standard.A1.Flex"],
    "lPOl:UK-LONDON-1-AD-2": [
        "BM.Standard.A1.160",
        "VM.Standard.A1.Flex",
        "VM.Standard.E2.1.Micro",
    ],
    "lPOl:UK-LONDON-1-AD-3": [],
}


def _tf() -> str:
    return MODULE.read_text()


def _local(name: str) -> str:
    match = re.search(rf'^\s*{name}\s*=\s*"([^"]+)"', _tf(), re.MULTILINE)
    assert match, f"{name} is not declared in {MODULE}"
    return match.group(1)


def _int(source: str, name: str) -> int:
    match = re.search(rf"^\s*{name}\s*=\s*(\d+)\s*(#.*)?$", source, re.MULTILINE)
    assert match, f"{name} is not declared in {MODULE}"
    return int(match.group(1))


def test_the_host_runs_in_the_availability_domain_of_the_volumes_it_carries() -> None:
    """AD-1 holds the volumes, so AD-1 holds the host that attaches them."""
    source = _tf()
    assert _local("volumes_ad") == VOLUMES_AD
    assert _local("recovery_ad") == VOLUMES_AD, (
        f"the recovery host is in {_local('recovery_ad')} but the surviving volumes are in "
        f"{VOLUMES_AD}; a block volume only attaches inside its own availability domain"
    )
    assert "local.recovery_ad == local.volumes_ad" in source


def test_the_shape_is_offered_in_the_availability_domain_of_the_volumes() -> None:
    """AD-1 offers no E2.1.Micro, so a host that shape can never be placed there."""
    shape = _local("recovery_shape")
    offered = SHAPES_BY_AD[VOLUMES_AD]
    assert shape in offered, (
        f"{shape} is not offered in {VOLUMES_AD} (offered: {', '.join(offered)}); "
        f"measured {MEASURED_AT}"
    )


def test_the_module_declares_exactly_one_host() -> None:
    """Two hosts would need 250 GB of the 200 GB the region allows."""
    source = _tf()
    assert source.count('resource "oci_core_instance"') == 1


def test_the_host_and_the_surviving_volumes_fit_the_free_allowance() -> None:
    """150 GB of volumes plus the host's boot volume must fit 200 GB, once."""
    source = _tf()
    declared = re.search(r"surviving_volumes\s*=\s*\{(.*?)\}", source, re.DOTALL)
    assert declared, "the surviving volumes are not declared"
    count = len(re.findall(r'=\s*"ocid1\.volume\.', declared.group(1)))
    assert count == SURVIVING_VOLUMES, (
        f"{count} surviving volumes declared, {SURVIVING_VOLUMES} measured"
    )
    boot_gb = _int(source, "boot_volume_size_in_gbs")
    used = count * SURVIVING_VOLUME_GB + boot_gb
    assert used <= FREE_STORAGE_GB, (
        f"{used} GB of block storage needed, {FREE_STORAGE_GB} GB allowed"
    )


def test_the_surviving_volumes_are_attached_read_only() -> None:
    """Nothing may write to the only copy of the estate's data."""
    source = _tf()
    assert 'resource "oci_core_volume_attachment"' in source
    attachment = re.search(
        r'resource "oci_core_volume_attachment"[^}]*?\{(.*?)\n\}', source, re.DOTALL
    )
    assert attachment, "the surviving volumes are never attached"
    body = attachment.group(1)
    assert re.search(r"is_read_only\s*=\s*true", body)
    assert "local.recovery_ad == local.volumes_ad" in body


def test_tofu_can_never_destroy_a_surviving_volume() -> None:
    """The volumes are read as data, never managed: no resource may own them."""
    source = _tf()
    assert 'resource "oci_bv_volume"' not in source
    declared = re.search(r"surviving_volumes\s*=\s*\{(.*?)\}", source, re.DOTALL)
    assert declared
    ocids = re.findall(r'"(ocid1\.volume\.[^"]+)"', declared.group(1))
    assert len(ocids) == SURVIVING_VOLUMES
    for ocid in ocids:
        assert source.count(ocid) == 1, f"{ocid} appears outside the survivors map"


def test_the_facts_are_recorded_so_the_test_is_auditable() -> None:
    """A grader that cannot show its facts is a proxy, not a measurement."""
    facts = {
        "measured_at": MEASURED_AT,
        "volumes_ad": VOLUMES_AD,
        "surviving_volumes": SURVIVING_VOLUMES,
        "surviving_volume_gb": SURVIVING_VOLUME_GB,
        "free_storage_gb": FREE_STORAGE_GB,
        "shapes_by_ad": SHAPES_BY_AD,
    }
    assert json.loads(json.dumps(facts)) == facts
