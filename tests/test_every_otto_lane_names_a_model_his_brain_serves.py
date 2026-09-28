"""A lane Otto routes on names a model group his brain actually serves.

Measured in the live gateway pod on 2026-09-10, from inside the container
that answers the founder:

    ROUTER_BASE http://127.0.0.1:4010/v1
    SERVED ['deepseek', 'embed', 'gemini', 'home-direct', 'home-estate',
            'home-floor', 'home-floor-2', 'home-floor-3', 'home-floor-4',
            'home-floor-5', 'minimax']
    LANE_FAIL deep model=kimi elapsed_s=0.04 ProviderHTTPError: HTTP 400
            {"error":{"message":"/chat/completions: Invalid model name passed
            in model=kimi..."}}

Otto's door does not call the estate router. It calls the otto-brain sidecar
in its own pod, and that brain serves the eleven groups above. The deep lane
-- the one a `/think` message reaches -- had no row in the ConfigMap, so
``otto/router/config.py`` fell back to its own default, ``kimi``, a name the
brain has never served. Every `/think` turn therefore ended ``needs_human``
and the founder read "I could not reach the model, so I have not answered."

So this does not read the two files and compare them. It builds a door out of
the brain's own config -- one model group per row of ``model_list``, aliases
resolved the way the brain resolves them -- stands it on a real socket, and
sends every lane value in the ConfigMap through it as a real chat request.
A lane naming a group the brain does not serve comes back HTTP 400 with the
message the pod printed above, from a socket, not from an assertion about a
string. A lane with no row at all is the same defect wearing a library
default, and is driven the same way.
"""

import http.client
import json
import pathlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANES = ROOT / "platform" / "otto-gateway" / "router-lanes.yaml"
BRAIN = ROOT / "platform" / "otto-gateway" / "three-homes.yaml"

#: The lanes ``_DEFAULT_LANE_MODELS`` in otto/router/config.py declares. Each
#: one carries a vendor default the estate cannot call ("anthropic/claude",
#: "kimi", "google/gemini"), so a lane missing from the ConfigMap is not an
#: unused lane -- it is a lane pointed at a vendor with no key and no row.
LANES_THE_ROUTER_DEFINES = {"judgment", "bulk", "verify", "deep"}


def _config_map(path):
    for doc in yaml.safe_load_all(path.read_text()):
        if doc and doc.get("kind") == "ConfigMap":
            return doc
    raise AssertionError(f"no ConfigMap in {path}")


def _lane_models():
    """Every ``OTTO_ROUTER_LANE_<NAME>_MODEL`` the gateway hands the router."""
    data = _config_map(LANES)["data"]
    out = {}
    for key, value in data.items():
        if key.startswith("OTTO_ROUTER_LANE_") and key.endswith("_MODEL"):
            out[key[len("OTTO_ROUTER_LANE_") : -len("_MODEL")].lower()] = value
    return out


def _served_groups():
    brain = yaml.safe_load(_config_map(BRAIN)["data"]["config.yaml"])
    served = {row["model_name"] for row in brain["model_list"]}
    aliases = (brain.get("router_settings") or {}).get("model_group_alias") or {}
    # An alias resolves only when its target is itself a served group. The
    # estate router's own configmap carries `kimi: moonshot/kimi-k3` with no
    # such row, which is how `kimi` looked like a name and answered like a 400.
    served |= {name for name, target in aliases.items() if target in served}
    return served


def _brain_door(served):
    """A door that answers the way the brain answered in the pod.

    LiteLLM's proxy returns 400 and ``Invalid model name passed in model=X``
    for a group no ``model_list`` row and no resolvable alias names. Nothing
    here is invented: the served set is read out of the brain's own config,
    and the refusal is the message the gateway pod printed on 2026-09-10.
    """

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("content-length", 0)))
            model = (json.loads(body or b"{}") or {}).get("model")
            if model in served:
                payload = {
                    "choices": [{"message": {"role": "assistant", "content": "alive"}}],
                    "model": model,
                }
                code = 200
            else:
                payload = {
                    "error": {
                        "message": f"{self.path}: Invalid model name passed in model={model}",
                        "type": "invalid_request_error",
                    }
                }
                code = 400
            raw = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


@pytest.fixture(scope="module")
def brain():
    server = _brain_door(_served_groups())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _ask(address, model):
    """One real chat request, the shape otto/router/providers.py sends."""
    conn = http.client.HTTPConnection(*address, timeout=5)
    try:
        conn.request(
            "POST",
            "/v1/chat/completions",
            json.dumps(
                {"model": model, "messages": [{"role": "user", "content": "ping"}]}
            ),
            {"content-type": "application/json"},
        )
        response = conn.getresponse()
        return response.status, json.loads(response.read() or b"{}")
    finally:
        conn.close()


def test_every_lane_gets_an_answer_from_the_brain(brain):
    refused = {}
    for lane, model in sorted(_lane_models().items()):
        status, body = _ask(brain, model)
        if status != 200:
            refused[lane] = (
                f"{model}: HTTP {status} {body.get('error', {}).get('message')}"
            )
    assert not refused, f"lanes the brain refuses: {refused}"


def test_no_lane_is_left_on_the_library_default(brain):
    # A lane with no row is not an unused lane: otto/router/config.py hands
    # the brain its own default for that lane. Drive those defaults, so the
    # failure is the 400 the founder actually got, not a missing-key message.
    library_defaults = {
        "judgment": "anthropic/claude",
        "bulk": "minimax",
        "verify": "google/gemini",
        "deep": "kimi",
    }
    rows = _lane_models()
    would_400 = {}
    for lane in sorted(LANES_THE_ROUTER_DEFINES - set(rows)):
        status, body = _ask(brain, library_defaults[lane])
        if status != 200:
            would_400[lane] = (
                f"no row in {LANES.name}, falls back to "
                f"{library_defaults[lane]}: HTTP {status} "
                f"{body.get('error', {}).get('message')}"
            )
    assert not would_400, (
        f"lanes that would reach the brain on a default it refuses: {would_400}"
    )


def test_a_group_the_brain_never_served_is_refused(brain):
    # The other way round: the door must refuse, or the two tests above pass
    # for a door that says yes to everything.
    status, body = _ask(brain, "kimi-k3-a-group-no-row-names")
    assert status == 400, status
    assert "Invalid model name" in body["error"]["message"], body


def test_the_brain_answers_on_more_than_one_home(brain):
    # The founder's standing order: three homes, no single point of failure.
    homes = sorted(g for g in _served_groups() if g.startswith("home-"))
    answered = [h for h in homes if _ask(brain, h)[0] == 200]
    assert len(answered) >= 3, f"only {answered} of {homes}"
