"""crew#307, 2026-08-29. The founder's surfaces (every stack with a URL) and the god view
vanished from the live portal home, and no playbook could say why: nothing read the
catalogue pod. Diagnose now prints the founder file, the ConfigMaps, the catalogue log
and the catalogue API's founder-surface entities. This test pins those four rows."""
from pathlib import Path

PLAYBOOK = Path(__file__).resolve().parents[1] / "bin" / "idp-oke-break-glass"
ROWS = (
    "catalogue-founder-file",
    "catalogue-founder-configmap",
    "catalogue-log-locations",
    "catalogue-entities",
)


def test_diagnose_reads_the_founder_catalogue_in_the_pod():
    text = PLAYBOOK.read_text()
    missing = [row for row in ROWS if f"show {row} " not in text]
    assert not missing, f"diagnose no longer prints {missing}; the founder surfaces can vanish unseen again"
    assert "/estate/founder" in text
    assert "spec.type=founder-surface" in text
