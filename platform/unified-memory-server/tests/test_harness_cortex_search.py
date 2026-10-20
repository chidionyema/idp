"""PostgresCortexAdapter searches by the query, in the caller's namespace (2026-10-19).

It used to ignore `query_text`, order by a NULL distance and filter on a `status` column
`memories` does not have: the brief every recall carries was 25 arbitrary rows, or an error.
"""

from __future__ import annotations

from datetime import datetime, timezone

from harness import ActiveMemoryEngine, HarnessTelemetry, PostgresCortexAdapter

T0 = datetime(2026, 10, 19, tzinfo=timezone.utc)


def row(key, content, cosine=None, **prov):
    r = {
        "id": key,
        "tenant_id": "t",
        "namespace": "estate",
        "key": key,
        "content": content,
        "trust_tier": "verified",
        "provenance": prov,
        "valid_from": T0,
        "updated_at": T0,
        "version": 1,
    }
    if cosine is not None:
        r["cosine_sim"] = cosine
    return r


class Conn:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def cursor(self):
        conn = self

        class Cur:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, sql, params):
                conn.calls.append((sql, params))

            def fetchall(self):
                return conn.rows

        return Cur()


def test_the_query_vector_orders_the_search_and_the_floor_drops_the_far():
    conn = Conn([row("near", "dns01", 0.8, subject="meridian"), row("far", "x", 0.05)])
    adapter = PostgresCortexAdapter(
        conn, embed=lambda t: [0.1, 0.2], namespace="estate", min_cosine=0.2
    )
    facts = adapter.search_associative_facts("t", "edge acme dns01", limit=10)
    sql, params = conn.calls[0]
    assert "embedding <=> %s::vector" in sql and "status" not in sql
    assert params == ("[0.1,0.2]", "t", "estate", "[0.1,0.2]", 10)
    assert [(f.subject, f.project_id, f.confidence) for f in facts] == [
        ("near", "meridian", 0.8)
    ]


def test_with_no_vector_the_search_matches_the_query_words_never_any_row():
    conn = Conn([row("k", "acme dns01 for meridian")])
    adapter = PostgresCortexAdapter(conn, embed=lambda t: None, namespace="estate")
    facts = adapter.search_associative_facts("t", "Edge ACME dns01")
    sql, params = conn.calls[0]
    assert "ILIKE ANY" in sql
    assert params[2] == ["%edge%", "%acme%", "%dns01%"]
    assert len(facts) == 1
    assert (
        PostgresCortexAdapter(Conn([]), namespace="estate").search_associative_facts(
            "t", "a b"
        )
        == []
    )  # nothing to match on: no query is sent at all


def test_preferences_are_global_and_other_facts_belong_to_their_subject():
    adapter = PostgresCortexAdapter(Conn([]))
    pref, fact = adapter._rows_to_facts(
        [
            row("p", "x", kind="preference", subject="anything"),
            row("f", "y", subject="meridian"),
        ]
    )
    assert (pref.scope, pref.project_id) == ("global_preference", None)
    assert (fact.scope, fact.project_id) == ("project_fact", "meridian")


class Scratch:
    def get_working_scratchpad(self, conn, tenant_id, run_id):
        return {}


def brief_for(project_id):
    rows = [
        row("a", "about meridian", 0.9, subject="meridian"),
        row("b", "about other", 0.9, subject="other"),
    ]
    adapter = PostgresCortexAdapter(
        Conn(rows), embed=lambda t: [1.0], namespace="estate"
    )
    engine = ActiveMemoryEngine(adapter, Scratch(), HarnessTelemetry())
    brief, _ = engine.build_active_context_brief(None, "t", project_id, "r", "q")
    return brief


def test_a_run_with_a_project_sees_its_facts_and_a_run_without_one_sees_all():
    assert "about meridian" in brief_for("meridian") and "about other" not in brief_for(
        "meridian"
    )
    unscoped = brief_for(None)
    assert "about meridian" in unscoped and "about other" in unscoped
