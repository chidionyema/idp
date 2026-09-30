"""fleetview_backend.harv: what /fleet shows of the harvester, parsed from the real `harv funnel`
output, and that an unreadable harvester is unavailable with its reason, never an empty funnel."""

import json
import stat

import pytest

from fleetview_backend import harv, routes

REAL = """harvest-1790508356:
  crates-indexed            100
  crates-license-ok         100
  crates-fetched            100
  crates-inventoried         97
  fns-public               6253
  fns-compiled             1891
  fns-zero-imports         1385
  shelved                  1352
  shelved-t1               1234
  shelved-t2                105
  shelved-t3                 13
shelf by tier: [("t1", 1244), ("t2", 118), ("t3", 15)]
evidence entries (ring4-ledger): 2957
"""


def _tool(tmp_path, body, rc=0):
    p = tmp_path / "harv"
    p.write_text(f"#!/bin/sh\ncat <<'EOF'\n{body}\nEOF\nexit {rc}\n")
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return p


def test_parse_real_funnel():
    d = harv.parse_funnel(REAL)
    assert d["run_at"] == 1790508356
    assert d["stages"][0] == {"stage": "crates-indexed", "n": 100}
    assert {"stage": "fns-public", "n": 6253} in d["stages"]
    assert d["shelf"] == {"t1": 1244, "t2": 118, "t3": 15}
    assert d["shelved"] == 1377 and d["evidence"] == 2957


def test_parse_refuses_output_with_no_funnel():
    with pytest.raises(ValueError):
        harv.parse_funnel("error: registry locked\n")


def test_status_is_served_and_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("HARV_BIN", str(_tool(tmp_path, REAL)))
    harv._cache.update(at=0.0, body=None)
    body = harv.harv_status(now=1000.0)
    assert body["available"] is True and body["evidence"] == 2957
    _tool(tmp_path, "boom", rc=3)
    assert harv.harv_status(now=1010.0) is body  # inside CACHE_S: not re-run
    again = harv.harv_status(now=1100.0)
    assert again["available"] is False and "stages" not in again


def test_missing_binary_is_unavailable_not_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("HARV_BIN", str(tmp_path / "nope"))
    harv._cache.update(at=0.0, body=None)
    body = harv.harv_status(now=5.0)
    assert body["available"] is False and "harv" in body["error"]
    env, status = routes.harv_envelope()
    assert status == 200 and json.dumps(env)


def test_garbage_output_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("HARV_BIN", str(_tool(tmp_path, "hello")))
    harv._cache.update(at=0.0, body=None)
    body = harv.harv_status(now=9.0)
    assert body["available"] is False and "no funnel rows" in body["error"]
