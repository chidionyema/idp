"""platform/estate/memory/snapshot.py and bin/memory-snapshot: memory's second home (#7397)."""

import importlib.machinery
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "platform", "estate", "memory"))

import focus  # noqa: E402
import snapshot  # noqa: E402

NOW = 1_800_000_000.0


def _snap(facts=(), focus_rows=(), facts_at=NOW, focus_at=NOW):
    return {
        "version": 1,
        "namespace": "estate",
        "source": "test",
        "facts_at": facts_at,
        "facts": list(facts),
        "focus_at": focus_at,
        "focus": list(focus_rows),
    }


def _fact(key, text, kind="fact", at="2026-10-27T10:00:00+00:00"):
    return {
        "key": key,
        "content": text,
        "provenance": {"kind": kind},
        "recorded_at": at,
    }


# --- R2 is reached with a correct signature ----------------------------------------------------


def test_the_signer_matches_the_published_sigv4_example():
    # AWS S3 docs, "Example: GET Object": the known answer for this exact request.
    auth = snapshot.sign(
        "GET",
        "examplebucket.s3.amazonaws.com",
        "/test.txt",
        {"Range": "bytes=0-9"},
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "AKIAIOSFODNN7EXAMPLE",
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "us-east-1",
        "20130524T000000Z",
    )
    assert auth == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    )


def test_r2_is_configured_by_name_or_not_at_all():
    env = {
        "R2_ACCOUNT_ID": "acct",
        "R2_ACCESS_KEY_ID": "ak",
        "R2_SECRET_ACCESS_KEY": "sk",
        "R2_BUCKET": "b",
    }
    cfg = snapshot.r2_config(env)
    assert cfg["host"] == "acct.r2.cloudflarestorage.com" and cfg["region"] == "auto"
    assert snapshot.r2_config({**env, "R2_BUCKET": ""}) is None


# --- the local copy: bounded, atomic, never below the disk floor -------------------------------


def test_the_local_copy_is_never_written_below_the_disk_floor(tmp_path):
    path = str(tmp_path / "snapshot.json")
    assert snapshot.write_local(_snap([_fact("a", "old")]), path, floor_mb=0) == ""
    why = snapshot.write_local(_snap([_fact("b", "new")]), path, floor_mb=10**9)
    assert why.startswith("disk floor:")
    assert [f["key"] for f in snapshot.read_local(path)["facts"]] == ["a"]


def test_a_failed_write_leaves_the_old_copy_and_no_litter(tmp_path, monkeypatch):
    path = str(tmp_path / "snapshot.json")
    snapshot.write_local(_snap([_fact("a", "old")]), path, floor_mb=0)

    def full(*_a):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(snapshot.os, "replace", full)
    assert "No space left" in snapshot.write_local(
        _snap([_fact("b", "new")]), path, floor_mb=0
    )
    assert [f["key"] for f in snapshot.read_local(path)["facts"]] == ["a"]
    assert os.listdir(tmp_path) == ["snapshot.json"]


def test_the_document_is_bounded_and_keeps_the_newest_facts():
    facts = [
        _fact(
            f"k{i}", "x" * 200, at=f"2026-10-{10 + i % 18:02d}T00:00:{i % 60:02d}+00:00"
        )
        for i in range(400)
    ]
    body = snapshot.encode(_snap(facts), max_bytes=20_000)
    kept = json.loads(body)["facts"]
    assert len(body) <= 20_000 and 0 < len(kept) < 400
    newest = max(f["recorded_at"] for f in facts)
    assert newest in {f["recorded_at"] for f in kept}


def test_a_corrupt_or_foreign_file_is_no_snapshot(tmp_path):
    p = tmp_path / "snapshot.json"
    p.write_text("{not json")
    assert snapshot.read_local(str(p)) is None
    p.write_text(json.dumps({"version": 99, "facts": [], "focus": []}))
    assert snapshot.read_local(str(p)) is None


# --- reading: local when young, R2 when old, old local when R2 is down --------------------------


def test_a_young_local_copy_is_used_without_asking_r2(tmp_path):
    path = str(tmp_path / "s.json")
    snapshot.write_local(_snap(facts_at=NOW - 60), path, floor_mb=0)

    def never(_cfg):
        raise AssertionError("R2 asked for a young copy")

    assert (
        snapshot.load(path, cfg={"x": 1}, now=NOW, getter=never)["facts_at"] == NOW - 60
    )


def test_an_old_local_copy_is_replaced_by_a_newer_r2_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "DISK_FLOOR_MB", 0)
    path = str(tmp_path / "s.json")
    snapshot.write_local(
        _snap(facts_at=NOW - 7200, focus_at=NOW - 7200), path, floor_mb=0
    )
    remote = snapshot.encode(_snap([_fact("r", "from r2")], facts_at=NOW - 300))
    got = snapshot.load(path, cfg={"x": 1}, now=NOW, getter=lambda _c: remote)
    assert [f["key"] for f in got["facts"]] == ["r"]
    assert snapshot.read_local(path)["facts_at"] == NOW - 300  # kept for the next read


def test_r2_down_still_answers_with_the_old_local_copy(tmp_path):
    path = str(tmp_path / "s.json")
    snapshot.write_local(
        _snap([_fact("a", "old")], facts_at=NOW - 7200), path, floor_mb=0
    )

    def down(_cfg):
        raise OSError("r2 unreachable")

    assert [
        f["key"]
        for f in snapshot.load(path, cfg={"x": 1}, now=NOW, getter=down)["facts"]
    ] == ["a"]
    assert (
        snapshot.load(str(tmp_path / "none.json"), cfg={"x": 1}, now=NOW, getter=down)
        is None
    )


