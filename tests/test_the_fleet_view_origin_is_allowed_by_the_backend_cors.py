"""The origins the estate actually serves must be allowed by the backend CORS allowlist.

WHY. 2026-10-30: the founder's own URL -- http://roses-macbook-pro.tail3f2ff4.ts.net:8443/fleet/
-- rendered the guest wall, because `backend.cors.origin` named exactly one origin
(http://localhost:3100) and the browser's API request carried an origin the allowlist did not
list. The page still returned 200, so the refusal was invisible from the outside (idp#7662).

WHAT THIS PROVES. `@backstage/backend-defaults` readCorsOptions() matches the request Origin
against `cors.origin` with case-insensitive minimatch (nocase, noglobstar). These are the
origins the estate serves -- the IPv4 loopback every probe in this repo dials, the IPv6 loopback
the dev server binds, and the tailnet origin the founder uses -- and a gate that cannot fail is
not a gate: origins the estate does NOT serve must still be refused.

HOW. The matcher below is minimatch's semantics for the pattern forms this allowlist uses (`*`
inside a path segment, backslash-escaped literals). It is deliberately not a minimatch
dependency, so the gate runs wherever pytest runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[1] / "backstage" / "app-config.yaml"

ESTATE_ORIGINS = (
    "http://localhost:3100",
    "http://127.0.0.1:3100",
    "http://[::1]:3100",
    "http://roses-macbook-pro.tail3f2ff4.ts.net:8443",
)

FOREIGN_ORIGINS = (
    "http://evil.example.com",
    "http://localhost:3000",
    "http://127.0.0.1:7107",
    "http://roses-macbook-pro.tail3f2ff4.ts.net:9999",
)


def _patterns() -> list[str]:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    origin = config["backend"]["cors"]["origin"]
    return [origin] if isinstance(origin, str) else list(origin)


def _regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "\\" and index + 1 < len(pattern):
            parts.append(re.escape(pattern[index + 1]))
            index += 2
            continue
        if char == "*":
            parts.append("[^/]*")
            index += 1
            continue
        parts.append(re.escape(char))
        index += 1
    return re.compile("".join(parts), re.IGNORECASE)


def _allowed(origin: str, patterns: list[str]) -> bool:
    return any(_regex(pattern).fullmatch(origin) for pattern in patterns)


def test_every_origin_the_estate_serves_is_allowed() -> None:
    patterns = _patterns()
    refused = [origin for origin in ESTATE_ORIGINS if not _allowed(origin, patterns)]
    assert not refused, (
        f"CORS allowlist refuses estate origins: {refused} (patterns: {patterns})"
    )


def test_origins_the_estate_does_not_serve_are_refused() -> None:
    patterns = _patterns()
    admitted = [origin for origin in FOREIGN_ORIGINS if _allowed(origin, patterns)]
    assert not admitted, (
        f"CORS allowlist admits foreign origins: {admitted} (patterns: {patterns})"
    )


def test_the_allowlist_is_a_list_so_origins_can_be_added_without_editing_one() -> None:
    patterns = _patterns()
    assert len(patterns) > 1, f"the allowlist is a single origin again: {patterns}"
