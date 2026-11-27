"""hindsight-api's vendor venv carries no fixable CRITICAL below its floor (idp#6113).

ghcr.io/vectorize-io/hindsight-api:0.9.2 ships a venv whose certifi, claude-agent-sdk, pillow
and uv are below the first fixed version of a CRITICAL advisory (main build-multiarch run
46043500706, 2026-11-27). hindsight-api.Dockerfile installs floors for them and asserts the
installed versions. These tests prove every advisory below has a floor at or above its fix,
and that the check would catch a missing or a low floor. `--optimus` prints the count of
advisories the Dockerfile does not floor.
"""

from __future__ import annotations

import re
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


if __name__ == "__main__" and "--optimus" in sys.argv:
    print(
        f"optimus.images.hindsight_api_critical_pkgs_unfloored={len(unfloored(DOCKERFILE.read_text()))}"
    )
