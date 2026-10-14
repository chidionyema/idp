"""The hourly face probe grades the asset, not the status code.

2026-10-14: probes/surfaces.py built each face asset URL from the file's basename, so
three/build/three.module.js was fetched as /face/three.module.js. That path does not exist; the
SPA answered it with its 10835B HTML shell, and "200, >=1000B, no login page" graded eleven
scripts PASS every hour. The same run enumerated the voice states as EMPTY.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from probes import surfaces  # noqa: E402

SPA_SHELL = "<!DOCTYPE html><html><head><title>Estate</title>" + "x" * 10_800


def test_face_assets_are_probed_at_the_path_they_are_served_from():
    assets = surfaces.enumerate_inventory()["face_assets"]
    assert "/face/three/build/three.module.js" in assets
    assert "/face/brunette.glb" in assets
    assert "/face/three.module.js" not in assets


def test_the_voice_states_enumerate():
    states = surfaces.enumerate_inventory()["voice_states"]
    assert {"off", "listening", "thinking", "speaking", "error"} <= set(states)


def _grade(bodies: dict[str, str]) -> dict[str, bool]:
    inv = {"public_pages": [], "pages": [], "face_assets": sorted(bodies)}

    def get(url, timeout=15):
        return 200, bodies[url.removeprefix("https://h")]

    return {
        a["name"]: a["ok"] for a in surfaces.l1_gate_battery("https://h", inv, get=get)
    }


def test_an_html_shell_where_a_script_should_be_fails():
    graded = _grade({"/face/three/build/three.module.js": SPA_SHELL})
    assert graded == {"l1.gate/face/three/build/three.module.js": False}


def test_a_model_that_is_not_gltf_fails():
    graded = _grade({"/face/brunette.glb": SPA_SHELL})
    assert graded == {"l1.gate/face/brunette.glb": False}


def test_the_real_assets_pass():
    graded = _grade(
        {
            "/face/three/build/three.module.js": "/**\n * @license\n" + "x" * 2_000,
            "/face/brunette.glb": "glTF\x02\x00\x00\x00" + "x" * 2_000,
        }
    )
    assert all(graded.values()), graded
