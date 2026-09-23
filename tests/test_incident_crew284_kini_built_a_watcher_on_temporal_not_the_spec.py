"""crew#284 / crew#396, founder 2026-08-30: "what I spec'd was not what was built; I wouldn't spec
a dumb watcher to use Temporal; that's just silly."

The KINI spec (docs/reference/specs/kini-master-spec.md) is a sovereign control plane. What ran
was a Temporal server + Postgres + worker serving two 15-minute receipt CronJobs, red since
2026-08-27. The Flux row stays suspended until crew#284 carries a checkpoint the founder used;
un-suspending it is a founder decision recorded on that ticket, and this test pins the state.
"""

from pathlib import Path

import yaml

PLATFORM = Path(__file__).resolve().parents[1] / "clusters" / "oke" / "platform.yaml"


def _row(name: str) -> dict:
    for doc in yaml.safe_load_all(PLATFORM.read_text()):
        if (
            doc
            and doc.get("kind") == "Kustomization"
            and doc["metadata"]["name"] == name
        ):
            return doc
    raise AssertionError(f"no Kustomization named {name}")


def test_temporal_row_is_suspended_on_the_founders_word():
    assert _row("temporal")["spec"].get("suspend") is True


def test_nothing_else_in_the_file_depends_on_temporal():
    for doc in yaml.safe_load_all(PLATFORM.read_text()):
        if not doc or doc.get("kind") != "Kustomization":
            continue
        deps = [d["name"] for d in doc["spec"].get("dependsOn", [])]
        assert "temporal" not in deps, doc["metadata"]["name"]
