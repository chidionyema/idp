import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader(
    "sb", str(ROOT / "bin/idp-storage-budget")
)
_spec = importlib.util.spec_from_loader("sb", _loader)
sb = importlib.util.module_from_spec(_spec)
_loader.exec_module(sb)

TF = "boot_volume_size = 100\nboot_volume_size = 100\n"


def test_small_pvcs_round_up_to_the_csi_minimum():
    ok, total, _, pvcs = sb.check(
        TF, {"a.yaml": "storageClass: oci-bv\nsize: 10Gi"}, nodes=1
    )
    assert pvcs == [("a.yaml", 50)] and total == 150 and ok


def test_two_nodes_plus_three_pvcs_exceeds_the_allowance():
    files = {f"{i}.yaml": "storageClass: oci-bv\nsize: 5Gi" for i in range(3)}
    ok, total, limit, _ = sb.check(TF, files, nodes=2)
    assert not ok and total == 350 and limit == 200


def test_non_oci_bv_claims_are_not_counted():
    assert sb.pvc_gb({"a.yaml": "storageClassName: local-path\nstorage: 5Gi"}) == []


def test_the_current_tree_reports_its_demand():
    files = {
        str(p.relative_to(ROOT)): p.read_text()
        for p in (ROOT / "platform").rglob("*.yaml")
    }
    _, total, _, _ = sb.check(
        (ROOT / "platform/oci/main.tf").read_text(), files, nodes=1
    )
    assert total > 0
