"""crew#401 CP4 (2026-08-27): the portal on the cluster reads the estate catalogue from an OCI
artifact (clusters/oke/catalog.yaml). bin/catalog-render regenerated the file after every hourly
inventory but only a person running bin/idp-catalog-push ever published it; measured
2026-08-27 00:40Z: ghcr estate-catalog last updated 2026-08-25T23:38:54Z, inventory taken
2026-08-26T18:14:33Z. Rule (rung 4): the scheduled render publishes what it generates, and a
machine that cannot publish says BLIND rather than staying silent.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_incident_crew401_render_pushes_the_catalogue_after_generating_it():
    src = (ROOT / "bin/catalog-render").read_text()
    gen, push = src.index('"catalog-gen"'), src.index("idp-catalog-push")
    unchanged = src.index("page unchanged")
    assert gen < push < unchanged, "the push must follow catalog-gen and run even when the page is unchanged"
    assert re.search(r'"BLIND ".*catalogue push', src), "a machine that cannot push must say BLIND"

