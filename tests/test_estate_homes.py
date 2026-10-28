"""The drill's rules, proved offline.

    pytest tests/test_estate_homes.py

What is proved here is the part that can be wrong quietly: that a lane is OK only when it
answered, that a lane on another machine is not "down", that a lane whose secret this host does
not carry is UNKNOWN rather than a false FAIL, and that the ladder in the repository is a
ladder at all (every lane names a url, a provider and a verdict vocabulary).
"""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parent.parent
DOOR = IDP / "bin/idp-estate-homes"


def _load():
    spec = importlib.util.spec_from_loader(
        "idp_estate_homes",
        importlib.machinery.SourceFileLoader("idp_estate_homes", str(DOOR)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


door = _load()


class _Handler(BaseHTTPRequestHandler):
    code = 200

    def do_GET(self):  # noqa: N802 - the name is the http.server's
        self.send_response(self.code)
        self.send_header("content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence the server's own logging
        return


@pytest.fixture()
def server():
    holder = {}

    def start(code):
        HTTPServer.allow_reuse_address = True
        httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        httpd.RequestHandlerClass.code = code
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        holder["port"] = httpd.server_address[1]
        return httpd.server_address[1]

    yield start
    for httpd in getattr(holder, "httpd_list", []):
        httpd.shutdown()


def test_a_lane_that_answers_is_measured_ok(server):
    port = server(200)
    verdict, detail = door.probe(f"http://127.0.0.1:{port}/health")
    assert verdict == door.OK, detail


def test_a_lane_that_answers_wrongly_is_measured_fail(server):
    port = server(503)
    verdict, detail = door.probe(f"http://127.0.0.1:{port}/health")
    assert verdict == door.FAIL, detail
    assert "503" in detail


def test_a_lane_that_cannot_be_asked_on_this_host_is_not_here():
    # A loopback lane that is not running here is not down: the runner is not the laptop.
    verdict, _ = door.probe("http://127.0.0.1:9/health", timeout=2)
    assert verdict == door.NOT_HERE


def test_a_lane_that_needs_a_secret_this_host_does_not_carry_is_unknown():
    service = {
        "service": "llm-router",
        "legs": [
            {
                "name": "groq free tier",
                "provider": "groq",
                "url": "https://api.groq.com/openai/v1/models",
                "secret": "GROQ_API_KEY",
                "headers": {"Authorization": "Bearer ${GROQ_API_KEY}"},
            }
        ],
    }
    rows = door.grade_service(service, {}, 2.0, "mumchimp.com")
    assert rows[0]["verdict"] == door.UNKNOWN
    assert "secret" in rows[0]["detail"]


def test_the_verdicts_are_the_ones_otto_already_uses():
    assert (door.OK, door.FAIL, door.UNKNOWN) == (
        "MEASURED_OK",
        "MEASURED_FAIL",
        "UNKNOWN",
    )


def test_the_board_counts_what_answered_and_what_did_not():
    rows = [
        {
            "service": "s",
            "leg": "a",
            "provider": "p",
            "verdict": door.OK,
            "detail": "HTTP 200",
        },
        {
            "service": "s",
            "leg": "b",
            "provider": "p",
            "verdict": door.FAIL,
            "detail": "no answer",
        },
    ]
    text = door.render(rows)
    assert "1 of 2 lane(s) answered" in text
    assert "DOWN" in text


def test_the_ladder_in_the_repository_is_a_ladder():
    config = door.load_config(IDP / "platform/ladder/critical-lanes.json")
    assert config["services"], "the ladder has no services"
    for service in config["services"]:
        assert service.get("service"), "a service has no name"
        assert service.get("legs"), f"{service.get('service')} has no lanes"
        for leg in service["legs"]:
            assert leg.get("name"), "a lane has no name"
            assert leg.get("url"), f"the lane {leg.get('name')} has no url"
            assert leg.get("provider"), f"the lane {leg.get('name')} has no provider"


def test_every_lane_in_the_ladder_is_reachable_as_a_question():
    """A lane that cannot be asked is a lane nobody measures: the drill would report it as
    a hole in the estate's surface rather than as a lane it could not see."""
    config = door.load_config(IDP / "platform/ladder/critical-lanes.json")
    for service in config["services"]:
        for leg in service["legs"]:
            assert leg["url"].startswith("http"), leg
            assert "${" not in leg["url"], (
                f"the lane {leg['name']} has an unexpanded secret"
            )


def test_the_json_board_is_data_a_workflow_can_read():
    config = door.load_config(IDP / "platform/ladder/critical-lanes.json")
    rows = door.grade(config, {}, timeout=1, only="")
    assert rows, "the drill measured nothing"
    blob = json.dumps(rows)
    assert "verdict" in blob
