"""platform/unified-memory-server against a real PostgreSQL, never a mock.

Each test starts the FastAPI app with its real lifespan (schema migration, pool, SET ROLE)
against a throwaway PostgreSQL 16 with pgvector that pgserver runs from a pip wheel: no
Docker, no cluster. The app connects as the database superuser because that is what the
manifest (oke-unified-memory.yaml) gives it -- the case where row-level security used to
be bypassed.

The first three tests are the three defects measured on main (2026-09-27) before this change:
  1. the second boot died:  DuplicateObject: type "trust_tier_enum" already exists
  2. tenant B read tenant A's memory (row-level security bypassed by owner and superuser)
  3. an update destroyed the value it replaced
The rest cover the bi-temporal history: as_of / known_at reads, late writes, the future
valid_from refusal, append-only history, the order-independent digest, and a seeded
randomised comparison against an independent reference model.
"""

import concurrent.futures
import hashlib
import importlib.util
import json
import os
import random
import secrets
import sys
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pgserver = pytest.importorskip("pgserver")
psycopg = pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")
from fastapi.testclient import TestClient  # noqa: E402
from psycopg.conninfo import make_conninfo  # noqa: E402

SERVER_DIR = Path(__file__).resolve().parents[1] / "platform" / "unified-memory-server"


@pytest.fixture(scope="module")
def pg():
    server = pgserver.get_server(
        tempfile.mkdtemp(prefix="umem-pg-"), cleanup_mode="delete"
    )
    yield server
    server.cleanup()


@pytest.fixture()
def database_url(pg):
    # A fresh database per test: no test can pass on another test's rows.
    name = "umem_" + uuid.uuid4().hex[:12]
    with psycopg.connect(pg.get_uri(), autocommit=True) as c:
        c.execute(f"CREATE DATABASE {name}")
    return make_conninfo(pg.get_uri(), dbname=name)


def load_app(database_url, **env):
    """A fresh module instance per call: its own `pool` global, like a separate pod."""
    for name in ("DATABASE_URL", "DATABASE_URL_FILE", "MEMORY_SURFACE_TOKEN_FILE"):
        os.environ.pop(name, None)
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    os.environ.update(env)
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))
    spec = importlib.util.spec_from_file_location(
        "unified_memory_main_" + uuid.uuid4().hex[:8], SERVER_DIR / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tenant:
    """A tenant with surface tokens. A fresh token every 25 requests keeps a long test
    under the server's 30-per-minute limit without touching the limiter itself."""

    def __init__(self, database_url, name):
        self.database_url = database_url
        with psycopg.connect(database_url, autocommit=True) as c:
            self.id = c.execute(
                "INSERT INTO tenants(name) VALUES (%s) RETURNING tenant_id", (name,)
            ).fetchone()[0]
        self.uses = 0
        self.token = None

    def headers(self):
        if self.token is None or self.uses >= 25:
            self.token = secrets.token_urlsafe(32)
            with psycopg.connect(self.database_url, autocommit=True) as c:
                c.execute(
                    "INSERT INTO surface_tokens(tenant_id, surface_name, token_hash) "
                    "VALUES (%s, 'test', %s)",
                    (self.id, hashlib.sha256(self.token.encode()).hexdigest()),
                )
            self.uses = 0
        self.uses += 1
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture()
def booted(database_url):
    module = load_app(database_url)
    with TestClient(module.app) as client:
        client.module = module
        yield client, database_url


def put(client, tenant, ns, key, content, **extra):
    body = {"namespace": ns, "key": key, "content": content, **extra}
    return client.put(f"/memories/{ns}/{key}", json=body, headers=tenant.headers())


def db_now(database_url):
    with psycopg.connect(database_url) as c:
        return c.execute("SELECT clock_timestamp()").fetchone()[0]


def iso(t):
    return t.isoformat()


# --- the three defects measured on main --------------------------------------------------


def test_second_boot_succeeds_and_data_survives_it(database_url):
    with TestClient(load_app(database_url).app) as client:
        a = Tenant(database_url, "A")
        assert put(client, a, "user_42", "drink", "tea").status_code == 200
    # Boot two: the schema runs again against a database that already has it.
    with TestClient(load_app(database_url).app) as client:
        r = client.get("/memories/user_42/drink", headers=a.headers())
        assert r.status_code == 200, r.text
        assert r.json()["content"] == "tea"


def test_pods_booting_at_the_same_moment_all_come_up(database_url):
    def boot():
        with TestClient(load_app(database_url).app) as client:
            return client.get("/docs").status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(lambda _: boot(), range(3))) == [200, 200, 200]


