"""A pinned image tag must exist in the registry.

Spec: bin/idp-image-pin-guard's header.

THE INCIDENT. 55e276948 (2026-10-20) rolled backstage back to main-14676, a tag that was never
published (build-multiarch 14676 failed). The catalogue sat in ImagePullBackOff and /fleet and
/face served 503; every offline render check passed. These tests run the guard against a local
fake registry and prove it refuses the missing tag, passes the published one, and does not
refuse a tag it cannot read.
"""

from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "bin" / "idp-image-pin-guard"

PUBLISHED = "main-14666-ac59a5c418d9d46f27b624ec607925d5094b3deb"
NEVER_BUILT = "main-14676-e403b8c0dfe388dd74df09b048fcd628aef455fb"
PRIVATE = "main-5-8fc1d21bb1c94e288bb51d44b877e86626d164e4"

OVERLAY = """\
images:
  - name: ghcr.io/chidionyema/backstage
    newName: ghcr.io/chidionyema/backstage
    newTag: {tag} # {{"$imagepolicy": "flux-system:backstage:tag"}}
"""


class _FakeGhcr(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def do_GET(self) -> None:
        body = json.dumps({"token": "t"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self) -> None:
        tag = self.path.rsplit("/", 1)[-1]
        self.send_response({PUBLISHED: 200, PRIVATE: 401}.get(tag, 404))
        self.end_headers()


def _run(tmp_path: Path, tag: str) -> subprocess.CompletedProcess:
    overlay = tmp_path / "platform" / "backstage" / "overlays" / "oke"
    overlay.mkdir(parents=True)
    (overlay / "kustomization.yaml").write_text(OVERLAY.format(tag=tag))
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeGhcr)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        return subprocess.run(
            ["python3", str(GUARD)],
            capture_output=True,
            text=True,
            env={
                "IDP_ROOT": str(tmp_path),
                "IDP_REGISTRY_URL": f"http://127.0.0.1:{server.server_port}",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
            },
        )
    finally:
        server.shutdown()


def test_the_shipped_defect_is_refused(tmp_path: Path) -> None:
    """Pinning the never-built main-14676 tag is refused, and the file is named."""
    r = _run(tmp_path, NEVER_BUILT)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "platform/backstage/overlays/oke/kustomization.yaml:4" in r.stdout
    assert NEVER_BUILT in r.stdout


def test_a_published_tag_passes(tmp_path: Path) -> None:
    r = _run(tmp_path, PUBLISHED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "none missing" in r.stdout


def test_a_tag_it_cannot_read_is_warned_not_refused(tmp_path: Path) -> None:
    """A private package answers 401 to an anonymous token; that is not proof it is missing."""
    r = _run(tmp_path, PRIVATE)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "not verifiable: 401" in r.stdout
