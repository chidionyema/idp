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


# --- the ladder, judged (founder, 2026-10-30: "never allowing a critical service to be a
# single point of failure"). A board that counts lanes cannot say that a ladder with one
# working provider left is one failure from empty; these tests say it. -------------------


def _row(leg, provider, verdict, service="svc", role="home"):
    return {
        "service": service,
        "leg": leg,
        "provider": provider,
        "role": role,
        "verdict": verdict,
        "detail": "x",
    }


def test_two_providers_answering_is_redundant():
    rows = [
        _row("a", "oracle", door.OK),
        _row("b", "cloudflare", door.OK),
        _row("c", "groq", door.FAIL),
    ]
    assert door.ladder(rows)["state"] == "REDUNDANT"


def test_one_provider_answering_is_a_single_point_of_failure():
    """Three of four lanes dead is the same state as the estate on 2026-10-28."""
    rows = [
        _row("cloud", "oracle", door.FAIL),
        _row("lifeboat", "cloudflare", door.FAIL),
        _row("floor", "groq", door.FAIL),
        _row("laptop", "laptop", door.OK),
    ]
    got = door.ladder(rows)
    assert got["state"] == "SPOF"
    assert got["providers_ok"] == ["laptop"]


def test_two_homes_in_one_provider_are_one_failure_domain():
    rows = [_row("a", "oracle", door.OK), _row("b", "oracle", door.OK)]
    assert door.ladder(rows)["state"] == "SPOF"


def test_nothing_answering_is_down():
    rows = [_row("a", "oracle", door.FAIL), _row("b", "groq", door.FAIL)]
    assert door.ladder(rows)["state"] == "DOWN"


def test_a_lane_nobody_could_ask_makes_the_ladder_unproven_never_redundant():
    """The runner's view of the router: the laptop is NOT_HERE and the floor is UNKNOWN. The
    drill must say it cannot prove a second home, not that the ladder is fine."""
    rows = [
        _row("cloud", "oracle", door.FAIL),
        _row("lifeboat", "cloudflare", door.FAIL),
        _row("floor", "groq", door.UNKNOWN),
        _row("laptop", "laptop", door.NOT_HERE),
    ]
    got = door.ladder(rows)
    assert got["state"] == "UNPROVEN"
    assert got["unasked"] == ["floor", "laptop"]
    one_ok = [_row("a", "oracle", door.OK), _row("b", "groq", door.UNKNOWN)]
    assert door.ladder(one_ok)["state"] == "UNPROVEN"


def test_a_row_set_with_no_roles_is_not_a_ladder():
    """The estate-doors list is fourteen names, not fourteen homes of one service."""
    rows = [_row("api", "oracle", door.OK, role=None) for _ in range(3)]
    assert door.ladders(rows) == []


def test_the_board_names_the_state_and_what_it_could_not_ask():
    rows = [
        _row("cloud", "oracle", door.FAIL, service="llm-router"),
        _row("laptop", "laptop", door.NOT_HERE, service="llm-router"),
    ]
    text = door.render(rows)
    assert "LADDER  llm-router: UNPROVEN" in text
    assert "laptop" in text.split("LADDER")[1]


def test_the_closing_comment_claims_only_what_was_asked(monkeypatch):
    """It used to say 'every lane of <service> answered again' while a lane was UNKNOWN."""
    calls = []

    def fake_gh(args):
        calls.append(args)
        if args[:2] == ["issue", "list"]:
            return 0, json.dumps([{"number": 7, "title": "t"}]), ""
        return 0, "", ""

    monkeypatch.setattr(door, "_gh", fake_gh)
    rows = [
        _row("cloud", "oracle", door.OK),
        _row("floor", "groq", door.OK),
        _row("laptop", "laptop", door.NOT_HERE),
    ]
    actions = door.file_issues(rows)
    comment = next(c for c in calls if c[:2] == ["issue", "comment"])
    body = comment[comment.index("--body") + 1]
    assert "every lane" not in body
    assert "laptop" in body and "could not be asked" in body
    assert ["issue", "close", "7"] in calls
    assert any("closed #7" in a for a in actions)