def test_a_tenant_cannot_read_or_overwrite_another_tenants_memory(booted):
    client, url = booted
    a, b = Tenant(url, "A"), Tenant(url, "B")
    assert put(client, a, "user_42", "secret", "A-private").status_code == 200

    assert (
        client.get("/memories/user_42/secret", headers=b.headers()).status_code == 404
    )
    assert client.get("/memories/user_42", headers=b.headers()).json()["facts"] == []
    history = client.get("/memories/user_42/secret/history", headers=b.headers())
    assert history.json()["versions"] == []
    assert client.get("/digest/user_42", headers=b.headers()).json()["facts"] == 0

    # B writing the same key makes B's own row; A's value is untouched.
    assert (
        put(client, b, "user_42", "secret", "B-private").json()["status"] == "CREATED"
    )
    assert client.get("/memories/user_42/secret", headers=a.headers()).json()[
        "content"
    ] == ("A-private")


def test_requests_run_as_the_app_role_not_the_superuser(booted):
    client, url = booted
    with psycopg.connect(url) as c:
        assert c.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
        ).fetchone()[0], "the test must connect as a superuser, as the manifest does"
    pool = client.module.pool

    async def whoami():
        async with pool.connection() as conn:
            cur = await conn.execute("SELECT current_user")
            return (await cur.fetchone())["current_user"]

    assert client.portal.call(whoami) == "memory_app"


def test_an_update_keeps_the_value_it_replaced(booted):
    client, url = booted
    a = Tenant(url, "A")
    for value in ("tea", "coffee", "water"):
        assert put(client, a, "user_42", "drink", value).status_code == 200
    versions = client.get("/memories/user_42/drink/history", headers=a.headers()).json()
    assert [v["content"] for v in versions["versions"]] == ["tea", "coffee", "water"]
    assert (
        client.get("/memories/user_42/drink", headers=a.headers()).json()["content"]
        == "water"
    )


# --- bi-temporal reads ---------------------------------------------------------------------


def test_as_of_returns_the_value_that_was_true_then(booted):
    client, url = booted
    a = Tenant(url, "A")
    t0 = datetime.now(timezone.utc) - timedelta(days=3)
    for i, value in enumerate(("tea", "coffee", "water")):
        r = put(
            client, a, "user_42", "drink", value, valid_from=iso(t0 + timedelta(days=i))
        )
        assert r.status_code == 200, r.text

    def at(t):
        r = client.get(
            "/memories/user_42/drink", params={"as_of": iso(t)}, headers=a.headers()
        )
        return r.json().get("content") if r.status_code == 200 else r.status_code

    assert at(t0 - timedelta(seconds=1)) == 404  # nothing was true yet
    assert at(t0) == "tea"  # valid_from is inclusive
    assert at(t0 + timedelta(hours=12)) == "tea"
    assert at(t0 + timedelta(days=1)) == "coffee"
    assert at(t0 + timedelta(days=1, hours=23)) == "coffee"
    assert at(t0 + timedelta(days=2)) == "water"
    assert at(datetime.now(timezone.utc)) == "water"


