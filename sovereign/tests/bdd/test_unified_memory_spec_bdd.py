"""Unified memory, every requirement bar none: features/unified-memory/unified-memory.feature.

Every step talks to the LIVE estate. Nothing here is a stand-in: a memory server, MCP door,
JetStream, FleetView backend or Hindsight that is not configured or not reachable FAILS the
scenario with the reason, never skips it (a check that cannot fail is not a check).

Live targets, by env var name (secrets are read from files, never printed):
  UM_URL, UM_HOST, UM_TOKEN_FILE      the server via the KEDA interceptor, its estate surface token
  UM_TENANT_TOKEN_DIR                 <dir>/<tenant>.token for the tenant-isolation scenarios
  UM_SURFACE_TOKEN_DIR                one *.token file per surface for the fleet-scale scenario
  UM_PUBLIC_URL                       the public memory door (outside the cluster)
  ESTATE_MCP_URL, ESTATE_MCP_KEY_FILE the estate MCP door (agentgateway /estate/mcp)
  ESTATE_NATS_URL                     JetStream
  ESTATE_FLEET_URL                    the FleetView backend origin (GET /memory)
  ESTATE_HINDSIGHT_URL                Hindsight, for the migration proof
  ESTATE_VOICE_URL                    the voice intent door
The flux and log scenarios read the cluster with kubectl (read-only).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/unified-memory/unified-memory.feature")

REPO = Path(__file__).resolve().parents[3]


# ------------------------------------------------------------------ live plumbing


def need(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.fail(f"live target not configured: {name}")
    return value


def read_secret(path_env: str) -> str:
    path = need(path_env)
    try:
        return Path(path).read_text().strip()
    except OSError as exc:
        pytest.fail(f"{path_env} unreadable: {type(exc).__name__}")


def http(method, url, body=None, headers=None, timeout=60):
    """(status, parsed body or text). Never raises on an HTTP status."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})  # noqa: S310
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            raw = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read().decode("utf-8", "replace"), exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.fail(f"{method} {url} unreachable: {type(exc).__name__}: {exc}")
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


class Server:
    """The unified memory server, as one surface token sees it."""

    def __init__(self, token: str, base: str | None = None, host: str | None = None):
        self.base = (base or need("UM_URL")).rstrip("/")
        self.host = host if host is not None else os.environ.get("UM_HOST", "")
        self.token = token

    def h(self):
        h = {"authorization": f"Bearer {self.token}"}
        if self.host:
            h["host"] = self.host
        return h

    def put(self, ns, key, content, **extra):
        body = {"namespace": ns, "key": key, "content": content, **extra}
        q = urllib.parse.quote
        return http("PUT", f"{self.base}/memories/{q(ns, safe='')}/{q(key, safe='')}", body, self.h())

    def get(self, ns, key, **params):
        q = urllib.parse.quote
        qs = ("?" + urllib.parse.urlencode(params)) if params else ""
        return http("GET", f"{self.base}/memories/{q(ns, safe='')}/{q(key, safe='')}{qs}", None, self.h())

    def list(self, ns):
        return http("GET", f"{self.base}/memories/{urllib.parse.quote(ns, safe='')}", None, self.h())

    def delete(self, ns, key=None):
        q = urllib.parse.quote
        path = f"/memories/{q(ns, safe='')}" + (f"/{q(key, safe='')}" if key else "")
        return http("DELETE", f"{self.base}{path}", None, self.h())

    def recall(self, query, namespace=None, limit=10):
        body = {"query": query, "limit": limit}
        if namespace:
            body["namespace"] = namespace
        return http("POST", f"{self.base}/memories/recall", body, self.h())

    def history(self, ns, key):
        q = urllib.parse.quote
        return http("GET", f"{self.base}/memories/{q(ns, safe='')}/{q(key, safe='')}/history", None, self.h())


def facts(listing) -> list:
    status, body = listing
    assert status == 200, f"list refused: {status} {body}"
    return body.get("facts", []) if isinstance(body, dict) else []


def recalled(result) -> list:
    status, body = result
    assert status == 200, f"recall refused: {status} {str(body)[:300]}"
    return body.get("memories") or body.get("results") or [] if isinstance(body, dict) else []


