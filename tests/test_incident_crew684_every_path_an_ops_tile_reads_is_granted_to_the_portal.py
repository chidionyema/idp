"""crew#684 incident (2026-08-30 05:01Z, login drill run 33294482021): the Ops page's cluster tile
read /api/v1/nodes through the Kubernetes plugin with the catalogue's own ServiceAccount, and
platform/backstage/base/rbac.yaml had never granted nodes, so the API answered 403 and the page
was red. A tile that reads a cluster path ships only with the read right that path needs: every
API path constant in the home modules maps to a rule in the portal's ClusterRole.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home"
RBAC = ROOT / "platform" / "backstage" / "base" / "rbac.yaml"

# '/api/v1/<resource>' (core group) or '/apis/<group>/<version>/<resource>'
PATH = re.compile(
    r"'/api(?:s/(?P<group>[a-z0-9.-]+)/v[0-9a-z]+|/v1)/(?P<resource>[a-z]+)'"
)


def _paths_the_tiles_read() -> set[tuple[str, str]]:
    found = set()
    for ts in HOME.glob("*.ts"):
        if ts.name.endswith(".test.ts"):
            continue
        for m in PATH.finditer(ts.read_text()):
            found.add((m.group("group") or "", m.group("resource")))
    return found


def _granted_reads(rbac_text: str) -> set[tuple[str, str]]:
    granted = set()
    for doc in yaml.safe_load_all(rbac_text):
        if not doc or doc.get("kind") != "ClusterRole":
            continue
        for rule in doc["rules"]:
            if not {"get", "list"} <= set(rule["verbs"]):
                continue
            for group in rule["apiGroups"]:
                for res in rule["resources"]:
                    granted.add((group, res))
    return granted


def test_every_cluster_path_an_ops_tile_reads_is_granted_get_and_list() -> None:
    read = _paths_the_tiles_read()
    assert ("", "nodes") in read, "the incident's own path is the first case"
    missing = sorted(read - _granted_reads(RBAC.read_text()))
    assert not missing, (
        f"the Ops page reads {missing} but platform/backstage/base/rbac.yaml grants no get+list "
        "on them: the tile answers 403 and the login drill fails the page"
    )
