"""The avatar's triangles face outward, so the browser draws the face instead of the inside of
the back of its own head.

WHAT THIS GRADES, AND WHY IT EXISTS
-----------------------------------
#5661: `_bust()` wound its rings clockwise as seen from outside. glTF draws the front face of a
triangle whose vertices run counter-clockwise to the viewer, so the renderer culled the outside of
the head and drew the inside of the far wall -- the page showed the back of the head, from within,
and no face. The fix landed in #5658 ("face: draw the outside of the avatar head and give it a neck
and shoulders") and shipped with no test at all. Nothing named the winding, so the identical
one-line reversal -- `[a, b, a+1, ...]` where `_bust()` writes `[a, a+1, b, ...]` -- would have
gone green and put the defect straight back.

The invariant is the one the renderer actually obeys: a triangle's normal, taken by the right-hand
rule from its own vertex order, must point away from the body. This is a bust about a vertical
axis -- head, then neck, then shoulders flaring out -- so "away from the body" is the outward
direction from that axis in the xz plane. A sphere seen from inside fails this everywhere; a
correctly wound one passes everywhere.

Measured on this tree (2026-10-12) before writing the assertion: 4424 of the 4424 non-degenerate
triangles face outward, worst case dot = 0.0476; reversing the winding puts 0 of 4424 outward. So
the test below can fail, which is the only reason it is worth having.

`_bust()` is the generator's geometry, and
tests/test_the_face_avatar_is_commercially_clean_and_reproducible.py::
test_the_committed_glb_matches_its_generator proves that output is byte-for-byte the estate.glb
that ships -- so this grades the asset the browser loads, not a paraphrase of it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[1]
AVATAR = ROOT / "bin/estate-face-avatar"


def _avatar_module() -> dict:
    """Execute bin/estate-face-avatar (no .py extension) and hand back its namespace."""
    ns: dict = {"__name__": "estate_face_avatar_probe", "__file__": str(AVATAR)}
    exec(compile(AVATAR.read_text(), str(AVATAR), "exec"), ns)  # noqa: S102 -- our own script
    return ns


def _outwardness(
    pos: NDArray[np.float64], idx: NDArray[np.uint32]
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """Per-triangle dot(normal from vertex order, outward direction from the body's y axis).

    Returns the graded dot products and a mask of the triangles that could be graded: a triangle
    with no area has no normal, and one sitting exactly on the axis has no outward direction.
    """
    tri = idx.reshape(-1, 3)
    a, b, c = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    n = np.cross(b - a, c - a)
    area = np.linalg.norm(n, axis=1)

    radial = ((a + b + c) / 3.0).copy()
    radial[:, 1] = 0.0  # the body's axis is vertical, so only xz can be "outward"
    reach = np.linalg.norm(radial, axis=1)

    graded = (area > 0) & (reach > 1e-9)
    unit_n = n / np.where(graded[:, None], area[:, None], 1.0)
    unit_r = radial / np.where(graded[:, None], reach[:, None], 1.0)
    return (unit_n * unit_r).sum(1), graded


def test_the_avatar_draws_its_outside():
    """Every triangle the renderer can cull says, by its own winding, 'I face away from the
    body'. If this fails the page draws the inside of the head again -- #5661."""
    pos, _nrm, _uv, idx = _avatar_module()["_bust"]()
    dot, graded = _outwardness(pos, idx)

    triangles = len(idx) // 3
    skipped = triangles - int(graded.sum())
    assert skipped * 50 < triangles, (
        f"{skipped} of {triangles} triangles are exempt from the check (no area, or exactly on "
        f"the axis); a gate that skips this much geometry is not grading the mesh"
    )

    inward = np.flatnonzero(graded & (dot <= 0))
    worst = float(dot[graded].min()) if graded.any() else float("nan")
    assert inward.size == 0, (
        f"{inward.size} of {int(graded.sum())} triangles are wound the wrong way round: their "
        f"normal points back into the body, so glTF culls them and the renderer draws the inside "
        f"of the head (#5661). Worst dot = {worst:.4f}; first offenders = {inward[:5].tolist()}"
    )


def test_the_gate_would_catch_the_reversal_that_caused_5661():
    """The premise of the test above: the same geometry, wound the other way, is reported inward.
    #5661 was exactly this reversal. If this ever stops failing, the test above is decoration."""
    pos, _nrm, _uv, idx = _avatar_module()["_bust"]()
    reversed_idx = idx.reshape(-1, 3)[:, [0, 2, 1]].reshape(-1)

    dot, graded = _outwardness(pos, reversed_idx)
    outward = int((dot[graded] > 0).sum())
    assert outward == 0, (
        f"reversing the winding left {outward} of {int(graded.sum())} triangles still facing "
        f"outward; on a correct tree it must leave none, or this check cannot see the reversal "
        f"that caused #5661"
    )
