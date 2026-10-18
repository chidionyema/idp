"""fleetview_backend.memory: what /fleet shows of the router's capture and the graph drain."""

from fleetview_backend import memory, routes


def _estate(tmp_path, monkeypatch):
    spool = tmp_path / "spool"
    spool.mkdir()
    (spool / "s1.md").write_text(
        "\n## t1 m agent=estate-agent\n\n**asked:** a\n\n## t2 m agent=otto\n\n**asked:** b\n"
    )
    (spool / "s2.md").write_text("\n## t3 m\n\n**answered:** c\n")
    g = tmp_path / "graph" / ".growmos"
    g.mkdir(parents=True)
    (g / "entities.jsonl").write_text('{"name":"a"}\n{"name":"b"}\n{"name":"c"}\n')
    (g / "relations.jsonl").write_text('{"s":"a","o":"b"}\n')
    (tmp_path / "graph" / "sessions").mkdir()
    (tmp_path / "graph" / "sessions" / "x.md").write_text("x")
    log = tmp_path / "drain.log"
    log.write_text(
        "2026-09-28T22:00:00Z moved=0\n2026-09-28T22:10:00Z moved=2 entities=3 agents=estate-agent,otto\n"
    )
    monkeypatch.setenv("ESTATE_GRAPH_SPOOL", str(spool))
    monkeypatch.setenv("ESTATE_GRAPH_ROOT", str(tmp_path / "graph"))
    monkeypatch.setenv("ESTATE_GRAPH_DRAIN_LOG", str(log))


def test_the_envelope_counts_what_is_on_disk(tmp_path, monkeypatch):
    _estate(tmp_path, monkeypatch)
    body, status = routes.memory_envelope()
    assert status == 200
    assert body["spool"]["sessions_waiting"] == 2
    assert body["spool"]["exchanges_waiting"] == 3
    assert body["graph"]["entities"] == 3
    assert body["graph"]["relations"] == 1
    assert body["graph"]["sessions_ingested"] == 1
    assert body["drain"]["last_run"].endswith(
        "moved=2 entities=3 agents=estate-agent,otto"
    )


def test_per_agent_attribution_is_counted_not_guessed(tmp_path, monkeypatch):
    """Claim #6228: stamps count per agent; a header with no stamp is 'unattributed',
    because a router running pre-stamp code must be visible, never smoothed over."""
    _estate(tmp_path, monkeypatch)
    body, _ = routes.memory_envelope()
    assert body["spool"]["exchanges_by_agent"] == {
        "estate-agent": 1,
        "otto": 1,
        "unattributed": 1,
    }
    assert body["drain"]["agents"] == ["estate-agent", "otto"]


def test_an_unreadable_part_is_reported_not_zeroed(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_GRAPH_SPOOL", str(tmp_path / "absent"))
    monkeypatch.setenv("ESTATE_GRAPH_ROOT", str(tmp_path / "absent"))
    monkeypatch.setenv("ESTATE_GRAPH_DRAIN_LOG", str(tmp_path / "absent.log"))
    body = memory.memory_status()
    for part in ("spool", "graph", "drain"):
        assert body[part]["available"] is False
        assert body[part]["error"]
        assert "entities" not in body[part]
