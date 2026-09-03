"""Incident test (rung 4), run 33447033447, 2026-08-31: tofu-apply failed 400
`InsufficientServicePermissions — Permissions granted to the object storage service principal
"objectstorage-uk-london-1" to this bucket are insufficient` on
oci_objectstorage_object_lifecycle_policy.shop_backups. Oracle's lifecycle page
(Content/Object/Tasks/usinglifecyclepolicies.htm): lifecycle rules run as the regional Object
Storage service principal, and that principal needs its own Allow-service grant, created in the
root compartment of the tenancy, on top of any user or group policy. The bucket and rules were
declared (idp crew#713 CP1) but the service grant never was, so every apply since the lifecycle
resource landed has failed at this step.

The grant lives in platform/oci/policy/estate-operators.statements.json: the tenancy-root copy is
written by the founder's bin/idp-oci-bootstrap run, the compartment copy by iam.tf from CI, and
bin/idp-iam-policy-drift grades both. A future edit that drops the line or trims the delete
permissions re-breaks the nightly apply silently — this test names it."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "platform" / "oci" / "policy" / "estate-operators.statements.json"
TF = ROOT / "platform" / "oci" / "shop-backups.tf"


def test_the_statements_ledger_grants_the_object_storage_service_principal():
    statements = json.loads(FILE.read_text())
    service = [s for s in statements if s.startswith("Allow service objectstorage-")]
    assert service, (
        "run 33447033447: no Allow-service statement for the Object Storage principal; "
        "the lifecycle policy on the shop-backups bucket fails 400 InsufficientServicePermissions"
    )
    (grant,) = service
    assert " to manage object-family in compartment estate" in grant, (
        "the service grant must cover object-family in the estate compartment"
    )
    for perm in ("OBJECT_DELETE", "OBJECT_VERSION_DELETE"):
        assert perm in grant, (
            f"the shop-backups lifecycle rules delete objects and previous versions; "
            f"without {perm} the apply fails 400 again"
        )


def test_the_grant_names_the_region_the_lifecycle_resource_lives_in():
    """The service principal is regional (objectstorage-<region>); a grant for another region is
    a grant for nobody. The lifecycle resource deploys where the provider does: uk-london-1."""
    statements = json.loads(FILE.read_text())
    (grant,) = [s for s in statements if s.startswith("Allow service objectstorage-")]
    assert grant.startswith("Allow service objectstorage-uk-london-1 "), (
        "the estate runs in uk-london-1; the Object Storage service principal is per-region"
    )
    assert re.search(
        r'resource\s+"oci_objectstorage_object_lifecycle_policy"', TF.read_text()
    ), (
        "the grant exists for the shop-backups lifecycle resource; if that resource is gone, "
        "remove the grant too"
    )
