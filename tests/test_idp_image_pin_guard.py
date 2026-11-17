"""The pin guard must tell a placeholder from a wrong pin.

MEASURED 2026-11-16: main was red on offline-gate because platform/mcp/kustomization.yaml pins
ghcr.io/chidionyema/gortex-engine:main-0-000<40 zeros> -- the estate's documented "not yet
built" placeholder ("the number is 0, so any real build wins it"), which a real build replaces.
The guard asked the registry, got the only possible answer (404), and refused a correct tree.
A placeholder is not a wrong pin; a never-published real tag still is.

Each case runs the guard against a local fake registry, so no network is involved.
"""

from __future__ import annotations

import http.server
import os
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "bin" / "idp-image-pin-guard"

PLACEHOLDER = "main-0-" + "0" * 40


class _FakeRegistry(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 -- http.server's interface
        if self.server.existing and self.server.existing in self.path:  # type: ignore[attr-defined]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # keep the test output clean
        pass


def _start(existing: str | None) -> tuple[http.server.HTTPServer, str]:
    srv = http.server.HTTPServer(("127.0.0.1", 0), _FakeRegistry)
    srv.existing = existing  # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _tree(tmp_path: Path, image: str, tag: str) -> Path:
    d = tmp_path / "tree"
    (d / "platform" / "mcp").mkdir(parents=True)
    (d / "platform" / "mcp" / "kustomization.yaml").write_text(
        "images:\n"
        f"  - name: ghcr.io/chidionyema/{image}\n"
        f'    newTag: {tag} # {{"$imagepolicy": "flux-system:{image}:tag"}}\n'
    )
    return d


def _run(tree: Path, registry: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GUARD)],
        cwd=tree,
        env=dict(os.environ, IDP_REGISTRY_URL=registry, IDP_ROOT=str(tree)),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_documented_placeholder_is_skipped(tmp_path):
    srv, url = _start(existing=None)
    try:
        proc = _run(_tree(tmp_path, "gortex-engine", PLACEHOLDER), url)
    finally:
        srv.shutdown()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "not-yet-built placeholder" in proc.stdout


def test_a_never_published_real_tag_is_still_refused(tmp_path):
    srv, url = _start(existing=None)
    try:
        proc = _run(_tree(tmp_path, "backstage", "main-14676-e403b8c0"), url)
    finally:
        srv.shutdown()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "which the registry does not have" in proc.stdout


def test_a_published_tag_passes(tmp_path):
    srv, url = _start(existing="backstage")
    try:
        proc = _run(_tree(tmp_path, "backstage", "main-14676-e403b8c0"), url)
    finally:
        srv.shutdown()
    assert proc.returncode == 0, proc.stdout + proc.stderr