# --- answering from it ---------------------------------------------------------------------------


def test_a_brief_from_the_snapshot_has_the_servers_shape_and_says_what_it_is():
    snap = _snap(
        [
            _fact(
                "router.lanes",
                "the laptop router dropped 19 lanes",
                "incident",
                "2026-10-28T01:00:00+00:00",
            ),
            _fact(
                "memory.home",
                "unified memory ran only in the OKE cluster",
                "incident",
                "2026-10-28T02:00:00+00:00",
            ),
            _fact(
                "adr.34",
                "workloads are placed by the free tier",
                "decision",
                "2026-09-26T00:00:00+00:00",
            ),
            _fact("misc", "unrelated note", "fact"),
        ],
        facts_at=NOW - 3600,
    )
    b = snapshot.brief(
        snap, "why did unified memory go down with the cluster", limit=2, now=NOW
    )
    assert [f["key"] for f in b["relevant"]] == ["memory.home"]
    assert [f["key"] for f in b["recent"]] == ["router.lanes", "adr.34"]
    assert b["search_by_meaning"] is False
    assert b["snapshot"] == {"source": "test", "facts_age_s": 3600}


def test_the_snapshot_focus_is_aged_so_a_lapsed_claim_is_not_live():
    rows = [
        {
            "claim": "idp#1",
            "agent": "a",
            "paths": "x",
            "heartbeat_age_s": 60,
            "live": True,
        },
        {
            "claim": "idp#2",
            "agent": "b",
            "paths": "y",
            "heartbeat_age_s": 7000,
            "live": True,
        },
    ]
    got = snapshot.focus_rows(_snap(focus_rows=rows, focus_at=NOW - 600), now=NOW)
    assert [(r["claim"], r["live"], r["stale_s"]) for r in got] == [
        ("idp#1", True, 600),
        ("idp#2", False, 600),
    ]


# --- the writer ----------------------------------------------------------------------------------


def _writer():
    path = os.path.join(ROOT, "bin", "memory-snapshot")
    loader = importlib.machinery.SourceFileLoader("memory_snapshot", path)
    spec = importlib.util.spec_from_loader("memory_snapshot", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Bucket:
    def __init__(self, body=None, corrupt=False):
        self.body, self.corrupt, self.puts = body, corrupt, 0

    def get(self, _cfg, timeout=0):
        if self.body is None:
            raise OSError("404")
        return b"garbage" if self.corrupt else self.body

    def put(self, _cfg, body, timeout=0):
        self.puts += 1
        self.body = body


def test_the_writer_stores_facts_and_focus_and_proves_the_read_back(capsys):
    w = _writer()
    bucket = _Bucket()
    briefs = {
        t: {
            "relevant": [_fact(f"k.{t}", f"about {t}")],
            "recent": [_fact("d", "decided", "decision")],
        }
        for t in ("a", "b")
    }
    rc = w.write(
        cfg={"x": 1},
        topics=["a", "b"],
        brief_fn=lambda task: briefs[task],
        focus_fn=lambda: [{"claim": "idp#7397", "live": True, "heartbeat_age_s": 1}],
        get=bucket.get,
        put=bucket.put,
        now=NOW,
    )
    out = capsys.readouterr().out
    assert rc == 0, out
    snap = snapshot.decode(bucket.body)
    assert {f["key"] for f in snap["facts"]} == {"k.a", "k.b", "d"}
    assert snap["facts_at"] == NOW and snap["focus_at"] == NOW
    assert "read back sha256 equal" in out


def test_a_dead_door_keeps_the_old_facts_and_their_age_and_goes_red_when_too_old(
    capsys,
):
    w = _writer()
    old = snapshot.encode(
        _snap([_fact("kept", "from before")], facts_at=NOW - w.FACTS_STALE_S - 1)
    )
    bucket = _Bucket(old)

    def dead(_task):
        raise OSError("URLError EOF occurred in violation of protocol")

    rc = w.write(
        cfg={"x": 1},
        topics=["a"],
        brief_fn=dead,
        focus_fn=lambda: [{"claim": "idp#1", "live": True, "heartbeat_age_s": 1}],
        get=bucket.get,
        put=bucket.put,
        now=NOW,
    )
    out = capsys.readouterr().out
    snap = snapshot.decode(bucket.body)
    assert [f["key"] for f in snap["facts"]] == ["kept"]
    assert (
        snap["facts_at"] == NOW - w.FACTS_STALE_S - 1
    )  # old facts are never re-stamped new
    assert snap["focus_at"] == NOW  # the ledger was up: focus is fresh
    assert rc == 1 and "FAIL" in out and "door" in out


def test_a_read_back_that_differs_is_a_failed_run(capsys):
    w = _writer()
    bucket = _Bucket()
    real_put = bucket.put

    def put(cfg, body, timeout=0):
        real_put(cfg, body)
        bucket.corrupt = True

    rc = w.write(
        cfg={"x": 1},
        topics=["a"],
        brief_fn=lambda t: {"relevant": [_fact("k", "v")], "recent": []},
        focus_fn=lambda: [],
        get=bucket.get,
        put=put,
        now=NOW,
    )
    assert rc == 1 and "read back" in capsys.readouterr().out


def test_focus_rows_survive_the_write_unchanged():
    # the writer stores focus.register_from_issues rows; age_rows is what readers apply
    rows = [
        {
            "claim": "idp#3",
            "agent": "x",
            "paths": "p",
            "heartbeat_age_s": 5,
            "live": True,
        }
    ]
    assert focus.age_rows(rows, 0)[0]["live"] is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
