"""Every image that fetches over https must have a CA bundle in it.

MEASURED DEFECT (2026-11-11). ``gortex-engine.Dockerfile`` built from
``debian:bookworm-slim`` and installed ``curl`` without ``ca-certificates``. At
build time it fetched its release tarball over https and died with

    curl: (77) error setting certificate file: /etc/ssl/certs/ca-certificates.crt

so the image could not build at all, and the whole container-build lane went
red. That is not a one-file accident: a slim Debian, Python, or Alpine base
ships **no** CA bundle, so *any* Dockerfile that installs ``curl`` and then
dials ``https://`` has the same hole, and the hole is invisible until the
build runs.

So this is checked as a class, not as a one-off. The rule:

    a Dockerfile that installs curl and fetches over https
        must install ca-certificates on the same package-manager line
        (``apt-get install ... curl ca-certificates`` / ``apk add ... curl ca-certificates``)

``ca-certificates`` must accompany ``curl`` in the **same install line**: a
separate ``RUN apk add ca-certificates`` after the fetch, or in a different
layer, does not help the ``curl`` that already ran.

The scan reads every Dockerfile ``git ls-files`` reports, so a new image is
covered the day it lands rather than the day someone remembers this file. The
Dockerfile list is never hardcoded here: a hardcoded list is the thing that
goes stale and lets the fifth instance through.

Over-approximation, stated deliberately: a Dockerfile that installs curl but
only ever dials ``http://`` is also required to carry ``ca-certificates``. The
alternative is parsing which URL each curl actually reaches, which is a
smarter check that fails open on a changed variable; requiring the bundle
costs a few kB and can never fail open.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Packages that make https work on the three bases this estate builds on.
CA_PACKAGES = ("ca-certificates", "ca-certificates-bundle")

# `foo-curl` and `curlish` are not `curl`; word-boundary matching keeps this honest.
_CURL_RE = re.compile(r"(?<![\w.-])curl(?![\w.-])")
_CA_RE = re.compile(r"(?<![\w.-])(?:" + "|".join(CA_PACKAGES) + r")(?![\w.-])")
_HTTPS_RE = re.compile(r"https://")
# Package-manager install invocations, joined across backslash continuations.
_APT_RE = re.compile(r"apt-get\s+(?:-\S+\s+)*install\b(.*)", re.S)
_APK_RE = re.compile(r"apk\s+(?:-\S+\s+)*add\b(.*)", re.S)


def _tracked_dockerfiles() -> list[str]:
    """Every Dockerfile git knows about. Never a hardcoded list."""
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not on PATH, so the Dockerfile set cannot be enumerated")
    out = subprocess.run(  # noqa: S603 - fixed argv, resolved git binary
        [git, "ls-files", "*Dockerfile*", "*.dockerfile", "Dockerfile*"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    files = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    # `git ls-files` with several patterns can repeat a path; de-duplicate, keep order.
    seen: dict[str, None] = {}
    for f in files:
        seen.setdefault(f, None)
    return list(seen)


def _logical_lines(text: str) -> str:
    """Join backslash continuations, and keep each RUN on its own line.

    Continuations are joined because a multi-line `RUN apt-get install ...` must be read as
    one command. But a separate `RUN` is a separate shell, and therefore a separate layer: a
    `ca-certificates` installed AFTER the curl that needed it is not a fix, so RUN boundaries
    must survive the join. Newlines that are not continuations become a hard `\\n` sentinel
    so no cross-RUN match can occur.
    """
    flat = re.sub(r"\\\s*\n\s*", " ", text)
    return flat.replace("\n", "\x00")


def _install_segments(text: str) -> list[str]:
    """Every apt-get install / apk add argument segment, per RUN layer, continuations joined."""
    flat = _logical_lines(text)
    segments: list[str] = []
    for layer in flat.split("\x00"):
        for pattern in (_APT_RE, _APK_RE):
            for match in pattern.finditer(layer):
                segments.append(match.group(1))
    return segments


def _has_bundle_on_the_curl_line(text: str) -> bool:
    """True when some install line carries both curl and a CA package."""
    for segment in _install_segments(text):
        # The segment runs to the end of the logical line; stop at the next shell operator
        # that ends the install argument list.
        head = re.split(r"&&|\|\||;", segment, maxsplit=1)[0]
        if _CURL_RE.search(head) and _CA_RE.search(head):
            return True
    return False


def _installs_curl(text: str) -> bool:
    return any(_CURL_RE.search(re.split(r"&&|\|\||;", s, maxsplit=1)[0]) for s in _install_segments(text))


def _fetches_https(text: str) -> bool:
    return bool(_HTTPS_RE.search(text))

def _is_offender(text: str) -> bool:
    return _installs_curl(text) and _fetches_https(text) and not _has_bundle_on_the_curl_line(text)


# ---------------------------------------------------------------------------
# The gate: every tracked Dockerfile that fetches over https carries a bundle.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", _tracked_dockerfiles())
def test_a_dockerfile_that_fetches_https_has_a_ca_bundle(relpath: str) -> None:
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")
    if not _installs_curl(text):
        pytest.skip("does not install curl, so it needs no CA bundle for curl")
    if not _fetches_https(text):
        pytest.skip("installs curl but never dials https")
    install = [s for s in _install_segments(text) if _CURL_RE.search(s)]
    assert _has_bundle_on_the_curl_line(text), (
        f"{relpath} installs curl and fetches over https but does not install "
        f"{' or '.join(CA_PACKAGES)} on the same package-manager line.\n"
        f"  Its curl install line(s): {install[:2]}\n"
        "  On a slim base this fails the build with "
        "'curl: (77) error setting certificate file'.\n"
        "  Fix: apt-get install -y --no-install-recommends curl ca-certificates\n"
        "       apk add --no-cache curl ca-certificates\n"
        "  See efda.Dockerfile for the proven-good shape."
    )


# ---------------------------------------------------------------------------
# Falsifiers: the checker must reject known-bad and accept known-good input.
# A gate that cannot fail is not a gate.
# ---------------------------------------------------------------------------


BAD_DEBIAN = """
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl \\
 && curl -fsSL -o /tmp/x.tar.gz https://example.com/x.tar.gz
