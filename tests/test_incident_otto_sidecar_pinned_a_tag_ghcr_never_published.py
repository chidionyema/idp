"""2026-08-29: once idp#767 let the gateway start without its tailscale secret, the pod moved
from ContainerCreating to 1/2 ImagePullBackOff (architect-doctor run 33248277010):
`container "tailscale" ... trying and failing to pull image`. The sidecar pinned
`ghcr.io/tailscale/tailscale:v1.80.2`, a tag ghcr never published (manifest 404; v1.80.3 and
v1.102.3 answer 200). The tag was typed from memory (d86a89a6), never checked against the
registry, and nothing between the PR and the cluster reads the registry.

Fence: every ghcr.io image pinned under platform/ must answer 200 for its manifest. Anonymous
pull tokens are enough for public images; a private image answers 401/403 and is skipped as
BLIND rather than read as green.
"""

import json
import re
import urllib.request
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
IMAGE = re.compile(
    r"^\s*(?:-\s*)?image:\s*['\"]?(ghcr\.io/([^:@'\"\s]+)):(v?\d[^'\"\s#]*)", re.M
)
ACCEPT = (
    "application/vnd.oci.image.index.v1+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json, "
    "application/vnd.oci.image.manifest.v1+json, "
    "application/vnd.docker.distribution.manifest.v2+json"
)


def _pins():
    seen = {}
    for p in sorted((IDP / "platform").rglob("*.yaml")):
        for m in IMAGE.finditer(p.read_text(errors="replace")):
            seen.setdefault((m.group(2), m.group(3)), str(p.relative_to(IDP)))
    return seen


def _status(repo: str, tag: str) -> int:
    tok = json.load(
        urllib.request.urlopen(
            f"https://ghcr.io/token?scope=repository:{repo}:pull", timeout=20
        )
    )["token"]
    req = urllib.request.Request(
        f"https://ghcr.io/v2/{repo}/manifests/{tag}",
        method="HEAD",
        headers={"Authorization": f"Bearer {tok}", "Accept": ACCEPT},
    )
    try:
        return urllib.request.urlopen(req, timeout=20).status  # noqa: S310 https literal
    except urllib.error.HTTPError as e:
        return e.code


def test_the_sidecar_is_pinned_to_a_tag_that_exists():
    pins = _pins()
    assert ("tailscale/tailscale", "v1.102.3") in pins, pins


@pytest.mark.parametrize("repo,tag,where", [(r, t, w) for (r, t), w in _pins().items()])
def test_every_ghcr_pin_under_platform_answers_200(repo, tag, where):
    try:
        code = _status(repo, tag)
    except OSError as e:
        pytest.skip(f"BLIND: ghcr unreachable ({e})")
    if code in (401, 403):
        pytest.skip(f"BLIND: {repo} is private to an anonymous token")
    assert code == 200, (
        f"{where}: ghcr.io/{repo}:{tag} answers {code}; the sidecar would sit in ImagePullBackOff"
    )