def test_known_at_answers_what_the_server_believed_at_that_moment(booted):
    client, url = booted
    a = Tenant(url, "A")
    now = datetime.now(timezone.utc)
    t_early, t_late = now - timedelta(days=2), now - timedelta(days=1)
    assert (
        put(client, a, "u", "city", "Leeds", valid_from=iso(t_late)).status_code == 200
    )
    before_correction = db_now(url)
    r = put(client, a, "u", "city", "York", valid_from=iso(t_early))
    assert r.json()["status"] == "RECORDED_AS_PAST"

    def read(as_of, known_at=None):
        params = {"as_of": iso(as_of)}
        if known_at:
            params["known_at"] = iso(known_at)
        r = client.get("/memories/u/city", params=params, headers=a.headers())
        return r.json().get("content") if r.status_code == 200 else r.status_code

    probe = t_early + timedelta(hours=1)
    assert read(probe, known_at=before_correction) == 404  # not yet known then
    assert read(probe) == "York"  # known now
    assert read(t_late, known_at=before_correction) == "Leeds"


def test_a_late_write_does_not_overwrite_the_current_value(booted):
    client, url = booted
    a = Tenant(url, "A")
    now = datetime.now(timezone.utc)
    first = put(
        client, a, "u", "role", "lead", valid_from=iso(now - timedelta(hours=1))
    )
    late = put(
        client, a, "u", "role", "junior", valid_from=iso(now - timedelta(days=30))
    )
    assert late.status_code == 200
    assert late.json() == {
        "status": "RECORDED_AS_PAST",
        "id": first.json()["id"],
        "version": 1,
    }
    assert (
        client.get("/memories/u/role", headers=a.headers()).json()["content"] == "lead"
    )
    facts = client.get("/memories/u", headers=a.headers()).json()["facts"]
    assert [(f["key"], f["content"], f["version"]) for f in facts] == [
        ("role", "lead", 1)
    ]
    history = client.get("/memories/u/role/history", headers=a.headers()).json()[
        "versions"
    ]
    assert [v["content"] for v in history] == ["junior", "lead"]


def test_valid_from_is_refused_far_in_the_future_or_without_a_timezone(booted):
    client, url = booted
    a = Tenant(url, "A")
    now = datetime.now(timezone.utc)
    r = put(client, a, "u", "k", "v", valid_from=iso(now + timedelta(hours=1)))
    assert (
        r.status_code == 422 and r.json()["detail"]["error"] == "VALID_FROM_IN_FUTURE"
    )
    assert (
        put(client, a, "u", "k", "v", valid_from="2026-01-01T00:00:00").status_code
        == 422
    )
    # Inside the 60 s skew allowance is accepted.
    assert put(
        client, a, "u", "k", "v", valid_from=iso(now + timedelta(seconds=30))
    ).status_code == (200)


def test_human_confirmed_memory_is_protected_on_the_late_write_path_too(booted):
    client, url = booted
    a = Tenant(url, "A")
    assert (
        put(client, a, "u", "name", "Chidi", trust_tier="human_confirmed").status_code
        == 200
    )
    past = iso(datetime.now(timezone.utc) - timedelta(days=5))
    r = put(
        client,
        a,
        "u",
        "name",
        "someone else",
        trust_tier="llm_derived",
        valid_from=past,
    )
    assert r.status_code == 403
    history = client.get("/memories/u/name/history", headers=a.headers()).json()[
        "versions"
    ]
    assert [v["content"] for v in history] == ["Chidi"]


@pytest.mark.parametrize(
    "statement",
    ["UPDATE memory_versions SET content = 'x'", "DELETE FROM memory_versions"],
)
def test_history_is_append_only_even_for_the_superuser(booted, statement):
    client, url = booted
    a = Tenant(url, "A")
    assert put(client, a, "u", "k", "v").status_code == 200
    with psycopg.connect(url) as c:
        with pytest.raises(
            psycopg.errors.CheckViolation, match="HISTORY_IS_APPEND_ONLY"
        ):
            c.execute(statement)


# --- the digest ----------------------------------------------------------------------------


