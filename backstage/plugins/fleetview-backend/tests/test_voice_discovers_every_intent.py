"""The voice operator can name every committed intent when asked -- the discovery process.

Founder 2026-09-29: a capability told to the founder in chat is void; nothing in the estate
will surface it again. So the committed catalogue enters every voice answer (voice.catalog_block)
and a committed intent without a description the operator could speak is refused here, before
it can be merged undiscoverable.
"""

from __future__ import annotations

import pathlib

import yaml
from fleetview_backend import voice, voice_intents as vi

REPO = pathlib.Path(__file__).resolve().parents[4]
INTENTS = REPO / "platform" / "estate" / "intents"


def test_every_committed_intent_has_a_description_the_operator_can_speak() -> None:
    missing = []
    for path in sorted(INTENTS.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text()) or {}
        desc = " ".join(str(doc.get("description") or "").split())
        if len(desc) < 20:
            missing.append(path.name)
    assert not missing, f"undiscoverable by voice (no description): {missing}"


def test_catalog_block_names_every_voice_reachable_intent() -> None:
    block = voice.catalog_block()
    for name in vi.load_catalog():
        spoken = name.replace("-", " ").replace(".", " ").replace("_", " ")
        assert f"say '{spoken}'" in block, name
        assert vi.description(name), name


def test_catalog_block_is_in_the_operators_brief(monkeypatch, tmp_path) -> None:
    d = tmp_path / "intents"
    d.mkdir()
    (d / "policy-status.yaml").write_text(
        "name: policy-status\ndescription: What the policy gate decided today.\n"
        "steps:\n  - cmd: echo\n"
    )
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(d))
    block = voice.catalog_block()
    assert "say 'policy status': What the policy gate decided today." in block
    assert "asked what can be asked" in voice.SYSTEM
