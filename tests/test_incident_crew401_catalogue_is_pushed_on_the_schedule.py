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


def test_incident_crew401_render_commit_subject_names_a_ticket():
    """Measured 2026-08-27: no live-diagram PR merged since 2026-08-25T21:16Z because the
    commit-msg default (crew#53) refused every scheduled commit: the subject named no issue and
    the branch state/live-diagram names none either. The subject the renderer commits with must
    carry an issue reference; the branch cannot be relied on for it."""
    src = (ROOT / "bin" / "catalog-render").read_text()
    subjects = re.findall(r'"docs\(architecture\): [^"\n]*', src)
    assert subjects, "renderer no longer commits a docs(architecture) subject"
    for s in subjects:
        assert re.search(r"(crew|idp)#\d+", s), s
