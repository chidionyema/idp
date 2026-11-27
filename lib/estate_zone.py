"""The estate's DNS zone, resolved the one way every reader resolves it.

The zone is written once, in clusters/<cluster>/estate-config.yaml (ESTATE_ZONE; LAW 46). Every
reader that needs a hostname -- the router front, the voice engine, the estate's own tools -- asks
this module, so the zone is read in one place instead of copied into twenty files with twenty
different failure modes. Measured 2026-11-17: the router front died at import under launchd on a
bare os.environ["ESTATE_ZONE"], and the voice loop died the same way, because the laptop has no
shell profile that exports the zone.

Two sources, in this order:
  1. the environment, because the cluster's ConfigMap sets ESTATE_ZONE for every workload;
  2. the file that declares it, because the laptop has no exported zone (measured: printenv
     ESTATE_ZONE is empty in this machine's session) and the tree that declares it is right
     here -- clusters/*/estate-config.yaml, whichever cluster tree holds it.

An unknown zone is an empty string, never an exception. A reader that cannot know the zone says
so and stops; it never dials a guessed host.

The module lives in lib/ beside estate_spatial.py, the estate's other shared resolver, and is
imported the same way (a sys.path insert of the tree's lib/ directory), so it can be copied into
a container image the way that one is (see fleetview-backend.Dockerfile).

    python3 lib/estate_zone.py          # prints the zone, or nothing
"""

from __future__ import annotations

import os
import pathlib
import re

ZONE_KEY = re.compile(r"^\s*ESTATE_ZONE:\s*(\S+)", re.M)
CLUSTER_GLOB = "*/estate-config.yaml"


def _roots() -> list[pathlib.Path]:
    """The directories that may hold a clusters/<cluster>/estate-config.yaml, in order.

    ESTATE_ZONE_ROOT is the zone of ANOTHER checkout (bin/estate-zone-gate --root uses it), so a
    reader can be pointed at the tree that declares the zone it cares about.
    """
    roots: list[pathlib.Path] = []
    external = os.environ.get("ESTATE_ZONE_ROOT", "").strip()
    if external:
        roots.append(pathlib.Path(external))
    # This module's own tree: lib/estate_zone.py -> the tree root is its parent's parent.
    here = pathlib.Path(__file__).resolve()
    roots.append(here.parents[1])
    # The runtime copy of the tree, which is what a launchd job or an installed tool sees.
    roots.append(pathlib.Path.home() / ".estate" / "runtime" / "idp")
    return roots


def _from_config() -> str:
    for root in _roots():
        clusters = root / "clusters"
        if not clusters.is_dir():
            continue
        for cfg in sorted(clusters.glob(CLUSTER_GLOB)):
            match = ZONE_KEY.search(cfg.read_text(errors="replace"))
            if match:
                return match.group(1)
    return ""


def estate_zone() -> str:
    """The estate's zone, or "" when no source knows it."""
    return os.environ.get("ESTATE_ZONE", "").strip() or _from_config()


def estate_host(name: str, path: str = "") -> str:
    """https://<name>.<zone><path>, or "" when the zone is unknown."""
    zone = estate_zone()
    if not zone or not name:
        return ""
    return f"https://{name}.{zone}{path}"


def estate_router(path: str = "") -> str:
    """The estate's router front, https://llm.<zone><path>, or "" when the zone is unknown."""
    return estate_host("llm", path)


if __name__ == "__main__":  # pragma: no cover - the shell entry point
    print(estate_zone())
