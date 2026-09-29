"""fleetview_backend.greenlane: what /fleet shows of the lane, and that an unreadable lane is
reported as unavailable with its reason, never as green."""

import json

from fleetview_backend import greenlane, routes


def test_status_is_served_and_cached(monkeypatch, tmp_path):
    tool = tmp_path / "bin" / "idp-greenlane"
    tool.parent.mkdir()
    payload = {
        "invariants": {"main_green": True, "open_prs_not_raised_by_engine": 0},
        "open_prs": [],
    }
    tool.write_text(
        "#!/usr/bin/env python3\nimport json\nprint(json.dumps(%r))\n" % payload
    )
    monkeypatch.setenv("ESTATE_IDP_ROOT", str(tmp_path))
    greenlane._cache.update(at=0.0, body=None)
    body = greenlane.greenlane_status(now=1000.0)
    assert body["available"] is True
    assert body["invariants"]["main_green"] is True
    tool.write_text("#!/usr/bin/env python3\nraise SystemExit(3)\n")
    assert greenlane.greenlane_status(now=1010.0) is body  # inside CACHE_S: not re-read
    again = greenlane.greenlane_status(now=1100.0)
    assert again["available"] is False and "rc=3" in again["error"]


def test_missing_tool_is_unavailable_not_green(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_IDP_ROOT", str(tmp_path))
    greenlane._cache.update(at=0.0, body=None)
    body = greenlane.greenlane_status(now=5.0)
    assert body["available"] is False
    assert "idp-greenlane" in body["error"]
    env, status = routes.greenlane_envelope()
    assert status == 200 and json.dumps(env)
