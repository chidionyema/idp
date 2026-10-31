"""fleetview_backend.topology: one snapshot for /fleet and the face, with the voids and no invented packets."""

from fleetview_backend import routes, topology


def test_snapshot_carries_the_model_the_voids_and_an_honest_live_part():
    s = topology.topology_snapshot()
    assert s["available"] and s["problems"] == []
    assert {e["source"] for e in s["edges"]} >= {"lane", "verified", "integrated"}
    assert s["abyss"]["count"] == len(s["voids"]) and s["abyss"]["verdict"] in (
        "ABYSS",
        "NO_ABYSS",
    )
    assert s["live"]["available"] is False and "simulated" in s["live"]["error"]


def test_every_void_edge_is_flagged_on_the_edge_itself():
    s = topology.topology_snapshot()
    flagged = {"%s->%s" % (e["source"], e["target"]) for e in s["edges"] if e["void"]}
    named = {v["edge"] for v in s["voids"] if "->" in v["edge"]}
    assert named <= flagged


def test_route_serves_the_snapshot_and_503s_when_the_model_is_missing(
    tmp_path, monkeypatch
):
    body, status = routes.topology_envelope()
    assert status == 200 and body["available"]
    monkeypatch.setenv("ESTATE_REPO_ROOT", str(tmp_path))
    body, status = routes.topology_envelope()
    assert (
        status == 503 and body["available"] is False and "unreadable" in body["error"]
    )
