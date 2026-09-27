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
import os
import random
import secrets
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
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
    server = pgserver.get_server(tempfile.mkdtemp(prefix="umem-pg-"), cleanup_mode="delete")
    yield server
    server.cleanup()


@pytest.fixture()
def database_url(pg):
    # A fresh database per test: no test can pass on another test's rows.
    name = "umem_" + uuid.uuid4().hex[:12]
    with psycopg.connect(pg.get_uri(), autocommit=True) as c:
        c.execute(f"CREATE DATABASE {name}")
    return make_conninfo(pg.get_uri(), dbname=name)


def load_app(database_url):
    """A fresh module instance per call: its own `pool` global, like a separate pod."""
    os.environ["DATABASE_URL"] = database_url
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))
    spec = importlib.util.spec_from_file_location(
        "unified_memory_main_" + uuid.uuid4().hex[:8], SERVER_DIR / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tenant:
    """A tenant with surface tokens. A fresh token every 100 requests keeps a long test
    under the server's 120-per-minute limit without touching the limiter itself."""

    def __init__(self, database_url, name):
        self.database_url = database_url
        with psycopg.connect(database_url, autocommit=True) as c:
            self.id = c.execute(
                "INSERT INTO tenants(name) VALUES (%s) RETURNING tenant_id", (name,)
            ).fetchone()[0]
        self.uses = 0
        self.token = None

    def headers(self):
        if self.token is None or self.uses >= 100:
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

    assert client.get("/memories/user_42/secret", headers=b.headers()).status_code == 404
    assert client.get("/memories/user_42", headers=b.headers()).json()["facts"] == []
    history = client.get("/memories/user_42/secret/history", headers=b.headers())
    assert history.json()["versions"] == []
    assert client.get("/digest/user_42", headers=b.headers()).json()["facts"] == 0

    # B writing the same key makes B's own row; A's value is untouched.
    assert put(client, b, "user_42", "secret", "B-private").json()["status"] == "CREATED"
    assert client.get("/memories/user_42/secret", headers=a.headers()).json()["content"] == (
        "A-private"
    )


def test_requests_run_as_the_app_role_not_the_superuser(booted):
    client, url = booted
    with psycopg.connect(url) as c:
        assert c.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()[
            0
        ], "the test must connect as a superuser, as the manifest does"
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
    assert client.get("/memories/user_42/drink", headers=a.headers()).json()["content"] == "water"


# --- bi-temporal reads ---------------------------------------------------------------------


def test_as_of_returns_the_value_that_was_true_then(booted):
    client, url = booted
    a = Tenant(url, "A")
    t0 = datetime.now(timezone.utc) - timedelta(days=3)
    for i, value in enumerate(("tea", "coffee", "water")):
        r = put(client, a, "user_42", "drink", value, valid_from=iso(t0 + timedelta(days=i)))
        assert r.status_code == 200, r.text

    def at(t):
        r = client.get("/memories/user_42/drink", params={"as_of": iso(t)}, headers=a.headers())
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
    assert put(client, a, "u", "city", "Leeds", valid_from=iso(t_late)).status_code == 200
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
    first = put(client, a, "u", "role", "lead", valid_from=iso(now - timedelta(hours=1)))
    late = put(client, a, "u", "role", "junior", valid_from=iso(now - timedelta(days=30)))
    assert late.status_code == 200
    assert late.json() == {"status": "RECORDED_AS_PAST", "id": first.json()["id"], "version": 1}
    assert client.get("/memories/u/role", headers=a.headers()).json()["content"] == "lead"
    facts = client.get("/memories/u", headers=a.headers()).json()["facts"]
    assert [(f["key"], f["content"], f["version"]) for f in facts] == [("role", "lead", 1)]
    history = client.get("/memories/u/role/history", headers=a.headers()).json()["versions"]
    assert [v["content"] for v in history] == ["junior", "lead"]


def test_valid_from_is_refused_far_in_the_future_or_without_a_timezone(booted):
    client, url = booted
    a = Tenant(url, "A")
    now = datetime.now(timezone.utc)
    r = put(client, a, "u", "k", "v", valid_from=iso(now + timedelta(hours=1)))
    assert r.status_code == 422 and r.json()["detail"]["error"] == "VALID_FROM_IN_FUTURE"
    assert put(client, a, "u", "k", "v", valid_from="2026-01-01T00:00:00").status_code == 422
    # Inside the 60 s skew allowance is accepted.
    assert put(client, a, "u", "k", "v", valid_from=iso(now + timedelta(seconds=30))).status_code == (
        200
    )


def test_human_confirmed_memory_is_protected_on_the_late_write_path_too(booted):
    client, url = booted
    a = Tenant(url, "A")
    assert put(client, a, "u", "name", "Chidi", trust_tier="human_confirmed").status_code == 200
    past = iso(datetime.now(timezone.utc) - timedelta(days=5))
    r = put(client, a, "u", "name", "someone else", trust_tier="llm_derived", valid_from=past)
    assert r.status_code == 403
    history = client.get("/memories/u/name/history", headers=a.headers()).json()["versions"]
    assert [v["content"] for v in history] == ["Chidi"]


@pytest.mark.parametrize("statement", ["UPDATE memory_versions SET content = 'x'",
                                       "DELETE FROM memory_versions"])
def test_history_is_append_only_even_for_the_superuser(booted, statement):
    client, url = booted
    a = Tenant(url, "A")
    assert put(client, a, "u", "k", "v").status_code == 200
    with psycopg.connect(url) as c:
        with pytest.raises(psycopg.errors.CheckViolation, match="HISTORY_IS_APPEND_ONLY"):
            c.execute(statement)


# --- the digest ----------------------------------------------------------------------------


def reference_digest(facts):
    """Independent of the SQL: sha256 over length-prefixed key + sha256(content), byte order."""
    lines = sorted(
        f"{len(k)}:{k}{hashlib.sha256(v.encode()).hexdigest()}" for k, v in facts.items()
    )
    lines.sort(key=lambda s: s.encode())
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def test_digest_depends_on_the_facts_not_the_order_they_were_written(booted):
    client, url = booted
    rng = random.Random(20260927)
    facts = {f"k{i:02d}{rng.choice('aBz_é')}": f"value {rng.random()}" for i in range(25)}
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
    assert client.get("/digest/subject", headers=tenants[0].headers()).json()["digest"] != (
        digests[0]
    )


# --- randomised comparison against a reference model ---------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_randomised_writes_match_the_reference_model(booted, seed):
    """Random writes with colliding and out-of-order valid_from values, then every
    (as_of, known_at) pair is compared with a model written without the server's SQL:
    the answer is the write with the greatest (valid_from, write order) among writes
    made by known_at whose valid_from is at or before as_of."""
    client, url = booted
    rng = random.Random(seed)
    a = Tenant(url, "A")
    base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    slots = [base + timedelta(minutes=m) for m in range(6)]  # few slots: ties are common

    writes, checkpoints = [], []  # writes: (valid_from, seq, content)
    for seq in range(14):
        vf = rng.choice(slots)
        content = f"s{seed}-w{seq}"
        r = put(client, a, "subj", "pred", content, valid_from=iso(vf))
        assert r.status_code == 200, r.text
        current_before = max(writes)[0] if writes else None
        expected_status = (
            "RECORDED_AS_PAST" if current_before is not None and vf < current_before
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
    history = client.get("/memories/subj/pred/history", headers=a.headers()).json()["versions"]
    assert len(history) == len(writes)


def test_the_table_owner_is_held_to_tenant_isolation_too(pg):
    """FORCE ROW LEVEL SECURITY, measured on its own: a non-superuser that owns the tables
    (the role that ran schema.sql) reads with no SET ROLE, and still sees only its tenant."""
    name = "umem_" + uuid.uuid4().hex[:12]
    owner = "owner_" + uuid.uuid4().hex[:8]
    with psycopg.connect(pg.get_uri(), autocommit=True) as c:
        c.execute(f"CREATE ROLE {owner} LOGIN PASSWORD 'x'")
        c.execute(f"CREATE DATABASE {name} OWNER {owner}")
        # A non-superuser cannot create memory_app itself, so an administrator does, once.
        c.execute(
            "DO $$ BEGIN CREATE ROLE memory_app NOLOGIN NOSUPERUSER NOBYPASSRLS;"
            " EXCEPTION WHEN duplicate_object THEN NULL; END $$"
        )
        c.execute(f"GRANT memory_app TO {owner} WITH ADMIN OPTION")
    with psycopg.connect(make_conninfo(pg.get_uri(), dbname=name), autocommit=True) as c:
        c.execute("CREATE EXTENSION vector")
    url = make_conninfo(pg.get_uri(), dbname=name, user=owner, password="x")
    with TestClient(load_app(url).app) as client:
        a = Tenant(url, "A")
        Tenant(url, "B")
        assert put(client, a, "u", "secret", "A-private").status_code == 200
    with psycopg.connect(url, autocommit=True) as c:
        b_id = c.execute("SELECT tenant_id FROM tenants WHERE name = 'B'").fetchone()[0]
        c.execute("SELECT set_config('app.tenant_id', %s, false)", (str(b_id),))
        assert c.execute("SELECT content FROM memories").fetchall() == []
        assert c.execute("SELECT content FROM memory_versions").fetchall() == []
