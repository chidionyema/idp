"""hindsight-api's vendor venv carries no fixable CRITICAL below its floor (idp#6113).

ghcr.io/vectorize-io/hindsight-api:0.9.2 ships a venv whose certifi, claude-agent-sdk, pillow
and uv are below the first fixed version of a CRITICAL advisory (main build-multiarch run
46043500706, 2026-11-27). hindsight-api.Dockerfile installs floors for them and asserts the
installed versions. These tests prove every advisory below has a floor at or above its fix,
and that the check would catch a missing or a low floor. `--optimus` prints the count of
advisories the Dockerfile does not floor.

idp#8667: Trivy scans every site-packages in the image, and main run 46049122666 failed on uv
0.12.5 in the base image's system interpreter while the check looked at the venv alone. The tests
below run the Dockerfile's own check against a fake image tree: it must refuse a low package in any
interpreter and refuse a scan that found no interpreter under /usr. `--optimus` also prints
whether the check still passes a low system-interpreter package (1 on main 86a662e3c, 0 here).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "platform/hindsight/hindsight-api.Dockerfile"

# package -> the first version that fixes a CRITICAL the vendor venv carries.
ADVISORIES = {
    "certifi": "2026.10.18",  # GHSA-6q48-6c7w-9gw2
    "claude-agent-sdk": "0.2.121",  # CVE-2026-96620
    "pillow": "13.0.0",  # CVE-2026-112393 and four more
    "uv": "0.13.4",  # GHSA-hq85-5cpj-mr62
}


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split(".")[:3])


def floors(dockerfile: str) -> dict[str, str]:
    """package -> the `>=` floor the Dockerfile's `uv pip install` takes."""
    return {
        name.lower(): version
        for name, version in re.findall(
            r"'([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?>=([0-9][0-9.]*)'", dockerfile
        )
    }


def unfloored(dockerfile: str) -> list[str]:
    got = floors(dockerfile)
    return [
        p
        for p, fixed in ADVISORIES.items()
        if p not in got or _key(got[p]) < _key(fixed)
    ]


def asserted(dockerfile: str) -> dict[str, str]:
    """package -> floor in the build-time `floors = {...}` assertion."""
    m = re.search(r"floors = \{([^}]*)\}", dockerfile)
    return dict(re.findall(r"'([a-z0-9_.-]+)': '([0-9.]+)'", m.group(1))) if m else {}


def test_every_advisory_is_floored_at_or_above_its_fix():
    assert unfloored(DOCKERFILE.read_text()) == []


def test_the_build_asserts_the_installed_versions_against_the_same_floors():
    text = DOCKERFILE.read_text()
    assert asserted(text) == {p: floors(text)[p] for p in ADVISORIES}
    assert "assert not low, low" in text


def test_falsifier_a_missing_floor_is_counted():
    text = "uv pip install 'pyjwt[crypto]>=2.14.0' 'pillow>=13.0.0'"
    assert unfloored(text) == ["certifi", "claude-agent-sdk", "uv"]


def test_falsifier_a_floor_below_the_fix_is_counted():
    text = (
        "'certifi>=2026.10.18' 'claude-agent-sdk>=0.2.87' 'pillow>=12.3.0' 'uv>=0.13.4'"
    )
    assert unfloored(text) == ["claude-agent-sdk", "pillow"]


FIXED = dict(ADVISORIES)
VENV = "app/api/.venv/lib/python3.11/site-packages"
SYSTEM = "usr/local/lib/python3.11/site-packages"


def build_check(dockerfile: str) -> str:
    """The python the Dockerfile runs after the install, as the shell hands it to python -c."""
    m = re.search(r'/app/api/\.venv/bin/python -c "\\\n(.*?)"\n', dockerfile, re.S)
    assert m, "no build-time floor check"
    return m.group(1).replace(" \\\n", " ").replace("\\\n", "")


def run_check(
    dockerfile: str, root: Path, sites: dict[str, dict[str, str]]
) -> subprocess.CompletedProcess:
    """Run the Dockerfile's check against a fake image tree rooted at `root`."""
    for site, pkgs in sites.items():
        for name, version in pkgs.items():
            d = root / site / f"{name.replace('-', '_')}-{version}.dist-info"
            d.mkdir(parents=True, exist_ok=True)
            (d / "METADATA").write_text(
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            )
    script = (
        build_check(dockerfile)
        .replace("'/usr", f"'{root}/usr")
        .replace("'/app'", f"'{root}/app'")
    )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(root / VENV),
        "PYTHONNOUSERSITE": "1",
    }
    return subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def passes_a_low_system_package(dockerfile: str, root: Path) -> bool:
    return (
        run_check(dockerfile, root, {VENV: FIXED, SYSTEM: {"uv": "0.12.5"}}).returncode
        == 0
    )


def test_the_system_interpreter_raises_uv_too():
    assert re.search(
        r"/usr/local/bin/python3 -m pip install [^\n]*'uv>=0\.13\.4'",
        DOCKERFILE.read_text(),
    )


def test_the_check_passes_an_image_at_every_floor(tmp_path):
    r = run_check(
        DOCKERFILE.read_text(), tmp_path, {VENV: FIXED, SYSTEM: {"uv": "0.13.10"}}
    )
    assert r.returncode == 0, r.stderr


def test_the_check_refuses_a_low_package_in_the_system_interpreter(tmp_path):
    r = run_check(
        DOCKERFILE.read_text(), tmp_path, {VENV: FIXED, SYSTEM: {"uv": "0.12.5"}}
    )
    assert r.returncode != 0 and "uv" in r.stderr


def test_the_check_refuses_a_scan_that_found_no_system_interpreter(tmp_path):
    r = run_check(DOCKERFILE.read_text(), tmp_path, {VENV: FIXED})
    assert r.returncode != 0


def test_falsifier_a_venv_only_check_passes_the_low_system_uv(tmp_path):
    venv_only = """/app/api/.venv/bin/python -c "\\
import importlib.metadata as m; \\
floors = {'uv': '0.13.4'}; \\
key = lambda v: tuple(int(x) for x in v.split('.')[:3]); \\
low = {n: m.version(n) for n, f in floors.items() if key(m.version(n)) < key(f)}; \\
assert not low, low"
"""
    assert passes_a_low_system_package(venv_only, tmp_path)


if __name__ == "__main__" and "--optimus" in sys.argv:
    import tempfile

    text = DOCKERFILE.read_text()
    print(
        f"optimus.images.hindsight_api_critical_pkgs_unfloored={len(unfloored(text))}"
    )
    with tempfile.TemporaryDirectory() as d:
        print(
            f"optimus.images.hindsight_api_floor_sites_unchecked={int(passes_a_low_system_package(text, Path(d)))}"
        )