def reference_digest(facts):
    """Independent of the SQL: sha256 over length-prefixed key + sha256(content), byte order."""
    lines = sorted(
        f"{len(k)}:{k}{hashlib.sha256(v.encode()).hexdigest()}"
        for k, v in facts.items()
    )
    lines.sort(key=lambda s: s.encode())
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def test_digest_depends_on_the_facts_not_the_order_they_were_written(booted):
    client, url = booted
    rng = random.Random(20260927)  # noqa: S311 - seeded, reproducible test data
    facts = {
        f"k{i:02d}{rng.choice('aBz_é')}": f"value {rng.random()}" for i in range(25)
    }
    tenants = [Tenant(url, f"T{i}") for i in range(4)]
    digests = []
    for tenant in tenants:
        order = list(facts.items())
        rng.shuffle(order)
        for k, v in order:
            assert put(client, tenant, "subject", k, v).status_code == 200
        body = client.get("/digest/subject", headers=tenant.headers()).json()
        assert body["facts"] == len(facts)
        digests.append(body["digest"])
    assert len(set(digests)) == 1
    assert digests[0] == reference_digest(facts)

    changed_key = sorted(facts)[7]
    put(client, tenants[0], "subject", changed_key, facts[changed_key] + "!")
    assert (
        client.get("/digest/subject", headers=tenants[0].headers()).json()["digest"]
        != (digests[0])
    )


# --- randomised comparison against a reference model ---------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_randomised_writes_match_the_reference_model(booted, seed):
    """Random writes with colliding and out-of-order valid_from values, then every
    (as_of, known_at) pair is compared with a model written without the server's SQL:
    the answer is the write with the greatest (valid_from, write order) among writes
    made by known_at whose valid_from is at or before as_of."""
    client, url = booted
    rng = random.Random(seed)  # noqa: S311 - seeded, reproducible test data
    a = Tenant(url, "A")
    base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    slots = [
        base + timedelta(minutes=m) for m in range(6)
    ]  # few slots: ties are common

    writes, checkpoints = [], []  # writes: (valid_from, seq, content)
    for seq in range(14):
        vf = rng.choice(slots)
        content = f"s{seed}-w{seq}"
        r = put(client, a, "subj", "pred", content, valid_from=iso(vf))
        assert r.status_code == 200, r.text
        current_before = max(writes)[0] if writes else None
        expected_status = (
            "RECORDED_AS_PAST"
            if current_before is not None and vf < current_before
            else ("CREATED" if not writes else "UPDATED")
        )
        assert r.json()["status"] == expected_status, (seed, seq)
        writes.append((vf, seq, content))
        checkpoints.append(db_now(url))

    def model(as_of, upto):
        known = [w for w in writes[: upto + 1] if w[0] <= as_of]
        return max(known)[2] if known else None

    probes = [s + timedelta(seconds=d) for s in slots for d in (-1, 0, 30)]
    for k, known_at in enumerate(checkpoints):
        for as_of in probes:
            r = client.get(
                "/memories/subj/pred",
                params={"as_of": iso(as_of), "known_at": iso(known_at)},
                headers=a.headers(),
            )
            got = r.json()["content"] if r.status_code == 200 else None
            assert got == model(as_of, k), (seed, k, as_of)

    current = client.get("/memories/subj", headers=a.headers()).json()["facts"]
    assert [f["content"] for f in current] == [max(writes)[2]]
    history = client.get("/memories/subj/pred/history", headers=a.headers()).json()[
        "versions"
    ]
    assert len(history) == len(writes)


def estate_db_shaped(pg):
    """The database the way estate-db hands it over: a login role with no CREATEROLE that owns
    its database, memory_app declared by the operator with that role a plain member (CNPG
    managed.roles inRoles: no ADMIN OPTION), and vector created by the Database resource."""
    name = "umem_" + uuid.uuid4().hex[:12]
    owner = "owner_" + uuid.uuid4().hex[:8]
    with psycopg.connect(pg.get_uri(), autocommit=True) as c:
        c.execute(f"CREATE ROLE {owner} LOGIN NOCREATEROLE PASSWORD 'x'")
        c.execute(f"CREATE DATABASE {name} OWNER {owner}")
        if not c.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'memory_app'"
        ).fetchone():
            c.execute("CREATE ROLE memory_app NOLOGIN NOSUPERUSER NOBYPASSRLS")
        c.execute(f"GRANT memory_app TO {owner}")
    with psycopg.connect(
        make_conninfo(pg.get_uri(), dbname=name), autocommit=True
    ) as c:
        c.execute("CREATE EXTENSION vector")
    return make_conninfo(pg.get_uri(), dbname=name, user=owner, password="x")  # noqa: S106 - throwaway test database