def test_a_single_provider_ladder_files_a_ticket_though_no_lane_failed(monkeypatch):
    calls = []

    def fake_gh(args):
        calls.append(args)
        return (0, "[]", "") if args[:2] == ["issue", "list"] else (0, "", "")

    monkeypatch.setattr(door, "_gh", fake_gh)
    rows = [_row("a", "oracle", door.OK), _row("b", "oracle", door.OK)]
    door.file_issues(rows)
    created = [c for c in calls if c[:2] == ["issue", "create"]]
    assert created, "a ladder with one failure domain left must be a ticket"
    assert "single point of failure" in created[0][created[0].index("--title") + 1]


@pytest.fixture()
def serve():
    """Servers that each answer their own code (the shared `server` fixture sets the code on
    one handler class, so two servers cannot differ)."""
    started = []

    def start(code):
        handler = type("Handler", (_Handler,), {"code": code})
        httpd = HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return httpd.server_address[1]

    yield start
    for httpd in started:
        httpd.shutdown()


def _config(tmp_path, legs):
    path = tmp_path / f"ladder-{len(list(tmp_path.iterdir()))}.json"
    path.write_text(json.dumps({"services": [{"service": "svc", "legs": legs}]}))
    return str(path)


def _leg(name, provider, port, **more):
    return {
        "name": name,
        "provider": provider,
        "role": "home",
        "url": f"http://127.0.0.1:{port}/",
        "expect": [200],
        **more,
    }


def test_gate_exit_codes_say_redundant_spof_and_unproven(tmp_path, serve):
    up_a, up_b = serve(200), serve(200)
    down = serve(500)
    two = _config(tmp_path, [_leg("a", "p1", up_a), _leg("b", "p2", up_b)])
    one = _config(tmp_path, [_leg("a", "p1", up_a), _leg("b", "p2", down)])
    blind = _config(
        tmp_path,
        [
            _leg("a", "p1", up_a),
            _leg("b", "p2", up_b, url="http://127.0.0.1:1/${NOT_IN_THIS_ENV}"),
        ],
    )
    argv = ["--no-file", "--gate", "--config"]
    assert door.main(argv + [two]) == 0
    assert door.main(argv + [one]) == 1
    assert door.main(argv + [blind]) == 2
    # without --gate the drill keeps its old contract: it reports, a ticket carries the news
    assert door.main(["--no-file", "--config", one]) == 0


def test_the_json_board_carries_the_ladders(tmp_path, serve, capsys):
    port = serve(200)
    cfg = _config(tmp_path, [_leg("a", "p1", port), _leg("b", "p2", port)])
    door.main(["--no-file", "--json", "--config", cfg])
    data = json.loads(capsys.readouterr().out)
    assert data["ladders"] == [
        {
            "service": "svc",
            "state": "REDUNDANT",
            "providers_ok": ["p1", "p2"],
            "down": [],
            "unasked": [],
        }
    ]


def test_every_declared_ladder_keeps_adr_0037_r1_three_homes_two_providers():
    config = door.load_config(IDP / "platform/ladder/critical-lanes.json")
    for service in config["services"]:
        legs = service["legs"]
        if not any(leg.get("role") for leg in legs):
            continue  # a list of doors, not a ladder of homes
        assert len(legs) >= 3, f"{service['service']}: fewer than three homes"
        assert len({leg["provider"] for leg in legs}) >= 2, (
            f"{service['service']}: homes in one provider"
        )


@pytest.mark.parametrize(
    "raised",
    [
        door.urllib.error.URLError(OSError("Tunnel connection failed: 403 Forbidden")),
        OSError("Tunnel connection failed: 403 Forbidden"),
    ],
)
def test_a_proxy_that_refuses_the_tunnel_is_a_lane_nobody_asked(monkeypatch, raised):
    def refuse(*args, **kwargs):
        raise raised

    monkeypatch.setattr(door.urllib.request, "urlopen", refuse)
    verdict, detail = door.probe("https://llm.example.invalid/health", timeout=1)
    assert verdict == door.UNKNOWN and "proxy refused the tunnel" in detail


def test_a_direct_connect_that_fails_is_still_a_failure(monkeypatch):
    def refuse(*args, **kwargs):
        raise door.urllib.error.URLError(OSError("[Errno 111] Connection refused"))

    monkeypatch.setattr(door.urllib.request, "urlopen", refuse)
    verdict, _ = door.probe("https://llm.example.invalid/health", timeout=1)
    assert verdict == door.FAIL


# --- the topology proof (founder, 2026-10-30: "the router must never fail again"). The board
# measures lanes; this asks the question a measurement cannot: is there ONE failure domain whose
# loss empties the service? A client reaches a home only through a selector, so a selector and a
# home that share a domain share a fate. Set arithmetic, no network, so CI can run it. --------


