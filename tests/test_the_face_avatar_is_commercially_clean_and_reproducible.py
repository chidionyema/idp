"""The shipped face avatar, graded on the asset itself.

Three facts have to hold, and each was a live defect:

1. The avatar is commercially licensed. The face shipped brunette.glb (Ready Player Me, CC BY-NC
   4.0 -- non-commercial) into a product the estate is trying to sell. bin/face-licence-gate
   refuses that now; this proves the gate is still wired to the real tree.

2. The committed GLB matches the generator that claims to have authored it. The licence record
   says "authored by bin/estate-face-avatar"; this is what makes the claim checkable.

3. The generator is deterministic. This is the one that actually broke (2026-10-04): bone
   positions are accumulated by float addition, producing values like 0.45999999999999996, and
   `json.dumps` writes them through `repr()` -- which is not guaranteed byte-identical across
   CPython builds. The same script produced different bytes in the CI container than on the
   laptop, `--check` failed, and portal-app went red with an empty error string. The fix rounds
   every embedded float to 6dp; this test pins that property so the noise cannot return.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AVATAR = ROOT / "bin/estate-face-avatar"
GATE = ROOT / "bin/face-licence-gate"
GLB = ROOT / "backstage/packages/app/public/face/estate.glb"
VERSIONS = ROOT / "backstage/packages/app/public/face/VERSIONS"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _avatar_module() -> dict:
    """Execute bin/estate-face-avatar (no .py extension) and hand back its namespace."""
    ns: dict = {"__name__": "estate_face_avatar_probe", "__file__": str(AVATAR)}
    exec(compile(AVATAR.read_text(), str(AVATAR), "exec"), ns)  # noqa: S102 -- our own script
    return ns


def test_the_non_commercial_avatar_is_gone_and_the_shipped_one_is_estate_owned():
    assert GLB.is_file(), "the face ships estate.glb"
    assert not (GLB.parent / "brunette.glb").exists(), (
        "brunette.glb is CC BY-NC 4.0 and cannot ship in a commercial product; it must not return"
    )
    text = VERSIONS.read_text()
    assert "estate.glb" in text
    assert "commercial" in text.lower()
    assert "brunette" not in text, (
        "the licence record must not still describe the removed asset"
    )


def test_the_licence_gate_passes_on_the_real_tree():
    r = _run(str(GATE))
    assert r.returncode == 0, (
        f"bin/face-licence-gate refused the shipped tree:\n{r.stdout}{r.stderr}"
    )
    assert "every face asset carries a commercial licence" in r.stdout


def test_the_committed_glb_matches_its_generator():
    r = _run(sys.executable, str(AVATAR), "--check")
    assert r.returncode == 0, (
        "the committed asset and bin/estate-face-avatar disagree; regenerate and commit:\n"
        f"{r.stdout}{r.stderr}"
    )
    assert "matches the generator" in r.stdout


def test_the_generator_emits_no_float_that_carries_accumulation_noise():
    """The exact defect: a float like 0.45999999999999996 is an accumulation artefact, and its
    repr is what drifted between interpreters. This grades the bytes the generator WOULD write,
    not the committed file -- a stale commit must not be able to hide a noisy generator."""
    ns = _avatar_module()
    world = ns["_bone_world_positions"]()
    # The raw accumulator DOES produce noise -- that is the premise, and if this ever stops being
    # true the test below would pass vacuously.
    raw_noisy = [f for v in world.values() for f in v if len(repr(float(f))) > 14]
    assert raw_noisy, "premise check: the accumulator is expected to produce fp noise"

    # Grade what the generator actually serialises: read the JSON chunk out of build().
    data = ns["build"]()
    assert data[0:4] == b"glTF"
    length = int.from_bytes(data[12:16], "little")
    gltf = json.loads(data[20 : 20 + length].decode("utf8"))

    # EVERY float in the document, not just the bone translations. The 106 values that actually
    # drifted live in accessors[].min/max -- mesh bounding boxes computed from float32 vertex
    # data (e.g. -0.0949999988079071). Their repr is what differed between interpreters.
    def floats(o, path=""):
        if isinstance(o, bool):
            return
        if isinstance(o, float):
            yield path, o
        elif isinstance(o, dict):
            for k, v in o.items():
                yield from floats(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from floats(v, f"{path}[{i}]")

    noisy = [(p, f) for p, f in floats(gltf) if round(f, 6) != f]
    assert not noisy, (
        f"{len(noisy)} floats in the serialised GLTF are not 6dp-rounded, so their repr is not "
        f"stable across interpreters and --check becomes a coin flip: {noisy[:5]}"
    )
    # -0.0 reprs as '-0.0' and is a second source of byte drift.
    assert repr(ns["_quantise"](-0.0)) == "0.0", (
        "negative zero must collapse or the bytes can differ"
    )


def test_two_builds_of_the_avatar_are_byte_identical():
    """Determinism by construction: same source, same bytes, in the same interpreter."""
    ns = _avatar_module()
    assert ns["build"]() == ns["build"](), "build() is not deterministic"


def test_the_embedded_json_is_serialisable_and_carries_no_float_noise():
    """Read the real GLB's JSON chunk the way a loader does, and check what actually shipped."""
    buf = GLB.read_bytes()
    assert buf[0:4] == b"glTF", "not a GLB container"
    length = int.from_bytes(buf[12:16], "little")
    gltf = json.loads(buf[20 : 20 + length].decode("utf8"))
    # Bone translations are what is accumulated; they are the ones that drifted.
    noise = []
    for node in gltf.get("nodes", []):
        for f in node.get("translation", []):
            if round(f, 6) != f:
                noise.append((node.get("name"), f))
    assert not noise, (
        f"shipped node translations carry float-accumulation noise, so the bytes are not "
        f"reproducible across interpreters: {noise[:5]}"
    )