def test_the_table_owner_is_held_to_tenant_isolation_too(pg):
    """FORCE ROW LEVEL SECURITY, measured on its own: a non-superuser that owns the tables
    (the role that ran schema.sql) reads with no SET ROLE, and still sees only its tenant."""
    url = estate_db_shaped(pg)
    with TestClient(load_app(url).app) as client:
        a = Tenant(url, "A")
        Tenant(url, "B")
        assert put(client, a, "u", "secret", "A-private").status_code == 200
    with psycopg.connect(url, autocommit=True) as c:
        b_id = c.execute("SELECT tenant_id FROM tenants WHERE name = 'B'").fetchone()[0]
        c.execute("SELECT set_config('app.tenant_id', %s, false)", (str(b_id),))
        assert c.execute("SELECT content FROM memories").fetchall() == []
        assert c.execute("SELECT content FROM memory_versions").fetchall() == []


def test_boot_deletes_the_named_test_leftovers_and_nothing_else(pg):
    """schema.sql section 10, on the estate-db shape (an owner held to FORCE ROW LEVEL
    SECURITY): the named leftovers go with their history, in every tenant; a real fact and a
    leftover's key in another namespace stay; the append-only guard is back on after; a
    later boot changes nothing."""
    url = estate_db_shaped(pg)
    with TestClient(load_app(url).app) as client:
        a, b = Tenant(url, "A"), Tenant(url, "B")
        for tenant in (a, b):
            assert (
                put(
                    client, tenant, "estate", "gate-smoke", "gate smoke probe"
                ).status_code
                == 200
            )
            assert (
                put(
                    client, tenant, "estate", "gate-smoke", "gate smoke again"
                ).status_code
                == 200
            )
            assert (
                put(
                    client, tenant, "founder", "estate.test.bddb939df044952", "v"
                ).status_code
                == 200
            )
        assert put(client, a, "estate", "fact.greenlane.x", "real").status_code == 200
        assert (
            put(client, a, "other", "gate-smoke", "not a leftover").status_code == 200
        )

    def rows(tenant):
        with psycopg.connect(url, autocommit=True) as c:
            c.execute(
                "SELECT set_config('app.tenant_id', %s, false)", (str(tenant.id),)
            )
            return (
                c.execute(
                    "SELECT namespace, key FROM memories ORDER BY 1, 2"
                ).fetchall(),
                c.execute(
                    "SELECT DISTINCT namespace, key FROM memory_versions ORDER BY 1, 2"
                ).fetchall(),
            )

    kept = [("estate", "fact.greenlane.x"), ("other", "gate-smoke")]
    for _ in range(2):  # the boot that deletes, then one that must be a no-op
        with TestClient(load_app(url).app):
            pass
        assert rows(a) == (kept, kept)
        assert rows(b) == ([], [])

    with psycopg.connect(url) as c:
        # A's tenant set, so the delete reaches rows and the row trigger has one to refuse.
        c.execute("SELECT set_config('app.tenant_id', %s, false)", (str(a.id),))
        with pytest.raises(
            psycopg.errors.CheckViolation, match="HISTORY_IS_APPEND_ONLY"
        ):
            c.execute("DELETE FROM memory_versions")


# --- the production shape: estate-db, a mounted secret, the vault's token, the limit -------


