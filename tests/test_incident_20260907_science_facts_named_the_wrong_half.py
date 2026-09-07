"""2026-09-07: the estate was blind for a day and its own instrument pointed at the wrong thing.

`FAIL science-facts ... sources=0 rows=0 (no row carried attribute science.source: the science
writer never reached the collector)` had been standing hourly since 19:07Z. The sentence was a
guess the query could not support, and it was false: signoz-otel-collector was answering 200 to
every writer, and ClickHouse behind it was refusing every insert with `code: 241 ... memory limit
exceeded ... maximum: 3.60 GiB` (collector and langfuse-worker logs, and `kubectl top pod` reading
3908Mi of the 4Gi cgroup). A reader who believed the sentence went hunting the writer.

The instrument now asks one more question when the count is zero -- how many log rows of any kind
landed in the same window -- and says which half that measurement rules out. These cases grade
that behaviour through the shipped code: the ConfigMap body is compiled and run against a stub
backend, so a change to the manifest that breaks the logic fails here.
"""

# ruff: noqa: S101, S102
#   S101: pytest cases assert.
#   S102: the point of these cases is to run the collect.py the CronJob actually mounts,
#   so the ConfigMap body is compiled here rather than copied into the test, where a copy
#   would drift from the manifest and grade nothing.

import pathlib
import types

import yaml

MANIFEST = (
    pathlib.Path(__file__).resolve().parents[1] / "platform/science/science-facts.yaml"
)


def collect_module():
    """Compile the collect.py the CronJob actually mounts, out of the ConfigMap in the manifest."""
    for doc in yaml.safe_load_all(MANIFEST.read_text()):
        if (
            doc
            and doc.get("kind") == "ConfigMap"
            and "collect.py" in (doc.get("data") or {})
        ):
            mod = types.ModuleType("science_collect")
            exec(
                compile(doc["data"]["collect.py"], str(MANIFEST), "exec"), mod.__dict__
            )
            return mod
    raise AssertionError("science-facts.yaml carries no ConfigMap with collect.py")


def stub(per_source, any_rows):
    """A ClickHouse that answers the grouped query, then the count-everything query."""

    def answer(sql):
        if "GROUP BY source" in sql:
            return [(s, str(n), "2026-09-07 19:00:00") for s, n in per_source.items()]
        return [(str(any_rows),)]

    return answer


def test_a_source_in_the_window_is_ok():
    head, body = collect_module().main(clickhouse=stub({"otto": 12}, 999))
    assert head.split()[0] == "ok"
    assert body["sources"]["otto"]["rows"] == 12
    # The second query is not asked when there is something to report.
    assert body["rows_any_kind"] is None


def test_zero_science_rows_while_other_rows_land_blames_the_science_lane():
    head, body = collect_module().main(clickhouse=stub({}, 4210))
    assert head.split()[0] == "FAIL"
    assert body["rows_any_kind"] == 4210
    assert "science lane alone is missing" in head


def test_zero_rows_of_any_kind_sends_the_reader_to_the_backend():
    """The 2026-09-07 shape: nothing at all was landing, and the writer was not the place to start."""
    head, body = collect_module().main(clickhouse=stub({}, 0))
    assert head.split()[0] == "FAIL"
    assert body["rows_any_kind"] == 0
    assert "collector's exporter errors" in head


def test_a_backend_that_answers_neither_question_is_not_a_verdict_about_the_writer():
    def refuse(sql):
        raise RuntimeError("connection refused")

    head, body = collect_module().main(clickhouse=refuse)
    assert head.split()[0] == "BLIND"
    assert body["rows_any_kind"] is None


def test_a_second_query_that_fails_alone_stays_a_fail_and_says_it_is_unmeasured():
    """The grouped query answered, so the backend is reachable; only the discriminator broke."""

    def half(sql):
        if "GROUP BY source" in sql:
            return []
        raise RuntimeError("read timed out")

    head, body = collect_module().main(clickhouse=half)
    assert head.split()[0] == "FAIL"
    assert body["rows_any_kind"] is None
    assert body["backend_errors"]["all_rows"]
    assert "unmeasured" in head