def _topo(selectors, **legs):
    return {
        "service": "svc",
        "selectors": selectors,
        "legs": [
            {"name": name, "provider": name, "role": "home", "fate": fate}
            for name, fate in legs.items()
        ],
    }


def test_a_selector_that_shares_a_domain_with_every_home_is_a_single_point():
    """Four homes behind one front on one host are one home."""
    svc = _topo(
        [{"name": "front", "fate": ["host:laptop"]}],
        cloud=["provider:oke"],
        lifeboat=["provider:cf"],
        floor=["provider:groq"],
    )
    got = door.prove(svc)
    assert got["verdict"] == "FAILS"
    assert got["single_points"] == ["host:laptop"]


def test_two_selectors_with_disjoint_fate_leave_no_single_point():
    svc = _topo(
        [
            {"name": "front", "fate": ["host:laptop"]},
            {"name": "edge", "fate": ["provider:cf"]},
        ],
        cloud=["provider:oke"],
        floor=["provider:groq"],
    )
    got = door.prove(svc)
    assert got["verdict"] == "PROVEN", got
    assert got["single_points"] == []


def test_a_home_the_selector_does_not_reach_does_not_count():
    """Declared is not wired: the lifeboat on the ladder does not help a front that never dials
    it. The cloud dying leaves only the laptop; the laptop dying leaves only the cloud."""
    svc = _topo(
        [
            {
                "name": "front",
                "fate": ["host:laptop"],
                "reaches": ["cloud", "laptop"],
            },
        ],
        cloud=["provider:oke"],
        laptop=["host:laptop"],
        lifeboat=["provider:cf"],
    )
    assert door.prove(svc)["single_points"] == ["host:laptop"]
    svc["selectors"].append({"name": "edge", "fate": ["provider:cf"]})
    assert door.prove(svc)["verdict"] == "PROVEN"


def test_a_home_that_shares_the_only_selectors_domain_cannot_rescue_it():
    svc = _topo(
        [{"name": "front", "fate": ["provider:oke"]}],
        cloud=["provider:oke"],
        floor=["provider:groq"],
    )
    assert door.prove(svc)["single_points"] == ["provider:oke"]


def test_a_service_with_no_declared_fate_is_undeclared_never_proven():
    svc = {"service": "svc", "legs": [{"name": "a", "provider": "p", "role": "home"}]}
    assert door.prove(svc)["verdict"] == "UNDECLARED"
    assert door.prove({"service": "doors", "legs": [{"name": "api"}]}) is None


def test_a_selector_that_names_a_home_that_does_not_exist_is_refused():
    svc = _topo([{"name": "f", "fate": ["x"], "reaches": ["nope"]}], a=["y"])
    with pytest.raises(ValueError):
        door.prove(svc)


def test_the_prove_flag_exits_by_verdict(tmp_path, capsys):
    bad = _topo([{"name": "front", "fate": ["host:laptop"]}], a=["p:1"], b=["p:2"])
    good = _topo(
        [{"name": "f", "fate": ["h:1"]}, {"name": "e", "fate": ["p:cf"]}],
        a=["p:1"],
        b=["p:2"],
    )
    for name, svc, code in (("bad", bad, 1), ("good", good, 0)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({"services": [svc]}))
        assert door.main(["--prove", "--config", str(path)]) == code
    assert "host:laptop" in capsys.readouterr().out


@pytest.mark.xfail(
    strict=True,
    reason=(
        "host:laptop is on the path of every home of llm-router (incident 2026-10-30). "
        "Ticket router-second-selector. strict: when the topology is fixed this XPASSes and "
        "the suite fails until the marker is removed, so the fix cannot land unrecorded."
    ),
)
def test_the_estate_router_has_no_single_failure_domain():
    config = door.load_config(IDP / "platform/ladder/critical-lanes.json")
    router = next(s for s in config["services"] if s["service"] == "llm-router")
    assert door.prove(router)["verdict"] == "PROVEN"


def test_the_estate_router_topology_is_declared_so_it_can_be_proved():
    config = door.load_config(IDP / "platform/ladder/critical-lanes.json")
    router = next(s for s in config["services"] if s["service"] == "llm-router")
    got = door.prove(router)
    assert got["verdict"] in ("PROVEN", "FAILS"), got
    assert "host:laptop" in got["domains"]
