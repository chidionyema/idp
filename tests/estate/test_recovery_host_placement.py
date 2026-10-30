"""The recovery host's placement rules, proved offline (idp#7387).

The OKE cluster was deleted and the tenancy is Always Free only, so the estate's data now sits
on three 50 GB block volumes that the dead cluster's CSI driver left behind -- the only copy of
it, with no backup configured and volume backups refused at the free limit. The recovery host
mounts them read-only and streams them off-provider.

Three measured facts decide where that host has to live, and all three are read from the
provider, not inferred:

  * a block volume only attaches inside its own availability domain, and all three surviving
    volumes are in AD-1, so a host in another AD can never carry them -- it can only carry the
    stateless router;
  * the Always Free allowance is 200 GB of block storage for the whole region, and 150 GB of
    that is the surviving volumes themselves, so exactly ONE host with a 50 GB boot volume fits
    -- a second one does not, and the refusal arrives as LimitExceeded at apply time;
  * AD-1 has no Always Free capacity today. Four governed applies asked it for a VM.Standard.A1.Flex
    host and OCI refused every one with "Error: 500-InternalError, Out of host capacity." while
    the same region's quota reported standard-a1-core-count available=2. Quota headroom is not
    capacity.

So the placement is a class, not a preference: a host in the wrong AD, a shape the AD does not
offer, a second host, or an AD-1 placement the provider refuses are all the same failure wearing
four costumes. These tests grade the module against the measured facts, so the mistake is caught
by a test instead of by a provider refusal after the data has been left unattended.

The two placements that are legal are:

  ("VM.Standard.A1.Flex", "lPOl:UK-LONDON-1-AD-1")  the data route -- carries the volumes
  ("VM.Standard.E2.1.Micro", "lPOl:UK-LONDON-1-AD-2") the router-only interim -- no volumes

Anything else is unmeasured: A1.Flex in AD-2 was refused for capacity, and E2.1.Micro is not
offered in AD-1 at all.
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

# The only placements that are measured to exist on this tenancy. See the module docstring.
ALLOWED_PLACEMENTS = {
    ("VM.Standard.A1.Flex", "lPOl:UK-LONDON-1-AD-1"),  # the data route
    ("VM.Standard.E2.1.Micro", "lPOl:UK-LONDON-1-AD-2"),  # the router-only interim
}

# The measured refusal that closed the AD-1 route, and the runs that produced it. Every apply is
# listed: a record of one failure is an anecdote, a record of four is a class.
AD1_REFUSAL = "Out of host capacity"
AD1_REFUSAL_RUNS = ("40983597207", "40985289787", "40988200652", "40989327811")


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


def test_the_data_stays_in_the_availability_domain_that_holds_it() -> None:
    """The volumes live in AD-1 (measured) and the module never moves them."""
    assert _local("volumes_ad") == VOLUMES_AD, (
        f"the surviving volumes are in {VOLUMES_AD}; the module declares "
        f"{_local('volumes_ad')} and the data would be orphaned"
    )


def test_the_placement_is_one_of_the_two_measured_legal_ones() -> None:
    """A shape the AD does not offer, or an AD with no capacity, is refused at apply time."""
    shape = _local("recovery_shape")
    ad = _local("recovery_ad")
    assert (shape, ad) in ALLOWED_PLACEMENTS, (
        f"({shape}, {ad}) is not a measured placement; legal: "
        f"{sorted(ALLOWED_PLACEMENTS)}; measured {MEASURED_AT}"
    )
    offered = SHAPES_BY_AD[ad]
    assert shape in offered, (
        f"{shape} is not offered in {ad} (offered: {', '.join(offered)}); measured {MEASURED_AT}"
    )


def test_the_host_never_attaches_a_volume_across_an_availability_domain() -> None:
    """The attachment set is the guard's answer: all three volumes, or none of them."""
    source = _tf()
    assert "local.recovery_ad == local.volumes_ad" in source, (
        "the attachment guard is gone: a cross-AD attachment would be refused by OCI"
    )
    same_ad = _local("recovery_ad") == _local("volumes_ad")
    expected = SURVIVING_VOLUMES if same_ad else 0
    guard = re.search(
        r"for_each\s*=\s*(local\.recovery_ad\s*==\s*local\.volumes_ad\s*\?\s*local\.surviving_volumes\s*:\s*\{\})",
        source,
        re.DOTALL,
    )
    assert guard, "the attachment for_each is not the availability-domain guard"
    assert expected in (0, SURVIVING_VOLUMES)


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


def test_the_host_is_never_created_before_the_one_it_replaces_is_destroyed() -> None:
    """Two boot volumes at once is 250 GB against a 200 GB allowance: LimitExceeded."""
    source = _tf()
    assert not re.search(r"create_before_destroy\s*=\s*true", source), (
        "create_before_destroy would hold two 50 GB boot volumes at once and be refused"
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


def test_the_ad1_capacity_refusal_is_recorded_with_every_run_that_produced_it() -> None:
    """The reason the AD-2 interim exists is a measurement, and it is auditable."""
    source = _tf()
    assert AD1_REFUSAL in source, (
        "the AD-1 refusal line is not recorded in the module: the placement looks arbitrary"
    )
    for run in AD1_REFUSAL_RUNS:
        assert run in source, f"apply run {run} is not recorded in the module"


def test_the_facts_are_recorded_so_the_test_is_auditable() -> None:
    """A grader that cannot show its facts is a proxy, not a measurement."""
    facts = {
        "measured_at": MEASURED_AT,
        "volumes_ad": VOLUMES_AD,
        "surviving_volumes": SURVIVING_VOLUMES,
        "surviving_volume_gb": SURVIVING_VOLUME_GB,
        "free_storage_gb": FREE_STORAGE_GB,
        "shapes_by_ad": SHAPES_BY_AD,
        "allowed_placements": [list(pair) for pair in sorted(ALLOWED_PLACEMENTS)],
        "ad1_refusal": AD1_REFUSAL,
        "ad1_refusal_runs": list(AD1_REFUSAL_RUNS),
    }
    assert json.loads(json.dumps(facts)) == facts
