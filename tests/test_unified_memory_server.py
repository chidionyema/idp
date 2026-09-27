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


# --- recall: word search ranked by retrievability (Ebbinghaus) ---------------------------


def recall(client, tenant, query, **extra):
    r = client.post(
        "/memories/recall", json={"query": query, **extra}, headers=tenant.headers()
    )
    assert r.status_code == 200, r.text
    return r.json()["results"]


def age(database_url, ns, key, days):
    """Move a memory's write, and its last recall if any, `days` into the past."""
    with psycopg.connect(database_url, autocommit=True) as c:
        c.execute("ALTER TABLE memories DISABLE TRIGGER trg_bump_memory_version")
        c.execute(
            "UPDATE memories SET updated_at = updated_at - make_interval(days => %s) "
            "WHERE namespace = %s AND key = %s",
            (days, ns, key),
        )
        c.execute("ALTER TABLE memories ENABLE TRIGGER trg_bump_memory_version")
        c.execute(
            "UPDATE memory_strength SET last_recalled = last_recalled - make_interval(days => %s) "
            "WHERE memory_id = (SELECT id FROM memories WHERE namespace = %s AND key = %s)",
            (days, ns, key),
        )


def test_recall_finds_a_memory_by_its_words_in_any_namespace(booted):
    client, url = booted
    a = Tenant(url, "A")
    put(
        client,
        a,
        "estate",
        "memory.door",
        "the memory door is mcp.zone/memories via keda",
    )
    put(client, a, "voice", "lane", "voice runs on the groq lane")
    got = recall(client, a, "where is the memory door?")
    assert [r["key"] for r in got] == ["memory.door"]
    assert got[0]["namespace"] == "estate"
    assert 0 < got[0]["similarity"] < 1
    # One word the memory does not use does not hide it (OR, not AND).
    assert [r["key"] for r in recall(client, a, "groq zebra")] == ["lane"]
    assert recall(client, a, "the of and") == []  # stopwords only: nothing to search


def test_an_unused_memory_decays_below_a_fresh_one_that_says_the_same(booted):
    client, url = booted
    a = Tenant(url, "A")
    put(client, a, "estate", "old", "postgres runs on estate-db")
    put(client, a, "estate", "new", "postgres runs on estate-db")
    age(url, "estate", "old", 10)
    got = recall(client, a, "postgres estate-db", limit=2)
    assert [r["key"] for r in got] == ["new", "old"]
    new, old = got
    assert new["similarity"] == old["similarity"]
    # R = sim * e^(-10/1): ten idle days at strength one leave ~0.005% of it.
    assert old["retrievability"] < new["retrievability"] * 1e-3


def test_recall_is_rehearsal_strength_doubles_and_the_fact_is_not_rewritten(booted):
    client, url = booted
    a = Tenant(url, "A")
    put(client, a, "estate", "k", "calico is the pod network")
    for expected_strength, expected_recalls in ((1.0, 0), (2.0, 1), (4.0, 2)):
        (hit,) = recall(client, a, "calico network")
        assert hit["strength_days"] == expected_strength
        assert hit["recalls"] == expected_recalls
    # A read is not a new version of the fact: version and history are untouched.
    assert hit["version"] == 1
    hist = client.get("/memories/estate/k/history", headers=a.headers()).json()
    assert len(hist["versions"]) == 1


def test_a_rehearsed_memory_outlasts_an_idle_one(booted):
    client, url = booted
    a = Tenant(url, "A")
    put(client, a, "estate", "asked", "the router listens on four thousand")
    for _ in range(4):  # strength 1 -> 16 days; 'idle' does not exist yet
        recall(client, a, "router listens", namespace="estate", limit=1)
    put(client, a, "estate", "idle", "the router listens on four thousand")
    for key in ("asked", "idle"):
        age(url, "estate", key, 5)
    got = recall(client, a, "router listens", limit=2)
    assert [r["key"] for r in got] == ["asked", "idle"]
    asked, idle = got
    assert (asked["strength_days"], idle["strength_days"]) == (16.0, 1.0)
    # e^(-5/16) against e^(-5/1): the rehearsed one keeps ~73%, the idle one under 1%.
    assert idle["retrievability"] < asked["retrievability"] * 0.05


def test_recall_never_crosses_tenants(booted):
    client, url = booted
    a, b = Tenant(url, "A"), Tenant(url, "B")
    put(client, a, "estate", "secretish", "tenant a keeps the zebra fact")
    assert recall(client, b, "zebra") == []
    assert [r["key"] for r in recall(client, a, "zebra")] == ["secretish"]
