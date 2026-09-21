"""GOV-01 (idp#3525 CP8, spec section 6): "Zero laptop dependency in the production
path: no config, lane, or fallback may resolve to founder hardware. Dev-local
convenience files not in the routing path are exempt by classification record."

ACCEPT: "dependency scan of the routing path shows zero laptop-resolved targets."
METHOD: config audit.

The routing path is platform/llm/**/*.yaml -- the cluster-deployed lane.
tests/test_ollama_cluster_lane.py already proved Ollama's own move off
host.docker.internal one service at a time; this module generalises that into a scan
over the whole directory, so a new lane added later cannot reintroduce the dependency
silently.

llm/*.yaml is the pre-cluster laptop-compose config, kept for founder-local dev only. It
is EXEMPT_FILES below, by classification record, not by being unscanned --
scan_exempt_files() proves the scanner still sees the pattern there; it is the
exemption, not blindness, that lets it stay off the production routing path.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTING_PATH_DIRS = (REPO_ROOT / "platform" / "llm",)

# Dev-local convenience files, not in the production routing path (GOV-01's own exemption
# clause). Each entry names the file and the reason it is exempt -- a bare boolean would
# let a file join this list with no record of why.
EXEMPT_FILES: dict[str, str] = {
    "llm/config.yaml": (
        "pre-cluster laptop-compose config; superseded in the routing path by "
        "platform/llm/config.yaml (idp#3525 CP1)"
    ),
    "llm/config.base.yaml": (
        "pre-cluster laptop-compose config; superseded by "
        "platform/llm/config.base.yaml (idp#3525 CP1)"
    ),
    "llm/litellm.yml": (
        "founder's own laptop-compose LiteLLM proxy; the cluster's LiteLLM ships in "
        "platform/llm/litellm.yaml"
    ),
}

LAPTOP_PATTERNS = (
    re.compile(r"host\.docker\.internal"),
    re.compile(r"founder'?s?\s+(?:own\s+)?mac\b", re.I),
)


def _laptop_hits(text: str) -> list[str]:
    """Laptop-resolved targets in LIVE yaml values only. Every reference this scan must
    catch is one that would actually resolve at runtime -- an `api_base:` value, a probe
    URL -- not a `#` comment recounting the founder's own Mac being killed on 2026-09-10;
    the routing path's history is text, not a dependency."""
    hits = []
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        code = line.split("#", 1)[0]
        for p in LAPTOP_PATTERNS:
            hits.extend(m.group(0) for m in p.finditer(code))
    return hits


def scan_routing_path(root: Path | None = None) -> dict[str, list[str]]:
    """Every *.yaml under the routing path, file -> laptop-resolved hits. An empty dict
    is GOV-01's ACCEPT: zero laptop-resolved targets in the production routing path."""
    root = root or REPO_ROOT
    hits: dict[str, list[str]] = {}
    for d in ROUTING_PATH_DIRS:
        scan_dir = root / d.relative_to(REPO_ROOT)
        if not scan_dir.is_dir():
            continue
        for f in sorted(scan_dir.rglob("*.yaml")):
            found = _laptop_hits(f.read_text())
            if found:
                hits[str(f.relative_to(root))] = found
    return hits


def scan_exempt_files(root: Path | None = None) -> dict[str, list[str]]:
    """The dev-local files named in EXEMPT_FILES, same scan -- proves the classifier
    still sees the pattern there rather than the files simply never being looked at."""
    root = root or REPO_ROOT
    hits: dict[str, list[str]] = {}
    for rel in EXEMPT_FILES:
        f = root / rel
        if f.is_file():
            found = _laptop_hits(f.read_text())
            if found:
                hits[rel] = found
    return hits
