"""OBS-02 (idp#3525 CP8, spec section 6): "Founder-facing deliverables SHALL render on
the local board (127.0.0.1:8787 /look) or a permanent collector page, or be pushed
directly as a file. External hosting only with # vendor-surface-intended + reason."

ACCEPT, verbatim: "board serves the record; no external publish in trace." METHOD: check.

This runs the real bin/board_serve.py module (imported by path, since bin/ has no
__init__.py) against a real HTTP request over loopback, not a stand-in.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "board_serve", ROOT / "bin" / "board_serve.py"
)
board_serve = importlib.util.module_from_spec(_spec)
sys.modules["board_serve"] = board_serve
_spec.loader.exec_module(board_serve)


def test_publish_writes_the_same_pair_format_idp_reports_render_uses(tmp_path):
    meta = {
        "id": "cp8-smoke",
        "title": "CP8 smoke deliverable",
        "generated_at": "2026-09-15T00:00:00Z",
        "source": "test",
    }
    path = board_serve.publish(meta, "body text\n", board_dir=tmp_path)
    assert path == tmp_path / "cp8-smoke.md"
    assert (tmp_path / "cp8-smoke.md").read_text() == "body text\n"
    assert (tmp_path / "cp8-smoke.meta.json").is_file()


def test_look_renders_a_published_deliverable(tmp_path):
    meta = {
        "id": "cp8-render",
        "title": "Rendered Deliverable",
        "generated_at": "2026-09-15T00:00:00Z",
        "source": "unit test",
    }
    board_serve.publish(meta, "the record\n", board_dir=tmp_path)
    page = board_serve.render_look(tmp_path)
    assert "Rendered Deliverable" in page
    assert "the record" in page


def test_look_says_so_when_the_board_is_empty(tmp_path):
    assert "No deliverables" in board_serve.render_look(tmp_path)


def test_external_host_with_no_reason_is_refused():
    meta = {"id": "x"}
    try:
        board_serve.check_no_unlisted_external_publish(
            meta, "see https://example.com/report"
        )
    except board_serve.ExternalPublishError:
        pass
    else:
        raise AssertionError("expected ExternalPublishError")


def test_external_host_tagged_vendor_surface_intended_is_allowed():
    meta = {
        "id": "x",
        "vendor-surface-intended": "founder asked for a copy on the vendor's own status page",
    }
    board_serve.check_no_unlisted_external_publish(
        meta, "see https://example.com/report"
    )  # must not raise


def test_estate_hosts_never_require_the_tag():
    meta = {"id": "x"}
    for url in (
        "http://127.0.0.1:8787/look",
        "http://localhost:8787/look",
        "http://llm.svc.cluster.local/health",
        "https://catalogue.internal/entities",
    ):
        board_serve.check_no_unlisted_external_publish(
            meta, f"see {url}"
        )  # must not raise


def test_publish_refuses_to_write_when_the_external_check_fails(tmp_path):
    meta = {"id": "unwritten"}
    try:
        board_serve.publish(meta, "see https://example.com", board_dir=tmp_path)
    except board_serve.ExternalPublishError:
        pass
    else:
        raise AssertionError("expected ExternalPublishError")
    assert not (tmp_path / "unwritten.md").exists()
    assert not (tmp_path / "unwritten.meta.json").exists()


def test_board_binds_loopback_only():
    """GOV-01's own spirit, applied to the board itself: a founder-only local tool has
    no business listening on anything but loopback."""
    assert board_serve.HOST == "127.0.0.1"


def test_real_server_serves_look_and_healthz_over_http(tmp_path, monkeypatch):
    monkeypatch.setattr(board_serve, "BOARD_DIR", tmp_path)
    meta = {
        "id": "live",
        "title": "Live Deliverable",
        "generated_at": "2026-09-15T00:00:00Z",
        "source": "integration test",
    }
    board_serve.publish(meta, "live body\n", board_dir=tmp_path)

    server = board_serve.ThreadingHTTPServer(("127.0.0.1", 0), board_serve.BoardHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 5
        last_err = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/healthz", timeout=1
                ) as resp:
                    assert resp.read() == b"ok"
                break
            except Exception as e:  # noqa: BLE001 - polling until the server thread is ready
                last_err = e
                time.sleep(0.05)
        else:
            raise AssertionError(f"server never came up: {last_err}")

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/look", timeout=2) as resp:
            page = resp.read().decode("utf-8")
        assert "Live Deliverable" in page
        assert "live body" in page

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=2)
            raise AssertionError("expected a 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        thread.join(timeout=5)