def test_boots_twice_on_estate_db_from_a_mounted_secret_with_the_vault_token(
    pg, tmp_path
):
    url = estate_db_shaped(pg)
    token = secrets.token_urlsafe(32)
    (tmp_path / "url").write_text(url + "\n")
    (tmp_path / "token").write_text(token + "\n")
    env = {
        "DATABASE_URL_FILE": str(tmp_path / "url"),
        "MEMORY_SURFACE_TOKEN_FILE": str(tmp_path / "token"),
    }
    auth = {"Authorization": f"Bearer {token}"}
    body = {"namespace": "estate", "key": "k", "content": "v"}
    with TestClient(load_app(None, **env).app) as client:
        assert (
            client.put("/memories/estate/k", json=body, headers=auth).status_code == 200
        )
    second = load_app(None, **env)  # the second pod, the next deploy
    with TestClient(second.app) as client:
        assert client.get("/memories/estate/k", headers=auth).json()["content"] == "v"
        whoami = client.portal.call(_current_user, second.pool)
        assert whoami == "memory_app"
    with psycopg.connect(url) as c:
        rows = c.execute(
            "SELECT t.name, s.surface_name FROM surface_tokens s JOIN tenants t USING (tenant_id)"
        ).fetchall()
    assert rows == [("estate", "estate-agents")]  # registered once, not once per boot


async def _current_user(pool):
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT current_user")
        return (await cur.fetchone())["current_user"]


def test_thirty_requests_a_minute_per_token_and_a_refused_token_is_counted(booted):
    client, url = booted
    a = Tenant(url, "A")
    headers = a.headers()
    window = client.module.time.time() // 60
    codes = [client.get("/memories/u", headers=headers).status_code for _ in range(31)]
    if client.module.time.time() // 60 != window:
        pytest.skip("the minute rolled over mid-test; the count restarted")
    assert codes[:30] == [200] * 30 and codes[30] == 429

    bad = {"Authorization": "Bearer not-a-token"}
    assert [client.get("/memories/u", headers=bad).status_code for _ in range(3)] == [
        403
    ] * 3
    token_hash = hashlib.sha256(b"not-a-token").hexdigest()
    with psycopg.connect(url) as c:
        counted = c.execute(
            "SELECT sum(request_count) FROM rate_limits WHERE surface_id = %s",
            (token_hash,),
        ).fetchone()[0]
    assert counted == 3


# --- the vector is written by the server, or recall finds nothing ------------------------------
# Measured 2026-10-02: 47 facts and 0 vectors in the store, and every probe still said healthy,
# because the search ranks by `embedding <=> query` and no code anywhere wrote that column.
# These run the real app and a real HTTP listener standing in for the estate router's `embed`
# lane -- the server's own call is the thing under test, not a patched function.