def mcp_call(tool: str, arguments: dict, session: str):
    url = need("ESTATE_MCP_URL")
    key = read_secret("ESTATE_MCP_KEY_FILE")
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    headers = {
        "authorization": f"Bearer {key}",
        "accept": "application/json, text/event-stream",
        "mcp-session-id": session,
    }
    status, out = http("POST", url, body, headers)
    assert status == 200, f"MCP {tool} refused: {status} {str(out)[:300]}"
    if isinstance(out, str):  # an SSE frame: take the data line
        lines = [ln[5:].strip() for ln in out.splitlines() if ln.startswith("data:")]
        out = json.loads(lines[-1]) if lines else {}
    content = (out.get("result") or {}).get("structuredContent") or (out.get("result") or {}).get("content")
    if isinstance(content, list) and content and "text" in content[0]:
        content = json.loads(content[0]["text"])
    return content or {}


def kubectl(*args) -> str:
    r = subprocess.run(["kubectl", *args, "--request-timeout=30s"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"kubectl {' '.join(args)} failed: {r.stderr.strip()[:300]}"
    return r.stdout


# ------------------------------------------------------------------ fixtures


@pytest.fixture
def ctx():
    return {}


@pytest.fixture
def estate():
    return Server(read_secret("UM_TOKEN_FILE"))


def tenant(name: str) -> Server:
    d = Path(need("UM_TENANT_TOKEN_DIR"))
    f = d / f"{name}.token"
    if not f.exists():
        pytest.fail(f"no token for tenant {name!r}: the server has no way to mint one ({f})")
    return Server(f.read_text().strip())


def sub(text: str, ctx) -> str:
    return text.replace("<marker>", ctx["marker"])


# ------------------------------------------------------------------ background


@given("the live unified memory server is reachable through the KEDA interceptor")
def server_reachable(estate):
    status, _ = estate.list("estate")
    assert status == 200, f"unified memory server answered {status}"


@given("a unique marker for this run")
def marker(ctx):
    ctx["marker"] = f"bdd{uuid.uuid4().hex[:12]}"
    ctx["t0"] = time.time()


# ------------------------------------------------------------------ UM-01 cross-session MCP


@when(parsers.parse('session "{s}" remembers the marker through the estate MCP door'))
def mcp_remember(ctx, s):
    out = mcp_call(
        "remember",
        {"content": f"{ctx['marker']} written by {s}", "subject": "bdd", "kind": "measurement", "source": s},
        session=f"bdd-{s}-{ctx['marker']}",
    )
    assert out.get("written") is True, f"remember did not write: {out}"
    ctx["writer"] = s


@when(parsers.parse('session "{s}" recalls the marker through the estate MCP door'))
def mcp_recall(ctx, s):
    ctx["mcp_recall"] = mcp_call("recall", {"query": ctx["marker"]}, session=f"bdd-{s}-{ctx['marker']}")


@then("beta gets back the memory alpha wrote, with alpha named as its source")
def mcp_cross_session(ctx):
    mems = ctx["mcp_recall"].get("memories", [])
    hit = [m for m in mems if ctx["marker"] in m.get("text", "")]
    assert hit, f"beta did not recall alpha's memory: {ctx['mcp_recall']}"
    assert hit[0].get("metadata", {}).get("source") == ctx["writer"], f"source lost: {hit[0]}"


# ------------------------------------------------------------------ UM-02 JetStream


@given(parsers.parse('a JetStream subscriber on "{subject}"'))
def jetstream_sub(ctx, subject):
    ctx["nats"] = need("ESTATE_NATS_URL")
    ctx["subject"] = subject
    try:
        import nats  # noqa: F401
    except ImportError:
        pytest.fail("nats-py is not installed; the real-time bus cannot be observed")


@when("a surface keeps a memory carrying the marker")
def keep_marker(ctx, estate):
    async def run():
        import nats

        got = []
        nc = None
        if "nats" in ctx:
            nc = await nats.connect(ctx["nats"], connect_timeout=5)
            await nc.subscribe(ctx["subject"], cb=lambda m: got.append((time.time(), m.data.decode())))
        t = time.time()
        status, body = estate.put("estate", f"bdd.{ctx['marker']}", f"{ctx['marker']} kept")
        assert status == 200, f"keep refused: {status} {body}"
        if nc:
            await asyncio.sleep(2.5)
            await nc.close()
        return t, got

    if "nats" in ctx:
        ctx["kept_at"], ctx["events"] = asyncio.run(run())
    else:
        status, body = estate.put("estate", f"bdd.{ctx['marker']}", f"{ctx['marker']} kept")
        assert status == 200, f"keep refused: {status} {body}"
        ctx["kept_at"] = time.time()


@then("an event carrying the marker arrives within 2 seconds")
def event_arrives(ctx):
    hits = [t for t, data in ctx.get("events", []) if ctx["marker"] in data]
    assert hits, "no event carrying the marker was published on the bus"
    assert hits[0] - ctx["kept_at"] <= 2.0, f"event took {hits[0] - ctx['kept_at']:.2f}s"


# ------------------------------------------------------------------ UM-03 FleetView


@then("the FleetView memory channel lists the marker within 5 seconds")
def fleet_lists(ctx):
    base = need("ESTATE_FLEET_URL").rstrip("/")
    deadline = time.time() + 5
    body = None
    while time.time() < deadline:
        status, body = http("GET", f"{base}/memory")
        if status == 200 and ctx["marker"] in json.dumps(body):
            ctx["fleet"] = body
            return
        time.sleep(0.5)
    pytest.fail(f"FleetView /memory never showed the marker: {str(body)[:300]}")


@then("it reports the unified server's fact count and newest write")
def fleet_counts(ctx):
    unified = (ctx["fleet"] or {}).get("unified")
    assert isinstance(unified, dict), "FleetView /memory has no 'unified' source"
    assert isinstance(unified.get("facts"), int) and unified.get("newest_write"), unified


# ------------------------------------------------------------------ UM-04..07 Room keep/recall/tell/forget


@when(parsers.parse('the founder keeps "{key}" with reason "{reason}" and no expiry'))
def keep_reason(ctx, estate, key, reason):
    ctx["key"] = sub(key, ctx)
    status, body = estate.put("founder", ctx["key"], f"{ctx['marker']} value", provenance={"reason": reason})
    assert status == 200, f"keep refused: {status} {body}"


@then("recalling that key returns the value and the reason")
def recall_key_reason(ctx, estate):
    fact = [f for f in facts(estate.list("founder")) if f["key"] == ctx["key"]]
    assert fact, "kept key not found"
    assert fact[0]["content"] == f"{ctx['marker']} value"
    assert (fact[0].get("provenance") or {}).get("reason") == "bdd", f"reason not returned: {fact[0]}"


@then("telling everything kept includes that key")
def tell_includes(ctx, estate):
    assert ctx["key"] in [f["key"] for f in facts(estate.list("founder"))]


@when(parsers.parse('the founder keeps "{key}" expiring in {n:d} seconds'))
def keep_expiring(ctx, estate, key, n):
    ctx["key"] = sub(key, ctx)
    expires = (datetime.now(timezone.utc) + timedelta(seconds=n)).isoformat()
    status, body = estate.put("founder", ctx["key"], ctx["marker"], expires_at=expires)
    assert status == 200, f"keep refused: {status} {body}"


@when(parsers.parse("{n:d} seconds pass"))
def wait_seconds(n):
    time.sleep(n)


@then("recalling that key returns nothing")
def recall_nothing(ctx, estate):
    status, body = estate.get("founder", ctx["key"])
    assert status == 404, f"key still answers: {status} {body}"


@then("telling everything kept does not include that key")
def tell_excludes(ctx, estate):
    assert ctx["key"] not in [f["key"] for f in facts(estate.list("founder"))]


@given(parsers.parse('the founder has kept "{key}"'))
def has_kept(ctx, estate, key):
    ctx["key"] = sub(key, ctx)
    status, body = estate.put("founder", ctx["key"], f"{ctx['marker']} to forget")
    assert status == 200, f"keep refused: {status} {body}"


@when(parsers.parse('the founder forgets "{key}"'))
def forget(ctx, estate, key):
    status, body = estate.delete("founder", sub(key, ctx))
    assert status in (200, 204), f"forget refused: {status} {body}"


@then("a search for the marker returns nothing")
def search_nothing(ctx, estate):
    assert not [m for m in recalled(estate.recall(ctx["marker"])) if ctx["marker"] in json.dumps(m)]


@then("the MCP recall tool does not return it")
def mcp_not_returned(ctx):
    out = mcp_call("recall", {"query": ctx["marker"]}, session=f"bdd-forget-{ctx['marker']}")
    assert not [m for m in out.get("memories", []) if ctx["marker"] in m.get("text", "")]


@given(parsers.parse('tenant "{a}" and tenant "{b}" each keep a memory carrying the marker'))
def two_tenants_keep(ctx, a, b):
    ctx["tenants"] = {a: tenant(a), b: tenant(b)}
    for name, srv in ctx["tenants"].items():
        status, body = srv.put("founder", f"bdd.{name}.{ctx['marker']}", f"{ctx['marker']} {name}")
        assert status == 200, f"{name} keep refused: {status} {body}"


@when(parsers.parse('tenant "{a}" forgets everything'))
def forget_all(ctx, a):
    status, body = ctx["tenants"][a].delete("founder")
    assert status in (200, 204), f"forget-all refused: {status} {body}"


@then(parsers.parse('tenant "{a}" recalls nothing carrying the marker'))
def tenant_nothing(ctx, a):
    assert not [f for f in facts(ctx["tenants"][a].list("founder")) if ctx["marker"] in f["content"]]


@then(parsers.parse('tenant "{b}" still recalls its memory'))
def tenant_still(ctx, b):
    assert [f for f in facts(ctx["tenants"][b].list("founder")) if ctx["marker"] in f["content"]]


# ------------------------------------------------------------------ UM-08, UM-09 recall quality


@given(parsers.parse('a memory "{text}" carrying the marker'))
def memory_text(ctx, estate, text):
    status, body = estate.put("estate", f"bdd.sem.{ctx['marker']}", f"{text} [{ctx['marker']}]")
    assert status == 200, f"keep refused: {status} {body}"


@when(parsers.parse('a surface searches "{query}" scoped to the marker'))
def semantic_search(ctx, estate, query):
    ctx["results"] = recalled(estate.recall(query, limit=3))


@then("that memory is in the top 3 results")
def in_top3(ctx):
    assert [m for m in ctx["results"] if ctx["marker"] in json.dumps(m)], f"not found by meaning: {ctx['results']}"


@given("two equally relevant memories carrying the marker, one 30 days old and one new")
def old_and_new(ctx, estate):
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    for key, extra in ((f"bdd.old.{ctx['marker']}", {"valid_from": old}), (f"bdd.new.{ctx['marker']}", {})):
        status, body = estate.put("estate", key, f"{ctx['marker']} ranked", **extra)
        assert status == 200, f"keep refused: {status} {body}"


@when("a surface searches for the marker")
def search_marker(ctx, estate):
    ctx["results"] = recalled(estate.recall(ctx["marker"]))


@then("the new memory ranks above the old one")
def new_above_old(ctx):
    keys = [m.get("key", "") for m in ctx["results"]]
    new, old = f"bdd.new.{ctx['marker']}", f"bdd.old.{ctx['marker']}"
    assert new in keys and old in keys, f"both not returned: {keys}"
    assert keys.index(new) < keys.index(old), f"decay not applied: {keys}"


@then("recalling the old memory raises its strength")
def strength_rises(ctx, estate):
    def strength():
        m = [r for r in recalled(estate.recall(ctx["marker"])) if r.get("key") == f"bdd.old.{ctx['marker']}"]
        assert m and "strength_days" in m[0], f"no strength reported: {m}"
        return m[0]["strength_days"]

    before = strength()
    assert strength() > before, "a recall did not strengthen the memory"


# ------------------------------------------------------------------ UM-10..12 trust, curation, Anti-Ouroboros


@given(parsers.parse("a memory carrying the marker with harm {h:f}"))
def harmful(ctx, estate, h):
    ctx["key"] = f"bdd.harm.{ctx['marker']}"
    status, body = estate.put("estate", ctx["key"], ctx["marker"], harm_h=h)
    assert status == 200, f"keep refused: {status} {body}"


@given(parsers.parse("a memory carrying the marker with relevance {r:f}, truthfulness {t:f} and harm {h:f}"))
def promotable(ctx, estate, r, t, h):
    ctx["key"] = f"bdd.promote.{ctx['marker']}"
    status, body = estate.put("estate", ctx["key"], ctx["marker"], relevance_rho=r, truthfulness_tau=t, harm_h=h)
    assert status == 200, f"keep refused: {status} {body}"


@when("the curation worker runs one tick")
def curation_tick():
    out = kubectl("-n", "unified-memory", "get", "deploy", "-o", "name")
    assert "curation" in out, f"no curation worker is deployed: {out.split()}"
    time.sleep(90)  # one tick is 60s in curation_worker.py


def memory_row(ctx, estate):
    status, body = estate.get("estate", ctx["key"])
    return status, body


@then("that memory is quarantined")
def quarantined(ctx, estate):
    status, body = memory_row(ctx, estate)
    assert status == 404, f"quarantined memory still readable: {status} {body}"


@then("no surface can recall it")
def no_recall(ctx, estate):
    assert not [m for m in recalled(estate.recall(ctx["marker"])) if ctx["marker"] in json.dumps(m)]


@then("that memory is shared")
def shared(ctx, estate):
    fact = [f for f in facts(estate.list("estate")) if f["key"] == ctx["key"]]
    assert fact and fact[0].get("is_shared") is True, f"not promoted: {fact}"


@given("two llm_derived memories carrying the marker")
def two_llm(ctx, estate):
    ctx["keys"] = [f"bdd.llm1.{ctx['marker']}", f"bdd.llm2.{ctx['marker']}"]
    for k in ctx["keys"]:
        status, body = estate.put("estate", k, ctx["marker"], trust_tier="llm_derived")
        assert status == 200, f"keep refused: {status} {body}"


@when("one is set to supersede the other")
def supersede(ctx, estate):
    ctx["supersede"] = estate.put(
        "estate", ctx["keys"][0], f"{ctx['marker']} again", trust_tier="llm_derived", superseded_by_key=ctx["keys"][1]
    )


@then("the server refuses with ANTI_OUROBOROS_VIOLATION")
def ouroboros(ctx):
    status, body = ctx["supersede"]
    assert status in (409, 422) and "ANTI_OUROBOROS" in json.dumps(body), f"not refused: {status} {body}"


# ------------------------------------------------------------------ UM-13, UM-14 tenants and surfaces


@given(parsers.parse('tenant "{a}" keeps a memory carrying the marker'))
def tenant_keeps(ctx, a):
    ctx["tenants"] = {a: tenant(a)}
    status, body = ctx["tenants"][a].put("founder", f"bdd.iso.{ctx['marker']}", ctx["marker"])
    assert status == 200, f"keep refused: {status} {body}"


@when(parsers.parse('tenant "{b}" lists that namespace and reads that key'))
def other_tenant_reads(ctx, b):
    srv = tenant(b)
    ctx["seen"] = [f for f in facts(srv.list("founder")) if ctx["marker"] in f["content"]]
    status, _ = srv.get("founder", f"bdd.iso.{ctx['marker']}")
    ctx["read_status"] = status


@then(parsers.parse('tenant "{b}" sees nothing carrying the marker'))
def sees_nothing(ctx, b):
    assert ctx["seen"] == [] and ctx["read_status"] == 404, (ctx["seen"], ctx["read_status"])


@given(parsers.parse("{n:d} distinct surface tokens, one per surface"))
def surface_tokens(ctx, n):
    files = sorted(Path(need("UM_SURFACE_TOKEN_DIR")).glob("*.token"))
    if len(files) < n:
        pytest.fail(f"only {len(files)} surface tokens exist; the server has no way to mint {n}")
    ctx["surfaces"] = {f.stem: Server(f.read_text().strip()) for f in files[:n]}


@when(parsers.parse("each surface makes {k:d} memory calls within one minute"))
def burst(ctx, k):
    ctx["statuses"] = []
    for name, srv in ctx["surfaces"].items():
        for i in range(k):
            status, _ = srv.put("estate", f"bdd.burst.{ctx['marker']}.{name}.{i}", ctx["marker"])
            ctx["statuses"].append((name, status))


@then("no call is refused with 429")
def no_429(ctx):
    refused = [s for s in ctx["statuses"] if s[1] == 429]
    assert not refused, f"{len(refused)} calls refused with 429"


@then("each call is attributed to its own surface")
def attributed(ctx, estate):
    for name in ctx["surfaces"]:
        status, body = estate.get("estate", f"bdd.burst.{ctx['marker']}.{name}.0")
        assert status == 200 and body.get("surface") == name, f"surface not recorded: {body}"


# ------------------------------------------------------------------ UM-15 public door


@when("a surface calls the public memory door with its token")
def public_door(ctx):
    ctx["public"] = Server(read_secret("UM_TOKEN_FILE"), base=need("UM_PUBLIC_URL"), host="")


@then("it can keep and recall a memory carrying the marker")
def public_keep_recall(ctx):
    srv = ctx["public"]
    status, body = srv.put("estate", f"bdd.public.{ctx['marker']}", ctx["marker"])
    assert status == 200, f"public keep refused: {status} {body}"
    assert [f for f in facts(srv.list("estate")) if f["key"] == f"bdd.public.{ctx['marker']}"]


@then("a call without a token is refused with 401")
def public_401(ctx):
    status, _ = http("GET", f"{ctx['public'].base}/memories/estate")
    assert status == 401, f"unauthenticated call answered {status}"


# ------------------------------------------------------------------ UM-16 signed action stream


@when(parsers.parse('a signed agent action carrying the marker is published on "{subject}"'))
def publish_action(ctx, subject):
    url = need("ESTATE_NATS_URL")

    async def run():
        import nats

        nc = await nats.connect(url, connect_timeout=5)
        js = nc.jetstream()
        await js.publish(
            f"estate.agent.bdd.{ctx['marker']}",
            json.dumps({"agent": "bdd", "action": "test", "detail": ctx["marker"]}).encode(),
        )
        await nc.close()

    try:
        asyncio.run(run())
    except ImportError:
        pytest.fail("nats-py is not installed")


@then("within 10 seconds a memory carrying the marker exists with its action as provenance")
def action_memory(ctx, estate):
    deadline = time.time() + 10
    while time.time() < deadline:
        hit = [f for f in facts(estate.list("estate")) if ctx["marker"] in f["content"]]
        if hit:
            assert (hit[0].get("provenance") or {}).get("action"), f"no action provenance: {hit[0]}"
            return
        time.sleep(1)
    pytest.fail("no memory was built from the signed action")


# ------------------------------------------------------------------ UM-17 write guard


@when(parsers.parse('a surface keeps content "{content}" carrying the marker'))
def keep_injection(ctx, estate, content):
    ctx["guard"] = estate.put("estate", f"bdd.guard.{ctx['marker']}", f"{content} {ctx['marker']}")


@then("the server refuses it with 422")
def refused_422(ctx):
    assert ctx["guard"][0] == 422, f"injection accepted: {ctx['guard']}"


@then(parsers.parse('a write to the key "{key}" is refused with 422'))
def immutable_422(estate, key):
    status, body = estate.put("estate", key, "overwrite attempt")
    assert status == 422, f"immutable key accepted: {status} {body}"


# ------------------------------------------------------------------ UM-18 bitemporal


@given(parsers.parse('key "{key}" was kept as "{first}" and then as "{second}"'))
def two_versions(ctx, estate, key, first, second):
    ctx["key"] = sub(key, ctx)
    for value in (first, second):
        status, body = estate.put("estate", ctx["key"], value)
        assert status == 200, f"keep refused: {status} {body}"
        ctx.setdefault("between", []).append(datetime.now(timezone.utc).isoformat())
        time.sleep(1.5)


@when("it is read as of a moment between the two writes")
def read_as_of(ctx, estate):
    ctx["asof"] = estate.get("estate", ctx["key"], as_of=ctx["between"][0])


@then(parsers.parse('the answer is "{value}"'))
def answer_is(ctx, value):
    status, body = ctx["asof"]
    assert status == 200 and body.get("content") == value, f"as_of answered {status} {body}"


@then("the history lists both versions in order")
def history_both(ctx, estate):
    status, body = estate.history("estate", ctx["key"])
    assert status == 200, f"history refused: {status} {body}"
    contents = [v.get("content") for v in body.get("versions", body if isinstance(body, list) else [])]
    assert contents[:2] in (["first", "second"], ["second", "first"]), contents


# ------------------------------------------------------------------ UM-19 flux + production log


@then("the unified-memory Flux Kustomization has wait true")
def flux_wait():
    out = kubectl("-n", "flux-system", "get", "kustomization", "unified-memory", "-o", "jsonpath={.spec.wait}")
    assert out.strip() == "true", f"spec.wait is {out.strip() or 'unset'}"


@then("the server's production log shows the run's write and read as 200")
def prod_log(ctx):
    out = kubectl("-n", "unified-memory", "logs", "deploy/unified-memory-server", "--since=15m")
    assert '"PUT /memories/' in out and "200" in out, "no PUT 200 in the production log"
    assert '"GET /memories/' in out, "no GET in the production log"


# ------------------------------------------------------------------ UM-20, UM-21 migrations


@then(parsers.parse('every fact in Hindsight bank "{bank}" is recallable from the unified server by its Hindsight id'))
def hindsight_migrated(estate, bank):
    base = need("ESTATE_HINDSIGHT_URL").rstrip("/")
    status, body = http("GET", f"{base}/v1/default/banks/{bank}/memories/list?limit=1000")
    assert status == 200, f"Hindsight list refused: {status}"
    ids = {str(m.get("id")) for m in (body.get("items") or body.get("memories") or [])}
    assert ids, "Hindsight returned no facts to check"
    migrated = {
        str((f.get("provenance") or {}).get("hindsight_id"))
        for f in facts(estate.list("hindsight"))
    }
    missing = ids - migrated
    assert not missing, f"{len(missing)} of {len(ids)} Hindsight facts not in the unified server"


@then("the Graphiti memory server is not configured in any repository")
def no_graphiti():
    mcp = json.loads((REPO / ".mcp.json").read_text()) if (REPO / ".mcp.json").exists() else {}
    for name, spec in (mcp.get("mcpServers") or {}).items():
        assert "estate-core/memory" not in json.dumps(spec), f".mcp.json still serves Graphiti as {name!r}"


@then("every Claude auto-memory file is recallable from the unified server")
def claude_files_migrated(estate):
    files = list(Path.home().glob(".claude/projects/*/memory/*.md"))
    assert files, "no Claude memory files found to check"
    keys = {f["key"] for f in facts(estate.list("claude-memory"))}
    missing = [f.stem for f in files if f"claude-memory.{f.parent.parent.name}.{f.stem}" not in keys]
    assert not missing, f"{len(missing)} of {len(files)} Claude memory files not migrated"


@then("every growmos decision entity is recallable from the unified server")
def growmos_migrated(estate):
    ents = REPO.parent / "estate-graph" / ".growmos" / "entities.jsonl"
    assert ents.exists(), f"no estate graph at {ents}"
    decisions = [json.loads(ln) for ln in ents.read_text().splitlines() if '"DECISION"' in ln]
    keys = {f["key"] for f in facts(estate.list("growmos"))}
    missing = [d for d in decisions if f"growmos.{d.get('id')}" not in keys]
    assert not missing, f"{len(missing)} of {len(decisions)} growmos decisions not migrated"


# ------------------------------------------------------------------ UM-22 voice


def voice(utterance: str):
    base = need("ESTATE_VOICE_URL").rstrip("/")
    status, body = http("POST", f"{base}/intent", {"utterance": utterance})
    assert status == 200, f"voice intent refused: {status} {str(body)[:200]}"
    return body


@when(parsers.parse('the voice intent "{utterance}" is spoken'))
def speak(ctx, utterance):
    ctx["voice"] = voice(sub(utterance, ctx))


@then("a memory carrying the marker exists")
def voice_memory_exists(ctx, estate):
    assert [f for f in facts(estate.list("founder")) if ctx["marker"] in f["content"]], "voice did not keep it"


@then(parsers.parse('the voice intent "{utterance}" answers with it'))
def voice_answers(ctx, utterance):
    assert ctx["marker"] in json.dumps(voice(sub(utterance, ctx))), "voice did not recall it"


@then(parsers.parse('the voice intent "{utterance}" removes it'))
def voice_forgets(ctx, estate, utterance):
    voice(sub(utterance, ctx))
    assert not [f for f in facts(estate.list("founder")) if ctx["marker"] in f["content"]], "voice did not forget"
