"""Founder, 2026-08-29: "no cryptic shit in backstage -- it's a founder's surface."
Measured that day on main: 10 of the 18 founder-surface descriptions in
backstage/founder/catalog-info.yaml carried a ticket code, a checkpoint number or a hash,
and two link labels read "Tracked item crew#NNN". Rung 4, incident test (crew#612 CP4).

Rule: every title, description and link label on a founder surface is plain English --
no crew#NNN, idp#NNN, CPn, commit hash or run id in the sentence. Receipts go in the
link URL, never in the words he reads.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"
CRYPTIC = re.compile(r"\b(?:crew|idp|cg)#\d+|\bCP\d+\b|\b[0-9a-f]{7,40}\b|\b\d{9,}\b")


def _founder_surfaces():
    docs = [d for d in yaml.safe_load_all(FOUNDER.read_text()) if d]
    return [d for d in docs if (d.get("spec") or {}).get("type") == "founder-surface"]


def test_founder_surface_words_carry_no_ticket_code_hash_or_run_id():
    surfaces = _founder_surfaces()
    assert len(surfaces) >= 18, "the founder catalogue lost entities"
    bad = []
    for d in surfaces:
        m = d["metadata"]
        fields = {"title": m.get("title", ""), "description": m.get("description", "")}
        for i, link in enumerate(m.get("links") or []):
            fields[f"links[{i}].title"] = link.get("title", "")
        for field, text in fields.items():
            hit = CRYPTIC.search(str(text))
            if hit:
                bad.append(f"{m['name']}.{field}: ...{hit.group(0)}...")
    assert not bad, "\n".join(bad)


def test_the_check_itself_catches_each_cryptic_shape():
    for sample in ("done in crew#612", "see CP4", "at b426a4d", "run 33034521953", "idp#661 merged"):
        assert CRYPTIC.search(sample), sample
    for clean in ("Every model call goes through here", "P1 = a fire", "seven KINI checkpoints", "/ui"):
        assert not CRYPTIC.search(clean), clean
