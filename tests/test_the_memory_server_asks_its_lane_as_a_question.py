"""A recall query and the facts it searches are embedded by one model, from two directions.

The `embed` lane's model (nvidia llama-nemotron-embed-vl-1b-v2) is asymmetric: a passage and a
query are embedded differently, on purpose, and a search compares a query vector against
passage vectors. Until 2026-10-13 the memory server embedded its recall query through `embed`,
which pins input_type: passage, so recall compared passage with passage. Probed on the live
lane that day, the same query typed passage vs query flipped the ranking of the stored facts.

The two lanes are only comparable while they are the same model at the same width, so this reads
both off the rendered router config through the names the memory server's Deployment actually
holds: change one lane's model or width and not the other's, and this fails before recall
silently compares vectors from two spaces.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTER = ROOT / "platform" / "llm" / "config.yaml"
DEPLOY = ROOT / "platform" / "unified-memory-server" / "oke-unified-memory.yaml"


def _env():
    for doc in yaml.safe_load_all(DEPLOY.read_text()):
        if doc and doc.get("kind") == "Deployment":
            return {
                e["name"]: e.get("value")
                for c in doc["spec"]["template"]["spec"]["containers"]
                for e in c.get("env") or []
            }
    raise AssertionError("no Deployment in the memory server's manifest")


def _lane(name):
    rows = [
        r
        for r in yaml.safe_load(ROUTER.read_text())["model_list"]
        if r["model_name"] == name
    ]
    assert len(rows) == 1, f"router lane {name!r} is served by {len(rows)} rows, not 1"
    return rows[0]["litellm_params"]


def test_facts_are_embedded_as_passages_and_queries_as_questions():
    env = _env()
    assert _lane(env["MEMORY_EMBED_MODEL"])["input_type"] == "passage"
    assert _lane(env["MEMORY_EMBED_QUERY_MODEL"])["input_type"] == "query"


def test_both_directions_are_one_model_at_the_columns_width():
    env = _env()
    fact, query = (
        _lane(env["MEMORY_EMBED_MODEL"]),
        _lane(env["MEMORY_EMBED_QUERY_MODEL"]),
    )
    assert fact["model"] == query["model"]
    assert fact["dimensions"] == query["dimensions"] == int(env["MEMORY_EMBED_DIM"])
