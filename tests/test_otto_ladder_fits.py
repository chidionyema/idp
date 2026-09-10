"""Otto's fallback ladder has to fit inside the turn that climbs it, so climb it.

Otto is the founder's assistant and every outage he has lived through had the same shape: the
ladder read longer than it was. `platform/otto-gateway/three-homes.yaml` declares seven homes
in three chains; `OTTO_ROUTER_TIMEOUT_SECONDS` in the Deployment is how long Otto's own client
waits before it hangs up. If the rungs' timeouts add up past either budget, the last homes are
unreachable and the matrix has fewer homes than it claims -- silently, because nothing fails
until the day every lane above is down, which is exactly the day it matters.

Measured 2026-09-10, before the change that added this file: the longest chain summed to 197s
against a `request_timeout` of 155. The last rung -- the direct MiniMax line, the one home
that survives both the cluster and every free tier being spent -- could not be reached.

This does not assert the file's numbers back at it. It stands up a real socket for every lane
the config names, one that accepts the connection and never answers -- the worst case the
timeouts exist for -- and climbs each chain against it with the timeouts the config declares,
in order, the way the router does. Then it grades what actually happened: was the last home
reached, and was it reached before the client would have hung up.

Real seconds are divided by SCALE so a suite can run it; the arithmetic under test is a ratio
between the rungs and the budget, and dividing both sides leaves it intact. What is NOT
simulated is the socket: every hop below is a real connection to a real listener that really
withholds its answer, so a timeout that does not mean what the config says it means fails here.
"""

import http.server
import os
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

yaml = pytest.importorskip("yaml")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BRAIN = os.path.join(ROOT, "platform", "otto-gateway", "three-homes.yaml")
DEPLOY = os.path.join(ROOT, "platform", "otto-gateway", "deployment.yaml")

# Wall-clock is divided by this. 153 seconds of ladder is not a unit test; 5 is.
SCALE = 30.0
# The loopback hop between the gateway container and the sidecar, once per rung. A ladder
# graded to the last second is a ladder that fails the day one hop is slow.
HOP_SECONDS = 1.0


class _Silent(http.server.BaseHTTPRequestHandler):
    """Accepts the request and never answers it: every vendor at once, all of them down."""

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's spelling
        time.sleep(30)

    def log_message(self, *a):  # keep the suite's output the suite's
        pass


@pytest.fixture(scope="module")
def dead_vendor():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Silent)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d/v1/chat/completions" % srv.server_address[1]
    srv.shutdown()


def _brain():
    with open(BRAIN) as fh:
        cm = yaml.safe_load(fh)
    return yaml.safe_load(cm["data"]["config.yaml"])


def _client_ceiling():
    with open(DEPLOY) as fh:
        for doc in yaml.safe_load_all(fh):
            if not doc or doc.get("kind") != "Deployment":
                continue
            for c in doc["spec"]["template"]["spec"]["containers"]:
                for e in c.get("env") or []:
                    if e.get("name") == "OTTO_ROUTER_TIMEOUT_SECONDS":
                        return float(e["value"])
    raise AssertionError("no OTTO_ROUTER_TIMEOUT_SECONDS on any container in " + DEPLOY)


def _lanes(cfg):
    return {
        m["model_name"]: float(m["litellm_params"].get("timeout", 0))
        for m in cfg["model_list"]
    }


def _chains(cfg):
    out = {}
    for entry in cfg["router_settings"].get("fallbacks") or []:
        for head, rungs in entry.items():
            out[head] = [head, *rungs]
    return out


def _ask(url, seconds):
    """One hop against a vendor that will not answer. Returns what it really cost."""
    started = time.monotonic()
    req = urllib.request.Request(  # noqa: S310
        url, data=b"{}", headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=seconds).read()  # noqa: S310
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError):
        pass
    return time.monotonic() - started


@pytest.mark.parametrize("chain", sorted(_chains(_brain())))
def test_the_founder_reaches_the_last_home_before_his_client_hangs_up(
    chain, dead_vendor
):
    cfg = _brain()
    lanes = _lanes(cfg)
    rungs = _chains(cfg)[chain]

    unknown = [r for r in rungs if r not in lanes]
    assert not unknown, (  # noqa: S101
        f"chain {chain!r} names {unknown}, which no model_list entry serves; the climb raises "
        "at that rung and every home after it is unreachable"
    )

    budget = float(cfg["litellm_settings"]["request_timeout"]) / SCALE
    ceiling = _client_ceiling() / SCALE
    assert budget <= ceiling, (  # noqa: S101
        f"the brain allows a turn {budget * SCALE:.0f}s but Otto's client hangs up at "
        f"{ceiling * SCALE:.0f}s (OTTO_ROUTER_TIMEOUT_SECONDS): the founder never sees the "
        "last homes answer even when they would have"
    )

    spent = 0.0
    reached = []
    for rung in rungs:
        if spent + lanes[rung] / SCALE + HOP_SECONDS / SCALE > budget:
            break
        spent += _ask(dead_vendor, lanes[rung] / SCALE) + HOP_SECONDS / SCALE
        reached.append(rung)

    assert reached == rungs, (  # noqa: S101
        f"chain {chain!r} climbed only {reached} in {spent * SCALE:.0f}s of a "
        f"{budget * SCALE:.0f}s budget; {[r for r in rungs if r not in reached]} were never "
        "asked, so those homes are decoration"
    )
    assert spent <= ceiling, (  # noqa: S101
        f"chain {chain!r} took {spent * SCALE:.0f}s to reach its last home, past the "
        f"{ceiling * SCALE:.0f}s Otto's client waits"
    )


def test_no_chain_begins_inside_the_cluster(dead_vendor):
    """The founder, 2026-09-10: "theesare fr lands, can we use oront".

    A head rung is the one every turn pays for. While that rung was the estate router,
    losing the cluster cost Otto the first hop of every ladder before he could climb.
    The free lanes cost nothing and need no cluster, so they head the chains and the
    router is a rung in the middle. This holds that shape: it fails the moment anyone
    moves a `.svc.cluster.local` lane back to the front.
    """
    cfg = _brain()
    params = {m["model_name"]: m["litellm_params"] for m in cfg["model_list"]}
    chains = _chains(cfg)

    inside = [
        h
        for h in sorted(chains)
        if ".svc.cluster.local" in params[h].get("api_base", "")
    ]
    assert not inside, (  # noqa: S101
        f"chains {inside} open on the estate router, so every one of Otto's turns starts "
        "with a call into the cluster and a cluster outage costs him the first rung"
    )

    # and the router is still IN each chain -- dropped, not demoted, is a different bug.
    missing = [
        h
        for h in sorted(chains)
        if not any(
            ".svc.cluster.local" in params[r].get("api_base", "") for r in chains[h]
        )
    ]
    assert not missing, (  # noqa: S101
        f"chains {missing} no longer reach the estate router at all; it is where estate "
        "spend accounting and tracing live and it belongs in the middle, not gone"
    )

    # the heads must really be reachable without the cluster: prove the hop leaves this
    # process for a vendor address, not a cluster DNS name that resolves nowhere here.
    for head in sorted(chains):
        assert params[head]["api_base"].startswith("https://"), (  # noqa: S101
            f"head lane {head!r} is not a direct vendor line: {params[head]['api_base']}"
        )
    assert _ask(dead_vendor, 0.2) < 5.0, (  # noqa: S101
        "the loopback vendor answered nothing, as designed"
    )
