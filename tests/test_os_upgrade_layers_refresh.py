"""An OS-upgrade layer must be able to re-run, or a published fix never reaches the image.

build-multiarch reads its layer cache from GHCR (cache-from type=registry). A RUN that upgrades
OS packages has the same text and the same parent every build, so BuildKit replays it: lago-api
amd64 in main run 46012162636 printed `#8 CACHED` for `apt-get upgrade` while Trivy refused the
image for libbrotli1 1.1.0-2+b7, fixed in 1.1.0-2+deb13u1. The daily 04:23 sweep reads the same
cache, so it rescanned the same stale bytes. Eight images sat red on main (idp#8655).

Rule, per image bin/dockerfiles lists: every RUN that upgrades OS packages is preceded, in its
own stage, by `ARG OS_PACKAGES_AS_OF`. A changed value is a cache miss at that RUN, so the
default (the date of the change) re-runs it on landing and build-multiarch passing the UTC date
re-runs it daily, while every layer before it stays cached.
"""

import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
UPGRADE = re.compile(
    r"apt-get\s+(?:-\S+\s+)*(?:dist-)?upgrade|--only-upgrade|apk\s+(?:-\S+\s+)*upgrade"
    r"|(?:dnf|microdnf|yum)\s+(?:-\S+\s+)*(?:upgrade|update)\b"
)
ARG = re.compile(r"^ARG\s+OS_PACKAGES_AS_OF\b", re.I)


def logical_lines(text: str) -> list[str]:
    """Dockerfile instructions, with backslash continuations joined and comments dropped."""
    out, cur = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not cur and (not line or line.startswith("#")):
            continue
        if cur and line.startswith("#"):
            continue
        if line.endswith("\\"):
            cur += line[:-1] + " "
            continue
        out.append(cur + line)
        cur = ""
    if cur:
        out.append(cur)
    return out


def violations(text: str) -> list[str]:
    out, armed, stage = [], False, 0
    for line in logical_lines(text):
        if re.match(r"^FROM\s", line, re.I):
            armed, stage = False, stage + 1
        elif ARG.match(line):
            armed = True
        elif re.match(r"^RUN\s", line, re.I) and UPGRADE.search(line) and not armed:
            out.append(
                f"stage {stage}: OS upgrade without ARG OS_PACKAGES_AS_OF before it"
            )
    return out


def images() -> list[dict]:
    listing = subprocess.run(  # noqa: S603 -- the estate's own image inventory
        [str(ROOT / "bin" / "dockerfiles"), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(listing.stdout)


IMAGES = images()
UPGRADING = [d for d in IMAGES if UPGRADE.search((ROOT / d["dockerfile"]).read_text())]


def test_the_inventory_finds_upgrading_images():
    # An inventory that finds nothing would make every case below vacuous.
    assert {"lago-api", "lago-front", "sovereign-worker"} <= {
        d["name"] for d in UPGRADING
    }


@pytest.mark.parametrize("d", UPGRADING, ids=lambda d: d["name"])
def test_os_upgrade_layer_can_rerun(d):
    assert violations((ROOT / d["dockerfile"]).read_text()) == []


GOOD = (
    "FROM debian:13 AS b\n"
    "ARG OS_PACKAGES_AS_OF=2026-11-27\n"
    "RUN apt-get update \\\n    && apt-get upgrade -y \\\n    && rm -rf /var/lib/apt/lists/*\n"
)


def test_known_good_passes():
    assert violations(GOOD) == []


@pytest.mark.parametrize(
    "text",
    [
        # lago-api on main: the upgrade has nothing that can change its cache key
        "FROM getlago/api:v1.52.1\nRUN apt-get update \\\n    && apt-get upgrade -y\n",
        # lago-front on main
        "FROM getlago/front:v1.52.1\nRUN apk upgrade --no-cache\n",
        # hindsight-api's partial upgrade is still an upgrade
        "FROM x\nRUN apt-get install -y --only-upgrade perl-base\n",
        # the ARG after the upgrade does not reach it
        "FROM x\nRUN apt-get upgrade -y\nARG OS_PACKAGES_AS_OF=2026-11-27\n",
        # an ARG in an earlier stage does not reach a later stage
        "FROM x AS a\nARG OS_PACKAGES_AS_OF=1\nFROM y\nRUN apk upgrade\n",
        # a commented-out ARG is not an ARG
        "FROM x\n# ARG OS_PACKAGES_AS_OF=1\nRUN dnf upgrade -y\n",
    ],
)
def test_known_bad_is_refused(text):
    assert violations(text), text


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        n = sum(
            bool(violations((ROOT / d["dockerfile"]).read_text())) for d in UPGRADING
        )
        print(f"optimus.images.os_upgrade_layer_not_refreshable={n}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
