"""The shipped face avatar, graded on the asset itself.

Three facts have to hold, and each was a live defect:

1. The avatar the face loads carries a recorded licence, and when that licence is non-commercial
   the debt is declared, dated and printed -- never silent. The face shipped brunette.glb (Ready
   Player Me, CC BY-NC 4.0 -- non-commercial) into a product the estate is trying to sell; that
   was a sentence in VERSIONS nothing read, which is the defect. bin/face-licence-gate refuses a
   NEW non-commercial asset outright, and carries the one the founder restored on 2026-10-10
   (brunette.glb; estate.glb renders as a featureless bust, issue #5673) as dated debt in
   bin/face-licence-known-blockers. This proves the gate is wired to the real tree AND that the
   asset it grades is the asset the face loads.

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
import re
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


def test_the_non_commercial_avatar_is_a_declared_debt_not_a_silent_one():
    """brunette.glb ships by founder decision (2026-10-10, issue #5673). The licence defect was
    never that it shipped -- it was that nothing read the sentence saying it must not. So grade
    the declaration, not the asset's absence."""
    assert GLB.is_file(), (
        "the face ships estate.glb, the generator's estate-owned output"
    )
    shipped = GLB.parent / "brunette.glb"
    assert shipped.is_file(), (
        "brunette.glb is the avatar the face loads (faceEngine.ts showAvatar) since the "
        "2026-10-10 founder decision; if it is gone, delete its entry from "
        "bin/face-licence-known-blockers in the same change"
    )
    text = VERSIONS.read_text()
    assert "estate.glb" in text
    assert "brunette" in text, (
        "the licence record must name the non-commercial asset that ships, or the debt is silent"
    )
    known = (ROOT / "bin/face-licence-known-blockers").read_text()
    assert "brunette.glb: " in known, (
        "a non-commercial asset may ship only as a declared, dated entry in the ratchet; a "
        "non-commercial asset with no entry is the original defect"
    )


def test_the_licence_gate_carries_the_debt_and_claims_no_clearance():
    r = _run(str(GATE))
    assert r.returncode == 0, (
        f"bin/face-licence-gate refused the shipped tree:\n{r.stdout}{r.stderr}"
    )
    assert "PASS-WITH-DEBT" in r.stdout, (
        "the gate must not claim clean clearance while a non-commercial asset ships"
    )
    assert "brunette.glb is non-commercial and still shipped" in r.stdout, (
        "the carried debt must be printed, not merely tolerated"
    )
    assert "every face asset carries a commercial licence" not in r.stdout, (
        "that verdict line means 'no debt', and debt is carried"
    )


def test_the_gate_grades_the_avatar_the_face_actually_loads():
    """The gate claims to grade "the assets the face actually loads". That is only true if it
    reads the load: a GLB fetched from anywhere but the directory it globs would be graded by
    nothing while the glob passed. faceEngine.ts is where the face names its avatar."""
    src = ROOT / "backstage/packages/app/src/modules/home/faceEngine.ts"
    loaded = set(re.findall(r"([A-Za-z0-9_.-]+\.glb)", src.read_text()))
    assert loaded, "faceEngine.ts must name the avatar it loads"
    r = _run(str(GATE), "--list")
    assert r.returncode == 0, (
        f"bin/face-licence-gate --list failed:\n{r.stdout}{r.stderr}"
    )
    listed = set(re.findall(r"([A-Za-z0-9_.-]+\.glb)", r.stdout))
    missing = loaded - listed
    assert not missing, (
        f"the face loads {sorted(missing)} and bin/face-licence-gate does not grade it; "
        f"the gate grades only what it lists: {sorted(listed)}"
    )


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