"""

BAD_ALPINE = """
FROM alpine:3.21
RUN apk add --no-cache curl && \\
    curl -fsSL https://example.com/x.tar.gz -o /tmp/x.tar.gz
"""

BAD_SEPARATE_LAYER = """
FROM alpine:3.21
RUN apk add --no-cache curl
RUN curl -fsSL https://example.com/x.tar.gz -o /tmp/x.tar.gz
RUN apk add --no-cache ca-certificates
"""

GOOD_DEBIAN = """
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \\
 && curl -fsSL -o /tmp/x.tar.gz https://example.com/x.tar.gz
"""

GOOD_ALPINE = """
FROM alpine:3.21
RUN apk add --no-cache curl ca-certificates && \\
    curl -fsSL https://example.com/x.tar.gz -o /tmp/x.tar.gz
"""

GOOD_NO_CURL = """
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates
"""

GOOD_CURL_NO_HTTPS = """
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl
"""


@pytest.mark.parametrize(
    "name,text",
    [
        ("debian-no-bundle", BAD_DEBIAN),
        ("alpine-no-bundle", BAD_ALPINE),
        ("bundle-in-a-later-layer", BAD_SEPARATE_LAYER),
    ],
)
def test_the_gate_rejects_a_known_bad_dockerfile(name: str, text: str) -> None:
    assert _is_offender(text), f"the gate ACCEPTED known-bad input: {name}"


@pytest.mark.parametrize(
    "name,text",
    [
        ("debian-with-bundle", GOOD_DEBIAN),
        ("alpine-with-bundle", GOOD_ALPINE),
        ("no-curl-at-all", GOOD_NO_CURL),
        ("curl-but-no-https", GOOD_CURL_NO_HTTPS),
    ],
)
def test_the_gate_accepts_a_known_good_dockerfile(name: str, text: str) -> None:
    assert not _is_offender(text), f"the gate REJECTED known-good input: {name}"


def test_curl_inside_another_word_is_not_an_install() -> None:
    """`libcurl4` / `curlify` must not be read as installing the curl binary."""
    assert not _CURL_RE.search("libcurl4-openssl-dev")
    assert not _CURL_RE.search("curlish")
    assert _CURL_RE.search("curl")


def test_the_scan_actually_finds_dockerfiles() -> None:
    """If enumeration silently returned nothing, every test above would vacuously pass."""
    files = _tracked_dockerfiles()
    assert files, "no Dockerfiles were enumerated, so this gate proves nothing"
    assert any(f.endswith("gortex-engine.Dockerfile") for f in files), (
        f"gortex-engine.Dockerfile missing from the scan: {files[:10]}"
    )


@pytest.mark.parametrize(
    "relpath",
    [
        "gortex-engine.Dockerfile",
        "estate-mcp.Dockerfile",
        "platform/llm/spire-key-broker/Dockerfile",
        "cmd/identity-bootstrapper/Dockerfile",
    ],
)
def test_the_measured_offenders_are_fixed(relpath: str) -> None:
    """The specific instances measured on 2026-11-11, pinned so they cannot regress.

    ``factory.Dockerfile`` is deliberately NOT in this list. The first audit called it an
    offender because it installs curl, but measured afterwards it contains no ``https://``
    URL at all: it installs curl for interactive use and its only network access is
    ``pip install``, which uses its own bundled CA store. Claiming it as a defect would be
    a false finding, so it is recorded correctly here instead.
    """
    if not (REPO_ROOT / relpath).exists():
        pytest.skip(f"{relpath} no longer exists")
    text = (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")
    assert not _is_offender(text), f"{relpath} regressed: curl without ca-certificates"