@contextmanager
def fake_router(width):
    """An OpenAI-shaped /v1/embeddings listener answering `width` floats, and counting calls."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("content-length", 0))
            seen.append(
                {
                    "path": self.path,
                    "auth": self.headers.get("authorization"),
                    "body": json.loads(self.rfile.read(n)),
                }
            )
            out = json.dumps(
                {"data": [{"embedding": [0.01 * ((i % 7) + 1) for i in range(width)]}]}
            ).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", seen
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def booted_with_embed(database_url, url, **extra):
    env = {
        "MEMORY_EMBED_URL": url,
        "MEMORY_EMBED_MODEL": "embed",
        "MEMORY_EMBED_API_KEY": "router-key",
        "MEMORY_EMBED_TIMEOUT_S": "3",
        **extra,
    }
    try:
        module = load_app(database_url, **env)
        with TestClient(module.app) as client:
            yield client
    finally:
        for name in env:
            os.environ.pop(name, None)


def embedding_status(client, tenant):
    return client.get("/embeddings/status", headers=tenant.headers()).json()


def test_a_written_fact_gets_its_vector_from_the_embed_lane(database_url):
    with fake_router(1536) as (url, seen), booted_with_embed(database_url, url) as c:
        a = Tenant(database_url, "A")
        r = put(c, a, "estate", "k1", "the router key lives in the vault")
        assert r.status_code == 200
        assert r.json()["search_by_meaning"] is True
        assert seen[0]["path"] == "/v1/embeddings"
        assert seen[0]["auth"] == "Bearer router-key"
        assert seen[0]["body"] == {
            "model": "embed",
            "input": "the router key lives in the vault",
        }
        status = embedding_status(c, a)
        assert (status["facts"], status["vectorised"], status["unvectorised"]) == (
            1,
            1,
            0,
        )


def test_a_vector_of_the_wrong_width_is_refused_not_stored(database_url):
    # A hop of another width writes a vector the store cannot compare to anything it holds,
    # and does it silently. The fact is still kept; the gap is a number, not a surprise.
    with fake_router(1024) as (url, _), booted_with_embed(database_url, url) as c:
        a = Tenant(database_url, "A")
        r = put(c, a, "estate", "k1", "fact written through a lane of the wrong width")
        assert r.status_code == 200
        assert r.json()["search_by_meaning"] is False
        assert embedding_status(c, a)["unvectorised"] == 1


def test_a_down_router_never_fails_the_write_and_the_gap_is_counted(database_url):
    # Nothing listens on port 9: the connection is refused. The agent's write must still land.
    with booted_with_embed(database_url, "http://127.0.0.1:9/v1") as c:
        a = Tenant(database_url, "A")
        r = put(c, a, "estate", "k1", "written while the embed lane was down")
        assert r.status_code == 200
        assert r.json()["search_by_meaning"] is False
        status = embedding_status(c, a)
        assert (status["facts"], status["unvectorised"]) == (1, 1)
        assert status["embed_lane_configured"] is True


def test_an_update_re_embeds_the_new_content(database_url):
    with fake_router(1536) as (url, seen), booted_with_embed(database_url, url) as c:
        a = Tenant(database_url, "A")
        put(c, a, "estate", "k1", "first wording")
        put(c, a, "estate", "k1", "second wording")
        assert [s["body"]["input"] for s in seen] == ["first wording", "second wording"]
        assert embedding_status(c, a)["vectorised"] == 1


def test_a_non_http_embed_url_is_never_opened(database_url, tmp_path):
    # file:// through urlopen would be a filesystem read dressed as a model call.
    secret = tmp_path / "x.json"
    secret.write_text(json.dumps({"data": [{"embedding": [0.1] * 1536}]}))
    with booted_with_embed(database_url, secret.as_uri()) as c:
        a = Tenant(database_url, "A")
        r = put(c, a, "estate", "k1", "a fact")
        assert r.status_code == 200
        assert r.json()["search_by_meaning"] is False


# --- recall by meaning, and the backfill that makes old facts reachable -------------------------
# The lane here is a concept model, not a constant: each concept a text mentions lights one axis,
# so two texts that share no words but share a concept are near, and two unrelated ones are
# orthogonal. That is the property the real lane has and a constant-vector stub cannot show.

CONCEPTS = {
    "secret": ("password", "credential", "token", "vault", "secret"),
    "storage": ("database", "postgres", "disk", "volume"),
    "voice": ("kokoro", "speech", "tts", "voice"),
}


def concept_vector(text, width=1536):
    low = text.lower()
    vec = [0.0] * width
    for axis, words in enumerate(CONCEPTS.values()):
        if any(w in low for w in words):
            vec[axis] = 1.0
    if not any(vec):
        vec[width - 1] = 1.0
    return vec


@contextmanager
def concept_router():
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("content-length", 0))
            text = json.loads(self.rfile.read(n))["input"]
            seen.append(text)
            out = json.dumps({"data": [{"embedding": concept_vector(text)}]}).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", seen
    finally:
        server.shutdown()
        server.server_close()


def recall(client, tenant, query, ns="estate", limit=5):
    return client.post(
        "/memories/recall",
        json={"query": query, "namespace": ns, "limit": limit},
        headers=tenant.headers(),
    )


def test_recall_finds_a_fact_by_meaning_when_no_word_is_shared(database_url):
    with concept_router() as (url, _), booted_with_embed(database_url, url) as c:
        a = Tenant(database_url, "A")
        put(c, a, "estate", "k1", "the postgres volume filled its disk overnight")
        put(c, a, "estate", "k2", "kokoro speech is rendered on the gpu node")
        r = recall(c, a, "where is the database stored")
        assert r.status_code == 200
        keys = [m["key"] for m in r.json()["results"]]
        # "database"/"stored" never appear in k1's text; "postgres volume disk" is the same
        # concept. k2 is an unrelated concept and must not come back.
        assert keys == ["k1"]
        assert r.json()["results"][0]["provenance"] == {}


def test_recall_does_not_cross_namespaces_or_tenants(database_url):
    with concept_router() as (url, _), booted_with_embed(database_url, url) as c:
        a, b = Tenant(database_url, "A"), Tenant(database_url, "B")
        put(c, a, "estate", "k1", "the vault holds the credential")
        put(c, a, "other", "k2", "the vault holds another credential")
        assert [m["key"] for m in recall(c, a, "secret").json()["results"]] == ["k1"]
        assert recall(c, b, "secret").json()["results"] == []


def test_recall_with_the_lane_down_says_so_instead_of_returning_nothing(database_url):
    with booted_with_embed(database_url, "http://127.0.0.1:9/v1") as c:
        a = Tenant(database_url, "A")
        put(c, a, "estate", "k1", "the vault holds the credential")
        r = recall(c, a, "credential")
        assert r.status_code == 503
        assert "embed lane" in r.json()["detail"]


def test_backfill_makes_unvectorised_facts_searchable_without_touching_history(
    database_url,
):
    # written while the lane was down: stored, but with no vector
    with booted_with_embed(database_url, "http://127.0.0.1:9/v1") as down:
        a = Tenant(database_url, "A")
        put(down, a, "estate", "k1", "the postgres volume filled its disk overnight")
        put(down, a, "estate", "k2", "the vault holds the credential")
        assert embedding_status(down, a)["unvectorised"] == 2

    def history_and_versions():
        with psycopg.connect(database_url) as conn:
            return (
                conn.execute("SELECT count(*) FROM memory_versions").fetchone()[0],
                conn.execute(
                    "SELECT key, version FROM memories ORDER BY key"
                ).fetchall(),
            )

    before = history_and_versions()
    with concept_router() as (url, _), booted_with_embed(database_url, url) as c:
        assert recall(c, a, "database").json()["results"] == []  # nothing to find yet
        r = c.post("/embeddings/backfill", headers=a.headers())
        assert r.status_code == 200
        assert r.json() == {"embedded": 2, "failed": 0, "remaining": 0}
        assert [m["key"] for m in recall(c, a, "database").json()["results"]] == ["k1"]
        assert embedding_status(c, a)["unvectorised"] == 0
        # a second pass has nothing to do and says so
        assert c.post("/embeddings/backfill", headers=a.headers()).json() == {
            "embedded": 0,
            "failed": 0,
            "remaining": 0,
        }
    # a vector is not a new version of the fact: no bump, no history row
    assert history_and_versions() == before


def test_backfill_only_touches_the_callers_own_tenant(database_url):
    with booted_with_embed(database_url, "http://127.0.0.1:9/v1") as down:
        a, b = Tenant(database_url, "A"), Tenant(database_url, "B")
        put(down, a, "estate", "k1", "tenant a credential")
        put(down, b, "estate", "k1", "tenant b credential")
    with concept_router() as (url, seen), booted_with_embed(database_url, url) as c:
        assert (
            c.post("/embeddings/backfill", headers=a.headers()).json()["embedded"] == 1
        )
        assert seen == ["tenant a credential"]
        assert embedding_status(c, a)["unvectorised"] == 0
        assert embedding_status(c, b)["unvectorised"] == 1


def test_backfill_with_the_lane_down_counts_failures_and_changes_nothing(database_url):
    with booted_with_embed(database_url, "http://127.0.0.1:9/v1") as c:
        a = Tenant(database_url, "A")
        put(c, a, "estate", "k1", "stored without a vector")
        r = c.post("/embeddings/backfill", headers=a.headers())
        assert r.status_code == 200
        assert r.json() == {"embedded": 0, "failed": 1, "remaining": 1}


def test_backfill_with_no_lane_configured_is_refused_not_silent(database_url):
    with TestClient(load_app(database_url).app) as c:
        a = Tenant(database_url, "A")
        r = c.post("/embeddings/backfill", headers=a.headers())
        assert r.status_code == 503
        assert "not configured" in r.json()["detail"]
